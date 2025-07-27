Installation
============

Installing with conda
---------------------

In an active Anaconda environment::

    conda install ouroboros-gis

Installing with pip
-------------------

ouroboros depends on Rasterio for reading raster datasets from geodatabases, which must be installed with GDAL
version 3.8 or higher. Installation of ouroboros with raster support is different for each platform.

Windows
^^^^^^^

Simply do a standard Python package installation in a terminal via **pip**::

    python -m pip install ouroboros-gis --user

ArcGIS Pro
..........

To install in the default ArcGIS Pro conda environment, run the above command in the
`Python Command Prompt <https://developers.arcgis.com/python/latest/guide/install-and-set-up/arcgis-pro/#installation-using-python-command-prompt>`__,
which can be launched from the Start Menu > All Programs > ArcGIS > Python Command Prompt.

Linux
^^^^^

First install Rasterio using your distribution's package manager, for example, on Ubuntu::

    sudo apt install rasterio
    python -m pip install ouroboros-gis --user

macOS
^^^^^

First install Rasterio with `Hombrew <https://formulae.brew.sh/formula/rasterio>`__ and then install with **pip**::

    brew install rasterio
    python -m pip install ouroboros-gis --user

