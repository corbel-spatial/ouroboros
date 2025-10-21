from ._utils import (
    fc_to_gdf,
    fc_to_json,
    fc_to_parquet,
    fc_to_shp,
    gdf_to_fc,
    get_info,
    list_datasets,
    list_layers,
    list_rasters,
    raster_to_tif,
    sanitize_gdf_geometry,
)

from ._utils import gdal_version as _gdal_version


@property
def gdal_version() -> None | str:
    """Return the version of GDAL imported by this package."""
    return _gdal_version
