[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=FFD43B&labelColor=306998&color=FFD43B)]()
[![arcpy 3.4](https://img.shields.io/badge/arcpy-3.4-blue?logo=arcgis&logoColor=fff)]()
[![ArcGIS Pro 3.4](https://img.shields.io/badge/ArcGIS_Pro-3.4-blue?logo=arcgis&logoColor=fff)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](https://github.com/corbel-spatial/ouroboros?tab=MIT-1-ov-file)
[![GitHub Actions Workflow Status: Pylint](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pylint.yml?label=pylint)]()

# ouroboros
A module that provides a wrapper class to manipulate arcpy feature classes in a more pythonic way.

## Requirements

- Windows 11
- ArcGIS Pro 3.4.x
- Anaconda and Python 3.11.x (installed with ArcGIS Pro)

## Installation

- Download this source
- In the [Python Command Prompt](https://developers.arcgis.com/python/latest/guide/install-and-set-up/#installation-using-python-command-prompt):

```
conda create -n arcgispro-py3-ob arcpy=3.4.* geojson shapely -c Esri -c conda-forge --solver libmamba -y
```

```
proswap arcgispro-py3-ob
```

## Usage

```
from ouroboros import ouroboros as ob

fc = ob.FeatureClass(r'C:\Users\zoot\spam.gdb\eggs_feature_class')
```

## Examples

- `ouroboros\docs\example.ipynb` (for use in ArcGIS Pro)

## References

- [Mutable Sequence](https://docs.python.org/3/library/stdtypes.html#mutable-sequence-types)
- [ArcPy](https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/what-is-arcpy-.htm)

## Changelog

### 1.0.0-alpha (work in progress)

- Initial proof of concept module
- Test suite (pytest) and sample geodatabase
- Jupyter notebook with basic examples 
