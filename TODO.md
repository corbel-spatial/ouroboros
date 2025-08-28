# TODO

- Write a utility function for saving a raster to a geodatabase ([GDAL OpenFileGDB](https://gdal.org/en/stable/drivers/raster/openfilegdb.html) does not support writing rasters)
- In Python 3.14.0 release check for spurious `ChainedAssignmentError` warnings from upstream `geopandas` and `pandas`
- Prebuild GDAL binaries for OpenFileGDB drivers and include with package
- Add full support for zipped geodatabases
