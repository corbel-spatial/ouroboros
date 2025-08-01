# Changelog

## 1.0.0 (planned)

- Release on conda-forge
- Add data manipulation methods to help with feature class processing
- Provide more details with get_info()

## 1.0.0-beta8

- Removed Rasterio dependency, instead using GDAL directly
- Getter methods return dicts instead of tuples
- GDAL raster support by default in conda, optional in pip install
- Dev environment setup/test/build batch scripts
- Added TODO.md list for long-term goals

## 1.0.0-beta7

- Pass kwargs to the GeoTIFF write operation
- Added get_info() and list_rasters() utility functions
- Docs additions and updates
- CI cross-platform testing fixes

## 1.0.0-beta6

- Added a utility function for exporting raster datasets to GeoTIFF
- Docs updates

## 1.0.0-beta5

- Switched sphinx theme to PyData for dark mode
- Added more example usage notebooks

## 1.0.0-beta4

- Major refactor:
  - Dropped arcpy as a dependency
  - Rereleased as ouroboros-gis on PyPI to reflect dropping arcpy, and archived ouroboros-arcpy
  - Added GeoDatabase and FeatureDataset classes for OOP flexibility
  - Using GeoPandas under the hood
  - Added FeatureClass export methods to various formats (shp, geojson, arrow, etc.)
  - Removed extraneous requirements files
  - Reverse engineered feature datasets for `ouroboros.list_datasets` function
- README and documentation updates
- Added GitHub actions for cross-platform testing, black, pylint, and coverage
- Skipping v1.0.0b3 to re-upload to PyPI

## 1.0.0-beta2

- Bump requests from 2.32.3 to 2.32.4 in /docs

## 1.0.0-beta1

- Initial release as ouroboros-arcpy in PyPI
- Proof of concept class `ouroboros.core.FeatureClass`
- Test suite (pytest) 
- Sample data geodatabase
- Jupyter notebook with basic examples 
- Documentation
