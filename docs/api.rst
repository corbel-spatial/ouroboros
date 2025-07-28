API
===

* Classes
    * `ouroboros.FeatureClass <#ouroboros.FeatureClass>`__
    * `ouroboros.FeatureDataset <#ouroboros.FeatureDataset>`__
    * `ouroboros.GeoDatabase <#ouroboros.GeoDatabase>`__

* Utility Functions
    * Delete a feature class: `ouroboros.delete_fc() <#ouroboros.delete_fc>`__
    * Load a feature class into a GeoDataFrame: `ouroboros.fc_to_gdf() <#ouroboros.fc_to_gdf>`__
    * Save a GeoDataFrame to a feature class: `ouroboros.gdf_to_fc() <#ouroboros.gdf_to_fc>`__
    * List the structure of feature datasets and feature classes in a geodatabase: `ouroboros.list_datasets() <#ouroboros.list_datasets>`__
    * List feature classes in a geodatabase: `ouroboros.list_layers() <#ouroboros.list_layers>`__
    * List raster datasets in a geodatabase: `ouroboros.list_rasters() <#ouroboros.list_rasters>`__
    * Export a raster dataset in a geodatabase to GeoTIFF: `ouroboros.raster_to_tif() <#ouroboros.raster_to_tif>`__

Classes
-------
.. autoclass:: ouroboros.FeatureClass
   :members:
   :special-members:
   :member-order: bysource
.. autoclass:: ouroboros.FeatureDataset
   :members:
   :special-members:
   :member-order: bysource
.. autoclass:: ouroboros.GeoDatabase
   :members:
   :special-members:
   :member-order: bysource

Utility Functions
-----------------
.. autofunction:: ouroboros.delete_fc
.. autofunction:: ouroboros.fc_to_gdf
.. autofunction:: ouroboros.gdf_to_fc
.. autofunction:: ouroboros.list_datasets
.. autofunction:: ouroboros.list_layers
.. autofunction:: ouroboros.list_rasters
.. autofunction:: ouroboros.raster_to_tif
