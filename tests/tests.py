import os
import pathlib
import tempfile
from random import uniform

import geopandas as gpd
import pytest
from shapely.geometry import Point

from src import ouroboros as ob


@pytest.fixture
def test_gdb(tmp_path):
    test_gdb_path = pathlib.Path(os.path.join(tmp_path, "test.gdb"))
    # test_gdb_path = "test.gdb"

    test_points = [Point(uniform(-170, 170), uniform(-70, 70)) for i in range(1000)]
    test_points = gpd.GeoDataFrame(crs="EPSG:4326", geometry=test_points)
    ob.gdf_to_fc(
        test_points,
        test_gdb_path,
        "test_points",
        "test",
        overwrite=True,
    )

    test_polygons = test_points.buffer(5.0)
    ob.gdf_to_fc(
        test_polygons,
        test_gdb_path,
        "test_polygons",
        "test",
        overwrite=True,
    )

    test_lines = test_polygons.boundary
    ob.gdf_to_fc(
        test_lines,
        test_gdb_path,
        "test_lines",
        feature_dataset="test",
        overwrite=True,
    )

    return test_gdb_path


def test_create_gdb(test_gdb):
    assert test_gdb
