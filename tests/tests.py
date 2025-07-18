import os
import uuid
from random import uniform

import geopandas as gpd
import pandas as pd
import pyogrio.errors
import pytest
from shapely.geometry import LineString, MultiLineString, Point

import ouroboros as ob


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
def temp_path(tmp_path):
    return tmp_path


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


class TestFeatureClass:
    def test_bad_inputs(self):
        with pytest.raises(TypeError):
            fc1 = ob.FeatureClass(0)  # noqa

        fc2 = ob.FeatureClass("01234")
        assert fc2.name.startswith("_")

        with pytest.raises(FileNotFoundError):
            fc3 = ob.FeatureClass("test", "thisdoesnotexist")

        with pytest.raises(TypeError):
            fc4 = ob.FeatureClass(
                "test",
                gpd.GeoDataFrame(geometry=[Point(0, 0), LineString([(0, 0), (0, 1)])]),
            )

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

            fc2 = ob.FeatureClass(fc.name, gdb.path, SAMPLE_FDS[fc.name])

            fc2.clear()
            fc2.save()
            fc3 = ob.FeatureClass(fc2.name, gdb.path)
            assert fc3.geom_type == fc2.geom_type

    def test_instatiate_gdf(self):
        fc = ob.FeatureClass("test", gpd.GeoDataFrame(geometry=[Point(0, 1)]))
        assert fc.saved is False
        assert str(fc) == fc.name

        fc2 = ob.FeatureClass("test", gpd.GeoDataFrame(geometry=[]))

    def test_instatiate_none(self):
        fc = ob.FeatureClass("test")
        assert fc.saved is False
        assert str(fc) == fc.name
        fc2 = ob.FeatureClass(
            "test",
        ).describe()

    def test_delitem(self, gdb):
        for fc in gdb:
            del fc[500]
            assert len(fc) == SAMPLES - 1
            with pytest.raises(TypeError):
                del fc["test"]

    def test_getitem(self, gdb):
        for fc in gdb:
            assert isinstance(fc[0], gpd.GeoDataFrame)
            assert isinstance(fc[-1], gpd.GeoDataFrame)
            assert isinstance(fc[100:105], gpd.GeoDataFrame)
            assert isinstance(fc[100, 200, 300], gpd.GeoDataFrame)
            assert isinstance(fc[(100, 200, 300)], gpd.GeoDataFrame)
            assert isinstance(fc[10, 100:105, 200, 300:305], gpd.GeoDataFrame)
            with pytest.raises(KeyError):
                x = fc["test"]  # noqa

    def test_iter(self, gdb):
        for fc in gdb:
            for row in fc:
                assert isinstance(row, tuple)
                assert isinstance(row[0], int)
                assert isinstance(row[1], str)
                assert isinstance(row[2], str)
                assert isinstance(row[3], str)
                assert isinstance(row[4], Point)
                break
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
            with pytest.raises(TypeError):
                fc[("s", "geometry")] = None  # noqa
            with pytest.raises(TypeError):
                fc[(0, dict())] = None  # noqa

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

    def test_head(self, gdb):
        for fc in gdb:
            h = fc.head(5)
            assert isinstance(h, pd.DataFrame)
            assert len(h) == 5

    def test_insert(self, gdb):
        fc = gdb["Test1_Points"]
        new_row = fc[500]
        fc.insert(600, new_row)
        assert len(fc) == SAMPLES + 1
        assert fc[500].iat[0, 0] == fc[600].iat[0, 0]
        fc.insert(0, new_row)
        fc.insert(-1, new_row)

        with pytest.raises(TypeError):
            fc.insert("s", new_row)  # noqa
        with pytest.raises(TypeError):
            fc.insert(0, "s")  # noqa
        with pytest.raises(ValueError):
            fc.insert(500, gpd.GeoDataFrame())
        with pytest.raises(ValueError):
            fc.insert(500, gpd.GeoDataFrame(columns=["test"]))

        with pytest.raises(TypeError):
            fc2 = ob.FeatureClass("test", gpd.GeoDataFrame(geometry=[Point(0, 1)]))
            fc2.insert(
                -1,
                gpd.GeoDataFrame(
                    geometry=[
                        LineString([(0, 1), (1, 1)]),
                        Point(0, 1),
                    ]
                ),
            )

        fc3 = ob.FeatureClass("test")
        assert fc3.geom_type is None
        fc3 = ob.FeatureClass(
            "test", gpd.GeoDataFrame({"col1": ["a"]}, geometry=[None])
        )
        assert fc3.geom_type == "Unknown"
        print("here")
        fc3.insert(
            -1,
            gpd.GeoDataFrame({"col1": ["aa"]}, geometry=[None]),
        )
        assert fc3.geom_type == "Unknown"
        fc3.insert(
            -1,
            gpd.GeoDataFrame({"col1": ["b"]}, geometry=[LineString([(0, 1), (1, 1)])]),
        )
        assert fc3.geom_type == "LineString"
        fc3.insert(
            -1,
            gpd.GeoDataFrame(
                {"col1": ["c"]},
                geometry=[MultiLineString([[(0, 1), (1, 1)], [(0, 1), (1, 1)]])],
            ),
        )
        fc3.insert(
            -1,
            gpd.GeoDataFrame(
                {"col1": ["d", "e"]},
                geometry=[
                    LineString([(0, 1), (1, 1)]),
                    MultiLineString([[(0, 1), (1, 1)], [(0, 1), (1, 1)]]),
                ],
            ),
        )
        assert fc3.geom_type == "MultiLineString"
        with pytest.raises(TypeError):
            fc3.insert(
                -1,
                gpd.GeoDataFrame(
                    {"col1": ["x", "y", "z"]},
                    geometry=[
                        LineString([(0, 1), (1, 1)]),
                        MultiLineString([[(0, 1), (1, 1)], [(0, 1), (1, 1)]]),
                        Point(0, 0),
                    ],
                ),
            )
        with pytest.raises(TypeError):
            fc3.insert(-1, gpd.GeoDataFrame({"col1": ["test"]}, geometry=[Point(0, 0)]))

    def test_save(self, gdb):
        for fc in gdb:
            fc.save()
            assert fc.saved is True
        with pytest.raises(AttributeError):
            fc2 = ob.FeatureClass("test")
            fc2.save()

    def test_sort(self, gdb):
        fc = gdb["Test1_Points"]
        case1 = fc[0].iat[0, 0]
        fc.sort("sample1", ascending=True)
        case2 = fc[0].iat[0, 0]
        fc.sort("sample1", ascending=False)
        case3 = fc[0].iat[0, 0]
        assert case1 != case2 != case3

    def test_to_geodataframe(self, gdb):
        gdf = gdb[0].to_geodataframe()

    def test_to_geojson(self, gdb, temp_path):
        gjs = gdb[0].to_geojson()
        gdb[0].to_geojson(os.path.join(temp_path, "test"))

    def test_to_pyarrow(self, gdb):
        arr = gdb[0].to_pyarrow()

    def test_to_shapefile(self, gdb, temp_path):
        gdb[0].to_shapefile(os.path.join(temp_path, "test"))


