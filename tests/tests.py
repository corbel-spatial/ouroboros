import os
import uuid
from random import uniform

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from src import ouroboros as ob


SAMPLE_FCS = (
    "Test1_Points",
    "Test1_Points_No_Dataset",
    "Test2_Polygons",
    "Test3_Lines",
)
SAMPLE_FDS = {
    "Test1_Points": "Test_1",
    "Test1_Points_No_Dataset": None,
    "Test2_Polygons": "Test_2",
    "Test3_Lines": "Test_3",
}
SAMPLES = 1000


@pytest.fixture
def gdb(tmp_path):
    test_gdb_path = os.path.join(tmp_path, "test.gdb")

    test_points = [Point(uniform(-170, 170), uniform(-70, 70)) for i in range(SAMPLES)]
    test_fields = {
        "sample1": [uuid.uuid4() for i in range(SAMPLES)],
        "sample2": [uuid.uuid4() for i in range(SAMPLES)],
        "sample3": [uuid.uuid4() for i in range(SAMPLES)],
    }
    test_points = gpd.GeoDataFrame(test_fields, crs="EPSG:4326", geometry=test_points)
    ob.gdf_to_fc(
        test_points,
        test_gdb_path,
        "Test1_Points",  # use upper and lower alphanum and underscore
        "Test_1",
        overwrite=True,
    )

    ob.gdf_to_fc(
        test_points,
        test_gdb_path,
        "Test1_Points_No_Dataset",
        None,
        overwrite=True,
    )

    test_polygons = test_points.buffer(5.0)
    ob.gdf_to_fc(
        test_polygons,
        test_gdb_path,
        "Test2_Polygons",
        "Test_2",
        overwrite=True,
    )

    test_lines = test_polygons.boundary
    ob.gdf_to_fc(
        test_lines,
        test_gdb_path,
        "Test3_Lines",
        feature_dataset="Test_3",
        overwrite=True,
    )

    return ob.GeoDatabase(test_gdb_path)


def test_create_gdb_fixture(gdb):
    assert isinstance(gdb, ob.GeoDatabase)


class TestUtilityFunctions:
    def test_delete_fc(self, gdb):
        fcs = ob.list_layers(gdb.path)
        count = len(fcs)
        for fc_name in fcs:
            ob.delete_fc(gdb.path, fc_name)
            gdb.reload()
            assert len(gdb) < count
            count -= 1
        assert len(gdb) == 0

    def test_fc_to_gdf(self, gdb):
        for fc in gdb:
            gdf = ob.fc_to_gdf(gdb.path, fc.name)
            assert isinstance(gdf, gpd.GeoDataFrame)

    def test_gdf_to_fc(self, gdb):
        for fc in gdb:
            gdf = fc._data
            ob.gdf_to_fc(gdf, gdb.path, fc.name + "_copy")
        gdb.reload()
        assert len(gdb) == len(SAMPLE_FCS) * 2

    def test_list_datasets(self, gdb):
        fds = ob.list_datasets(gdb.path)
        assert len(fds) == len(SAMPLE_FCS)
        for k, v in fds.items():
            assert isinstance(k, str) or k is None
            assert isinstance(v, list)

    def test_list_layers(self, gdb):
        assert len(ob.list_layers(gdb.path)) == len(SAMPLE_FCS)


