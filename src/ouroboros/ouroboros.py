from abc import abstractmethod
from collections.abc import MutableSequence
from pprint import pprint
from os import PathLike
from typing import overload, Iterable, TypeVar
from uuid import uuid4

import arcpy
import geojson
from geomet import wkt
from shapely import geometry as sg

_T = TypeVar("_T")


class _BaseClass(MutableSequence):
    def insert(self, index, value):
        pass

    @overload
    @abstractmethod
    def __getitem__(self, index: int) -> _T:
        ...

    @overload
    @abstractmethod
    def __getitem__(self, index: slice) -> MutableSequence[_T]:
        ...

    def __getitem__(self, index):
        pass

    @overload
    @abstractmethod
    def __setitem__(self, index: int, value: _T) -> None:
        ...

    @overload
    @abstractmethod
    def __setitem__(self, index: slice, value: Iterable[_T]) -> None:
        ...

    def __setitem__(self, index, value):
        pass

    @overload
    @abstractmethod
    def __delitem__(self, index: int) -> None:
        ...

    @overload
    @abstractmethod
    def __delitem__(self, index: slice) -> None:
        ...

    def __delitem__(self, index):
        pass

    def __len__(self):
        pass


def get_memory_path():
    return "memory\\fc_" + str(uuid4()).replace("-", "_")


def copy_to_memory(path: [str, PathLike]):
    out_path = get_memory_path()
    arcpy.ExportFeatures_conversion(path, out_path)
    return out_path


class FeatureClass(_BaseClass):
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

    def __add__(self, row: list[any]) -> None:
        """
        Append a row to the feature class.

        :param row: The list of values to append; list length and order must match that of method get_fields()
        :type row: list[any]
        """
        with arcpy.da.InsertCursor(self.path, ["*"]) as ic:
            ic.insertRow(row)
        return

    def __delitem__(self, index: int) -> None:
        """Delete the row at the given index."""
        with arcpy.da.UpdateCursor(self.path, [self._oid_name]) as uc:
            for idx, row in enumerate(uc):
                if idx == index:
                    uc.deleteRow()
                    return
            raise IndexError("Row index not found")
        return

    def __getitem__(self, index: slice) -> list[list[any]]:
        """Return a list of rows for the given index or slice."""
        rows = self.get_rows()
        return rows[index]

    def __len__(self) -> int:
        result = arcpy.GetCount_management(self.path)
        return int(result[0])

    def __repr__(self):
        return self.path

    def __setitem__(self, row_idx, value: tuple[int, any]) -> None:
        """Change the value of a given row/column in the attribute table.

        :param row_idx: List index of the row (not the ObjectID!)
        :type row_idx: int
        :param value: Two-member tuple (column index, value to set). Column index can be derived from method get_fields()
        :type value: tuple[int, any]
        """
        column_idx, value = value
        with arcpy.da.UpdateCursor(self.path, ["*"]) as uc:
            row: list
            for idx, row in enumerate(uc):
                if idx == row_idx:
                    row[column_idx] = value
                    uc.updateRow(row)
                    break
        return

    def append(self, row: list[any]) -> None:
        """Add a row to the end of the attribute table. Input the list of values to append; list length and order
        must match that of method get_fields()"""
        self.__add__(row)
        return

    def clear(self) -> None:
        """Delete all rows in the feature class."""
        arcpy.DeleteRows_management(self.path)
        return

    def describe(self) -> dict:
        properties = arcpy.da.Describe(self.path)
        self.properties = properties
        return properties

    def extend(self, rows: iter) -> None:
        """Append rows from an iterator list of rows."""
        for row in rows:
            self.append(row)
        return

    def get_fields(self) -> list[str]:
        return [f.name for f in arcpy.ListFields(self.path)]

    def get_oid(self, index: int) -> int:
        """Return the ObjectID for a given row index."""
        if not isinstance(index, int):
            raise TypeError
        item = self.__getitem__(slice(index))
        idx = self._oid_index
        return item[idx][0]

    def get_rows(self):
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

    def head(self, n=10, silent=False):
        if n > self.__len__():
            n = self.__len__()
        rows = self.get_rows()[0:n]
        if silent is False:
            pprint(rows)
        return rows

    def index(self, objectid: int, start: int = 0, stop: int = -1) -> int:
        """Return the row index for a given ObjectID."""
        if objectid < 1:
            raise ValueError("ObjectID must be integer 1 or greater")
        with arcpy.da.SearchCursor(self.path, [self._oid_name]) as sc:
            for idx, row in enumerate(sc):
                if row[0] == objectid:
                    index = idx
                    return index
            raise AttributeError("ObjectID not found")

    def index_field(self, field_name) -> int:
        """Return the column index for a given field name."""
        return self.get_fields().index(field_name)

    def insert(self, index, value):
        return NotImplemented

    def pop(self, index: int = -1) -> list:
        """Return and remove the row at the given index. Functionally the same as list.pop(index)"""
        if not isinstance(index, int):
            raise TypeError
        item = self.__getitem__(slice(index))
        oid = self.get_oid(index)
        self.remove(oid)
        return list(item)

    def remove(self, objectid: int) -> None:
        """Delete the row with the provided ObjectID."""
        index = self.index(objectid)
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
                raise NotImplementedError

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
                    raise NotImplementedError(geo)

                geoms.append(sf)

        return sg.GeometryCollection(geoms)

    def update(self, row_idx: int, value: tuple[int, any]):
        """
        Change the value of a given row/column in the attribute table.

        :param row_idx: List index of the row (not the ObjectID!)
        :type row_idx: int
        :param value: Two-member tuple (column index, value to set). Column index can be derived from method get_fields()
        :type value: tuple[int, any]
        """
        self.__setitem__(row_idx, value)
        return
