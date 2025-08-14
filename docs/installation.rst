Installation
============

.. note::
    :code:`ouroboros` supports vector feature class and raster dataset operations on geodatabases.
    Raster support depends on `GDAL <https://gdal.org/>`__, which is included when installed in a :code:`conda` environment.
    Installing with :code:`pip` only supports vector operations by default. See details below.

Conda (recommended)
-------------------

In an active `conda <https://www.anaconda.com/docs/getting-started/getting-started>`__ environment::

    conda install ourboros-gis -c conda-forge


Pip
---

For vector feature class support only::

    python -m pip install ouroboros-gis

For vector *and* raster dataset support you must have already installed the `GDAL binaries <https://gdal.org/en/stable/download.html#binaries>`__ (version >= 3.8), then::

    python -m pip install ouroboros-gis[raster]


ArcGIS Pro
----------

.. warning::

    This is experimental and may not work depending on your installation of ArcGIS!

To install in an ArcGIS Pro :code:`conda` environment:

1. Open the `Python Command Prompt <https://developers.arcgis.com/python/latest/guide/install-and-set-up/arcgis-pro/#installation-using-python-command-prompt>`__, which can be launched from the Start Menu > All Programs > ArcGIS > Python Command Prompt.

2. Create a new environment and install packages with this command::

    conda create python=3.11 arcpy=3.5 ouroboros-gis -c esri -c conda-forge --name new_env

3. Activate the new environment::

    proswap new_env

4. Close and reopen the Python Command Prompt. Then test the installation::

    new_env> python
    >>> import ouroboros as ob
    >>> ob.ouroboros._gdal_installed
    True

