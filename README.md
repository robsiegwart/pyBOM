python-BOM
==========

A Python program for flattening a layered bill-of-material (BOM) based
on Excel files. Part quantities are combined and a total quantity or
minimum-required-package-to-buy amount is calculated, in addition to
extended costs. A tree structure of the BOM hierarchy can also bre
created and converted to DOT syntax for further graphics generation.

Motivation
----------

The main problem solved is to combine identical parts from various
sub-assemblies and locations in your product BOM. Additionally, it is to
be used with Excel since Excel is common, easy, and does not require a
separate program or server to run. Flattening tells you the total QTY of
a part when it may be used in many sub-assemblies and levels in your
product structure. This is necessary to calculate the total QTY of a
part and therefore determine the mininum packages of the product to buy,
since many parts come in packs greater than QTY 1.

Structure
---------

BOMs are created by storing parts and assemblies in Excel files.

In a separate directory, put an Excel file named *Parts list.xlsx* to
serve as the master parts list \"database\". Then, each additional
assembly is described by a separate .xlsx file. Thus you might have: :

    my_project/
       Parts list.xlsx     <-- master parts list
       SKA-100.xlsx        <-- top level/root assembly
       TR-01.xlsx          <-- subassembly
       WH-01.xlsx          <-- subassembly

Root and sub-assemblies are inferred from item number relationships and
do not have to be explicitly identified.

*Parts list.xlsx* serves as the single point of reference for part
information. For example, it may have the following:

+-------+-------+-------+-------+-------+-------+-------+-------+-------+
| PN    | Name  | D     | Cost  | Item  | Sup   | Sup   | Pkg   | Pkg   |
|       |       | escri |       |       | plier | plier | QTY   | Price |
|       |       | ption |       |       |       | PN    |       |       |
+=======+=======+=======+=======+=======+=======+=======+=======+=======+
| SK10  | Be    | Wheel | 13.42 | part  | XYZ   | 7429  | 1     | 2.99  |
| 01-01 | aring | be    |       | part  | Be    | 5-942 |       |       |
| SK10  | Board | aring |       | part  | aring |       | 1 1   | 9.87  |
| 02-01 | Truck | Sta   |       | part  | Co.   | TR1-A | 50 4  | 12.25 |
| SK10  | half  | ndard |       | part  |       | TR1-B | 50    | 12.86 |
| 03-01 | Truck | type  |       | part  | Skatr | 9     |       | 9.87  |
| SK10  | half  | Truck |       | part  | Dude  | 2220A |       | 4.88  |
| 04-01 | Truck | fixed |       |       | Inc.  | WH    |       |       |
| SK10  | screw | Truck |       |       | Skatr | L-PRX |       |       |
| 05-01 | Wheel | mo    |       |       | Dude  | 9     |       |       |
| SK10  | Nut   | vable |       |       | Inc.  | 5479A |       |       |
| 06-01 |       | 1     |       |       | Bolts |       |       |       |
| SK10  |       | /4-20 |       |       | R Us  |       |       |       |
| 07-01 |       | SHCS  |       |       | Skatr |       |       |       |
|       |       | Hard  |       |       | Dude  |       |       |       |
|       |       | clear |       |       | Inc.  |       |       |       |
|       |       | ure   |       |       | Bolts |       |       |       |
|       |       | thane |       |       | R Us  |       |       |       |
|       |       | 1     |       |       |       |       |       |       |
|       |       | /4-20 |       |       |       |       |       |       |
|       |       | Hex   |       |       |       |       |       |       |
|       |       | nut   |       |       |       |       |       |       |
+-------+-------+-------+-------+-------+-------+-------+-------+-------+

For each assembly, all that is required is the part identification
number and its quantity which correspond to the following fields:

-   PN
-   QTY

Example:

  PN          QTY
  ----------- -----
  SK1003-01   1
  SK1004-01   1

Certain fields are used in calculating totals, such as in
`BOM.BOM.summary`, which are:

  ------------- -----------------------------------------------------------------------------
  `Pkg QTY`     The quantity of items in a specific supplier SKU (i.e. a bag of 100 screws)
  `Pkg Price`   The cost of a specific supplier SKU
  ------------- -----------------------------------------------------------------------------

Usage
-----

Create a folder to contain your BOM files and create a parts list and
any assemblies as individual Excel files (the file name becomes the
assembly item number by default). Then, call class method
`BOM.BOM.from_folder()` with the path to your folder to instantiate and
build BOM objects.

Then, call methods or properties on the root BOM returned from
`BOM.BOM.from_folder()` to obtain derived information:

`BOM.BOM.parts`

:   Get a list of all direct-child parts

`BOM.BOM.assemblies`

:   Get a list of all direct-child assemblies

`BOM.BOM.quantities`

:   Get the quantity of each direct child in the BOM

`BOM.BOM.aggregate`

:   Get the aggregated quantity of each part/assembly from the current
    BOM level down

`BOM.BOM.summary`

:   Get a summary in the form of a DataFrame containing the master parts
    list with each item\'s aggregated quantity and the required packages
    to buy if the `Pkg QTY` field is not 1.

`BOM.BOM.tree`

:   Return a string representation of the BOM tree hierarchy

Dependencies
------------

-   *pandas*
-   *anytree*
