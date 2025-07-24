import os
import uuid
from random import uniform
from pprint import pprint

import geojson
import geopandas as gpd
import pandas as pd
import pyarrow as pa
import pyogrio
import pytest
from shapely.geometry import LineString, MultiLineString, Point

import ouroboros as ob


SAMPLES = 1000


@pytest.fixture(scope="function")
def gdb_path(tmp_path_factory):
    gdb_path = tmp_path_factory.mktemp("test") / "test.gdb"
    return str(gdb_path)


@pytest.fixture
def gdf_points():
    test_points = [Point(uniform(-170, 170), uniform(-70, 70)) for i in range(SAMPLES)]
    test_fields = {
        "sample1": [str(uuid.uuid4()) for i in range(SAMPLES)],
        "sample2": [str(uuid.uuid4()) for i in range(SAMPLES)],
        "sample3": [str(uuid.uuid4()) for i in range(SAMPLES)],
    }
    return gpd.GeoDataFrame(test_fields, crs="EPSG:4326", geometry=test_points)


@pytest.fixture
def fc_points(gdb_path, gdf_points):
    ob.gdf_to_fc(gdf_points, gdb_path, "test_points")
    return os.path.join(gdb_path, "test_points")


@pytest.fixture
def fds_fc_points(tmp_path, gdf_points):
    gdb_path = tmp_path / "fc_points.gdb"
    ob.gdf_to_fc(
        gdf=gdf_points,
        gdb_path=gdb_path,
        fc_name="test_points",
        feature_dataset="test_dataset",
    )
    return os.path.join(gdb_path, "test_dataset", "test_points")


@pytest.fixture
def gdf_polygons(gdf_points):
    return gpd.GeoDataFrame(geometry=gdf_points.buffer(5.0))


@pytest.fixture
def gdf_lines(gdf_polygons):
    return gpd.GeoDataFrame(geometry=gdf_polygons.boundary)


@pytest.fixture
def gdb(gdb_path, gdf_points, gdf_lines, gdf_polygons):
    gdb = ob.GeoDatabase()
    gdb["test_points1"] = ob.FeatureClass(gdf_points)
    gdb["test_lines1"] = ob.FeatureClass(gdf_lines)
    gdb["test_polygons1"] = ob.FeatureClass(gdf_polygons)

    fds = ob.FeatureDataset(gdf_points.crs)
    fds["test_points2"] = ob.FeatureClass(gdf_points)
    fds["test_lines2"] = ob.FeatureClass(gdf_lines)
    fds["test_polygons2"] = ob.FeatureClass(gdf_polygons)

    gdb["test_fds"] = fds
    gdb.save(gdb_path)
    return gdb, gdb_path


def test_gdb_fixture(gdb):
    gdb, gdb_path = gdb
    assert isinstance(gdb, ob.GeoDatabase)
    for fds_name, fds in gdb.items():
        assert isinstance(fds_name, str) or fds_name is None
        assert isinstance(fds, ob.FeatureDataset)

        for fc_name, fc in fds.items():
            assert isinstance(fc_name, str)
            assert isinstance(fc, ob.FeatureClass)