class TestFeatureClass:
    def test_instantiate_gdb(self, gdb):
        for idx, fc in enumerate(gdb):
            fc_obj = ob.FeatureClass(
                fc.name,
                gdb.path,
            )
            assert isinstance(fc_obj, ob.FeatureClass)
            assert fc_obj.saved is True
            assert str(fc) == fc.path
            assert fc.feature_dataset == SAMPLE_FDS[fc.name]

    def test_instatiate_gdf(self):
        fc = ob.FeatureClass("test", gpd.GeoDataFrame(geometry=[Point(0, 1)]))
        assert fc.saved is False
        assert str(fc) == fc.name

    def test_instatiate_none(self):
        fc = ob.FeatureClass("test")
        assert fc.saved is False
        assert str(fc) == fc.name

    def test_delitem(self, gdb):
        for fc in gdb:
            del fc[500]
            assert len(fc) == SAMPLES - 1

    def test_gdf(self, gdb):
        for fc in gdb:
            gdf = fc.gdf()
            assert isinstance(gdf, gpd.GeoDataFrame)

    def test_getitem(self, gdb):
        for fc in gdb:
            assert isinstance(fc[0], gpd.GeoDataFrame)
            assert isinstance(fc[-1], gpd.GeoDataFrame)

    def test_iter(self, gdb):
        for fc in gdb:
            for row in fc:
                assert isinstance(row, tuple)
                break

    def test_len(self, gdb):
        for fc in gdb:
            assert len(fc) == SAMPLES

    def test_repr(self, gdb):
        for fc in gdb:
            assert isinstance(repr(fc), str)
            assert isinstance(eval(repr(fc)), ob.FeatureClass)

    def test_setitem(self, gdb):
        for fc in gdb:
            fc[(0, "geometry")] = None
            fc[(-1, 0)] = None

    def test_str(self, gdb):
        for fc in gdb:
            assert str(fc) == fc.path

    def test_append(self, gdb):
        fc = gdb["Test1_Points"]
        count = len(fc)
        new_row = fc[0]
        fc.append(new_row)
        assert len(fc) == count + 1
        assert fc[0].iat[0, 0] == fc[-1].iat[0, 0]

    def test_clear(self, gdb):
        for fc in gdb:
            fc.clear()
            assert len(fc) == 0

    def test_describe(self, gdb):
        for fc in gdb:
            assert isinstance(fc.describe(), dict)

    def test_get_fields(self, gdb):
        for fc in gdb:
            assert isinstance(fc.get_fields(), list)

    def test_head(self, gdb):
        for fc in gdb:
            h = fc.head(5, silent=True)
            assert isinstance(h, pd.DataFrame)
            assert len(h) == 5

    def test_insert(self, gdb):
        fc = gdb["Test1_Points"]
        new_row = fc[500]
        fc.insert(600, new_row)
        assert len(fc) == SAMPLES + 1
        assert fc[500].iat[0, 0] == fc[600].iat[0, 0]

    def test_save(self, gdb):
        for fc in gdb:
            fc.save()
            assert fc.saved is True

    def test_sort(self, gdb):
        fc = gdb["Test1_Points"]
        case1 = fc[0].iat[0, 0]
        fc.sort("sample1", ascending=True)
        case2 = fc[0].iat[0, 0]
        fc.sort("sample1", ascending=False)
        case3 = fc[0].iat[0, 0]
        assert case1 != case2 != case3


class TestGeoDatabase:
    def test_instantiate(self, gdb):
        assert isinstance(gdb, ob.GeoDatabase)

    def test_delitem(self, gdb):
        fcs = ob.list_layers(gdb.path)
        count = len(fcs)
        for fc_name in fcs:
            del gdb[fc_name]
            assert len(gdb) < count
            count -= 1
        assert len(gdb) == 0

    def test_getitem(self, gdb):
        for fc in gdb:
            assert isinstance(fc, ob.FeatureClass)

    def test_iter(self, gdb):
        count = 0
        for fc in gdb:
            count += 1
            assert isinstance(fc.name, str)
            assert isinstance(fc, ob.FeatureClass)
        assert count == len(gdb)

    def test_len(self, gdb):
        assert len(gdb) == len(SAMPLE_FCS)

    def test_setitem(self, gdb):
        fcs = ob.list_layers(gdb.path)
        count = len(fcs)
        for fc_name in fcs:
            with pytest.raises(KeyError):
                gdb[fc_name] = gdb[fc_name]
            gdb[fc_name + "_copy"] = gdb[fc_name]
            assert gdb[fc_name + "_copy"].name == fc_name + "_copy"
        assert len(gdb) == count * 2

    def test_reload(self, gdb):
        for fc in gdb:
            ob.gdf_to_fc(fc._data, gdb.path, fc.name + "_copy")
        assert len(gdb) == len(SAMPLE_FCS)
        gdb.reload()
        assert len(gdb) == len(SAMPLE_FCS) * 2

    def test_save(self, gdb):
        for fc in gdb:
            ob.gdf_to_fc(fc._data, gdb.path, fc.name + "_copy")
        gdb.save()
        assert gdb.saved is True
