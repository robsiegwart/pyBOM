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


def fn_base(arg):
    '''
    Return the part of a filename without the file extension. ::

        Foo_12.34.xlsx   =>   Foo_12.34

    :param arg:     String or list of strings to remove extension.
    :return:        String or list of strings
    '''
    if isinstance(arg, list):
        return [ fn_base(item) for item in arg ]
    return '.'.join(arg.split('.')[:-1])


class BOMObjectType:
    def __str__(self):
        return f'{self.name} item'


class PartType(BOMObjectType):
    name = 'Part'


class AssemblyType(BOMObjectType):
    name = 'Assembly'

    
class DrawingType(BOMObjectType):
    name = 'Drawing'


class DocumentType(BOMObjectType):
    name = 'Document'


class Item(NodeMixin):
    '''
    A terminal object in a bill-of-material. Represents a part, drawing, or
    document (not an assembly). Does not have child objects and must contain a
    parent.

    :param PN:              Part or item number (string or number)
    :param BOM parent:      BOM containing this item
    :param ``BOMObjectType``    obj_type:        A type descriptor
    :param kwargs:          Any other fields
    '''
    children = None

    def __init__(self, PN, parent=None, obj_type=None, **kwargs):
        self.PN = PN
        self.parent = parent
        self.obj_type = obj_type
    
        self.kwargs ={}
        for k,v in kwargs.items():
            try:
                setattr(self, k, v)
            except AttributeError:
                self.kwargs.update({k:v})
    
    def __repr__(self):
        return self.PN
    
    __str__ = __repr__


class BOM(NodeMixin):
    '''
    A bill-of-material. Can be a parent of another BOM or have several child
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
    :param BOM parts_list:      Parts list BOM object
    :param BOM root_bom:        an input root BOM
    :param str type:            type of object (e.g. Part, Assembly, Docu)
    '''
    def __init__(self, data=None, name=None, parent=None, children=None,
                 root_bom=None, parts_list=None, type=None):
        self.data = data
        self.name = name
        self.parent = parent
        self.children = children or []
        self.parts_list = parts_list
        self.root_bom = root_bom

    @classmethod
    def from_filename(cls, filename, name=None):
        data = pd.read_excel(filename)
        return cls(data=data, name=name or fn_base(os.path.basename(filename)))
    
    @property
    def fields(self):
        return list(self.data.columns)
    
    # @property
    # def parts(self):
    #     return list(self.data['PN'])

    # @property
    # def assemblies(self):
    #     pass
    
    # @property
    # def flat(self):
    #     '''
    #     Return a flattened version of the BOM, with each sub-assembly contained
    #     in it expanded.
    #     '''
    #     for assem in self.children:
    #         print(assem)
    
    @property
    def tree(self):
        return str(RenderTree(self))
    
    @classmethod
    def from_folder(cls, directory, parts_file='Parts list'):
        '''
        Generate a hierarchial BOM from a folder containing .xlsx files. The
        xlsx file with the same name as parameter ``parts_file`` is taken as the
        master parts list. All others are treated as sub-assemblies. The root
        BOM is discovered (there should only be one or an exception is raised)
        via inter-BOM references and each non-root BOM is assigned children and
        a parent. Each item not an assembly is converted to an ``Item`` object.

        :param str directory:   The source directory containing BOM files.
        :param str parts_file:  The name of the master parts list Excel file.
                                Default is ``Parts list.xlsx``.
        :return BOM:            Returns a top-level BOM with all sub-assemblies
                                as child BOMs.
        '''
        files = [ os.path.split(fn)[-1] for fn in glob.glob(os.path.join(directory, '*.xlsx')) ]
        assembly_files = [ x for x in files if fn_base(x).lower() != parts_file.lower() ]

        assemblies = [ BOM.from_filename(os.path.join(directory, file)) for file in assembly_files ]
        parts_bom = BOM.from_filename(os.path.join(directory, f'{parts_file}.xlsx'))
        
        # Assign parent/child relationships
        assembly_names = fn_base(assembly_files)
        for bom in assemblies:
            children = []
            for i,item in bom.data.iterrows():
                if item.PN in assembly_names:
                    boms_ = [ bom for bom in assemblies if bom.name == item.PN]
                    if len(boms_) > 1:
                        raise Exception('BOM\'s should have unique names')
                    sub_bom = boms_[0]
                    sub_bom.parent = bom
                    children.append(sub_bom)
                else:
                    children.append(Item(**{**item.to_dict(), **{'parent': bom}}))
            bom.children = children
        
        # Find root
        count = 0
        root = [ bom for bom in assemblies if not bom.parent ]
        if len(root) > 1:
            raise Exception('There should not be multiple root BOMs')
        
        return root[0]
            
    def __repr__(self):
        return self.name if self.name else f'BOM with {len(self.data)} items'
    
    __str__ = __repr__