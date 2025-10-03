import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import pytest
import shapely

import ouroboros as ob


def test_instantiate_fc(fc_points, fds_fc_points):
    with pytest.raises(TypeError):
        fc = ob.FeatureClass(0)  # noqa: F841

    fc1 = ob.FeatureClass(fc_points)
    assert isinstance(fc1.gdf, gpd.GeoDataFrame)

    fc2 = ob.FeatureClass(fds_fc_points)
    assert isinstance(fc2.gdf, gpd.GeoDataFrame)

    fc3 = ob.FeatureClass(gpd.GeoSeries([shapely.Point(0, 1)]))
    assert isinstance(fc3.gdf, gpd.GeoDataFrame)

    fc4 = ob.FeatureClass(fc3)
    assert isinstance(fc4.gdf, gpd.GeoDataFrame)

    with pytest.raises(TypeError):
        fc5 = ob.FeatureClass("test.gdb")

    with pytest.raises(FileNotFoundError):
        fc5 = ob.FeatureClass("doesnotexist.gdb/test_fc")  # noqa: F841


def test_instatiate_gdf():
    fc1 = ob.FeatureClass(gpd.GeoDataFrame(geometry=[shapely.Point(0, 1)]))
    assert isinstance(fc1.gdf, gpd.GeoDataFrame)

    fc2 = ob.FeatureClass(gpd.GeoDataFrame(geometry=[]))
    assert isinstance(fc2.gdf, gpd.GeoDataFrame)


def test_instatiate_none():
    fc1 = ob.FeatureClass()
    assert isinstance(fc1.gdf, gpd.GeoDataFrame)
    assert len(fc1.gdf) == 0


def test_delitem(gdf_points, samples):
    fc1 = ob.FeatureClass(gdf_points)
    del fc1[500]
    assert len(fc1) == samples - 1
    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        del fc1["test"]


def test_getitem(gdf_points):
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
        x = fc1["test"]  # noqa: F841


def test_iter(gdf_points):
    fc1 = ob.FeatureClass(gdf_points)
    for row in fc1:
        assert isinstance(row, tuple)
        assert isinstance(row[0], int)
        assert isinstance(row[1], str)
        assert isinstance(row[2], str)
        assert isinstance(row[3], str)
        assert isinstance(row[4], shapely.Point)


def test_len(gdf_points, samples):
    fc1 = ob.FeatureClass(gdf_points)
    assert len(fc1) == samples


def test_setitem(gdf_points):
    fc1 = ob.FeatureClass(gdf_points)
    fc1[(0, "geometry")] = None
    fc1[(-1, 0)] = None
    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        fc1[("s", "geometry")] = None
    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        fc1[(0, dict())] = None


def test_crs(ob_gdb):
    gdb, gdb_path = ob_gdb

    for fc in gdb.fcs:
        assert isinstance(fc.crs, pyproj.crs.CRS)

    fc1 = ob.FeatureClass()
    assert fc1.crs is None


