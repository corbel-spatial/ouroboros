import ouroboros as ob


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
