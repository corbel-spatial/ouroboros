import os
import arcpy
import pytest
import sys
from pprint import pprint

sys.path.append("../src")
from ouroboros import ouroboros as ob  # noqa


ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

test_points = os.path.join(ROOT_PATH, "test_data.gdb", "test_points")
test_polygons = os.path.join(ROOT_PATH, "test_data.gdb", "test_polygons")
test_polylines = os.path.join(ROOT_PATH, "test_data.gdb", "test_polylines")
test_fcs = [test_points, test_polygons, test_polylines]


@pytest.fixture
def fc():
    return ob.FeatureClass(test_points, in_memory=True)


def test_instantiate_feature_class():
    for fp in test_fcs:
        fc_test = ob.FeatureClass(fp)
        assert isinstance(fc_test, ob.FeatureClass)
    return True


def test_instantiate_fc_in_memory():
    for fp in test_fcs:
        fc_test = ob.FeatureClass(fp, in_memory=True)
        assert isinstance(fc_test, ob.FeatureClass)
        assert fc_test.path.startswith("memory")
    return True


def test_describe_properties(fc):
    print("\n")
    pprint(fc.describe())
    assert isinstance(fc.properties, dict)
    assert fc.properties.keys() == fc.describe().keys()
    return True


def test_head(fc):
    print("\n")
    fc.head()
    print("\n")
    fc.head(20)
    return True


def test_len(fc):
    print(len(fc))
    assert isinstance(len(fc), int)
    return True


def test_save(fc):
    fc.save(test_points + "2")
    return True


def test_sort(fc):
    print("\n")
    print(fc.get_fields())

    fc.sort("textfield", ascending=True)
    sort_asc = fc.head()

    print("\n")

    fc.sort("textfield", ascending=False)
    sort_desc = fc.head()

    assert sort_asc != sort_desc
    return True


def test_str(fc):
    print(str(fc))
    return True


def test_repr(fc):
    print(fc)
    return True


def test_properties(fc):
    print(fc.path)
    assert arcpy.Exists(fc.path)
    assert fc._oid_name in ["OID", "OBJECTID", "ObjectID"]

    return True


def test_list_fields(fc):
    print(fc.get_fields())
    assert isinstance(fc.get_fields(), list)
    return True


def test_to_shapely(fc):
    fc.to_shapely()
    return True


def test_to_geojson(fc):
    fc.to_geojson()
    return True


def test_iter(fc):
    for row in fc:
        print(row)
        break
    return True


def test_get_rows():
    r = ob.FeatureClass(test_points)
    print(r)
    return True


def test_append_rows():
    r = ob.FeatureClass(test_points)
    count1 = len(r)
    r.append(r[0])
    count2 = len(r)
    assert count1 < count2
    return True
