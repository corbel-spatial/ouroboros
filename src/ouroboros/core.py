from collections.abc import Sequence

import arcpy
import geojson
from geomet import wkt
from shapely import geometry as sg

from .utils import *


class FeatureClass(Sequence):
    """
    Wrapper class for more Pythonic manipulation of geodatabase feature classes.

    Allows for easy addition and removal of rows from a feature class, as well as
    conversion to other data formats such as GeoJSON or Shapely GeometryCollections.
    """

    def __init__(self, path: str, in_memory: bool = False, head_n: int = 10):
        """
        Initializes a new instance of an ouroboros FeatureClass object.

        :param path: Path to a feature class inside a geodatabase.
            e.g., "C:\\Users\\zoot\\spam.gdb\\eggs"
        :type path: str
        :param in_memory: Flag indicating whether to load the data into memory.
            Defaults to `False`.
        :type in_memory: bool, optional
        :param head_n: Number of rows to read from the feature class with FeatureClass.head()
            Defaults to 10.
        :type head_n: int, optional

        :raises FileNotFoundError: If the specified path does not exist.

        :return: None
        :rtype: None
        """
        if not arcpy.Exists(path):
            raise FileNotFoundError(path)

        if in_memory is True:
            self.path = copy_to_memory(path)
        else:
            self.path = path

        _properties = self.describe()
        self._oid_name = _properties["OIDFieldName"]
        self._geometry_type = _properties["shapeType"]

        _fields = self.get_fields()
        self._oid_index = _fields.index(self._oid_name)
        self._shape_column_index = _fields.index("Shape")

        self._head_n = head_n

        return

    def __add__(self, rows: [list[tuple], list[tuple, ...]]):
        """
        Append one or more rows to the feature class.

        :param rows: A single list of values or a list of lists to append; list lengths and order must match that of method get_fields()
        :type rows: list[any] or list[list[any]]
        :return: The self object of ouroboros.FeatureClass
        :rtype: object
        """
        if isinstance(rows, tuple) and any(isinstance(i, tuple) for i in rows):
            # list of rows
            with arcpy.da.InsertCursor(self.path, ["*"]) as ic:
                for row in rows:
                    ic.insertRow(row)
        else:
            # single row
            with arcpy.da.InsertCursor(self.path, ["*"]) as ic:
                ic.insertRow(rows)
        return self

    def __contains__(self, query: [tuple[any, str]]) -> bool:
        """
        Return true if the given query is in self, false otherwise.

        A query is a tuple where the first element is the value to count and the second
        element is the field name to look for. For example: ("value_to_count", "field_name")

        :param query: The query tuple (value_to_count, field_name)
        :type query: tuple[any, str]
        :return: True if the query is in self, False otherwise
        :rtype: bool
        """
        field_idx = self.index_field(query[1])
        for row in self._get_rows():
            value = row[field_idx]
            if value == query[0]:
                return True
        return False

    def __delitem__(self, index: int) -> None:
        """
        Delete the row at the given index.

        :param index: The index of the row to delete.
        :type index: int
        :raises IndexError: If the specified index is not found in the rows.
        :return: None
        :rtype: None
        """
        with arcpy.da.UpdateCursor(self.path, [self._oid_name]) as uc:
            for idx, row in enumerate(uc):
                if idx == index:
                    uc.deleteRow()
                    return
            raise IndexError("Row index not found")
        return

    def _get_oid(self, index: int) -> int:
        """
        Return the ObjectID for a given row index.

        :param index: The row index to retrieve the ObjectID for.
        :type index: int
        :raises TypeError: If ``index`` is not an integer.
        :return: The ObjectID associated with the specified row index.
        :rtype: int
        """
        if not isinstance(index, int):
            raise TypeError
        item = self.__getitem__(index)
        idx = self._oid_index
        return int(item[idx])

    def _get_rows(self) -> tuple[tuple, ...]:
        """
        Return all rows as a tuple of tuples. Geometry is stored as WKT.

        :return: A tuple of tuples, where each inner tuple represents a row in the feature class.
        :rtype: tuple[tuple, ...]
        """
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
                row = tuple(row)
                rows.append(row)
        return tuple(rows)

    def __getitem__(self, index: [int, slice]) -> [tuple[any], tuple[tuple[any]]]:
        """
        Return the row or rows at the given index or slice.

        :param index: The index or slice of the row to return.
        :type index: int or slice
        :return: The row or rows at the given index or slice.
        :rtype: tuple or tuple of tuples
        """
        rows = self._get_rows()
        return rows[index]

    def __iter__(self):
        """
        Return a new iterator object that can iterate over all the objects in the container.

        :return: A new iterator object.
        :rtype: object
        """
        return iter(self._get_rows())

    def __len__(self) -> int:
        """
        Returns the number of features in the table or feature class.

        :return: The count of features.
        :rtype: int
        """
        result = arcpy.GetCount_management(self.path)
        return int(result[0])

    def __repr__(self):
        """
        Returns a string representation of the object, which is the path to the feature class.

        :return: The path to the feature class.
        :rtype: str
        """
        return self.path

    def __reversed__(self):
        """
        Reverses the order of elements in the object.

        :return: Returns an iterator of rows.
        :rtype: object
        """
        return list(self._get_rows()).__reversed__()

    def __str__(self):
        """
        Returns a string representation of the feature class's rows.

        :return: A string representation of the feature class's rows.
        :rtype: str
        """
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
        """
        Delete all rows in the feature class.

        :return: None
        :rtype: None
        """
        arcpy.DeleteRows_management(self.path)
        return

    def count(self, query: [tuple[str, any]]) -> int:
        """
        Return the number of occurrences in the data.

        The query is expected to be a tuple containing two elements:
        - The value to count.
        - The name of the field to search in.

        :param query: A tuple with two elements: ("value_to_count", "field_name")
        :type query: [tuple[str, any]]
        :return: The total number of occurrences
        :rtype: int
        """
        field_idx = self.index_field(query[1])
        total = 0
        for row in self._get_rows():
            value = row[field_idx]
            if value == query[0]:
                total += 1
        return total

    def describe(self) -> dict:
        """
        Returns a dictionary containing metadata about the feature class.

        This method uses the ``arcpy.da.Describe`` function from ArcPy to fetch the metadata,
        which includes properties such as the dataset type, extent, spatial reference, and more.

        :return: A dictionary containing the metadata.
        :return type: dict
        """
        return arcpy.da.Describe(self.path)

    def get_fields(self) -> list[str]:
        """
        Returns a list of field names from the feature class.

        This method relies on the :mod:`arcpy` module for functionality.

        :return: A list of strings representing the field names.
        :return type: list[str]
        """
        return [f.name for f in arcpy.ListFields(self.path)]

    def head(self, n: [int, None] = None, silent: bool = False) -> tuple[tuple, ...]:
        """
        Prints and returns a specified number of rows from the data.

        :param n: The number of rows to return. If not provided, defaults to self._head_n.
                  If greater than the total number of rows, will return all available rows.
        :type n: int or None
        :param silent: If True, suppresses printing the output (default is False).
        :type silent: bool
        :return: A tuple of tuples containing the specified rows of data.
        :rtype: tuple[tuple, ...]
        """
        if n is None:
            n = self._head_n
        if n > self.__len__():
            n = self.__len__()
        rows = self._get_rows()[0:n]
        if silent is False:
            print(rows)
        return rows

    def index(self, oid: int, **kwargs) -> int:
        """
        Return the row index for a given ObjectID.

        .. note::
            This method assumes that the ObjectID column exists and has a unique value for each row.

        :param oid: The ObjectID to search for.
        :type oid: int
        :raises ValueError: If the ObjectID is less than 1.
        :raises AttributeError: If the ObjectID is not found in the dataset.
        :return: The row index of the ObjectID.
        :rtype: int
        """
        if oid < 1:
            raise ValueError("ObjectID must be integer 1 or greater")

        with arcpy.da.SearchCursor(self.path, [self._oid_name]) as sc:
            for idx, row in enumerate(sc):
                if row[0] == oid:
                    return idx
            raise AttributeError("ObjectID not found")

    def index_field(self, field_name) -> int:
        """Return the column index for a given field name.

        :param field_name: The name of the field for which to retrieve the index.
        :type field_name: str
        :return: The column index for the given field name.
        :rtype: int
        """
        return self.get_fields().index(field_name)

    def pop(self, index: int = -1) -> list:
        """
        Remove and return the row at the specified index.

        If no index is provided (-1 by default), the last element is removed.
        This function behaves identically to Python's built-in `list.pop()` method.

        :param index: The index of the row to remove (default=-1)
        :type index: int, optional
        :return: The removed row as a list
        :rtype: list
        """
        if not isinstance(index, int):
            raise TypeError
        item = self.__getitem__(slice(index))
        oid = self._get_oid(index)
        self.remove(oid)
        return list(item)

    def remove(self, oid: int) -> None:
        """Delete the row with the provided ObjectID.

        :param oid: The ObjectID to delete.
        :type oid: int
        :raises ValueError: If the ObjectID is not an integer or less than 1.
        :return: None
        :rtype: None
        """
        if oid < 1:
            raise ValueError("ObjectID must be integer 1 or greater")
        index = self.index(oid)
        self.__delitem__(index)
        return

    def save(self, out_path: [str, PathLike], overwrite_output=True) -> None:
        """
        Saves the feature class data to a geodatabase or file.

        :param out_path: The path where the output will be saved. Can be either a string (e.g., 'path/to/output') or a PathLike object.
        :type out_path: str, PathLike
        :param overwrite_output: If True, overwrites any existing output if it already exists at the specified location.
        :type overwrite_output: bool, optional
        :raises RuntimeError: If arcpy fails to export features due to an invalid path or other error.
        :return: None
        :rtype: None
        """
        with arcpy.EnvManager(overwriteOutput=overwrite_output):
            arcpy.ExportFeatures_conversion(self.path, out_path)
        return

    def sort(
        self,
        field_name: str,
        ascending: bool = True,
        out_path: [str, PathLike] = None,
    ) -> None:
        """
        Sort on a specified field (cannot be ObjectID).

        If `out_path` is not specified, the sorting is done in place. Otherwise,
        the sorted features are exported to the specified path.

        :param field_name: The name of the field to sort on.
            It cannot be the same as the ObjectID.
        :type field_name: str
        :param ascending: Whether to sort in ascending or descending order.
            Defaults to True (ascending).
        :type ascending: bool
        :param out_path: The path where the sorted features are exported,
            if not sorting in place. Defaults to None.
        :type out_path: [str, PathLike], optional
        :raises ValueError: If the field name is the same as the ObjectID.
        :return: None
        :rtype: None
        """
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
                del mem_path
        else:
            arcpy.Sort_management(self.path, out_path, [[field_name, direction]])

        return

    def to_geojson(self) -> geojson.FeatureCollection:
        """
        Return a geojson Feature Collection representation of the feature class.

        :return: A geojson Feature Collection representation of the feature class.
        :rtype: geojson.FeatureCollection
        """
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
        """
        Return a Shapely Geometry Collection representation of the feature class.

        :return: A Shapely Geometry Collection representation of the feature class.
        :rtype: shapely.geometry.GeometryCollection
        """
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
