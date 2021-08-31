pyBOM
=====

A Python program for flattening a layered bill-of-material (BOM) based on Excel
files. Part quantities are combined and a total quantity or
minimum-required-package-to-buy amount is calculated, in addition to extended
costs. A tree structure of the BOM hierarchy can also be created and converted
to DOT syntax for further graphics generation.

Motivation
----------

The main problem solved is to combine identical parts from various
sub-assemblies and locations in your product BOM. Additionally, it is to be used
with Excel since Excel is common, easy, and does not require a separate program
or server to run. Flattening tells you the total QTY of a part when it may be
used in many sub-assemblies and levels in your product structure. This is
necessary to calculate the total QTY of a part and therefore determine the
mininum packages of the product to buy, since many parts come in packs greater
than QTY 1.

Structure
---------

BOMs are created by storing parts and assemblies in Excel files.

In a separate directory, put an Excel file named *Parts list.xlsx* to serve as
the master parts list \"database\". Then, each additional assembly is described
by a separate .xlsx file. Thus you might have:

    my_project/
       Parts list.xlsx     <-- master parts list
       SKA-100.xlsx        <-- top level/root assembly
       TR-01.xlsx          <-- subassembly
       WH-01.xlsx          <-- subassembly

Root and sub-assemblies are inferred from item number relationships and do not
have to be explicitly identified.

*Parts list.xlsx* serves as the single point of reference for part information.
For example, it may have the following:

| PN        | Name        | Description         | Cost    | Item  | Supplier         | Supplier PN   | Pkg QTY   | Pkg Price  |
| --------- | ----------- | ------------------- | ------- | ----- | ---------------- | ------------- | --------- | ---------- |
| SK1001-01 | Bearing     | Wheel bearing       |         | part  | XYZ Bearing Co.  | 74295-942     | 1         | 2.99       |
| SK1002-01 | Board       | Standard type       | 13.42   | part  |                  |               |           |            |
| SK1003-01 | Truck half  | Truck fixed         |         | part  | Skatr Dude Inc.  | TR1-A         | 1         | 9.87       |
| SK1004-01 | Truck half  | Truck movable       |         | part  | Skatr Dude Inc.  | TR1-B         | 1         | 12.25      |
| SK1005-01 | Truck screw | 1/4-20 SHCS         |         | part  | Bolts R Us       | 92220A        | 50        | 12.86      |
| SK1006-01 | Wheel       | Hard clear urethane |         | part  | Skatr Dude Inc.  | WHL-PRX       | 4         | 9.87       |
| SK1007-01 | Nut         | 1/4-20 Hex nut      |         | part  | Bolts R Us       | 95479A        | 50        | 4.88       |

For each assembly, all that is required is the part identification number and
quantity which correspond to the following fields:

- PN
- QTY

Example:

| PN          | QTY   |
| ----------- | ----- |
| SK1003-01   | 1     |
| SK1004-01   | 1     |

Certain fields are used in calculating totals, such as in `BOM.BOM.summary`,
which are:

`Pkg QTY`
  : The quantity of items in a specific supplier SKU (i.e. a bag of 100 screws)

`Pkg Price`
  : The cost of a specific supplier SKU                                        

Usage
-----

After installing, (i.e. `pip install .`), import:

`import pyBOM`

Create a folder and create the necessary files (parts list and assemblies as
individual Excel files (the file name becomes the assembly item number by
default). Then, in a script call class method `from_folder` to instantiate the
BOM structure and return the top-level bill-of-material:

```python
import pyBOM
bom = pyBOM.BOM.from_folder('Example')
```

Then, call methods or properties on `BOM` objects to obtain derived information:

`BOM.parts`
  : Get a list of all direct-child parts

  ```
  >>> print(bom.parts)
  [Part SK1002-01, Part SK1005-01, Part SK1007-01]
  ```

`BOM.assemblies`
  : Get a list of all direct-child assemblies

  ```
  >>> print(bom.assemblies)
  [WH-01, TR-01]
  ```

`BOM.quantities`
  : Get the quantity of each direct-child part in the BOM

  ```
  >>> print(bom.quantities)
  {Part SK1002-01: 1, Part SK1005-01: 1, Part SK1007-01: 3, Part SK1006-01: 1,
  Part SK1001-01: 1, Part SK1003-01: 1, Part SK1004-01: 1}
  ```

`BOM.aggregate`
  : Get the aggregated quantity of each part/assembly from the current
  BOM level down

  ```
  >>> print(bom.aggregate)
  {Part SK1002-01: 1, Part SK1005-01: 8, Part SK1007-01: 14, Part SK1006-01: 8,
  Part SK1001-01: 4, Part SK1003-01: 2, Part SK1004-01: 2}
  ```

`BOM.summary`
  : Get a summary in the form of a DataFrame containing the master parts
  list with each item's aggregated quantity and the required packages
  to buy if the `Pkg QTY` field is not 1.

  ```
  >>> print(bom.summary)
          PN         Name          Description  ...  Total QTY Purchase QTY Subtotal
0  SK1001-01      Bearing        Wheel bearing  ...          4            4    11.96
1  SK1002-01        Board        Standard type  ...          1            1    13.42
2  SK1003-01   Truck half          Truck fixed  ...          2            2    19.74
3  SK1004-01   Truck half        Truck movable  ...          2            2    24.50
4  SK1005-01  Truck screw          1/4-20 SHCS  ...          8            1    12.86
5  SK1006-01        Wheel  Hard clear urethane  ...          8            2    19.74
6  SK1007-01          Nut       1/4-20 Hex nut  ...         14            1     4.88
  ```

`BOM.tree`
  : Return a string representation of the BOM tree hierarchy

  ```
  >>> print(bom.tree)
  SKA-100
  ├── Part SK1002-01    
  ├── WH-01
  │   ├── Part SK1006-01
  │   ├── Part SK1001-01
  │   └── Part SK1007-01
  ├── TR-01
  │   ├── Part SK1003-01
  │   ├── Part SK1004-01
  │   └── Part SK1007-01
  ├── Part SK1005-01
  └── Part SK1007-01
  ```

  Calling this on child assemblies shows the tree from that reference point:
  ```
  >>> sa = bom.assemblies[0]
  >>> sa
  WH-01
  >>> print(sa.tree)
  WH-01
  ├── Part SK1006-01
  ├── Part SK1001-01
  └── Part SK1007-01
  ```



### Command Line

Some quick functionality is extended to the command line via python module mode:


```
> python -m pyBOM FOLDER ACTION
```

Where `ACTION` is what to do and is just a property call on the resulting
top-level BOM:

```
> python -m pyBOM Example tree
SKA-100
├── Part SK1002-01
├── WH-01
│   ├── Part SK1006-01
│   ├── Part SK1001-01
│   └── Part SK1007-01
├── TR-01
│   ├── Part SK1003-01
│   ├── Part SK1004-01
│   └── Part SK1007-01
├── Part SK1005-01
└── Part SK1007-01
```

Dependencies
------------

- *pandas*
- *anytree*