class TestGeoDatabase:
    def test_instantiate(self, gdb):
        assert isinstance(gdb, ob.GeoDatabase)
        for fc in gdb:
            assert fc.name in gdb.feature_classes
            if gdb[fc.name].feature_dataset is not None:
                assert gdb[fc.name].feature_dataset in gdb.feature_datasets
        with pytest.raises(FileNotFoundError):
            gdb = ob.GeoDatabase("test")

    def test_delitem(self, gdb):
        fcs = ob.list_layers(gdb.path)
        count = len(fcs)
        for fc_name in fcs:
            del gdb[fc_name]
            assert len(gdb) < count
            count -= 1
            with pytest.raises(TypeError):
                del gdb[99]  # noqa
        assert len(gdb) == 0

    def test_getitem(self, gdb):
        for fc in gdb:
            assert isinstance(fc, ob.FeatureClass)
            with pytest.raises(IndexError):
                f = gdb[99]  # noqa
        fc = gdb["Test1_Points"]
        fc = gdb[0]
        with pytest.raises(TypeError):
            fc = gdb[list()]  # noqa

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
            new_fc = gdb[fc_name]
            new_fc.feature_dataset = "new_dataset"
            gdb[fc_name + "_copy"] = new_fc
            assert gdb[fc_name + "_copy"].name == fc_name + "_copy"
            assert fc_name + "_copy" in gdb.feature_classes
            if gdb[fc_name + "_copy"].feature_dataset is not None:
                assert gdb[fc_name + "_copy"].feature_dataset in gdb.feature_datasets
        assert len(gdb) == count * 2

        with pytest.raises(TypeError):
            gdb[0] = ob.FeatureClass("test")  # noqa
        with pytest.raises(TypeError):
            gdb["test"] = "test"  # noqa

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


