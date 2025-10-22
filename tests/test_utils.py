import os

import geojson
import geopandas as gpd
import pyogrio
import pytest
import shapely

import ouroboros as ob


def test_fc_to_json(tmp_path, ob_gdb):
    gdb, gdb_path = ob_gdb
    for fc_name, fc in gdb.fc_dict.items():
        gjs = ob.utils.fc_to_json(gdb_path, fc_name)
        assert isinstance(gjs, geojson.FeatureCollection)

    for fc_name, fc in gdb.fc_dict.items():
        fp = str(tmp_path / fc_name) + ".geojson"
        ob.utils.fc_to_json(gdb_path, fc_name, fp, indent=2)

        fp = str(tmp_path / fc_name)
        ob.utils.fc_to_json(gdb_path, fc_name, fp, indent=2)


def test_fc_to_parquet(tmp_path, ob_gdb):
    gdb, gdb_path = ob_gdb
    for fc_name, fc in gdb.fc_dict.items():
        fp = str(tmp_path / fc_name) + ".parquet"
        ob.utils.fc_to_parquet(gdb_path, fc_name, fp)

        fp = str(tmp_path / fc_name)
        ob.utils.fc_to_parquet(gdb_path, fc_name, fp)


def test_fc_to_shp(tmp_path, ob_gdb):
    gdb, gdb_path = ob_gdb
    for fc_name, fc in gdb.fc_dict.items():
        fp = str(tmp_path / fc_name) + ".shp"
        ob.utils.fc_to_shp(gdb_path, fc_name, fp)

        fp = str(tmp_path / fc_name)
        ob.utils.fc_to_shp(gdb_path, fc_name, fp)


def test_fc_to_gdf(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fc in ob.utils.list_layers(gdb_path):
        gdf = ob.utils.fc_to_gdf(gdb_path, fc)
        assert isinstance(gdf, gpd.GeoDataFrame)
    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        ob.utils.fc_to_gdf(gdb_path, 0)


def test_gdf_to_fc(ob_gdb):
    gdb, gdb_path = ob_gdb
    count = 0
    for fds in gdb.values():
        for fc_name, fc in fds.items():
            gdf = fc.gdf
            ob.utils.gdf_to_fc(gdf, gdb_path, fc_name + "_copy")
            ob.utils.gdf_to_fc(gdf, gdb_path, fc_name, overwrite=True)
            count += 2
    assert count == len(ob.utils.list_layers(gdb_path))

    with pytest.raises(FileNotFoundError):
        ob.utils.gdf_to_fc(gpd.GeoDataFrame(), "thisfiledoesnotexist", "test")

    # noinspection PyUnresolvedReferences
    with pytest.raises(pyogrio.errors.GeometryError):
        for fc_name, fc in gdb.fc_dict.items():
            ob.utils.gdf_to_fc(
                gdf=fc.gdf,
                gdb_path=gdb_path,
                fc_name=fc_name,
                feature_dataset=None,
                geometry_type="no",
                overwrite=True,
            )

    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        ob.utils.gdf_to_fc(list(), gdb_path, "test")

    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        ob.utils.gdf_to_fc(gpd.GeoDataFrame, "test", "test", overwrite="yes")

    ob.utils.gdf_to_fc(
        gpd.GeoSeries([shapely.LineString([(0, 1), (1, 1)])]),
        gdb_path,
        "geoseries",
        overwrite=True,
    )


def test_get_info(tmp_path, esri_gdb):
    gdb = ob.GeoDatabase(
        contents={
            "fds": ob.FeatureDataset(
                {
                    "fc": ob.FeatureClass(
                        gpd.GeoDataFrame(
                            {"col1": ["c"]},
                            geometry=[shapely.LineString([(0, 1), (1, 1)])],
                            crs="WGS 84",
                        ),
                    )
                }
            )
        }
    )
    gdb_path = tmp_path / "out.gdb"
    gdb.save(gdb_path, overwrite=True)
    info = ob.utils.get_info(gdb_path)
    assert isinstance(info, dict)

    info = ob.utils.get_info(esri_gdb)
    assert isinstance(info, dict)

    with pytest.raises(FileNotFoundError):
        ob.utils.get_info("bad_path")

    with pytest.raises(TypeError):
        try:  # pytest
            ob.utils.get_info("pyproject.toml")
        except FileNotFoundError:  # coverage
            ob.utils.get_info(os.path.join("..", "pyproject.toml"))


def test_list_datasets(ob_gdb, esri_gdb):
    gdb, gdb_path = ob_gdb
    fds1 = ob.utils.list_datasets(gdb_path)
    assert len(fds1) == 2
    for k, v in fds1.items():
        assert isinstance(k, str) or k is None
        assert isinstance(v, list)

    fds3 = ob.utils.list_datasets(esri_gdb)
    assert isinstance(fds3, dict)
    assert len(fds3) == 0

    with pytest.raises(FileNotFoundError):
        ob.utils.list_datasets("bad_path")

    with pytest.raises(TypeError):
        try:  # pytest
            ob.utils.list_datasets("pyproject.toml")
        except FileNotFoundError:  # coverage
            ob.utils.list_datasets(os.path.join("..", "pyproject.toml"))


def test_list_layers(ob_gdb):
    gdb, gdb_path = ob_gdb
    lyrs = ob.utils.list_layers(gdb_path)
    assert len(lyrs) == 6

    with pytest.raises(FileNotFoundError):
        ob.utils.list_layers("bad_path")

    with pytest.raises(TypeError):
        try:  # pytest
            ob.utils.list_layers("pyproject.toml")
        except FileNotFoundError:  # coverage
            ob.utils.list_layers(os.path.join("..", "pyproject.toml"))


def test_list_rasters(ob_gdb, esri_gdb):
    rasters = ob.utils.list_rasters(esri_gdb)
    assert len(rasters) == 1
    for raster in rasters:
        assert isinstance(raster, str)

    gdb, gdb_path = ob_gdb
    rasters = ob.utils.list_rasters(gdb_path)
    assert len(rasters) == 0

    with pytest.raises(FileNotFoundError):
        ob.utils.list_rasters("bad_path")

    with pytest.raises(TypeError):
        try:  # pytest
            ob.utils.list_rasters("pyproject.toml")
        except FileNotFoundError:  # coverage
            ob.utils.list_rasters(os.path.join("..", "pyproject.toml"))


def test_raster_to_tif(tmp_path, capsys, esri_gdb, gdal_version):
    if not gdal_version:
        with pytest.raises(ImportError):
            ob.utils.raster_to_tif(
                gdb_path=esri_gdb,
                raster_name="random_raster",
                tif_path=None,
            )
    else:
        with capsys.disabled():
            print("\n\t*** GDAL installed:", gdal_version, "***")
        ob.utils.raster_to_tif(
            gdb_path=esri_gdb,
            raster_name="random_raster",
            tif_path=None,
        )

        tif_path = tmp_path / "test"
        ob.utils.raster_to_tif(
            gdb_path=esri_gdb,
            raster_name="random_raster",
            tif_path=str(tif_path),
        )

        tif_path = tmp_path / "test.tif"
        ob.utils.raster_to_tif(
            gdb_path=esri_gdb,
            raster_name="random_raster",
            tif_path=str(tif_path),
            options={"TILED": "YES"},
        )


def test_version():
    version = ob.__version__
    assert isinstance(version, str)
    assert "." in version
