# TODO

- Create a utility function for writing a raster to a geodatabase
  - [GDAL OpenFileGDB](https://gdal.org/en/stable/drivers/raster/openfilegdb.html) does not support writing rasters
- Naive parsing of geodatabase contents solely on gdbtable XML
- FeatureClass method for field calculator style operation on a column
  - Use column names in quotes to use them in expressions
  - If column doesn't exist it will be created