class TestUtilityFunctions:
    def test_delete_fc(self, gdb):
        fcs = ob.list_layers(gdb.path)
        count = len(fcs)
        for fc_name in fcs:
            ob.delete_fc(gdb.path, fc_name)
            gdb.reload()
            assert len(gdb) < count
            count -= 1
            assert ob.delete_fc(gdb.path, "bad_fc_name") is False
        assert len(gdb) == 0
        with pytest.raises(FileNotFoundError):
            ob.delete_fc("thisdoesnotexist", "test")
        with pytest.raises(TypeError):
            ob.delete_fc(gdb.path, 0)  # noqa

    def test_fc_to_gdf(self, gdb):
        for fc in gdb:
            gdf = ob.fc_to_gdf(gdb.path, fc.name)
            assert isinstance(gdf, gpd.GeoDataFrame)
        with pytest.raises(FileNotFoundError):
            ob.fc_to_gdf("thisdoesnotexist", "test")
        with pytest.raises(TypeError):
            ob.fc_to_gdf(gdb.path, 0)  # noqa

    def test_gdf_to_fc(self, gdb):
        for fc in gdb:
            gdf = fc._data
            ob.gdf_to_fc(gdf, gdb.path, fc.name + "_copy")
            ob.gdf_to_fc(gdf, gdb.path, fc.name, overwrite=True)
            with pytest.raises(FileExistsError):
                ob.gdf_to_fc(gdf, gdb.path, fc.name)
        gdb.reload()
        assert len(gdb) == len(SAMPLE_FCS) * 2

        # with pytest.raises(FileNotFoundError):
        #     ob.gdf_to_fc(gpd.GeoDataFrame(), "thisfiledoesnotexist", "test")

        with pytest.raises(TypeError):
            ob.gdf_to_fc(gpd.GeoDataFrame(), gdb.path, 99)  # noqa
        with pytest.raises(TypeError):
            ob.gdf_to_fc(gpd.GeoDataFrame(), gdb.path, "test", 99)  # noqa
        with pytest.raises(pyogrio.errors.GeometryError):
            ob.gdf_to_fc(
                gdb[0].to_geodataframe(),
                gdb.path,
                "test_fc",
                gdb[0].feature_dataset,
                "no",  # noqa
            )
        with pytest.raises(TypeError):
            ob.gdf_to_fc(list(), gdb.path, "test")  # noqa

        with pytest.raises(TypeError):
            ob.gdf_to_fc(gpd.GeoDataFrame, "test", "test", overwrite="yes")  # noqa

    def test_list_datasets(self, gdb):
        fds = ob.list_datasets(gdb.path)
        assert len(fds) == len(SAMPLE_FCS)
        for k, v in fds.items():
            assert isinstance(k, str) or k is None
            assert isinstance(v, list)
        with pytest.raises(FileNotFoundError):
            ob.list_datasets("filedoesnotexist")

    def test_list_layers(self, gdb):
        assert len(ob.list_layers(gdb.path)) == len(SAMPLE_FCS)
        with pytest.raises(FileNotFoundError):
            ob.list_layers("filedoesnotexist")
