import os
import uuid
import zipfile
from random import uniform

import geojson
import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import pytest
from shapely.geometry import LineString, MultiLineString, Point

import ouroboros as ob


SAMPLES = 1000


@pytest.fixture
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
    gdb["test_lines1"] = ob.FeatureClass(gdf_lines)
    gdb["test_polygons1"] = ob.FeatureClass(gdf_polygons)

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


def test_gdb_fixtures(ob_gdb, esri_gdb):
    gdb, gdb_path = ob_gdb

    for this_gdb in [gdb, ob.GeoDatabase(path=esri_gdb)]:
        assert isinstance(this_gdb, ob.GeoDatabase)
        for fds_name, fds in this_gdb.items():
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

        fc3 = ob.FeatureClass(gpd.GeoSeries([Point(0, 1)]))
        assert isinstance(fc3.to_geodataframe(), gpd.GeoDataFrame)

        fc4 = ob.FeatureClass(fc3)
        assert isinstance(fc4.to_geodataframe(), gpd.GeoDataFrame)

        with pytest.raises(TypeError):
            fc5 = ob.FeatureClass("test.gdb")

        with pytest.raises(FileNotFoundError):
            fc5 = ob.FeatureClass("doesnotexist.gdb/test_fc")

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

        fc2 = ob.FeatureClass(fc1)
        count = len(fc2)
        new_row = ob.FeatureClass(fc2[0])
        fc2.append(new_row)
        assert len(fc2) == count + 1
        assert fc2[0].iat[0, 0] == fc2[-1].iat[0, 0]

        with pytest.raises(TypeError):
            fc2.append("bad_input")

    def test_calculate(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        fc1.calculate(
            "sample1",
            "test",
        )
        # fc1.select_columns("sample1", geometry=False).head()

        fc2 = ob.FeatureClass(gdf_points)
        fc2.calculate(
            "test2",
            "test",
        )
        # fc2.select_columns("test2", geometry=False).head()

        fc3 = ob.FeatureClass(gdf_points)
        fc3.calculate("test3", 2 * 2, np.uint8)
        # fc3.select_columns("test3", geometry=False).head()

        fc4 = ob.FeatureClass(gdf_points)
        fc4.calculate(
            "test4",
            "$sample2$ + '___' + $sample2$ + '___' + $sample3$",
            str,
        )
        # fc4.select_columns("test4", geometry=False).head()

        with pytest.raises(KeyError):
            fc4.calculate("sample1", "$badcol$")

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
        assert isinstance(fc1.describe(), dict)
        assert len(fc1.describe()["fields"]) == 5
        fc2 = ob.FeatureClass()
        assert fc2.describe()["row_count"] == 0

    def test_head(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        fc1.head(0, silent=False)
        h = fc1.head(5, silent=True)
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
            ob.FeatureClass(
                gpd.GeoDataFrame(
                    {"col1": ["c"]},
                    geometry=[LineString([(0, 1), (1, 1)])],
                )
            ),
        )

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

    def test_select_columns(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        cols1 = fc1.select_columns(["sample1", "sample2"])
        assert len(cols1) == 1000

        cols2 = fc1.select_columns(["sample1"], geometry=False)
        assert len(cols2) == 1000

        cols3 = fc1.select_columns("sample1", geometry=False)
        assert len(cols3) == 1000

        cols4 = fc1.select_columns("geometry", geometry=False)
        assert len(cols4) == 1000

        cols5 = fc1.select_columns(["sample1", "sample2", "geometry"], geometry=False)
        assert len(cols5) == 1000

        with pytest.raises(KeyError):
            bad_cols = fc1.select_columns(["bad"])

    def test_select_rows(self, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        rows1 = fc1.select_rows("ObjectID < 10")
        assert len(rows1) == 10
        rows1 = fc1.select_rows("sample1 > sample2")
        assert len(rows1) < SAMPLES

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

        fc1.to_geojson(os.path.join(tmp_path, "test1"))
        with open(os.path.join(tmp_path, "test1.geojson"), "r") as f:
            gjs2 = geojson.load(f)
        assert isinstance(gjs2, geojson.FeatureCollection)

        # no geometry
        fc2 = ob.FeatureClass(pd.Series({"col1": [0, 1, 2]}))
        gjs2 = fc2.to_geojson()
        assert isinstance(gjs2, dict)
        fc2.to_geojson(os.path.join(tmp_path, "test2"))

        # no features
        fc3 = ob.FeatureClass(
            gpd.GeoDataFrame({"col1": [], "geometry": []}, crs="WGS 84")
        )
        with pytest.raises(ValueError):
            gjs3 = fc3.to_geojson()
        with pytest.raises(ValueError):
            fc3.to_geojson(os.path.join(tmp_path, "test3"))

        # not JSON serializable
        some_object = object()
        fc4 = ob.FeatureClass(
            gpd.GeoDataFrame(
                {"col1": [some_object]},
                geometry=[LineString([(0, 1), (1, 1)])],
                crs="WGS 84",
            )
        )
        # GeoDataFrame.to_file() can handle objects but .to_json() cannot
        with pytest.raises(TypeError):
            fc4.to_geojson()
        fc4.to_geojson(os.path.join(tmp_path, "test4"))
        with open(os.path.join(tmp_path, "test4.geojson"), "r") as f:
            gjs4 = geojson.load(f)
        assert isinstance(gjs4, geojson.FeatureCollection)

    def test_to_shapefile(self, tmp_path, gdf_points):
        fc1 = ob.FeatureClass(gdf_points)
        fc1.to_shapefile(os.path.join(tmp_path, "test"))
        shp = gpd.read_file(os.path.join(tmp_path, "test.shp"))
        assert isinstance(shp, gpd.GeoDataFrame)


class TestFeatureDataset:
    def test_instantiate(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for fds_name, fds in gdb.items():
            assert isinstance(fds_name, str) or fds_name is None
            assert isinstance(fds, ob.FeatureDataset)

            for fc_name, fc in fds.items():
                assert isinstance(fc_name, str)
                assert isinstance(fc, ob.FeatureClass)

        fds1 = ob.FeatureDataset(crs="EPSG:4326")
        fds2 = ob.FeatureDataset(contents={"fc": ob.FeatureClass()})

    def test_delitem(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for fds in gdb.values():
            fcs = list(fds.feature_classes().keys())
            for fc_name in fcs:
                del fds[fc_name]
            assert len(fds) == 0

    def test_getitem(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for fds in gdb.values():
            fc_names = fds.keys()
            for fc_name in fc_names:
                assert isinstance(fds[fc_name], ob.FeatureClass)
            assert isinstance(fds[0], ob.FeatureClass)
            with pytest.raises(IndexError):
                f = fds[999]

    def test_iter(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for fds in gdb.values():
            for fc_name in fds:
                assert isinstance(fds[fc_name], ob.FeatureClass)

    def test_len(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for fds in gdb.values():
            assert len(fds) == 3

    def test_setitem(self, ob_gdb):
        gdb, gdb_path = ob_gdb
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

    def test_feature_classes(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for fds in gdb.values():
            for fc_name, fc in fds.feature_classes().items():
                assert isinstance(fc_name, str)
                assert isinstance(fc, ob.FeatureClass)

    def test_crs(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for idx, fds in enumerate(gdb.values()):
            test_fc = ob.FeatureClass()
            with pytest.raises(AttributeError):
                assert test_fc.crs != fds.crs
                fds[f"bad_fc_{idx}"] = test_fc

        fds2 = ob.FeatureDataset()
        fds2["fc1"] = ob.FeatureClass(gpd.GeoDataFrame(geometry=[], crs="EPSG:4326"))
        assert fds2.crs.equals("EPSG:4326")


class TestGeoDatabase:
    def test_instantiate(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        assert isinstance(gdb, ob.GeoDatabase)

        gdb2 = ob.GeoDatabase(
            path=gdb_path,
            contents={"extra_fc": ob.FeatureClass(), "extra_fds": ob.FeatureDataset()},
        )
        assert len(gdb2.feature_datasets()) == 3
        assert len(gdb2.feature_classes()) == 7

        with pytest.raises(FileNotFoundError):
            gdb3 = ob.GeoDatabase("doesnotexist.gdb")

    def test_delitem(self, ob_gdb):
        gdb, gdb_path = ob_gdb

        for fds_name in list(gdb.feature_datasets().keys()):
            for fc_name in list(gdb.feature_classes().keys()):
                try:
                    del gdb[fds_name][fc_name]
                except KeyError:
                    pass
            assert len(gdb[fds_name]) == 0
            del gdb[fds_name]
        assert len(gdb.feature_datasets()) == 0

        assert len(gdb) == 0

    def test_getitem(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for fds_name, fds in gdb.feature_datasets().items():
            for fc_name, fc in fds.feature_classes().items():
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

    def test_hash(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        assert isinstance(gdb.__hash__(), int)

    def test_iter(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for gdf_name in gdb:
            assert isinstance(gdf_name, str) or gdf_name is None

    def test_len(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        assert len(gdb) == 6

    def test_setitem(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        new_gdb = ob.GeoDatabase()
        for fds_name, fds in gdb.feature_datasets().items():
            new_gdb[fds_name] = fds
            with pytest.raises(KeyError):
                new_gdb[fds_name] = fds

        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            gdb["bad"] = 99

    def test_feature_classes(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for fc_name, fc in gdb.feature_classes().items():
            assert isinstance(fc_name, str)
            assert isinstance(fc, ob.FeatureClass)

    def test_feature_datasets(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for fds_name, fds in gdb.feature_datasets().items():
            # noinspection PyUnreachableCode
            assert isinstance(fds_name, str) or fds_name is None
            assert isinstance(fds, ob.FeatureDataset)

    def test_save(self, tmp_path, ob_gdb):
        gdb, gdb_path = ob_gdb
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
    def test_fc_to_gdf(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        for fc in ob.list_layers(gdb_path):
            gdf = ob.fc_to_gdf(gdb_path, fc)
            assert isinstance(gdf, gpd.GeoDataFrame)
        with pytest.raises(TypeError):
            # noinspection PyTypeChecker
            ob.fc_to_gdf(gdb_path, 0)

    def test_gdf_to_fc(self, ob_gdb):
        gdb, gdb_path = ob_gdb
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
            for fc_name, fc in gdb.feature_classes().items():
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

    def test_get_info(self, tmp_path, esri_gdb):
        gdb = ob.GeoDatabase(
            contents={
                "fds": ob.FeatureDataset(
                    {
                        "fc": ob.FeatureClass(
                            gpd.GeoDataFrame(
                                {"col1": ["c"]},
                                geometry=[LineString([(0, 1), (1, 1)])],
                                crs="WGS 84",
                            ),
                        )
                    }
                )
            }
        )
        gdb_path = tmp_path / "out.gdb"
        gdb.save(gdb_path, overwrite=True)
        info = ob.get_info(gdb_path)
        assert isinstance(info, dict)

        info = ob.get_info(esri_gdb)
        assert isinstance(info, dict)

        with pytest.raises(FileNotFoundError):
            ob.get_info("bad_path")

        with pytest.raises(TypeError):
            try:  # pytest
                ob.get_info("pyproject.toml")
            except FileNotFoundError:  # coverage
                ob.get_info(os.path.join("..", "pyproject.toml"))

    def test_list_datasets(self, ob_gdb, esri_gdb):
        gdb, gdb_path = ob_gdb
        fds1 = ob.list_datasets(gdb_path)
        assert len(fds1) == 2
        for k, v in fds1.items():
            assert isinstance(k, str) or k is None
            assert isinstance(v, list)

        fds3 = ob.list_datasets(esri_gdb)
        assert isinstance(fds3, dict)
        assert len(fds3) == 0

        with pytest.raises(FileNotFoundError):
            ob.list_datasets("bad_path")

        with pytest.raises(TypeError):
            try:  # pytest
                ob.list_datasets("pyproject.toml")
            except FileNotFoundError:  # coverage
                ob.list_datasets(os.path.join("..", "pyproject.toml"))

    def test_list_layers(self, ob_gdb):
        gdb, gdb_path = ob_gdb
        lyrs = ob.list_layers(gdb_path)
        assert len(lyrs) == 6

        with pytest.raises(FileNotFoundError):
            ob.list_layers("bad_path")

        with pytest.raises(TypeError):
            try:  # pytest
                ob.list_layers("pyproject.toml")
            except FileNotFoundError:  # coverage
                ob.list_layers(os.path.join("..", "pyproject.toml"))

    def test_list_rasters(self, ob_gdb, esri_gdb):
        rasters = ob.list_rasters(esri_gdb)
        assert len(rasters) == 1
        for raster in rasters:
            assert isinstance(raster, str)

        gdb, gdb_path = ob_gdb
        rasters = ob.list_rasters(gdb_path)
        assert len(rasters) == 0

        with pytest.raises(FileNotFoundError):
            ob.list_rasters("bad_path")

        with pytest.raises(TypeError):
            try:  # pytest
                ob.list_rasters("pyproject.toml")
            except FileNotFoundError:  # coverage
                ob.list_rasters(os.path.join("..", "pyproject.toml"))

    def test_raster_to_tif(self, tmp_path, capsys, esri_gdb):
        if not ob.gdal_installed:
            pytest.skip("GDAL is not installed")
        else:
            with capsys.disabled():
                print("\n\t*** GDAL installed:", ob.gdal_installed, "***")
            ob.raster_to_tif(
                gdb_path=esri_gdb,
                raster_name="random_raster",
                tif_path=None,
            )

            tif_path = tmp_path / "test"
            ob.raster_to_tif(
                gdb_path=esri_gdb,
                raster_name="random_raster",
                tif_path=str(tif_path),
            )

            tif_path = tmp_path / "test.tif"
            ob.raster_to_tif(
                gdb_path=esri_gdb,
                raster_name="random_raster",
                tif_path=str(tif_path),
                options={"TILED": "YES"},
            )


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

    def test_iters(self, ob_gdb):
        gdb, gdb_path = ob_gdb

        for fds_name, fds in gdb.items():
            for fc_name, fc in fds.items():
                assert isinstance(fc_name, str)
                assert isinstance(fc, ob.FeatureClass)

        for fds_name, fds in gdb.feature_datasets().items():
            for fc_name, fc in fds.items():
                assert isinstance(fc_name, str)
                assert isinstance(fc, ob.FeatureClass)

        for fc_name, fc in gdb.feature_classes().items():
            assert isinstance(fc_name, str)
            assert isinstance(fc, ob.FeatureClass)

        this_fds = None
        for fds in gdb:
            # noinspection PyTypeChecker
            this_fds = gdb[fds]
            break
        for fc_name, fc in this_fds.feature_classes().items():
            assert isinstance(fc_name, str)
            assert isinstance(fc, ob.FeatureClass)
