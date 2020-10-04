'''
Run the program from the command line via python module mode.

> python -m BOM FOLDER ACTION

    FOLDER      the folder name containing Excel files
    ACTION      the property to call on the ``BOM`` object

'''

import sys
import argparse
from .BOM import BOM


parser = argparse.ArgumentParser(
    prog='python -m BOM',
    description='Parse a folder of Excel Bill-of-Materials.'
)

parser.add_argument(
    'folder',
    help='The name of the folder containing Excel BOM files.'
)

parser.add_argument(
    'action',
    help='What to do with the resulting BOM.',
    default='tree'
)

ns = parser.parse_args()

bom = BOM.from_folder(ns.folder)
print(getattr(bom,ns.action))