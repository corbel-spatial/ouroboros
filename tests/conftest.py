import os
import uuid
import zipfile
from random import uniform

import geopandas as gpd
import pytest
import shapely

import ouroboros as ob


SAMPLES = 1000


@pytest.fixture
def samples():
    return SAMPLES


@pytest.fixture
def gdb_path(tmp_path_factory):
    gdb_path = tmp_path_factory.mktemp("test") / "test.gdb"
    return str(gdb_path)


@pytest.fixture
def gdf_points():
    test_points = [
        shapely.Point(uniform(-170, 170), uniform(-70, 70)) for i in range(SAMPLES)
    ]
    test_fields = {
        "sample1": [str(uuid.uuid4()) for i in range(SAMPLES)],
        "sample2": [str(uuid.uuid4()) for i in range(SAMPLES)],
        "sample3": [str(uuid.uuid4()) for i in range(SAMPLES)],
    }
    return gpd.GeoDataFrame(test_fields, crs="EPSG:4326", geometry=test_points)


@pytest.fixture
def fc_points(gdb_path, gdf_points):
    ob.utils.gdf_to_fc(gdf_points, gdb_path, "test_points")
    return os.path.join(gdb_path, "test_points")


@pytest.fixture
def fds_fc_points(tmp_path, gdf_points):
    gdb_path = tmp_path / "fc_points.gdb"
    ob.utils.gdf_to_fc(
        gdf=gdf_points,
        gdb_path=gdb_path,
        fc_name="test_points",
        feature_dataset="test_dataset",
    )
    return os.path.join(gdb_path, "test_dataset", "test_points")


@pytest.fixture
def gdf_polygons(gdf_points):
    polys = gdf_points.to_crs("EPSG:3857")
    polys = polys.buffer(5.0)
    polys = polys.to_crs("EPSG:4326")
    return gpd.GeoDataFrame(geometry=polys)


@pytest.fixture
def gdf_lines(gdf_polygons):
    return gpd.GeoDataFrame(geometry=gdf_polygons.boundary)


@pytest.fixture
def ob_gdb(gdb_path, gdf_points, gdf_lines, gdf_polygons):
    gdb = ob.GeoDatabase()
    gdb["test_points1"] = ob.FeatureClass(gdf_points)
    assert gdb["test_points1"].geom_type == "Point"
    gdb["test_lines1"] = ob.FeatureClass(gdf_lines)
    assert gdb["test_lines1"].geom_type == "LineString"
    gdb["test_polygons1"] = ob.FeatureClass(gdf_polygons)
    assert gdb["test_polygons1"].geom_type == "Polygon"

    fds = ob.FeatureDataset(crs=gdf_points.crs)
    fds["test_points2"] = ob.FeatureClass(gdf_points)
    fds["test_lines2"] = ob.FeatureClass(gdf_lines)
    fds["test_polygons2"] = ob.FeatureClass(gdf_polygons)

    gdb["test_fds"] = fds
    gdb.save(gdb_path)
    return gdb, gdb_path


@pytest.fixture
def esri_gdb(tmp_path):
    z = os.path.join("tests", "test_data.gdb.zip")
    try:
        gdb_path = os.path.abspath(os.path.join("..", z))
        assert os.path.exists(gdb_path)
    except AssertionError:  # for CI testing -- do not touch!
        gdb_path = os.path.abspath(os.path.join(".", z))
    zf = zipfile.ZipFile(gdb_path, "r")
    zf.extractall(tmp_path)
    return os.path.join(tmp_path, "test_data.gdb")
