# MIT License
# 
# Copyright (c) 2023 Rob Siegwart
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
Build and query multi-level and flattened BOMs based on elemental data stored in
Microsoft Excel files.
'''

import glob
import os
from collections import Counter
from collections.abc import Set
from math import ceil, nan
import pandas as pd
from anytree import NodeMixin, SymlinkNodeMixin, RenderTree
from anytree.exporter import DotExporter


def fn_base(arg):
    '''
    Return the part of a filename without the file extension. ::

        Foo_12.34.xlsx   =>  Foo_12.34

    :param arg:     String or list of strings to remove extension.
    :return:        String or list of strings
    '''
    if isinstance(arg, list):
        return [ fn_base(item) for item in arg ]
    return '.'.join(arg.split('.')[:-1])


class BaseItem:
    '''
    Base class for :class:`~BOM.Item` and :class:`~BOM.ItemLink`. 
    '''
    children = []

    def __init__(self, PN, parent=None, item_type=None, **kwargs):
        self.PN = PN
        self.parent = parent
        self.item_type = item_type
    
        self.kwargs =kwargs
        for k,v in kwargs.items():
            try:
                setattr(self,k,v)
            except AttributeError:
                continue
        
    @property
    def series(self):
        cols = ['PN','item_type','parent'] + list(self.kwargs.keys())
        return pd.Series({k:getattr(self,k,None) for k in cols})
    
    @property
    def name(self):
        return self.PN
    
    def __repr__(self):
        name = self.item_type.capitalize() if self.item_type else 'Item'
        return f'{name} {self.PN}'
    
    __str__ = __repr__


class Item(BaseItem, NodeMixin):
    '''
    A BOM item object. Represents a terminal object in a bill-of-material which
    does not have children: everything except assembly such as a part, drawing,
    or document. Does not have child objects and must contain a parent.

    :param PN:              Part or item number (string or number)
    :param BOM parent:      BOM containing this item
    :param str item_type:   A type descriptor
    :param kwargs:          Any other fields'''
    pass


class ItemLink(BaseItem, SymlinkNodeMixin):
    '''
    A link to a BOM item object. Used when a BOM item is used in more than one
    assembly; each 'copy' of the item is of this type.

    :param NodeMixin target:    The target node object (anytree)
    '''
    def __init__(self, target):
        self.target = target


class BOM(Set, NodeMixin):
    '''
    A bill-of-material. Can be a child of another BOM or have several child
    BOMs. The only required columns in the input DataFrame are a "PN" column
    denoting the part name and a "QTY" column denoting the quantity of that
    item.

    :param DataFrame df:        input BOM data
    :param PN:                  BOM item number
    :param BOM parent:          another :class:`~BOM.BOM` object which is the
                                parent assembly
    :param list items:          list of :class:`~BOM.BOM` or :class:`~BOM.Item`
                                objects included in this BOM.
    :param str item_type:       type description of the object, one of ``part``,
                                ``assembly``, ``document`` 
    :param BOM parts_db:        BOM object representing the master parts list
    '''
    def __init__(self, df=None, PN=None, parent=None, items=None,
                 item_type=None, parts_db=None):
        self.df = df
        self.PN = PN
        self.parent = parent
        self.children = items or []
        self.item_type = item_type.lower() if item_type else None
        self.parts_db = parts_db

        if self.parts_db and self.df:
            self.init_parts()

    def __contains__(self, item):
        return item in self.children

    def __iter__(self):
        for item in self.children:
            yield item
    
    def __len__(self):
        return len(self.children)
    
    @property
    def parts(self):
        '''Return a list of the parts that are direct children to this BOM'''
        return [ item for item in self.children if item.item_type == 'part' ]
    
    @property
    def assemblies(self):
        '''Return a list of assemblies that are direct children to this BOM'''
        return [ item for item in self.children if item.item_type == 'assembly' ]
    
    @property
    def flat(self):
        '''
        Return a flattened version of the BOM with each sub-assembly contained
        in it expanded.
        '''
        items = self.parts
        for assem in self.assemblies:
            items += assem.flat
        return items

    def QTY(self, PN):
        '''
        Return the quantity in the current BOM context for a given item
        identified by its item number, ``PN``.
        '''
        try:
            return self.df.loc[self.df['PN']==PN, 'QTY'].iloc[0]
        except IndexError as e:
            print(e)
            return None

    @property
    def tree(self):
        '''
        Return a string representation of the complete BOM hierarchy from the
        current BOM down as a tree.

        :rtype: str
        '''
        return str(RenderTree(self))
    
    @property
    def dot(self):
        '''
        Return the BOM tree structure from :py:attr:`BOM.BOM.tree` in DOT graph
        format (Graphiz)

        :rtype: str
        '''
        return '\n'.join([line for line in DotExporter(self)])

    @property
    def aggregate(self):
        '''
        Return a :py:class:`dict` of ``Item: count`` pairs for the entire BOM
        tree below the current BOM. Each item's local QTY is multiplied by the
        QTY of its containing BOM assembly.

        :rtype: dict
        '''
        parts = Counter()
        for p in self.parts:
            parts.update({p.PN: self.QTY(p.PN)})
        
        for bom in self.assemblies:
            for k, v in bom.aggregate.items():
                parts.update({k: v*self.QTY(bom.PN)})
        return { self.parts_db.get(k):v for k,v in parts.items() } if self.parts_db else parts
    
    @property
    def summary(self):
        '''
        Return a summary table with aggregated quantities alongside part table
        information.

        :rtype: DataFrame
        '''
        def packages_to_buy(row):
            if 'Pkg QTY' not in row or pd.isnull(row['Pkg QTY']):
                return row['Total QTY']
            try:
                packages_to_buy_ = ceil(row['Total QTY']/row['Pkg QTY'])
            except ValueError:
                packages_to_buy_ = 0
            return packages_to_buy_
        
        def subtotal(row):
            if 'Pkg Price' in row and not pd.isnull(row['Pkg Price']):
                cost_col = 'Pkg Price'
            elif 'Cost' in row and not pd.isnull(row['Cost']):
                cost_col = 'Cost'
            else:
                return nan
            return row['Purchase QTY']*row[cost_col]


        counts = { k.PN:v for k,v in self.aggregate.items() }
        df = self.parts_db.df
        df['Total QTY'] = df.apply(lambda row: counts.get(row.PN), axis=1)
        df['Purchase QTY'] = df.apply(packages_to_buy, axis=1)
        df['Subtotal'] = df.apply(subtotal, axis=1)
        return df
        
    @property
    def name(self):
        return self.PN

    @classmethod
    def from_file(cls, filename, PN=None):
        '''
        Create an instance of :py:class:`BOM.BOM` based on an existing Excel
        file.

        :param str filename:    Name of source Excel file
        :param PN:              Item number, defaults to the filename with its
                                extension removed.
        :rtype:                 BOM
        '''
        data = pd.read_excel(filename)
        return cls(df=data, PN=PN or fn_base(os.path.basename(filename)))
    
    @classmethod
    def from_folder(cls, directory, parts_file_name='Parts list'):
        '''
        Generate a hierarchial BOM from a folder containing Excel (.xlsx) files.
        The Excel file with the same name as parameter ``parts_file_name`` is
        used as the master parts list. All others are treated as sub-assemblies.
        The root BOM is discovered (there should only be one or an exception is
        raised) via inter-BOM references and each non-root BOM is assigned
        children and a parent. Each item not an assembly is converted to an
        :class:`~BOM.Item` object.

        **Note:** Any files starting with an underscore are not included.

        :param str directory:       The source directory containing BOM files.
        :param str parts_file_name: The name of the master parts list Excel
                                    file.
                                    Default is ``Parts list.xlsx``.
        :return:                    Returns a top-level BOM with all
                                    sub-assemblies as child BOMs.
        :rtype:                     BOM
        '''
        files = [os.path.split(fn)[-1] for fn in glob.glob(os.path.join(directory, '*.xlsx')) if
                 not os.path.basename(fn).startswith('_') and not os.path.basename(fn).startswith('~')]
        """All valid Excel files in the directory"""
        
        assembly_files = [ x for x in files if fn_base(x).lower() != parts_file_name.lower() ]
        """Those files which are assumed to be assemblies"""

        assemblies = { fn_base(file):BOM.from_file(os.path.join(directory, file)) for file in assembly_files }
        """Instances of ``BOM`` for each assembly keyed with its PN"""
        
        parts_db = PartsDB.from_file(os.path.join(directory, f'{parts_file_name}.xlsx'))
        """Master parts database, ``PartsDB`` instance"""

        return cls.parse_parent_child(parts_db, assemblies)
    
    @classmethod
    def single_file(cls, filename):
        '''
        Build a structured BOM from a single Excel file, where the tabs of the
        document form the data, with the following convention:

        - the first tab is the parts list 'database'
        - all subsequent tabs are assemblies

        For each assembly the tab/sheet name is the assembly part number (PN).
        '''
        excelfile = pd.ExcelFile(filename)
        sheets = excelfile.sheet_names
        if not len(sheets) > 1:
            raise Exception('The Excel file in single file format must contain more than one tab.')
        parts_db = PartsDB(excelfile.parse(sheets[0]))
        assemblies = { sheet_:BOM(excelfile.parse(sheet_), PN=sheet_) for sheet_ in sheets[1:] }
        return cls.parse_parent_child(parts_db, assemblies)
    
    @staticmethod
    def parse_parent_child(parts_db, assemblies):
        '''
        Assign parent/child relationships between parts and assemblies.

        :param DataFrame parts_db:      The parts database
        :param dict assemblies:         A dictionary of assemblies in the form
                                        {PN: :py:class:`BOM.BOM`}
        '''
        for name,bom in assemblies.items():
            children = []
            for i,row in bom.df.iterrows():
                if row.PN in assemblies:                    # it is an assembly
                    sub_bom = assemblies.get(row.PN)
                    if sub_bom.parent:
                        sym_bom = ItemLink(target=sub_bom)
                        children.append(sym_bom)
                    else:
                        sub_bom.parent = bom
                        sub_bom.item_type = 'assembly'
                        children.append(sub_bom)
                else:                                       # it is a part
                    try:
                        part_ = parts_db.get(row.PN)
                    except IndexError:
                        print(f'Unable to find part "{row.PN}"')
                        continue
                    if part_.parent:                        # is a multi-use part and has already has been placed in an assembly
                        sym_part = ItemLink(target=part_)   # therefore make any new copies of this part symlink objects
                        children.append(sym_part)
                    else:
                        children.append(part_)
            bom.children = children

        # Find root
        root = [ bom for bom in assemblies.values() if bom.is_root ]
        if len(root) > 1:
            raise Exception('Singular root BOM not found.')
        if len(root) == 0:
            raise Exception('No root BOM found.')
        root = root[0]
        root.parts_db = parts_db
        return root
    
    def __repr__(self):
        return self.PN or f'BOM with {len(self.df)} items'
    
    __str__ = __repr__


class PartsDB:
    '''
    A container for the master parts list.
    
    :param DataFrame df:    Input data as a DataFrame
    '''
    def __init__(self, df):
        self.df = df
        self.parts = { row.PN:Item(**{**row.to_dict(), **{'item_type': 'part'}}) for i,row in df.iterrows() }
    
    @classmethod
    def from_file(cls, filename):
        '''Instantiate a new instance from a file'''
        data = pd.read_excel(filename)
        return cls(data)
    
    def get(self, PN):
        '''Retrieve an ``Item`` object from the database'''
        return self.parts.get(PN, None)
    
    @property
    def fields(self):
        '''List the database fields (columns)'''
        return list(self.df.columns)
    
    def prop(self, PN, prop):
        '''Return a property for specific part'''
        try:
            return self.df.loc[self.df['PN']==PN, prop].iloc[0]
        except IndexError as e:
            print(e)
            return None
    
    def __repr__(self):
        return f'Parts List with {len(self.parts)} parts'

    __str__ = __repr__
