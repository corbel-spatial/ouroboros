import os
import pytest
import sys
from pprint import pprint

sys.path.append("../src")
import ouroboros as ob  # noqa
from ouroboros import utils  # noqa

assets = "../assets"

test_points = os.path.join(assets, "test_data.gdb", "test_points")
test_polygons = os.path.join(assets, "test_data.gdb", "test_polygons")
test_polylines = os.path.join(assets, "test_data.gdb", "test_polylines")
test_fcs = [test_points, test_polygons, test_polylines]


def test_instantiate_fcs():
    for fp in test_fcs:
        fc_test = ob.FeatureClass(fp)
        assert isinstance(fc_test, ob.FeatureClass)


def test_instantiate_fcs_in_memory():
    for fp in test_fcs:
        fc_test = ob.FeatureClass(fp, in_memory=True)
        assert isinstance(fc_test, ob.FeatureClass)
        assert fc_test.path.startswith("memory")


@pytest.fixture
def fc():
    return ob.FeatureClass(test_points, in_memory=True)


def test_add(fc):
    count1 = len(fc)
    extended = fc + fc[11:20]
    count2 = len(extended)
    assert count1 < count2
    return


def test_delitem(fc):
    count1 = len(fc)
    fc.__delitem__(0)
    count2 = len(fc)
    assert count1 > count2


def test_getitem(fc):
    item = fc.__getitem__(0)
    pprint(item)
    assert isinstance(item, tuple)


def test_get_rows(fc):
    rows = fc._get_rows()
    assert isinstance(rows, tuple)
    assert len(rows) == len(fc)


def test_iter(fc):
    for row in fc[:10]:
        assert isinstance(row, tuple)
    for row in fc.__iter__():
        assert isinstance(row, tuple)
        break


def test_len(fc):
    i = len(fc)
    pprint(i)
    assert isinstance(i, int)


def test_repr(fc):
    r = fc.__repr__()
    pprint(r)
    assert isinstance(r, str)
    assert r.startswith("C:") or r.startswith("memory")


def test_reversed(fc):
    r = reversed(fc)
    for row in r:
        assert row == fc[-1]
        break


def test_str(fc):
    s = str(fc)
    pprint(s)
    assert isinstance(s, str)


def test_append(fc):
    count1 = len(fc)
    fc.append(fc[0])
    count2 = len(fc)
    assert count1 < count2

    fc.append(fc[1:10])
    count3 = len(fc)
    assert count2 < count3


def test_clear(fc):
    count1 = len(fc)
    fc.clear()
    count2 = len(fc)
    assert count1 > count2
    assert count2 == 0


def test_count(fc):
    count = fc.count(("feature 1", "textfield"))
    print(count)
    assert count == 1


def test_describe(fc):
    desc = fc.describe()
    pprint(desc)
    assert isinstance(desc, dict)
    assert "shapeType" in desc


def test_get_fields(fc):
    fields = fc.get_fields()
    pprint(fields)
    assert isinstance(fields, list)


def test_get_oid(fc):
    oid = fc._get_oid(0)
    assert isinstance(oid, int)
    assert oid == fc[0][0]


def test_head(fc):
    print("\n")
    h = fc.head()
    assert isinstance(h, tuple)
    assert len(h) == 10

    print("\n")
    h = fc.head(20)
    assert isinstance(h, tuple)
    assert len(h) == 20


def test_index(fc):
    idx = fc.index(1)
    assert isinstance(idx, int)
    assert idx == 0


def test_index_field(fc):
    idx = fc.index_field("Shape")
    assert isinstance(idx, int)


def test_pop(fc):
    count1 = len(fc)
    p = fc.pop()
    count2 = len(fc)
    assert count2 == (count1 - 1)
    assert isinstance(p, list)


def test_remove(fc):
    count1 = len(fc)
    fc.remove(1)
    count2 = len(fc)
    assert count2 == (count1 - 1)


def test_save(fc):
    out_path = utils.get_memory_path()
    fc.save(out_path)
    fc.save(out_path, overwrite_output=True)
    out_fc = ob.FeatureClass(out_path)
    assert len(fc) == len(out_fc)


def test_sort(fc):
    fc.sort("textfield", ascending=True)
    sort_asc = fc.head()
    print("\n")
    fc.sort("textfield", ascending=False)
    sort_desc = fc.head()
    assert sort_asc != sort_desc


def test_to_geojson(fc):
    fc.to_geojson()


def test_to_shapely(fc):
    fc.to_shapely()
