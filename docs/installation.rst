Installation
============

conda (cross-platform)
----------------------

Coming soon!

..
    In an active `conda <https://www.anaconda.com/docs/getting-started/getting-started>`__ environment::

        conda install ourboros-gis -c conda-forge

pip
---

Feature class and feature dataset (vector driver) support should work cross-platform with a simple
:code:`pip install ouroboros-gis`. However, ouroboros depends on `Rasterio <https://rasterio.readthedocs.io/en/stable/installation.html>`__
for reading raster datasets from geodatabases, which must be installed with `GDAL <https://gdal.org/en/stable/download.html#binaries>`__
version 3.8 or higher for GDB support. Installation of ouroboros with raster support is thus slightly different
for each platform.

Windows
^^^^^^^

Simply do a standard Python package installation in a terminal via :code:`pip`::

    python -m pip install ouroboros-gis --user

ArcGIS Pro
..........

To install in an ArcGIS Pro conda environment, run the above command in the
`Python Command Prompt <https://developers.arcgis.com/python/latest/guide/install-and-set-up/arcgis-pro/#installation-using-python-command-prompt>`__,
which can be launched from the Start Menu > All Programs > ArcGIS > Python Command Prompt.

Linux
^^^^^

First install GDAL and Rasterio using your distribution's package manager, and then install with :code:`pip`. For example, on Ubuntu::

    sudo apt install gdal rasterio
    python -m pip install ouroboros-gis --user

macOS
^^^^^

First install GDAL and Rasterio with `Hombrew <https://formulae.brew.sh/formula/rasterio>`__ and then install with :code:`pip`::

    brew install gdal rasterio
    python -m pip install ouroboros-gis --user

