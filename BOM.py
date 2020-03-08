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

From a terminal call this program with the folder containing your source files.

    $ python BOM.py [OPTIONS] FOLDER_PATH

    Options:
        --config TEXT  Specify an alternate configuration using "config.ini".
        --outfn TEXT   Output filename stem.
        --supplier     Create individual supplier BOMs
        --tree         Create an ASCII representation of the BOM structure.
        --help         Show this message and exit.

'''

import sys
import glob
import os
import configparser
import pandas as pd
from numpy import ceil
import click
from asciitree import LeftAligned



def simplify_BOM(BOM_0):
    '''
    Combine duplicate Parts in a BOM and sum total QTY's.
    Calculate a mininum-required-package-to-buy parameter.
    '''
    BOM_sum = BOM_0[['PartNo','QTY']]
    BOM_sum = BOM_sum.groupby(['PartNo']).sum()

    BOM2 = BOM_0.drop(['QTY','Parent Assy'],axis=1).drop_duplicates()
    BOM = BOM_sum.join(BOM2.set_index('PartNo'))

    # calculate derived quantities
    BOM['Pkg Req'] = ceil(BOM.QTY/BOM['Pkg QTY'].astype('float'))
    BOM['Extended'] = BOM['Pkg Req']*BOM['Pkg Price']
    
    # reset numerical 'Item' numbering
    BOM = BOM.reset_index()
    BOM = BOM[['PartNo','Name','QTY','Pkg QTY','Pkg Price','Pkg Req','Extended','Supplier','Supplier PartNo']]
    BOM = BOM.set_index(pd.RangeIndex(1,len(BOM)+1))
    return BOM


@click.command()
@click.argument('folder_path', type=click.Path(exists=True))
@click.option('--config', default='DEFAULT', help='Specify an alternate configuration using "config.ini".')
@click.option('--outfn', default='BOM_flat', help='Output filename stem.')
@click.option('--supplier', default=False, is_flag=True, help='Create individual supplier BOMs')
@click.option('--tree', default=False, is_flag=True, help='Create an ASCII representation of the BOM structure.')
def build(folder_path, config, outfn, supplier, tree):
    '''
    Build a flat BOM from multi-level Excel BOM files.

    FOLDER_PATH is the path to a folder where the BOM files are stored.

    .xlsx format is used.
    '''
    # Read configuration
    Config = configparser.ConfigParser(defaults={'PARTS_DB':'Parts.xlsx',
                                                 'TOP_LEVEL_ASSY':'BOM.xlsx'})
    Config.read(os.path.join(folder_path,'config.ini'))
    TOP_LEVEL_BOM = Config.get(config,'TOP_LEVEL_ASSY')
    PARTS_DB = Config.get(config,'PARTS_DB')
    
    # Get files
    files = glob.glob(folder_path+'\\*.xlsx')
    files = list(filter(lambda x: '\\~' not in x, files))
    files_names = list(map(lambda x: os.path.split(x)[-1], files))
    
    # filenames
    parts_file = list(filter(lambda x: PARTS_DB in x, files))[0]
    BOM_file = list(filter(lambda x: TOP_LEVEL_BOM in x, files))[0]
    BOM_file_name = os.path.split(BOM_file)[-1].replace('.xlsx','')

    files.pop(files.index(parts_file))
    files.pop(files.index(BOM_file))

    # Check that a top level BOM and a parts database are present
    for each in [TOP_LEVEL_BOM, PARTS_DB]:
        if each not in files_names:
            print('{} not found. Exiting.'.format(each))
            return

    # load in the parts list to a pandas dataframe
    Parts = pd.read_excel(parts_file,index_col=0)   # set the index to PartNo
    BOM = pd.read_excel(BOM_file)

    # open a DataFrame to write the output BOM to
    output_columns = ['PartNo', 'Name', 'QTY', 'Parent Assy', 'Pkg Price', 'Pkg QTY', 'Supplier', 'Supplier PartNo']
    BOM_flat = pd.DataFrame(columns=output_columns)

    # check that the required columns are there
    #
    # the program needs PartNo, Pkg Price, Pkg QTY, and Supplier in the Parts Database
    # and PartNo and QTY in each of the BOM files
    req_part_labels = {'PartNo','Pkg Price','Supplier','Pkg QTY'}
    Parts_labels = set(Parts.columns)
    if Parts.index.name == 'PartNo':
        Parts_labels.add('PartNo')
    Parts_labels_net = req_part_labels - Parts_labels
    if Parts_labels_net:
        print('Additional columns needed in Parts database: {}'.format(Parts_labels_net))
        return

    file_labels = {'PartNo','QTY'}
    for file in [*files,BOM_file]:
        columns = set(pd.read_excel(file).columns)
        net_cols = file_labels - columns
        if net_cols:
            print('File {} needs additional columns: {}'.format(file,net_cols))
            return

    # Reading loop function
    def loop(df, BOM=None, BOM_QTY=1, i=1, fn=BOM_file_name):
        tree_seg = {}
        for index,row in BOM.iterrows():
            part_no = row.PartNo

            try:                      # try part lookup first
                part = Parts.loc[part_no]
                QTY = row.QTY * BOM_QTY
                df.loc[i] = [ part_no, part.Name, QTY, fn, part['Pkg Price'], part['Pkg QTY'], part.Supplier, part['Supplier PartNo'] ]
                i+=1
                tree_seg.update({ str(part_no).ljust(26): {} })
                
            except KeyError:          # then it is a subassembly not a part
                try:
                    sub_assem_file = list(filter(lambda x: part_no in x, files))[0]
                except IndexError:
                    print('\nNo corresponding part or subassembly found for item "{}". Skipping to next item.'.format(part_no))
                    continue
                else:
                    sa_fn = os.path.split(sub_assem_file)[-1]              # get subassembly name
                    sa = pd.read_excel(sub_assem_file)                     # read in subassembly
                    df, i, tree_seg_r = loop(df, sa, row.QTY, i, sa_fn)    # call loop() again
                    tree_seg = { **tree_seg, **{ str(sa_fn).replace('.xlsx',''): tree_seg_r } }

        return df, i, tree_seg
    
    # Call loop function and generate flat BOMs
    BOM_flat, i, tree_dict = loop(BOM_flat,BOM)
    BOM_flat_grouped = simplify_BOM(BOM_flat)

    tree_dict = { BOM_file_name: tree_dict }

    # Save out BOMs
    out_dir = os.path.join(folder_path,'flattened')
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)
    BOM_flat.to_excel(os.path.join(out_dir,'{}.xlsx'.format(outfn)))
    BOM_flat_grouped.to_excel(os.path.join(out_dir,'{}-grouped.xlsx'.format(outfn)))

    # Optionally create supplier-specific BOM's
    if supplier:
        suppliers = BOM_flat_grouped['Supplier'].drop_duplicates()
        for supplier in suppliers:
            BOM_flat_grouped.query('Supplier == @supplier').to_excel(os.path.join(out_dir,'{}-{}.xlsx'.format(outfn,supplier)))

    # Create ASCII hierarchy tree plot
    if tree:
        LA = LeftAligned()
        ASCII_tree = LA(tree_dict)
        with open(os.path.join(out_dir,'ASCII Tree.txt'),'w') as f:
            f.write(ASCII_tree)




if __name__ == '__main__':
    build()