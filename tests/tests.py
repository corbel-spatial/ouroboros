import os
import pathlib
from typing import NamedTuple
from random import uniform

import pytest
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from src import ouroboros as ob

SAMPLE_DEFS = ("test_points", "test_lines", "test_polygons")
SAMPLES = 1000


@pytest.fixture
def test_gdb(tmp_path):
    test_gdb_path = pathlib.Path(os.path.join(tmp_path, "test.gdb"))

    test_points = [Point(uniform(-170, 170), uniform(-70, 70)) for i in range(SAMPLES)]
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
        for fc in test_gdb:
            del test_gdb[fc][500]
            assert len(test_gdb[fc]) == SAMPLES - 1

    def test_getitem(self, test_gdb):
        for fc in test_gdb:
            assert isinstance(test_gdb[fc][0], pd.Series)
            assert isinstance(test_gdb[fc][-1], pd.Series)

    def test_iter(self, test_gdb):
        for fc in test_gdb:
            for row in test_gdb[fc]:
                assert isinstance(row, tuple)
                break

    def test_len(self, test_gdb):
        for fc in test_gdb:
            assert len(test_gdb[fc]) == SAMPLES

    def test_setitem(self, test_gdb):
        for fc in test_gdb:
            test_gdb[fc][(0, "geometry")] = None
            test_gdb[fc][(-1, 0)] = None

    def test_copy(self, test_gdb):
        count = len(test_gdb)
        for fc in test_gdb:
            with pytest.raises(KeyError):
                test_gdb[fc] = test_gdb[fc]
            test_gdb[fc].copy(fc + "_copy")
        test_gdb.reload()  # TODO auto reload?
        assert len(test_gdb) == count * 2

    def test_insert(self, test_gdb):
        for fc in test_gdb:
            new_row = test_gdb[fc][500]
            test_gdb[fc].insert(600, new_row)
            assert len(test_gdb[fc]) == SAMPLES + 1

    def test_save(self, test_gdb):
        for fc in test_gdb:
            test_gdb[fc].save()
            assert test_gdb[fc].saved is True


class TestGeoDatabase:
    def test_instantiate(self, test_gdb):
        assert isinstance(test_gdb, ob.GeoDatabase)

    def test_delitem(self, test_gdb):
        count = len(test_gdb)
        for fc in test_gdb:
            del test_gdb[fc]
            assert len(test_gdb) < count
            count -= 1
        assert len(test_gdb) == 0

    def test_getitem(self, test_gdb):
        for fc in test_gdb:
            assert isinstance(test_gdb[fc], ob.FeatureClass)

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
        for fc in test_gdb:
            with pytest.raises(KeyError):
                test_gdb[fc] = test_gdb[fc]
            test_gdb[fc].copy(fc + "_copy")
        test_gdb.reload()  # TODO auto reload?
        assert len(test_gdb) == count * 2

    def test_reload(self, test_gdb):
        count = len(test_gdb)
        test_gdb.reload()
        assert len(test_gdb) == count