class TestFeatureClass:
    def test_instantiate_fc(self, fc_points, fds_fc_points):
        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            fc = ob.FeatureClass(0)

        fc1 = ob.FeatureClass(fc_points)
        assert isinstance(fc1.to_geodataframe(), gpd.GeoDataFrame)

        fc2 = ob.FeatureClass(fds_fc_points)
        assert isinstance(fc2.to_geodataframe(), gpd.GeoDataFrame)

    def test_instatiate_gdf(self):
        fc1 = ob.FeatureClass(gpd.GeoDataFrame(geometry=[Point(0, 1)]))
        assert isinstance(fc1.to_geodataframe(), gpd.GeoDataFrame)

        fc2 = ob.FeatureClass(gpd.GeoDataFrame(geometry=[]))
        assert isinstance(fc2.to_geodataframe(), gpd.GeoDataFrame)

    def test_instatiate_none(self):
        fc1 = ob.FeatureClass()
        assert isinstance(fc1.to_geodataframe(), gpd.GeoDataFrame)
        assert len(fc1.to_geodataframe()) == 0

    def test_delitem(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        del fc1[500]
        assert len(fc1) == SAMPLES - 1
        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            del fc1["test"]

    def test_getitem(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        assert isinstance(fc1[0], gpd.GeoDataFrame)
        assert isinstance(fc1[-1], gpd.GeoDataFrame)
        assert isinstance(fc1[100:105], gpd.GeoDataFrame)
        assert isinstance(fc1[100, 200, 300], gpd.GeoDataFrame)
        assert isinstance(fc1[(100, 200, 300)], gpd.GeoDataFrame)
        assert isinstance(fc1[[100, 200, 300]], gpd.GeoDataFrame)
        assert isinstance(fc1[10, 100:105, 200, 300:305], gpd.GeoDataFrame)
        with pytest.raises(KeyError):
            # noinspection PyTypeChecker
            x = fc1["test"]

    def test_iter(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        for row in fc1:
            assert isinstance(row, tuple)
            assert isinstance(row[0], int)
            assert isinstance(row[1], str)
            assert isinstance(row[2], str)
            assert isinstance(row[3], str)
            assert isinstance(row[4], Point)

    def test_len(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        assert len(fc1) == SAMPLES

    def test_setitem(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        fc1[(0, "geometry")] = None
        fc1[(-1, 0)] = None
        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            fc1[("s", "geometry")] = None
        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            fc1[(0, dict())] = None

    def test_append(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        count = len(fc1)
        new_row = fc1[0]
        fc1.append(new_row)
        assert len(fc1) == count + 1
        assert fc1[0].iat[0, 0] == fc1[-1].iat[0, 0]

    def test_clear(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        fc1.clear()
        assert len(fc1) == 0

    def test_copy(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        fc2 = fc1.copy()
        assert len(fc1) == len(fc2)
        assert fc1 != fc2

    def test_describe(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        pprint(fc1.describe())
        assert isinstance(fc1.describe(), dict)
        assert len(fc1.describe()["fields"]) == 5
        fc2 = ob.FeatureClass()
        assert fc2.describe()["row_count"] == 0

    def test_head(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        h = fc1.head(5)
        assert isinstance(h, pd.DataFrame)
        assert len(h) == 5

    def test_insert(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        new_row = fc1[500]
        fc1.insert(600, new_row)
        assert len(fc1) == SAMPLES + 1
        assert fc1[500].iat[0, 0] == fc1[600].iat[0, 0]
        fc1.insert(0, new_row)
        fc1.insert(-1, new_row)

        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            fc1.insert("s", new_row)
        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            fc1.insert(0, "s")
        with pytest.raises(ValueError):
            fc1.insert(500, gpd.GeoDataFrame())
        with pytest.raises(ValueError):
            fc1.insert(500, gpd.GeoDataFrame(columns=["test"]))

        with pytest.raises(TypeError):
            fc2 = ob.FeatureClass(gpd.GeoDataFrame(geometry=[Point(0, 1)]))
            fc2.insert(
                -1,
                gpd.GeoDataFrame(
                    geometry=[
                        LineString([(0, 1), (1, 1)]),
                        Point(0, 1),
                    ]
                ),
            )

        # validate geometry
        fc3 = ob.FeatureClass()
        assert fc3.geom_type is None

        fc3 = ob.FeatureClass(gpd.GeoDataFrame({"col1": ["a"]}, geometry=[None]))
        assert fc3.geom_type == "Unknown"

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
                geometry=[LineString([(0, 1), (1, 1)])],
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

    def test_save(self, gdf_points, gdb_path):
        fc1 = ob.FeatureClass(gdf_points)

        fc1.save(
            gdb_path=gdb_path,
            fc_name="test_points1",
            feature_dataset=None,
            overwrite=False,
        )
        fc1.save(
            gdb_path=gdb_path,
            fc_name="test_points2",
            feature_dataset="test_fds",
            overwrite=False,
        )
        with pytest.raises(FileExistsError):
            fc1.save(
                gdb_path=gdb_path,
                fc_name="test_points2",
                feature_dataset="test_fds",
                overwrite=False,
            )

        with pytest.raises(FileNotFoundError):
            fc1.save("bad_path", "fc_name")

    def test_sort(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        case1 = fc1[0].iat[0, 0]
        fc1.sort("sample1", ascending=True)
        case2 = fc1[0].iat[0, 0]
        fc1.sort("sample1", ascending=False)
        case3 = fc1[0].iat[0, 0]
        assert case1 != case2 != case3

    def test_to_geodataframe(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        gdf = fc1.to_geodataframe()
        assert isinstance(gdf, gpd.GeoDataFrame)

    def test_to_geojson(self, tmp_path, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        gjs1 = fc1.to_geojson()
        assert isinstance(gjs1, geojson.FeatureCollection)

        fc1.to_geojson(os.path.join(tmp_path, "test"))
        with open(os.path.join(tmp_path, "test.geojson"), "r") as f:
            gjs2 = geojson.load(f)
        assert isinstance(gjs2, geojson.FeatureCollection)

    def test_to_pyarrow(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        arr = fc1.to_pyarrow()
        assert isinstance(arr, pa.Table)

    def test_to_shapefile(self, tmp_path, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        fc1.to_shapefile(os.path.join(tmp_path, "test"))
        shp = gpd.read_file(os.path.join(tmp_path, "test.shp"))
        assert isinstance(shp, gpd.GeoDataFrame)


class TestFeatureDataset:
    def test_instantiate(self, gdb):
        gdb, gdb_path = gdb
        for fds_name, fds in gdb.items():
            assert isinstance(fds_name, str) or fds_name is None
            assert isinstance(fds, ob.FeatureDataset)

            for fc_name, fc in fds.items():
                assert isinstance(fc_name, str)
                assert isinstance(fc, ob.FeatureClass)

        fds = ob.FeatureDataset("EPSG:4326")

    def test_delitem(self, gdb):
        gdb, gdb_path = gdb
        for fds in gdb.values():
            fcs = fds.feature_classes()
            for fc_name, fc in fcs:
                del fds[fc_name]
            assert len(fds) == 0

    def test_getitem(self, gdb):
        gdb, gdb_path = gdb
        for fds in gdb.values():
            fc_names = fds.keys()
            for fc_name in fc_names:
                assert isinstance(fds[fc_name], ob.FeatureClass)
            assert isinstance(fds[0], ob.FeatureClass)
            with pytest.raises(IndexError):
                f = fds[999]

    def test_iter(self, gdb):
        gdb, gdb_path = gdb
        for fds in gdb.values():
            for fc_name in fds:
                assert isinstance(fds[fc_name], ob.FeatureClass)

    def test_len(self, gdb):
        gdb, gdb_path = gdb
        for fds in gdb.values():
            assert len(fds) == 3

    def test_setitem(self, gdb):
        gdb, gdb_path = gdb
        with pytest.raises(KeyError):
            fds: ob.FeatureDataset
            for fds in gdb.values():
                fds.__setitem__(
                    "fc_test",
                    ob.FeatureClass(
                        gpd.GeoDataFrame(
                            geometry=[
                                LineString([(0, 1), (1, 1)]),
                                Point(0, 1),
                            ],
                            crs="EPSG:4326",
                        )
                    ),
                )

        fds: ob.FeatureDataset
        for fds in gdb.values():
            fc_names = list(fds.keys())
            for fc_name in fc_names:
                fds.__setitem__(fc_name + "_copy", fds[fc_name])
            assert len(fds) == 6 or len(fds) == 8

            with pytest.raises(TypeError):
                # noinspection PyTypeChecker
                fds.__setitem__("bad", 0)

            with pytest.raises(ValueError):
                fds.__setitem__("0_bad", ob.FeatureClass())

            with pytest.raises(ValueError):
                fds.__setitem__("bad!@#$", ob.FeatureClass())

    def test_feature_classes(self, gdb):
        gdb, gdb_path = gdb
        for fds in gdb.values():
            for fc_name, fc in fds.feature_classes():
                assert isinstance(fc_name, str)
                assert isinstance(fc, ob.FeatureClass)

    def test_crs(self, gdb):
        gdb, gdb_path = gdb
        for idx, fds in enumerate(gdb.values()):
            test_fc = ob.FeatureClass()
            with pytest.raises(AttributeError):
                assert test_fc.crs != fds.crs
                fds[f"bad_fc_{idx}"] = test_fc

        fds2 = ob.FeatureDataset()
        fds2["fc1"] = ob.FeatureClass(gpd.GeoDataFrame(geometry=[], crs="EPSG:4326"))
        assert fds2.crs.equals("EPSG:4326")


class TestGeoDatabase:
    def test_instantiate(self, gdb):
        gdb, gdb_path = gdb
        assert isinstance(gdb, ob.GeoDatabase)

        gdb2 = ob.GeoDatabase(gdb_path)
        assert len(gdb2.feature_datasets()) == 2
        assert len(gdb2.feature_classes()) == 6

    def test_delitem(self, gdb):
        gdb, gdb_path = gdb

        for fds_name, fds in gdb.feature_datasets():
            for fc_name, fc in gdb.feature_classes():
                try:
                    del gdb[fds_name][fc_name]
                except KeyError:
                    pass
            assert len(fds) == 0
            del gdb[fds_name]
        assert len(gdb.feature_datasets()) == 0

        assert len(gdb) == 0

    def test_getitem(self, gdb):
        gdb, gdb_path = gdb
        for fds_name, fds in gdb.feature_datasets():
            for fc_name, fc in fds.feature_classes():
                assert isinstance(gdb[fds_name][fc_name], ob.FeatureClass)

        with pytest.raises(KeyError):
            f = gdb["bad"]

        for idx in range(len(gdb)):
            f = gdb[idx]

        with pytest.raises(IndexError):
            f = gdb[999]

        with pytest.raises(KeyError):
            # noinspection PyTypeChecker
            f = gdb[list()]

        fc = gdb["test_points1"]
        assert isinstance(fc, ob.FeatureClass)

    def test_hash(self, gdb):
        gdb, gdb_path = gdb
        assert isinstance(gdb.__hash__(), int)

    def test_iter(self, gdb):
        gdb, gdb_path = gdb
        for gdf_name in gdb:
            assert isinstance(gdf_name, str) or gdf_name is None

    def test_len(self, gdb):
        gdb, gdb_path = gdb
        assert len(gdb) == 6

    def test_setitem(self, gdb):
        gdb, gdb_path = gdb
        new_gdb = ob.GeoDatabase()
        for fds_name, fds in gdb.feature_datasets():
            new_gdb[fds_name] = fds
            with pytest.raises(KeyError):
                new_gdb[fds_name] = fds

        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            gdb["bad"] = 99

    def test_feature_classes(self, gdb):
        gdb, gdb_path = gdb
        for fc_name, fc in gdb.feature_classes():
            assert isinstance(fc_name, str)
            assert isinstance(fc, ob.FeatureClass)

    def test_feature_datasets(self, gdb):
        gdb, gdb_path = gdb
        for fds_name, fds in gdb.feature_datasets():
            assert isinstance(fds_name, str) or fds_name is None
            assert isinstance(fds, ob.FeatureDataset)

    def test_save(self, tmp_path, gdb):
        gdb, gdb_path = gdb
        out_path = tmp_path / "out.gdb"
        gdb.save(out_path, overwrite=False)
        assert len(ob.list_layers(out_path)) > 0

        with pytest.raises(FileExistsError):
            gdb.save(out_path, overwrite=False)

        gdb.save(out_path, overwrite=True)
        assert len(ob.list_layers(out_path)) > 0

        out_path2 = tmp_path / "out2"
        gdb.save(out_path2, overwrite=False)
        assert len(ob.list_layers(str(out_path2) + ".gdb")) > 0


class TestUtilityFunctions:
    def test_delete_fc(self, gdb):
        gdb, gdb_path = gdb
        fcs = ob.list_layers(gdb_path)
        count = len(fcs)
        for fc_name in fcs:
            ob.delete_fc(gdb_path, fc_name)
            assert len(ob.list_layers(gdb_path)) < count
            count -= 1
            assert ob.delete_fc(gdb_path, "bad_fc_name") is False
        assert len(ob.list_layers(gdb_path)) == count
        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            ob.delete_fc(gdb_path, 0)

    def test_fc_to_gdf(self, gdb):
        gdb, gdb_path = gdb
        for fc in ob.list_layers(gdb_path):
            gdf = ob.fc_to_gdf(gdb_path, fc)
            assert isinstance(gdf, gpd.GeoDataFrame)
        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            ob.fc_to_gdf(gdb_path, 0)

    def test_gdf_to_fc(self, gdb):
        gdb, gdb_path = gdb
        count = 0
        for fds in gdb.values():
            for fc_name, fc in fds.items():
                gdf = fc.to_geodataframe()
                ob.gdf_to_fc(gdf, gdb_path, fc_name + "_copy")
                ob.gdf_to_fc(gdf, gdb_path, fc_name, overwrite=True)
                count += 2
        assert count == len(ob.list_layers(gdb_path))

        with pytest.raises(FileNotFoundError):
            ob.gdf_to_fc(gpd.GeoDataFrame(), "thisfiledoesnotexist", "test")

        # noinspection PyUnresolvedReferences
        with pytest.raises(pyogrio.errors.GeometryError):
            for fc_name, fc in gdb.feature_classes():
                ob.gdf_to_fc(
                    gdf=fc.to_geodataframe(),
                    gdb_path=gdb_path,
                    fc_name=fc_name,
                    feature_dataset=None,
                    geometry_type="no",
                    overwrite=True,
                )

        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            ob.gdf_to_fc(list(), gdb_path, "test")

        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            ob.gdf_to_fc(gpd.GeoDataFrame, "test", "test", overwrite="yes")

        ob.gdf_to_fc(
            gpd.GeoSeries([LineString([(0, 1), (1, 1)])]),
            gdb_path,
            "geoseries",
            overwrite=True,
        )

    def test_list_datasets(self, gdb):
        gdb, gdb_path = gdb
        fds = ob.list_datasets(gdb_path)
        assert len(fds) == 2
        for k, v in fds.items():
            assert isinstance(k, str) or k is None
            assert isinstance(v, list)

        gdb2 = ob.GeoDatabase()
        gdb2.save(gdb_path, overwrite=True)
        fds2 = ob.list_datasets(gdb_path)
        assert isinstance(fds2, dict)
        assert len(fds2) == 0

    def test_list_layers(self, gdb):
        gdb, gdb_path = gdb
        assert len(ob.list_layers(gdb_path)) == 6


class TestUsage:
    def test_add_fcs(self, gdf_points, gdf_lines, gdf_polygons):
        gdb1 = ob.GeoDatabase()
        fc1 = ob.FeatureClass(src=gdf_points)
        fc2 = ob.FeatureClass(src=gdf_lines)
        fc3 = ob.FeatureClass(src=gdf_polygons)

        gdb1["fc_1"] = fc1
        gdb1["fc_2"] = fc2
        gdb1["fc_3"] = fc3

        with pytest.raises(KeyError):
            gdb1["fc_1"] = fc1

        with pytest.raises(KeyError):
            gdb1["fc_1"] = fc1

        with pytest.raises(KeyError):
            gdb1["bad"]["fc_1"] = fc1

        with pytest.raises(KeyError):
            gdb1["bad"]["fc_1"] = fc1

    def test_add_fds(self, gdf_points, gdf_lines, gdf_polygons):
        gdb1 = ob.GeoDatabase()
        fc1 = ob.FeatureClass(src=gdf_points)
        fc2 = ob.FeatureClass(src=gdf_lines)
        fc3 = ob.FeatureClass(src=gdf_polygons)
        fds = ob.FeatureDataset(crs=fc1.crs)

        gdb1["fds_1"] = fds
        gdb1["fds_1"]["fc_1"] = fc1
        gdb1["fds_1"]["fc_2"] = fc2
        gdb1["fds_1"]["fc_3"] = fc3

        with pytest.raises(KeyError):
            gdb1["fc_1"] = fc1

        with pytest.raises(KeyError):
            gdb1["fc_1"] = fc1

        with pytest.raises(KeyError):
            gdb1["fds_1"]["fc_1"] = fc1

        with pytest.raises(KeyError):
            gdb1["fds_1"]["fc_1"] = fc1

        with pytest.raises(KeyError):
            gdb1["bad"]["fc_1"] = fc1

        with pytest.raises(KeyError):
            # noinspection PyTypeChecker
            gdb1["fds1"]["bad"]["fc_1"] = fc1

    def test_iters(self, gdb):
        gdb, gdb_path = gdb

        for fds_name, fds in gdb.items():
            for fc_name, fc in fds.items():
                assert isinstance(fc_name, str)
                assert isinstance(fc, ob.FeatureClass)

        for fds_name, fds in gdb.feature_datasets():
            for fc_name, fc in fds.items():
                assert isinstance(fc_name, str)
                assert isinstance(fc, ob.FeatureClass)

        for fc_name, fc in gdb.feature_classes():
            assert isinstance(fc_name, str)
            assert isinstance(fc, ob.FeatureClass)

        this_fds = None
        for fds in gdb:
            # noinspection PyTypeChecker
            this_fds = gdb[fds]
            break
        for fc_name, fc in this_fds.feature_classes():
            assert isinstance(fc_name, str)
            assert isinstance(fc, ob.FeatureClass)
