import os
from collections.abc import Sequence

import fiona
import geopandas as gpd
from pyogrio.errors import DataSourceError


def gdf_to_fc(
    gdf,
    gdb_path,
    fc_name,
    feature_dataset=None,
    overwrite=False,
    compatibility=True,
    reindex=False,
):
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
        fcs = read_gdb(gdb_path)
        if fc_name in fcs["name"].values:
            if overwrite:
                print(f"Overwriting feature class '{fc_name}'")
                fiona.remove(gdb_path, "OpenFileGDB", fc_name)
                try:
                    assert fc_name not in read_gdb(gdb_path)["name"].values
                except AssertionError:
                    raise IOError(f"Feature class '{fc_name}' could not be deleted")
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


def read_gdb(gdb_path):
    try:
        return gpd.list_layers(gdb_path)
    except DataSourceError:
        raise IOError(f"GDB '{gdb_path}' could not be read because it is empty.")


class FeatureClass(Sequence):
    def __init__(self, gdb_path, fc_name):
        assert os.path.exists(gdb_path)

    def __getitem__(self, index):
        pass

    def __len__(self):
        pass


class GeoDatabase(Sequence):
    def __init__(self, gdb_path):
        assert os.path.exists(gdb_path)

    def __getitem__(self, index):
        pass

    def __len__(self):
        pass
