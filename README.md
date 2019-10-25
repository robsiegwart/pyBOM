# python-BOM

A Python program for flattening a layered bill-of-material (BOM) based on Excel files. Part quantities are combined and a minimum-required-package-to-buy amount is calculated, in addition to extended costs. An ASCII hierarchy tree can also optionally be created.

Output BOMs are placed in a subdirectory of your source folder called 'flattened' by default. Produced files in this folder include:
  - a full flat BOM (containing duplicate parts)
  - a grouped flat BOM (duplicate parts merged with QTY's summed)
  - (optional) an ASCII tree representation of the BOM structure, when the `--plot` flag is used
  - (optional) a separate BOM for each supplier, when the `--supplier` flag is used

## Motivation

The main problem solved is to combine identical parts from various sub-assemblies and locations in your product BOM. Additionally, it is to be used with Excel since Excel is common, easy, and does not require a separate program or server to run. Flattening tells you the total QTY of a part when it may be used in many sub-assemblies and levels in your product structure. This is necessary to calculate the total QTY of a part and therefore determine the mininum packages of the product to buy, since many parts come in packs greater than QTY 1.

## Structure

BOMs are created by storing parts and assemblies in Excel files.

In a directory, put an Excel file named *BOM.xlsx* to serve as the top-level assembly. Then, parts and subassemblies are referenced from within *BOM.xlsx*. A master list of parts is contained in *Parts.xlsx*, for which all referenced parts must refer to. The default names of *BOM.xlsx* and *Parts.xlsx* can be changed with a config.ini file.

### Example:

```
Example\
 +-- BOM.xlsx             <- top level BOM
 +-- Parts.xlsx           <- Database of parts
 +-- SubAssem1.xlsx       <- Subassembly
```

*Parts.xlsx* serves as the single point of reference for part information, with the following data:

| PartNo     | Name       | Description       | Supplier         | Supplier PartNo     | Pkg QTY    | Pkg Price   |
| ---------- | ---------- | ----------------- | ---------------- | ------------------- | ---------- | ----------- |
| Scr1       | Screw      | 1/4-20 SHCS       | McMaster-Carr    | 92220A186           | 50         | 12.86       |
| Nut1       | Nut        | 1/4-20 Hex nut    | McMaster-Carr    | 95479A111           | 50         | 4.88        |
| Brack1     | Bracket1   | Bracket           | Fabricator       | BR0234              | 1          | 8.00        |
| Brack2     | Bracket2   | Bracket           | Fabricator       | BR4234              | 1          | 14.00       |


In *BOM.xlsx* there are parts/sub-assemblies, and their quantities:

| Item     | PartNo       | QTY     |
| -------- | ------------ | ------- |
| 1        | Scr1         | 4       |
| 2        | Nut1         | 4       |
| 3        | Brack1       | 1       |
| 4        | SubAssem1    | 1       |

When parsing through the BOM files, the program first looks in the *Parts.xlsx* file treating it as a part, and if there is no match then it looks in the list of files assuming it is a sub-assembly. If there is no match in either it prints a message to the console and and skips to the next part.

*SubAssem1.xlsx* also references parts from the parts list:

| Item    | PartNo    | QTY      |
| ------- | --------- | -------- |
| 1       | Brack2    | 1        |
| 2       | Scr1      | 8        |
| 3       | Nut1      | 8        |


With this BOM structure we obtain the following:

```
$ python BOM.py build Example --plot --supplier
```

```
Example\
 +-- BOM.xlsx
 +-- Parts.xlsx
 +-- SubAssem1.xlsx
 +-- flattened\            <-- Output directory
     +-- ASCII Tree.txt
     +-- BOM_flat.xlsx
     +-- BOM_flat-Fabricator.xlsx
     +-- BOM_flat-grouped.xlsx
     +-- BOM_flat-McMaster-Carr.xlsx
```

#### BOM_flat.xlsx

|   | PartNo | Name      | QTY  | Parent Assy     | Pkg Price   | Pkg QTY  | Supplier         | Supplier PartNo |
| - | ------ | --------- | ---- | --------------- | ----------- | -------- | ---------------- | --------------- |
| 1 | Scr1   | Screw     | 4    | BOM             | 12.86       | 50       |  McMaster-Carr   | 92220A186       |
| 2 | Nut1   | Nut       | 4    | BOM             | 4.88        | 50       |  McMaster-Carr   | 95479A111       |
| 3 | Brack1 | Bracket1  | 1    | BOM             | 8           | 1        |  Fabricator      | BR0234          |
| 4 | Brack2 | Bracket2  | 1    | SubAssem1.xlsx  | 14          | 1        |  Fabricator      | BR4234          |
| 5 | Scr1   | Screw     | 8    | SubAssem1.xlsx  | 12.86       | 50       |  McMaster-Carr   | 92220A186       |
| 6 | Nut1   | Nut       | 8    | SubAssem1.xlsx  | 4.88        | 50       |  McMaster-Carr   | 95479A111       |


#### BOM_flat-grouped.xlsx

|    | PartNo  | Name      | QTY   | Pkg QTY   | Pkg Price   | Pkg Req   | Extended   | Supplier        | Supplier PartNo   |
| -- | ------- | --------- | ----- | --------- | ----------- | --------- | ---------- | --------------- | ----------------- |
| 1  | Brack1  | Bracket1  | 1     | 1         | 8           | 1         | 8          | Fabricator      | BR0234            |
| 2  | Brack2  | Bracket2  | 1     | 1         | 14          | 1         | 14         | Fabricator      | BR4234            |
| 3  | Nut1    | Nut       | 12    | 50        | 4.88        | 1         | 4.88       | McMaster-Carr   | 95479A111         |
| 4  | Scr1    | Screw     | 12    | 50        | 12.86       | 1         | 12.86      | McMaster-Carr   | 92220A186         |


#### BOM_flat-Fabricator.xlsx

|    | PartNo   | Name       | QTY  | Pkg QTY  | Pkg Price   | Pkg Req   | Extended   | Supplier      | Supplier PartNo  |
| -- | -------- | ---------- | ---- | -------- | ----------- | --------- | ---------- | ------------- | ---------------- |
| 1  | Brack1   | Bracket1   | 1    | 1        | 8           | 1         | 8          | Fabricator    | BR0234           |
| 2  | Brack2   | Bracket2   | 1    | 1        | 14          | 1         | 14         | Fabricator    | BR4234           |


#### BOM_flat-McMaster-Carr.xlsx

|    | PartNo   | Name   | QTY  | Pkg QTY   | Pkg Price   | Pkg Req   | Extended   | Supplier Supplier   | PartNo       |
| -- | -------- | ------ | ---- | --------- | ----------- | --------- | ---------- | ------------------- | ------------ |
| 3  | Nut1     | Nut    | 12   | 50        | 4.88        | 1         | 4.88       | McMaster-Carr       | 95479A111    |
| 4  | Scr1     | Screw  | 12   | 50        | 12.86       | 1         | 12.86      | McMaster-Carr       | 92220A186    |


#### ASCII Tree.txt
```
BOM
 +-- Scr1                      
 +-- Nut1                      
 +-- Brack1                    
 +-- SubAssem1
     +-- Brack2                    
     +-- Scr1                      
     +-- Nut1
```


## Usage
```
$ python BOM.py build [OPTIONS] FOLDER_PATH

Options:
  --config TEXT  Specify an alternate configuration using "config.ini".
  --outfn TEXT   Output filename stem.
  --supplier     Create individual supplier BOMs
  --plot         Create an ASCII representation of the BOM structure.
  --help         Show this message and exit.
```


## Requirements
The following Python packages are required:
 - pandas
 - numpy
 - click
 - asciitree


## config.ini
A *config.ini* file may be used to specify alternate names for the *Parts.xlsx* and *BOM.xlsx* files. Place in the source directory.
```
[DEFAULT]
PARTS_DB = Parts.xlsx              # Set the file which stores the parts
TOP_LEVEL_ASSY = BOM.xlsx          # Set the file which is the top level assembly
```