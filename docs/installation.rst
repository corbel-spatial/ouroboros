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

To install in an ArcGIS Pro :code:`conda` environment:

- Clone and activate an editable environment (`instructions here <https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/clone-an-environment.htm>`__)

- Open the `Python Command Prompt <https://developers.arcgis.com/python/latest/guide/install-and-set-up/arcgis-pro/#installation-using-python-command-prompt>`__, which can be launched from the Start Menu > All Programs > ArcGIS > Python Command Prompt.

- Install with this command::

    conda install ourboros-gis -c conda-forge --user`

