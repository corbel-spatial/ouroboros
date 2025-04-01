[![PyPI - Version](https://img.shields.io/pypi/v/ouroboros-arcpy)](https://pypi.org/project/ouroboros-arcpy/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/ouroboros-arcpy)](https://pypistats.org/packages/ouroboros-arcpy)
![PyPI - Format](https://img.shields.io/pypi/format/ouroboros-arcpy)
[![Read the Docs](https://img.shields.io/readthedocs/ouroboros-arcpy)](https://ouroboros-arcpy.readthedocs.io/)
[![GitHub Actions Workflow Status: Pylint](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pylint.yml?label=pylint)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pylint.yml)
[![arcpy 3.4](https://img.shields.io/badge/arcpy-3.4-blue?logo=arcgis&logoColor=fff)](https://pro.arcgis.com/en/pro-app/3.4/arcpy/get-started/what-is-arcpy-.htm)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ouroboros-arcpy)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](https://github.com/corbel-spatial/ouroboros?tab=MIT-1-ov-file)

# ouroboros

A module that provides a wrapper class to manipulate `arcpy` feature classes in a more pythonic way. Uses the `Sequence` abstract base class to give list-like behavior to feature class objects.

## Requirements

- ArcGIS Pro 3.4
- Windows 11
  
## Installation

- In the [Python Command Prompt](https://developers.arcgis.com/python/latest/guide/install-and-set-up/#installation-using-python-command-prompt):

```PowerShell
python -m pip install ouroboros-arcpy
```

## Basic Usage

```Python
import ouroboros as ob

fc = ob.FeatureClass(r"C:\Users\zoot\spam.gdb\eggs_polygons", in_memory=True)  # cache in memory for better performance

for row in fc:
    print(row)
```

## Examples

- See `notebooks/example.ipynb`, best used in ArcGIS Pro

## Links

- [Documentation on Read the Docs](https://ouroboros-arcpy.readthedocs.io/)
- [GitHub repository](https://github.com/corbel-spatial/ouroboros)
- [Package on PyPI](https://pypi.org/project/ouroboros-arcpy/)

## References

- [Abstract Base Classes](https://docs.python.org/3/library/collections.abc.html)
- [ArcPy](https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/what-is-arcpy-.htm)

## Installation Steps for Development
```
cmd /k "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\proenv.bat"
```
```
git clone https://github.com/corbel-spatial/ouroboros
```
```
cd ouroboros
```
```
conda env create -f environment.yml
```

```
proswap arcgispro-py3-ob
```

```
python -m pip install -r requirements.txt
```

