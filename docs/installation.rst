Installation
============

.. note::
    ouroboros supports vector feature class and raster dataset operations on geodatabases.
    Raster support depends on `GDAL <https://gdal.org/>`__, which is included when installed in an Anaconda (conda) environment.
    Installing with pip only supports vector operations by default. See details below.

Conda (recommended)
-------------------

.. important::
    Coming soon! For now please install via pip.

In an active `conda <https://www.anaconda.com/docs/getting-started/getting-started>`__ environment::

    conda install ourboros-gis -c conda-forge

ArcGIS Pro
..........

To install in an ArcGIS Pro conda environment, run the above command in the
`Python Command Prompt <https://developers.arcgis.com/python/latest/guide/install-and-set-up/arcgis-pro/#installation-using-python-command-prompt>`__,
which can be launched from the Start Menu > All Programs > ArcGIS > Python Command Prompt.

Pip
---

For vector feature class support only::

    python -m pip install ouroboros-gis

For vector *and* raster dataset support you must have already installed `GDAL <https://gdal.org/en/stable/download.html#binaries>`__ binaries (version >= 3.8), then::

    python -m pip install ouroboros-gis[raster]

