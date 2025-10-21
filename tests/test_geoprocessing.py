import geopandas as gpd
import pandas as pd
import pytest
import shapely

import ouroboros as ob


def test_buffer(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fc in gdb.fcs:
        with pytest.warns(UserWarning):
            fc_buffered = ob.buffer(fc, 5.0)
            assert isinstance(fc_buffered, ob.FeatureClass)
    # fc_buffered.show()


def test_clip(ob_gdb):
    gdb, gdb_path = ob_gdb
    fc1 = gdb["test_polygons1"]
    fc2 = gdb["test_polygons2"]
    fc_clipped = ob.clip(fc1, fc2)
    assert isinstance(fc_clipped, ob.FeatureClass)
    # fc_clipped.show()


def test_overlay(ob_gdb):
    gdb, gdb_path = ob_gdb
    fc1 = gdb["test_polygons1"]
    fc2 = gdb["test_polygons2"]
    fc_overlaid = ob.overlay(fc1, fc2, "union")
    assert isinstance(fc_overlaid, ob.FeatureClass)
    # fc_overlaid.show()


def test_add_fcs(gdf_points, gdf_lines, gdf_polygons):
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


def test_add_fds(gdf_points, gdf_lines, gdf_polygons):
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


def test_iters(ob_gdb):
    gdb, gdb_path = ob_gdb

    for fds_name, fds in gdb.items():
        for fc_name, fc in fds.items():
            assert isinstance(fc_name, str)
            assert isinstance(fc, ob.FeatureClass)

    for fds_name, fds in gdb.fds_dict.items():
        for fc_name, fc in fds.items():
            assert isinstance(fc_name, str)
            assert isinstance(fc, ob.FeatureClass)

    for fc_name, fc in gdb.fc_dict.items():
        assert isinstance(fc_name, str)
        assert isinstance(fc, ob.FeatureClass)

    this_fds = None
    for fds in gdb:
        this_fds = gdb[fds]
        break
    for fc_name, fc in this_fds.fc_dict.items():
        assert isinstance(fc_name, str)
        assert isinstance(fc, ob.FeatureClass)


def test_sanitize_gdf_geometry(gdf_points, gdf_lines, gdf_polygons):
    with pytest.raises(TypeError):
        ob.utils.sanitize_gdf_geometry(pd.DataFrame())  # noqa

    with pytest.raises(TypeError):
        ob.utils.sanitize_gdf_geometry(
            gpd.GeoDataFrame(
                geometry=[
                    shapely.GeometryCollection(),
                    shapely.Point(),
                ]
            )
        )

    gdf1 = gpd.GeoDataFrame(
        geometry=[
            shapely.Point(),
            shapely.Point([0, 1]),
            shapely.MultiPoint([[0, 1], [0, 2]]),
            None,
        ]
    )
    gdf1_geom_type, gdf1 = ob.utils.sanitize_gdf_geometry(gdf1)
    assert gdf1_geom_type == "MultiPoint"

    gdf2 = gpd.GeoDataFrame(
        geometry=[
            shapely.LineString(),
            shapely.LineString([[0, 1], [0, 2]]),
            shapely.MultiLineString([[[0, 1], [0, 2]], [[0, 4], [0, 5]]]),
            None,
        ]
    )
    gdf2_geom_type, gdf2 = ob.utils.sanitize_gdf_geometry(gdf2)
    assert gdf2_geom_type == "MultiLineString"

    gdf3 = gpd.GeoDataFrame(
        geometry=[
            shapely.LinearRing(),
            shapely.LinearRing([[0, 1], [1, 1], [1, 0], [0, 0]]),
            shapely.MultiLineString([[[0, 1], [0, 2]], [[0, 4], [0, 5]]]),
            None,
        ]
    )
    gdf3_geom_type, gdf3 = ob.utils.sanitize_gdf_geometry(gdf3)
    assert gdf3_geom_type == "MultiLineString"

    gdf4 = gpd.GeoDataFrame(
        geometry=[
            shapely.LineString(),
            shapely.LineString([[0, 1], [0, 2]]),
            shapely.LinearRing(),
            shapely.LinearRing([[0, 1], [1, 1], [1, 0], [0, 0]]),
            shapely.MultiLineString([[[0, 0], [1, 2]], [[4, 4], [5, 6]]]),
            None,
        ]
    )
    gdf4_geom_type, gdf4 = ob.utils.sanitize_gdf_geometry(gdf4)
    assert gdf4_geom_type == "MultiLineString"

    gdf5 = gpd.GeoDataFrame(
        geometry=[
            shapely.LineString(),
            shapely.LineString([[0, 1], [0, 2]]),
            shapely.LinearRing(),
            shapely.LinearRing([[0, 1], [1, 1], [1, 0], [0, 0]]),
            None,
        ]
    )
    gdf5_geom_type, gdf5 = ob.utils.sanitize_gdf_geometry(gdf5)
    assert gdf5_geom_type == "LineString"

    gdf6 = gpd.GeoDataFrame(
        geometry=[
            shapely.Polygon(),
            shapely.Polygon([[0, 1], [1, 1], [1, 0], [0, 0]]),
            shapely.MultiPolygon(
                [
                    (
                        ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)),
                        [((0.1, 0.1), (0.1, 0.2), (0.2, 0.2), (0.2, 0.1))],
                    )
                ]
            ),
            None,
        ]
    )
    gdf6_geom_type, gdf6 = ob.utils.sanitize_gdf_geometry(gdf6)
    assert gdf6_geom_type == "MultiPolygon"

    with pytest.raises(TypeError):
        gdf7 = gpd.GeoDataFrame(
            geometry=[
                shapely.LineString(),
                shapely.LinearRing(),
                shapely.MultiLineString(),
                None,
                shapely.Point(),
            ]
        )
        ob.utils.sanitize_gdf_geometry(gdf7)
