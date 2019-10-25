'''
Title:          Python Bill-of-Material Generator (BOM)

Author:         RSS

Description:    Builds a multi-level and flattened BOM based on elemental data stored in
                Excel files.

Usage:          From a terminal call this program with the folder containining
                your source files.

                $ python BOM.py build [OPTIONS] FOLDER_PATH

                Options:
                    --config TEXT  Specify an alternate configuration using "config.ini".
                    --outfn TEXT   Output filename stem.
                    --supplier     Create individual supplier BOMs
                    --plot         Create an ASCII representation of the BOM structure.
                    --help         Show this message and exit.

'''

import sys
import glob
import os
import configparser
import pandas as pd
import numpy as np
import click
from asciitree import LeftAligned


@click.group()
def cli():
    pass

# @click.command()
# @click.argument('folder_path',type=click.Path(exists=True))
# @click.argument('existing_num')
# @click.argument('new_num')
# def PNrename(existing_num,new_num):
#     ''' Rename a part number across all BOM files. '''
#     pass


def simplify_BOM(BOM_0):
    '''
    Combine duplicate Parts in a BOM and sum total QTY's.
    Calculate a mininum-required-package-to-buy parameter.
    '''
    BOM_sum = BOM_0[['PartNo','QTY']]
    BOM_sum = BOM_sum.groupby(['PartNo']).sum()

    BOM2 = BOM_0.drop(['QTY','Parent Assy'],axis=1).drop_duplicates()

    BOM = BOM_sum.join(BOM2.set_index('PartNo'))
    BOM['Pkg Req'] = np.ceil(BOM.QTY/BOM['Pkg QTY'])
    BOM['Extended'] = BOM['Pkg Req']*BOM['Pkg Price']
    
    BOM = BOM.reset_index()
    BOM = BOM[['PartNo','Name','QTY','Pkg QTY','Pkg Price','Pkg Req','Extended','Supplier','Supplier PartNo']]
    BOM = BOM.set_index(pd.RangeIndex(1,len(BOM)+1))
    return BOM


@click.command()
@click.argument('folder_path', type=click.Path(exists=True))
@click.option('--config', default='DEFAULT', help='Specify an alternate configuration using "config.ini".')
@click.option('--outfn', default='BOM_flat', help='Output filename stem.')
@click.option('--supplier', default=False, is_flag=True, help='Create individual supplier BOMs')
@click.option('--plot', default=False, is_flag=True, help='Create an ASCII representation of the BOM structure.')
def build(folder_path, config, outfn, supplier, plot):
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
    files_names = list(map(lambda x: x.replace(folder_path+'\\',''), files))
    
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

    # ASCII tree container
    tree = {}

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
    BOM_flat, i, tree = loop(BOM_flat,BOM)
    BOM_flat_grouped = simplify_BOM(BOM_flat)

    tree = { BOM_file_name: tree }

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

    # Create ASCII hierarchy plot
    if plot:
        LA = LeftAligned()
        ASCII_tree = LA(tree)
        with open(os.path.join(out_dir,'ASCII Tree.txt'),'w') as f:
            f.write(ASCII_tree)



cli.add_command(build)
# cli.add_command(PNrename)


if __name__ == '__main__':
    cli()