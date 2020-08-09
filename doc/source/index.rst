Welcome to BOM.py's documentation
=================================

Background
----------

Some conventions used in this module are based on a few of the concepts from the
book *Engineering Documentation Control Handbook*, 4th Ed. by Frank B. Watts.
One of which is the use of a master parts list, which represents a singular
source of information for items - parts, drawings, documents, etc.
In the context of this program this is represented by an Excel file with a
special name (defaults to ``Parts list.xlsx``). For example, parts for a
skateboard might have:

=========== ============= ==================== ==================== =========== ======== ============== =====
PN          Name          Description          Supplier             Supplier PN Pkg QTY  Pkg Price      Item
=========== ============= ==================== ==================== =========== ======== ============== =====
SK1001-01   Bearing       Wheel bearing        XYZ Bearing Co.      74295-942   1        2.99           part
SK1002-01   Board         Standard type        Skatr Dude Inc.      BRX-02      1        15.99          part
SK1003-01   Truck half    Truck fixed          Skatr Dude Inc.      TR1-A       1        9.87           part
SK1004-01   Truck half    Truck movable        Skatr Dude Inc.      TR1-B       1        12.25          part
SK1005-01   Truck screw   1/4-20 SHCS          Bolts R Us           92220A      50       12.86          part
SK1006-01   Wheel         Hard clear urethane  Skatr Dude Inc.      WHL-PRX     4        9.87           part
SK1007-01   Nut           1/4-20 Hex nut       Bolts R Us           95479A      50       4.88           part
=========== ============= ==================== ==================== =========== ======== ============== =====

For each assembly, all that is required is the part identification number and
its quantity which correspond to the following fields:

- PN
- QTY

Example:

=========== =====
PN          QTY
=========== =====
SK1003-01   1
SK1004-01   1
=========== =====

Certain fields are used in calculating totals, such as in :py:attr:`BOM.BOM.summary`,
which are:

================= ==============================================================
``Pkg QTY``       The quantity of items in a specific supplier SKU (i.e. a bag
                  of 100 screws)
``Pkg Price``     The cost of a specific supplier SKU
================= ==============================================================


Usage
-----

Create a folder to contain your BOM files and create a parts list and any
assemblies as individual Excel files (the file name becomes the assembly item
number by default). Then, call class method :py:meth:`BOM.BOM.from_folder()`
with the path to your folder to instantiate and build BOM objects.

Then, call methods or properties on the root BOM returned from
:py:meth:`BOM.BOM.from_folder()` to obtain derived information:

:py:attr:`BOM.BOM.parts`
   Get a list of all direct-child parts

:py:attr:`BOM.BOM.assemblies`
   Get a list of all direct-child assemblies

:py:attr:`BOM.BOM.quantities`
   Get the quantity of each direct child in the BOM

:py:attr:`BOM.BOM.aggregate`
   Get the aggregated quantity of each part/assembly from the current BOM level
   down

:py:attr:`BOM.BOM.summary`
   Get a summary in the form of a DataFrame containing the master parts list
   with each item's aggregated quantity and the required packages to buy if the
   ``Pkg QTY`` field is not 1.

:py:attr:`BOM.BOM.tree`
   Return a string representation of the BOM tree hierarchy


Classes
-------

.. autoclass:: BOM.BaseItem
   :members:
.. autoclass:: BOM.Item
   :members:
.. autoclass:: BOM.ItemLink
   :members:
.. autoclass:: BOM.BOM
   :members: