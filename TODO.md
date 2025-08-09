# TODO

- Write a utility function for saving a raster to a geodatabase ([GDAL OpenFileGDB](https://gdal.org/en/stable/drivers/raster/openfilegdb.html) does not support writing rasters)
- Getter functions should parse geodatabase contents solely on gdbtable XML
- Fix upstream issues from `pandas` in 3.14
  - FutureWarning: Setting an item of incompatible dtype is deprecated
  - ChainedAssignmentError in Copy-on-Write mode
- Rewrite PyArrow demo notebook
- Add benchmarks