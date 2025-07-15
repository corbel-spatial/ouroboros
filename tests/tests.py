import os
import pathlib
from random import uniform

import fiona
import geopandas as gpd
import pytest
from shapely.geometry import Point

from src import ouroboros as ob


@pytest.fixture
def test_gdb(tmp_path):
    test_gdb_path = pathlib.Path(os.path.join(tmp_path, "test.gdb"))

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

    return ob.GeoDatabase(test_gdb_path)


def test_create_gdb_fixture(test_gdb):
    assert isinstance(test_gdb, ob.GeoDatabase)


def fc_to_gdf(test_gdb):
    raise NotImplementedError


def gdf_to_fc(test_gdb):
    raise NotImplementedError


class TestFeatureClass:
    def test_instantiate(self, test_gdb):
        print(test_gdb.path)
        for name in test_gdb.names:
            print(name)
            fc_obj = ob.FeatureClass(test_gdb.path, name)
            assert isinstance(fc_obj, ob.FeatureClass)

    def test_delitem(self, test_gdb):
        raise NotImplementedError

    def test_getitem(self, test_gdb):
        raise NotImplementedError

    def test_iter(self, test_gdb):
        raise NotImplementedError

    def test_len(self, test_gdb):
        assert isinstance(len(test_gdb), int)
        print(test_gdb._data.shape[0])
        assert len(test_gdb) == 1000

    def test_setitem(self, test_gdb):
        raise NotImplementedError

    def test_reload(self, test_gdb):
        raise NotImplementedError

    def test_save(self, test_gdb):
        raise NotImplementedError


class TestGeoDatabase:
    def test_instantiate(self, test_gdb):
        assert isinstance(test_gdb, ob.GeoDatabase)

    def test_delitem(self, test_gdb):
        count = len(test_gdb)
        for name in test_gdb.names:
            del test_gdb[name]
            assert len(test_gdb) < count
            count -= 1
        assert len(test_gdb) == 0

    def test_getitem(self, test_gdb):
        for name in test_gdb.names:
            assert isinstance(test_gdb[name], ob.FeatureClass)

    def test_iter(self, test_gdb):
        count = 0
        for name, fc in test_gdb.items():
            count += 1
            assert isinstance(name, str)
            assert isinstance(fc, ob.FeatureClass)
        assert count == len(test_gdb)

    def test_len(self, test_gdb):
        assert len(test_gdb) == 3

    def test_setitem(self, test_gdb):
        count = len(test_gdb)
        for name in test_gdb.names:
            with pytest.raises(KeyError):
                test_gdb[name] = test_gdb[name]
            test_gdb[name].copy(name + "_copy")
        assert len(test_gdb) == count * 2

    def test_reload(self, test_gdb):
        count = len(test_gdb)
        test_gdb.reload()
        assert len(test_gdb) == count