def test_gdf(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fc in gdb.fcs:
        assert isinstance(fc.gdf, gpd.GeoDataFrame)


def test_geom_type(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fc in gdb.fcs:
        assert fc.geom_type in (
            "Point",
            "MultiPoint",
            "LineString",
            "MultiLineString",
            "Polygon",
            "MultiPolygon",
            None,
        )

    fc1 = ob.FeatureClass()
    assert fc1.geom_type is None


def test_geometry(gdf_polygons):
    fc1 = ob.FeatureClass(gdf_polygons)
    assert isinstance(fc1.geometry.bounds, pd.DataFrame)
    with pytest.raises(AttributeError):
        fc1.geometry = False  # noqa

    fc2 = ob.FeatureClass()
    assert fc2.geometry is None


def test_append(gdf_points):
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


def test_calculate(gdf_points):
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


def test_clear(gdf_points):
    fc1 = ob.FeatureClass(gdf_points)
    fc1.clear()
    assert len(fc1) == 0


def test_copy(gdf_points):
    fc1 = ob.FeatureClass(gdf_points)
    fc2 = fc1.copy()
    assert len(fc1) == len(fc2)
    assert fc1 != fc2


def test_head(gdf_points):
    fc1 = ob.FeatureClass(gdf_points)
    fc1.head(0, silent=False)
    h = fc1.head(5, silent=True)
    assert isinstance(h, pd.DataFrame)
    assert len(h) == 5


def test_insert(gdf_points, samples):
    fc1 = ob.FeatureClass(gdf_points)
    new_row = fc1[500]
    fc1.insert(600, new_row)
    assert len(fc1) == samples + 1
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
        fc2 = ob.FeatureClass(gpd.GeoDataFrame(geometry=[shapely.Point(0, 1)]))
        fc2.insert(
            -1,
            gpd.GeoDataFrame(
                geometry=[
                    shapely.LineString([(0, 1), (1, 1)]),
                    shapely.Point(0, 1),
                ]
            ),
        )

    # validate geometry
    fc3 = ob.FeatureClass()
    assert fc3.geom_type is None

    fc3 = ob.FeatureClass(gpd.GeoDataFrame({"col1": ["a"]}, geometry=[None]))
    assert fc3.geom_type is None

    fc3.insert(
        -1,
        gpd.GeoDataFrame({"col1": ["aa"]}, geometry=[None]),
    )
    assert fc3.geom_type is None

    fc3.insert(
        -1,
        gpd.GeoDataFrame(
            {"col1": ["b"]}, geometry=[shapely.LineString([(0, 1), (1, 1)])]
        ),
    )
    assert fc3.geom_type == "LineString"

    fc3.insert(
        -1,
        ob.FeatureClass(
            gpd.GeoDataFrame(
                {"col1": ["c"]},
                geometry=[shapely.LineString([(0, 1), (1, 1)])],
            )
        ),
    )

    fc3.insert(
        -1,
        gpd.GeoDataFrame(
            {"col1": ["c"]},
            geometry=[shapely.LineString([(0, 1), (1, 1)])],
        ),
    )

    with pytest.raises(TypeError):
        fc3.insert(
            -1,
            gpd.GeoDataFrame(
                {"col1": ["d", "e"]},
                geometry=[
                    shapely.LineString([(0, 1), (1, 1)]),
                    shapely.MultiLineString([[(0, 1), (1, 1)], [(0, 1), (1, 1)]]),
                ],
            ),
        )

    with pytest.raises(TypeError):
        fc3.insert(
            -1,
            gpd.GeoDataFrame(
                {"col1": ["x", "y", "z"]},
                geometry=[
                    shapely.LineString([(0, 1), (1, 1)]),
                    shapely.MultiLineString([[(0, 1), (1, 1)], [(0, 1), (1, 1)]]),
                    shapely.Point(0, 0),
                ],
            ),
        )

    with pytest.raises(TypeError):
        fc3.insert(
            -1, gpd.GeoDataFrame({"col1": ["test"]}, geometry=[shapely.Point(0, 0)])
        )


def test_list_fields(gdf_points):
    fc1 = ob.FeatureClass(gdf_points)
    assert fc1.list_fields() == [
        "ObjectID",
        "sample1",
        "sample2",
        "sample3",
        "geometry",
    ]


def test_save(gdf_points, gdb_path):
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


def test_show(gdf_points):
    fc1 = ob.FeatureClass(gdf_points)
    fc1.show(block=False)


def test_select_columns(gdf_points):
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
        bad_cols = fc1.select_columns(["bad"])  # noqa: F841


def test_select_rows(gdf_points, samples):
    fc1 = ob.FeatureClass(gdf_points)
    rows1 = fc1.select_rows("ObjectID < 10")

    assert len(rows1) == 10
    rows2 = fc1.select_rows("sample1 > sample2")
    assert len(rows2) < samples

    rows3 = fc1.select_rows("ObjectID == 1")
    assert len(rows3) == 1

    test_id = fc1[0].iat[0, 0]
    assert isinstance(test_id, str)
    rows4 = fc1.select_rows(f"sample1 == '{test_id}'")
    assert len(rows4) == 1
    rows5 = fc1.select_rows(f'sample1 == "{test_id}"')
    assert len(rows5) == 1


def test_sort(gdf_points):
    fc1 = ob.FeatureClass(gdf_points)
    case1 = fc1[0].iat[0, 0]
    fc1.sort("sample1", ascending=True)
    case2 = fc1[0].iat[0, 0]
    fc1.sort("sample1", ascending=False)
    case3 = fc1[0].iat[0, 0]
    assert case1 != case2 != case3
