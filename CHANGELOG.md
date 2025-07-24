# Changelog

## 1.0.0-beta3

- Major refactor:
  - Dropped arcpy as a dependency
  - Rereleased as ouroboros-gis on PyPI to reflect dropping arcpy
  - Added GeoDatabase and FeatureDataset classes for OOP flexibility
  - Using GeoPandas under the hood
  - Added FeatureClass export methods to various formats (shp, geojson, arrow, etc.)
  - Removed extraneous requirements files
  - Reverse engineered feature datasets for `ouroboros.list_datasets` function
- README and documentation updates
- Added GitHub actions for cross-platform testing, black, pylint, and coverage

## 1.0.0-beta2

- Bump requests from 2.32.3 to 2.32.4 in /docs

## 1.0.0-beta1

- Initial release as ouroboros-arcpy in PyPI
- Proof of concept class `ouroboros.core.FeatureClass`
- Test suite (pytest) 
- Sample data geodatabase
- Jupyter notebook with basic examples 
- Documentation
