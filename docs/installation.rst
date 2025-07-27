Installation
============

Windows
-------

For a standard Python package installation in a terminal via **pip**::

    python -m pip install ouroboros-gis --user

To install in an ArcGIS Pro conda environment, run the above command in the
`Python Command Prompt <https://developers.arcgis.com/python/latest/guide/install-and-set-up/arcgis-pro/#installation-using-python-command-prompt>`__,
which can be launched from the Start Menu > All Programs > ArcGIS > Python Command Prompt.

macOS and Linux
---------------

Vector feature class support is supported natively with a standard Python package installation in a terminal via **pip**::

    python -m pip install ouroboros-gis --user

However, Rasterio does not include OpenFileGDB drivers in its standard installation on macOS and Linux. For raster support on
these platforms you must install GDAL and then Rasterio: https://rasterio.readthedocs.io/en/stable/installation.html
