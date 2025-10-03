import pytest

import ouroboros as ob


def test_instantiate(ob_gdb):
    gdb, gdb_path = ob_gdb
    assert isinstance(gdb, ob.GeoDatabase)

    gdb2 = ob.GeoDatabase(
        path=gdb_path,
        contents={"extra_fc": ob.FeatureClass(), "extra_fds": ob.FeatureDataset()},
    )
    assert len(gdb2.fds_dict) == 3
    assert len(gdb2.fc_dict) == 7

    with pytest.raises(FileNotFoundError):
        gdb3 = ob.GeoDatabase("doesnotexist.gdb")  # noqa: F841


def test_delitem(ob_gdb):
    gdb, gdb_path = ob_gdb

    for fds_name in list(gdb.fds_dict.keys()):
        for fc_name in list(gdb.fc_dict.keys()):
            try:
                del gdb[fds_name][fc_name]
            except KeyError:
                pass
        assert len(gdb[fds_name]) == 0
        del gdb[fds_name]
    assert len(gdb.fds_dict) == 0

    assert len(gdb) == 0


def test_fc_dict(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fc_name, fc in gdb.fc_dict.items():
        assert isinstance(fc_name, str)
        assert isinstance(fc, ob.FeatureClass)


def test_fc_names(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fc_name in gdb.fc_names:
        assert isinstance(fc_name, str)


def test_fcs(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fc in gdb.fcs:
        assert isinstance(fc, ob.FeatureClass)


def test_fds_dict(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fds_name, fds in gdb.fds_dict.items():
        assert isinstance(fds_name, str) or fds_name is None  # noqa
        assert isinstance(fds, ob.FeatureDataset)


def test_fds_names(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fds_name in gdb.fds_names:
        assert isinstance(fds_name, str) or fds_name is None  # noqa


def test_fds(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fds in gdb.fds:
        assert isinstance(fds, ob.FeatureDataset)


def test_getitem(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fds_name, fds in gdb.fds_dict.items():
        for fc_name, fc in fds.fc_dict.items():
            assert isinstance(gdb[fds_name][fc_name], ob.FeatureClass)

    with pytest.raises(KeyError):
        f = gdb["bad"]

    for idx in range(len(gdb)):
        f = gdb[idx]

    with pytest.raises(IndexError):
        f = gdb[999]

    with pytest.raises(KeyError):
        # noinspection PyTypeChecker
        f = gdb[list()]  # noqa: F841

    fc = gdb["test_points1"]
    assert isinstance(fc, ob.FeatureClass)


def test_hash(ob_gdb):
    gdb, gdb_path = ob_gdb
    assert isinstance(gdb.__hash__(), int)


def test_iter(ob_gdb):
    gdb, gdb_path = ob_gdb
    for gdf_name in gdb:
        assert isinstance(gdf_name, str) or gdf_name is None


def test_len(ob_gdb):
    gdb, gdb_path = ob_gdb
    assert len(gdb) == 6


def test_setitem(ob_gdb):
    gdb, gdb_path = ob_gdb
    new_gdb = ob.GeoDatabase()
    for fds_name, fds in gdb.fds_dict.items():
        new_gdb[fds_name] = fds
        with pytest.raises(KeyError):
            new_gdb[fds_name] = fds

    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        gdb["bad"] = 99


def test_feature_classes(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fc_name, fc in gdb.fc_dict.items():
        assert isinstance(fc_name, str)
        assert isinstance(fc, ob.FeatureClass)


def test_feature_datasets(ob_gdb):
    gdb, gdb_path = ob_gdb
    for fds_name, fds in gdb.fds_dict.items():
        assert isinstance(fds_name, str) or fds_name is None
        assert isinstance(fds, ob.FeatureDataset)


def test_save(tmp_path, ob_gdb):
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
