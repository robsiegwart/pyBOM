# MIT License
# 
# Copyright (c) 2020 Rob Siegwart
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
Build a multi-level and flattened BOM based on elemental data stored in Excel
files.
'''

import sys
import glob
import os
import pandas as pd
from numpy import ceil
import click
from anytree import NodeMixin, RenderTree


class Item(NodeMixin):
    '''
    A row in a BOM. Represents a part, subassembly, or document/drawing.
    '''
    def __init__(self, PN, parent=None, **kwargs):
        self.PN = PN
        self.parent = parent
        self.children = []
        self.kwargs ={}
        for k,v in kwargs.items():
            try:
                setattr(self, k, v)
            except AttributeError:
                self.kwargs.update({k:v})
    
    def __repr__(self):
        return self.PN
    
    __str__ = __repr__


class BOMProject:
    '''
    The main entry point for assembling BOMs and getting derived information.

    All Excel files in source directory whose name is not in ``MASTER_FILE`` are
    treated as sub-assemblies.

    :param str directory:   The source directory containing BOM files.
    '''
    MASTER_FILE = ['parts list', 'parts_list', 'master']
    """These are the names which identify a file as being a master parts list
    file"""

    def __init__(self, directory):
        # String name variables
        self.directory = directory
        self.xlsx_files = [ os.path.split(fn)[-1] for fn in glob.glob(os.path.join(directory, '*.xlsx')) ]
        self.assembly_files = list(filter(lambda x: self.fn_base(x).lower() not in self.MASTER_FILE, self.xlsx_files))
        self.master_file = list(filter(lambda x: self.fn_base(x).lower() in self.MASTER_FILE, self.xlsx_files))[0]

        # BOM object variables
        self.assemblies = [ BOM.from_filename(os.path.join(self.directory, file), name=self.fn_base(file)) for file in self.assembly_files ]
        self.master = BOM.from_filename(os.path.join(self.directory, self.master_file), name=self.fn_base(self.master_file))
        
        self.root_BOM = None
        self.items = []
    
    @property
    def parts(self):
        return self.master.data['PN'].to_list()
    
    def fn_base(self, arg):
        '''
        Return the part of a filename without the file extension. ::

            Foo_12.34.xlsx   =>   Foo_12.34

        :param arg:     String or list of strings to remove extension.
        :return:        String or list of strings
        '''
        if isinstance(arg, list):
            return [ self.fn_base(item) for item in arg ]
        return '.'.join(arg.split('.')[:-1])
    
    def get_assembly_by_name(self, name):
        try:
            return [ bom for bom in self.assemblies if bom.name == name][0]
        except TypeError:
            return None

    def generate_structure(self):
        assem_names = self.fn_base(self.assembly_files)
        for bom in self.assemblies:
            for i,item in bom.data.iterrows():
                if item.PN in assem_names:
                    sub_bom = self.get_assembly_by_name(item.PN)
                    sub_bom.parent = bom
                else:
                    self.items.append(Item(**{**item.to_dict(), **{'parent': bom}}))
                
    def print_tree(self):
        self.generate_structure()
        count = 0
        for bom in self.assemblies:
            if not bom.parent:
                if count > 1:
                    raise Exception('Multiple root BOMs found')
                count += 1
                self.root_BOM = bom

        print(RenderTree(self.root_BOM))
    

class BOM(NodeMixin):
    '''
    A Bill-of-material. Can be a parent of another BOM or have several child
    BOMs. At minimum there must be a "PN" column denoting the part name and a
    "QTY" column denoting the quantity of that part. Other columns maybe added
    and are passed through.

        PN        Description   QTY
        --------- ------------- -----
        17954-1   Wheel         2
        17954-2   Axle          1

    :param DataFrame data:      input BOM data
    :param str name:            optional BOM name
    :param BOM parent:          another ``BOM`` object which is the parent
                                assembly
    :param list children:       list of ``BOM`` objects which are sub-assemblies
    '''
    def __init__(self, data, name=None, parent=None, children=None):
        super().__init__()
        self.data = data
        self.name = name
        self.parent = parent
        self.children = children or []

    @classmethod
    def from_filename(cls, filename, **kwargs):
        data = pd.read_excel(filename)
        return cls(data, **kwargs)

    @property
    def fields(self):
        return list(self.data.columns)
    
    @property
    def parts(self):
        return list(self.data['PN'])

    def __repr__(self):
        return self.name if self.name else f'BOM with {len(self.data)} items'
    
    __str__ = __repr__