from collections.abc import Sequence
from pprint import pprint
from os import PathLike
from uuid import uuid4

import arcpy
import geojson
from geomet import wkt
from shapely import geometry as sg


def get_memory_path():
    return "memory\\fc_" + str(uuid4()).replace("-", "_")


def copy_to_memory(path: [str, PathLike]):
    out_path = get_memory_path()
    arcpy.ExportFeatures_conversion(path, out_path)
    return out_path


class FeatureClass(Sequence):
    """Wrapper class for more Pythonic manipulation of geodatabase feature classes."""

    def __init__(self, path: str, in_memory: bool = False):
        """
        :param path: Path to a feature class inside a geodatabase, e.g., "C:\\Users\\zoot\\spam.gdb\\eggs"
        :type path: str
        """
        if not arcpy.Exists(path):
            raise FileNotFoundError(path)

        if in_memory is True:
            self.path = copy_to_memory(path)
        else:
            self.path = path

        self.properties = self.describe()
        self._oid_name = self.properties["OIDFieldName"]
        self._geometry_type = self.properties["shapeType"]

        fields = self.get_fields()
        self._oid_index = fields.index(self._oid_name)
        self._shape_column_index = fields.index("Shape")

        return

    def __add__(self, rows: [list[any], list[list[any]]]):
        """
        Append one or more rows to the feature class.

        :param rows: A single list of values or a list of lists to append; list lengths and order must match that of method get_fields()
        :type rows: list[any] or list[list[any]]
        """
        if isinstance(rows, list) and any(isinstance(i, list) for i in rows):
            # list of rows
            with arcpy.da.InsertCursor(self.path, ["*"]) as ic:
                for row in rows:
                    ic.insertRow(row)
        else:
            # single row
            with arcpy.da.InsertCursor(self.path, ["*"]) as ic:
                ic.insertRow(rows)
        return self

    def __contains__(self, item):  # TODO
        raise NotImplementedError

    def __delitem__(self, index: int) -> None:
        """Delete the row at the given index."""
        with arcpy.da.UpdateCursor(self.path, [self._oid_name]) as uc:
            for idx, row in enumerate(uc):
                if idx == index:
                    uc.deleteRow()
                    return
            raise IndexError("Row index not found")
        return

    def _get_rows(self) -> list[list[any]]:
        """Return all rows as a list of lists."""
        fields = self.get_fields()
        shape_index = self._shape_column_index
        fields[shape_index] = "SHAPE@"

        rows = list()
        with arcpy.da.SearchCursor(self.path, fields) as sc:
            for row in sc:
                row = [i for i in row]
                geom = row[shape_index]
                try:
                    row[shape_index] = geom.WKT
                except AttributeError:
                    pass
                rows.append(row)
        return rows

    def __getitem__(self, index: [int, slice]) -> [list[any], list[list[any]]]:
        """Return the row or rows at the given index or slice."""
        rows = self._get_rows()
        return rows[index]

    def __iter__(self):  # TODO
        raise NotImplementedError

    def __len__(self) -> int:
        result = arcpy.GetCount_management(self.path)
        return int(result[0])

    def __repr__(self):
        return self.path

    def __str__(self):
        return str(self._get_rows())

    def append(self, rows: [list[any], list[list[any]]]) -> None:
        """
        Append one or more rows to the feature class.

        :param rows: A single list of values or a list of lists to append; list lengths and order must match that of method get_fields()
        :type rows: list[any] or list[list[any]]
        """
        self.__add__(rows)
        return

    def clear(self) -> None:
        """Delete all rows in the feature class."""
        arcpy.DeleteRows_management(self.path)
        return

    def count(self, value: [tuple[str, any]]) -> int:  # TODO
        raise NotImplementedError

    def describe(self) -> dict:
        properties = arcpy.da.Describe(self.path)
        self.properties = properties
        return properties

    def get_fields(self) -> list[str]:
        return [f.name for f in arcpy.ListFields(self.path)]

    def get_oid(self, index: int) -> int:
        """Return the ObjectID for a given row index."""
        if not isinstance(index, int):
            raise TypeError
        item = self.__getitem__(index)
        oidx = self._oid_index
        return int(item[oidx])

    def get_rows(self) -> list[list[any]]:
        """Return all rows as a list of lists."""
        return self._get_rows()

    def head(self, n=10, silent=False):
        if n > self.__len__():
            n = self.__len__()
        rows = self.get_rows()[0:n]
        if silent is False:
            pprint(rows)
        return rows

    def index(self, oid: int, **kwargs) -> int:
        """Return the row index for a given ObjectID."""
        if oid < 1:
            raise ValueError("ObjectID must be integer 1 or greater")

        with arcpy.da.SearchCursor(self.path, [self._oid_name]) as sc:
            for idx, row in enumerate(sc):
                if row[0] == oid:
                    return idx
            raise AttributeError("ObjectID not found")

    def index_field(self, field_name) -> int:
        """Return the column index for a given field name."""
        return self.get_fields().index(field_name)

    def pop(self, index: int = -1) -> list:
        """Return and remove the row at the given index. Functionally the same as list.pop(index)"""
        if not isinstance(index, int):
            raise TypeError
        item = self.__getitem__(slice(index))
        oid = self.get_oid(index)
        self.remove(oid)
        return list(item)

    def remove(self, oid: int) -> None:
        """Delete the row with the provided ObjectID."""
        if oid < 1:
            raise ValueError("ObjectID must be integer 1 or greater")
        index = self.index(oid)
        self.__delitem__(index)
        return

    def save(self, out_path: [str, PathLike], overwrite_output=True):
        with arcpy.EnvManager(overwriteOutput=overwrite_output):
            arcpy.ExportFeatures_conversion(self.path, out_path)
        return

    def sort(
        self,
        field_name: str,
        ascending: bool = True,
        out_path: [str, PathLike] = None,
    ):
        """Sort on field (cannot be ObjectID). If out_path is not specified then it will be sorted in place."""
        if field_name == self._oid_name:
            raise ValueError("Field name can't be same as ObjectID")

        if ascending is True:
            direction = "ASCENDING"
        else:
            direction = "DESCENDING"

        if out_path is None:
            mem_path = get_memory_path()
            with arcpy.EnvManager(addOutputsToMap=False):
                arcpy.Sort_management(self.path, mem_path, [[field_name, direction]])
            with arcpy.EnvManager(overwriteOutput=True):
                arcpy.ExportFeatures_conversion(mem_path, self.path)
                arcpy.Delete_management(mem_path)
        else:
            arcpy.Sort_management(self.path, out_path, [[field_name, direction]])

        return

    def to_geojson(self) -> geojson.FeatureCollection:
        """Return a geojson Feature Collection representation of the feature class."""
        items = self.__getitem__(slice(0, -1))

        oid_colindex = self._oid_index
        shape_colindex = self._shape_column_index

        out = list()
        for item in items:
            oid = item[oid_colindex]
            shape = item[shape_colindex]
            properties = dict()
            for i, f in enumerate(self.get_fields()):
                if f.upper() not in [
                    "OBJECTID",
                    "OID",
                    "SHAPE",
                    "SHAPE_LENGTH",
                    "SHAPE_AREA",
                ]:
                    properties[f] = item[i]

            if shape is None:
                gjs = geojson.Feature(id=oid, geometry=None, properties=properties)
            elif "POLYGON" in str(shape).upper():
                gjs = geojson.Polygon(
                    id=oid, geometry=wkt.loads(shape), properties=properties
                )
            elif "LINE" in str(shape).upper():
                gjs = geojson.Polygon(
                    id=oid, geometry=wkt.loads(shape), properties=properties
                )
            elif "POINT" in str(shape).upper():
                gjs = geojson.Feature(
                    id=oid, geometry=wkt.loads(shape), properties=properties
                )
            else:
                raise TypeError(f'Incompatible geometry type: "{shape}"')

            out.append(gjs)

        return geojson.FeatureCollection(out)

    def to_shapely(self) -> sg.GeometryCollection:
        """Return a shapely Geometry Collection representation of the feature class."""
        geoms = list()
        with arcpy.da.SearchCursor(self.path, ["SHAPE@"]) as sc:
            for row in sc:
                geo: arcpy.Geometry = row[0]
                if geo is None:
                    continue
                js = geojson.loads(geo.JSON)
                geo_type = geo.type

                if geo_type == "polygon":
                    js = js["rings"]
                    holes = None
                    if len(js) > 1:
                        holes = list()
                        for g in js[1:]:
                            holes.append(g)
                    sf = sg.Polygon(shell=js[0], holes=holes)
                elif geo_type == "point":
                    sf = sg.Point(js["x"], js["y"])
                elif geo_type == "polyline":
                    js = js["paths"][0]
                    sf = sg.LineString(js)
                else:
                    raise TypeError(f'Incompatible geometry type: "{geo_type}"')
                geoms.append(sf)
        return sg.GeometryCollection(geoms)
