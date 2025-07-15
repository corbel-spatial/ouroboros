import os

import fiona
import geopandas as gpd
from pyogrio.errors import DataSourceError


def fc_to_gdf(
    gdb_path: os.PathLike | str,
    fc_name: str,
) -> gpd.GeoDataFrame:
    return gpd.read_file(os.path.join(gdb_path, fc_name))


def gdf_to_fc(
    gdf: gpd.GeoDataFrame,
    gdb_path: os.PathLike | str,
    fc_name: str,
    feature_dataset: str = None,
    overwrite: bool = False,
    compatibility: bool = True,
    reindex: bool = False,
) -> None:
    """
    GeoDataFrame to Feature Class

    References:
    - https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.to_file.html
    - https://gdal.org/en/stable/drivers/vector/openfilegdb.html
    """
    layer_options = {
        "TARGET_ARCGIS_VERSION": True if compatibility else False,
        "OPENFILEGDB_IN_MEMORY_SPI": True if reindex else False,
        "FEATURE_DATASET": feature_dataset,
    }

    if os.path.exists(gdb_path):
        if fc_name in list_fcs(gdb_path):
            if overwrite:
                print(f"Overwriting feature class '{fc_name}'")
                fiona.remove(gdb_path, "OpenFileGDB", fc_name)
            else:
                raise FileExistsError(
                    f"{fc_name} already exists. To overwrite it use: gdf_to_fc(gdf, gdb_path, fc_name, overwrite=True"
                )

    gdf.to_file(
        gdb_path,
        driver="OpenFileGDB",
        layer=fc_name,
        layer_options=layer_options,
    )


def list_fcs(gdb_path: os.PathLike | str) -> list | None:
    try:
        return gpd.list_layers(gdb_path)["name"].values.tolist()
    except DataSourceError:
        return None
