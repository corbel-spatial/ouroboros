import os
import re
import shutil
import warnings
from collections.abc import MutableMapping, MutableSequence
from typing import Any, Iterator, Sequence
from uuid import uuid4

import fiona
import geojson
import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyogrio
from pyogrio.errors import DataSourceError
from pyproj.crs import CRS


# Check for optional install of GDAL>=3.8 for raster support
try:
    from osgeo import gdal  # noqa # fmt: skip
    gdal_installed = True
    gdal_version = gdal.__version__
except ModuleNotFoundError:
    gdal_installed = False
    gdal_version = None
if gdal_version:
    version_split = gdal_version.split(".")
    if int(version_split[0]) < 3 or int(version_split[1]) < 8:
        raise ImportError(
            "GDAL version must be >= 3.8, please upgrade to a newer version"
        )


class FeatureClass(MutableSequence):
    """
    The FeatureClass acts as a custom container built on top of GeoPandas' GeoDataFrame,
    allowing operations like accessing, modifying, appending, and deleting geospatial data
    while maintaining properties like CRS (Coordinate Reference System) and geometry type.
    """

    def __init__(
        self,
        src: "None | os.PathLike | str | FeatureClass | geopandas.GeoDataFrame | geopandas.GeoSeries | pandas.DataFrame | pandas.Series" = None,
    ):
        """
        Initializes the geospatial data container by parsing the source and extracting
        the necessary attributes, such as CRS (Coordinate Reference System) and
        geometry type. The source can be an existing GeoDataFrame, a file path to
        a geodatabase (GDB), or it can be empty.

        :param src:
            Source of the data. It can be:
              - None, for initializing an empty GeoDataFrame
              - String or os.PathLike path pointing to a file or a geodatabase dataset
              - GeoDataFrame or similar type to initialize directly, or
              - Existing FeatureClass object to copy
        :type src: None | os.PathLike | str | FeatureClass | geopandas.GeoDataFrame | geopandas.GeoSeries | pandas.DataFrame | pandas.Series

        :raises TypeError: Raised when the provided source type is unsupported or invalid

        """
        self._data = None
        self.crs = None
        self.geom_type = None

        # parse src
        if isinstance(src, gpd.GeoDataFrame):
            self._data = src

        elif isinstance(src, gpd.GeoSeries):
            self._data = gpd.GeoDataFrame(geometry=src)

        elif isinstance(src, pd.DataFrame) | isinstance(src, pd.Series):
            self._data = gpd.GeoDataFrame(src)

        elif isinstance(src, FeatureClass):
            self._data = src.to_geodataframe()

        elif isinstance(src, os.PathLike) or isinstance(src, str):  # load data from gdb
            src = os.path.abspath(src)
            split_path = src.split(os.sep)
            fc_name = split_path[-1]
            if not split_path[-2].endswith(".gdb"):
                # fds_name = split_path[-2]
                gdb_path = os.sep.join(split_path[:-2])
            else:
                # fds_name = None
                gdb_path = os.sep.join(split_path[:-1])
            self._data: gpd.GeoDataFrame = fc_to_gdf(gdb_path, fc_name)

        elif src is None:
            self._data = gpd.GeoDataFrame()

        else:
            raise TypeError((src, type(src)))

        self._data.index.name = "ObjectID"

        try:
            self.crs = self._data.crs
        except AttributeError:
            self.crs = None

        # parse geometry type
        try:
            geom_types = self._data.geom_type.unique()
            if len(geom_types) == 1 and geom_types[0] is None:
                self.geom_type = "Unknown"
            elif len(geom_types) == 1 and geom_types[0] is not None:
                self.geom_type = geom_types[0]

        except AttributeError:
            self.geom_type = None

    def __delitem__(self, index) -> None:
        """
        Deletes a row from the FeatureClass by its index.

        The ObjectID index is reset after deletion.

        :param index: The position of the item to delete
        :type index: int

        :raises: TypeError
            If the provided index is not an integer

        """
        if not isinstance(index, int):
            raise TypeError("index must be an integer")
        self._data = pd.concat(
            [self._data.iloc[: index - 1], self._data.iloc[index:]]
        ).reset_index(drop=True)

    def __getitem__(
        self, index: "int | slice | Sequence[int | slice]"
    ) -> gpd.GeoDataFrame:
        """
        Retrieves rows or slices of the FeatureClass based on the given index.

        The method supports indexing by integer, slice, list of integers or slices,
        and tuples of integers or slices. It returns the corresponding subset of the
        FeatureClass.

        :param index: The index, indices, rows, or slices to retrieve from the FeatureClass
        :type index: int | slice | Sequence[int | slice]

            * If an integer is provided, the corresponding row is retrieved
            * If a slice is provided, the corresponding rows are retrieved
            * If a list or tuple of integers or slices is given, multiple specific rows or slices are retrieved

        :return: A GeoDataFrame containing the rows matching the provided index
        :rtype: geopandas.GeoDataFrame

        :raises KeyError:
            Raised when the provided index is not of a valid type (i.e., not an integer, slice, or sequence of integers or slices)

        """
        if isinstance(index, int):
            return self._data.iloc[[index]]
        elif isinstance(index, slice):
            return self._data[index]
        elif isinstance(index, list):
            return self._data.iloc[index]
        elif isinstance(index, tuple):
            if slice in [type(x) for x in index]:
                c = list()
                for idx in index:
                    if isinstance(idx, slice):
                        c.append(self._data.iloc[idx])
                    else:  # int
                        c.append(self._data.iloc[[idx]])
                return gpd.GeoDataFrame(pd.concat(c))
            else:
                return self._data.iloc[list(index)]
        else:
            raise KeyError(f"Invalid index type: {type(index)}")

    def __iter__(self) -> Iterator[tuple]:
        """
        Returns an iterator over the rows of the FeatureClass as tuples.

        This method wraps geopandas.GeoDataFrame.itertuples()

        :return: An iterator that provides each row of the data as a named tuple
        :rtype: Iterator[tuple]:

        """
        return self._data.itertuples()

    def __len__(self) -> int:
        """
        Returns the number of rows in the FeatureClass.

        :return: The count of elements or items in the object
        :rtype int:

        """
        return self._data.shape[0]

    def __setitem__(
        self,
        index: tuple[int, int | str],
        value: any,
    ) -> None:
        """
        Assign a value to the specified cell in the FeatureClass using a tuple index
        composed of a row integer, and a column integer or column name as a string.

        The value provided will overwrite the current content of the cell specified.

        :param index:
            A tuple where the first element is an integer representing the row index,
            and the second element is either an integer for the column index or a
            string for the column name
        :type index: tuple[int, int | str]

        :param value: The value to assign to the specified cell
        :type value: any

        :raises: TypeError
            If the row index is not an integer, or if the column index is neither an integer nor a string

        """
        row, column = index

        if not isinstance(row, int):
            raise TypeError("Row index must be an integer")
        if not isinstance(column, int) and not isinstance(column, str):
            raise TypeError("Column index must be an integer or a column name string")

        if type(column) is int:
            self._data.iat[row, column] = value
        else:
            self._data.at[row, column] = value

    def append(self, value: "gpd.GeoDataFrame | FeatureClass") -> None:
        """
        Appends rows to the end of the GeoDataFrame.

        The appended data must be compatible with the GeoDataFrame data structure.

        :param value: The value to append to the collection.
        :type value: geopandas.GeoDataFrame | FeatureClass

        """
        if isinstance(value, gpd.GeoDataFrame):
            self.insert(-1, value)
        elif isinstance(value, FeatureClass):
            self.insert(-1, value.to_geodataframe())
        else:
            raise TypeError(
                f"Invalid type: {type(value)}, expected geopandas.GeoDataFrame or FeatureClass"
            )

    def clear(self) -> None:
        """
        Remove all rows from the FeatureClass, leaving an empty schema.

        Note: This will delete all data from memory! Use with caution.

        Use FeatureClass.save() to save to disk before deleting data.

        """
        self._data = self._data[0:0]

    def copy(self) -> "FeatureClass":
        """
        :return: A new instance of FeatureClass containing a deep copy of the internal data.
        :rtype: FeatureClass

        """
        return FeatureClass(self._data.copy(deep=True))

    def describe(self) -> dict:
        """
        Provides a detailed description of the dataset, including its spatial reference
        system, fields, geometry type, index name, and row count.

        The returned dictionary contains the following keys:

            * `crs`: The name of the Coordinate Reference System (CRS) if defined; otherwise, None
            * `fields`: A list of field names in the dataset
            * `geom_type`: The geometry type of the dataset
            * `index_name`: The name of the index column of the dataset
            * `row_count`: The number of rows in the dataset

        :return: A dictionary containing dataset information
        :rtype: dict

        """
        if self.crs is None:
            crs = None
        else:
            crs = self.crs.name

        return {
            "crs": crs,
            "fields": self.list_fields(),
            "geom_type": self.geom_type,
            "index_name": self._data.index.name,
            "row_count": len(self._data),
        }

    def head(self, n: int = 10, silent: bool = False) -> gpd.GeoDataFrame:
        """
        Returns the first `n` rows of the FeatureClass and prints them if `silent` is False.

        :param n: Number of rows to return from the FeatureClass, defaults to 10
        :type n: int
        :param silent: If True, suppresses printing the retrieved rows, defaults to False
        :type silent: bool

        :return: A GeoDataFrame containing the first `n` rows
        :rtype: geopandas.GeoDataFrame

        """
        h = self._data.head(n)
        if not silent:
            print(h)
        return h

    def insert(self, index: int, value: "gpd.GeoDataFrame | FeatureClass") -> None:
        """
        Insert a GeoDataFrame or FeatureClass into the current structure at a specified index.

        Ensures schema compatibility, geometry type consistency, and proper handling of mixed geometries.

        :param index: The position where the rows should be inserted
        :type index: int
        :param value: The GeoDataFrame or FeatureClass to insert -- must have the same schema as the current data
        :type value: geopandas.GeoDataFrame | FeatureClass

        :raises TypeError: If `index` is not an integer, if `value` is not an instance of geopandas.GeoDataFrame or FeatureClass,
                          or if the geometry types within `value` are incompatible with the existing
                          geometry type constraints
        :raises ValueError: If the schema of `value` does not match the schema of the existing data

        """
        if not isinstance(index, int):
            raise TypeError("Index must be an integer")
        if not isinstance(value, gpd.GeoDataFrame) and not isinstance(
            value, FeatureClass
        ):
            raise TypeError(
                "Value must be an instance of geopandas.GeoDataFrame or FeatureClass"
            )
        if isinstance(value, FeatureClass):
            value = value.to_geodataframe()

        if len(self._data.columns) >= 1:
            try:
                assert (value.columns == self._data.columns).all()
            except ValueError:
                raise ValueError("Schemas must match")

        # parse geometry types of new features
        new_geoms = value.geom_type.unique()
        if len(new_geoms) == 1:
            new_geom = new_geoms[0]
        elif len(new_geoms) == 2:
            if new_geoms[0].strip("Multi") == new_geoms[1].strip("Multi"):
                new_geom = f"Multi{new_geoms[0].strip('Multi')}"
            else:
                raise TypeError(f"Cannot mix geometry types: {new_geoms}")
        else:  # len(new_geoms) > 2:
            raise TypeError(f"Cannot mix geometry types: {new_geoms}")

        # validate geometry
        if self.geom_type is not None and self.geom_type == new_geom:
            pass
        elif self.geom_type in (None, "Unknown") and new_geom is not None:
            self.geom_type = new_geom
        elif self.geom_type in (None, "Unknown") and new_geom is None:
            self.geom_type = "Unknown"
        else:  # promote to Multi- type geometry (MultiPoint etc)
            self.geom_type: str
            simple_type = self.geom_type.strip("Multi")
            if new_geom.strip("Multi") != simple_type:
                raise TypeError(f"Geometry must be {simple_type} or Multi{simple_type}")
            else:
                self.geom_type = f"Multi{simple_type}"

        # insert features into dataframe
        if index == 0:
            c = [value, self._data]
        elif index == -1:
            c = [self._data, value]
        else:
            c = [self._data.iloc[:index], value, self._data.iloc[index:]]
        self._data = pd.concat(c, ignore_index=True)  # will reindex after concat

    def list_fields(self) -> list[str]:
        """
        Return a list of field names in the data.

        This method retrieves the column names of the underlying data object and
        adds the index name as the first field in the list.

        :return: A list of field names including the index name as the first item
        :rtype: list[str]

        """
        fields = self._data.columns.to_list()
        fields.insert(0, self._data.index.name)
        return fields

    def save(
        self,
        gdb_path: os.PathLike | str,
        fc_name: str,
        feature_dataset: str = None,
        overwrite: bool = False,
    ) -> None:
        """
        Save the current data object to a file geodatabase.

        Saves with a specified feature class name within a specified feature dataset, optionally allowing
        overwriting of any existing data.

        :param gdb_path: The path to the file geodatabase where the data will be saved
        :type gdb_path: os.PathLike | str
        :param fc_name: The name of the feature class within the geodatabase where the data will be written
        :type fc_name: str
        :param feature_dataset: The name of the feature dataset within the geodatabase to contain the feature class;
                                if not provided, the feature class will be saved at the root of the geodatabase
        :type feature_dataset: str, optional
        :param overwrite: If True, existing data in the specified feature class will be overwritten, defaults to False
        :type overwrite: bool, optional

        """
        gdf_to_fc(
            gdf=self._data,
            gdb_path=gdb_path,
            fc_name=fc_name,
            feature_dataset=feature_dataset,
            overwrite=overwrite,
        )

    def select_columns(
        self, columns: str | Sequence[str], geometry: bool = True
    ) -> "FeatureClass":
        """
        Return a FeatureClass of only the specified columns.

        :param columns: The names of the columns to select, can be a list of names or a single name
        :type columns: str | Sequence[str]

        :param geometry: Return the geometry column as well, defaults to True
        :type geometry: bool

        """
        if not isinstance(columns, str):
            for col in columns:
                if col not in self._data.columns:
                    raise KeyError(f"Column '{col}' not found in data.")
            columns = list(columns)
        else:
            columns = [columns]

        if geometry:
            columns.append("geometry")

        if len(columns) == 1:
            columns = columns[0]

        return FeatureClass(self._data[columns])

    def select_rows(self, expr: str) -> "FeatureClass":
        # noinspection PyUnresolvedReferences
        """
        Return a FeatureClass of the rows that match a query expression.

        Wrapper for `pandas.DataFrame.query <https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.query.html>`__

        :param expr: The query expression to use for filtering the rows
        :type expr: str

        Example::

            fc.query("colA > colB")

            ObjectID    colA    colB
            42          10      9
            99          201     0

        """
        return FeatureClass(gpd.GeoDataFrame(self._data.query(expr, inplace=False)))

    def sort(
        self,
        field_name: str,
        ascending: bool = True,
    ) -> None:
        """
        Sort the FeatureClass based on a specific field.

        Wraps the geopandas.GeoDataFrame.sort_values() method.

        :param field_name: The name of the field in the dataset to sort by
        :type field_name: str
        :param ascending: Defaults to True
        :type ascending: bool, optional

        """
        self._data.sort_values(by=field_name, ascending=ascending, inplace=True)

    def to_geodataframe(self) -> gpd.GeoDataFrame:
        """
        Returns a deep copy of the internal GeoDataFrame.

        :return: A deep copy of the internal GeoDataFrame
        :rtype: geopandas.GeoDataFrame

        """
        return self._data.copy(deep=True)

    def to_geojson(
        self, filename: os.PathLike | str = None
    ) -> "None | geojson.FeatureCollection":
        """Convert the FeatureClass to the GeoJSON format.

        When a filename is provided, the GeoJSON output will be written to that file. If no filename is
        specified, the GeoJSON format will be returned as a FeatureCollection object. The filename
        is automatically suffixed with '.geojson' if not specified in the provided name.

        :param filename: The name of the file where the GeoJSON output should be written
        :type filename: os.PathLike | str, optional

        :return: None when a filename is provided and the GeoJSON data is written to disk;
                 otherwise, returns a geojson.FeatureCollection object
        :rtype: None | geojson.FeatureCollection

        """
        if filename:
            if not filename.endswith(".geojson"):
                filename += ".geojson"
            self._data.to_file(filename, driver="GeoJSON")
            return None
        else:
            gjs = self._data.to_json(to_wgs84=True)
            return geojson.loads(gjs)

    def to_pyarrow(self) -> pa.Table:
        """
        Convert the FeatureClass to a PyArrow Table.

        Wraps the geopandas.GeoDataFrame.to_arrow() method.

        :return: A PyArrow Table object
        :rtype: pyarrow.Table

        """
        arrow_table = self._data.to_arrow()
        return pa.table(arrow_table)

    def to_shapefile(self, filename: os.PathLike | str) -> None:
        """
        Convert the FeatureClass to a shapefile.

        Adds a '.shp' suffix to the filename if not in the filename provided.

        :param filename: The name of the file where the shapefile will be saved
        :type filename: os.PathLike | str
        """
        if not filename.endswith(".shp"):
            filename += ".shp"
        with warnings.catch_warnings():  # hide pyogrio driver warnings
            warnings.simplefilter("ignore")
            self._data.to_file(filename=filename, driver="ESRI Shapefile")


class FeatureDataset(MutableMapping):
    """
    A `dict`-like collection of FeatureClass objects with an enforced CRS.

    A FeatureDataset is a mutable mapping that organizes feature classes and enforces consistency
    in their coordinate reference system (CRS).

    """

    def __init__(
        self,
        contents: None | dict[str, FeatureClass] = None,
        crs: Any | CRS = None,
        enforce_crs: bool = True,
    ):
        """
        Initialize a new FeatureDataset instance with an optional coordinate reference system (CRS).

        The CRS can be specified as any value compatible with the CRS class constructor.

        :param contents: A dict of FeatureClass names and their objects to initialize the FeatureDataset with
        :type contents: None | dict[str, FeatureClass]

        :param crs: The coordinate reference system to initialize the FeatureDataset with
        :type crs: Any | CRS

        :param enforce_crs: Whether to enforce the CRS in the FeatureDataset, defaults to True
        :type crs: bool

        :raises TypeError: If the provided CRS value cannot be converted to a valid CRS object

        """
        self.enforce_crs = enforce_crs

        self.crs = None
        self._fcs = dict()
        self._gdbs = set()

        if self.enforce_crs:
            if isinstance(crs, CRS) or crs is None:
                self.crs = crs
            else:
                self.crs = CRS(crs)
        else:
            self.crs = None

        if contents:
            for fc_name, fc in contents.items():
                self.__setitem__(fc_name, fc)

    def __delitem__(self, key, /):
        """
        Remove the FeatureClass from the FeatureDataset.

        The FeatureClass object itself is not deleted, and may be referenced by other
        FeatureDataset or GeoDatabase instances.

        :param key: The name of the FeatureClass to be removed
        :type key: str

        :raises KeyError: If the name is not present in the FeatureDataset

        """
        del self._fcs[key]

    def __getitem__(self, key: int | str, /) -> FeatureClass:
        """
        Retrieve a FeatureClass instance by either integer index or string key.

        :param key: The index or key to retrieve the FeatureClass
        :type key: int | str

        :return: The FeatureClass instance corresponding to the provided key or index
        :rtype: FeatureClass

        :raises IndexError: If an integer index is provided and it is out of range
        :raises KeyError: If a string key is provided and does not exist in the FeatureDataset

        """
        if isinstance(key, int):
            for idx, fc_obj in enumerate(self.feature_classes().values()):
                if idx == key:
                    return fc_obj
            raise IndexError(f"Index out of range: {key}")
        else:
            return self._fcs[key]

    def __iter__(self) -> Iterator[dict[str, FeatureClass]]:
        """
        Return an iterator over the FeatureDataset.

        :return: An iterator of a dict with the structure {FeatureClass name: FeatureClass object}
        :rtype: Iterator[dict[str, FeatureClass]]

        """
        return iter(self._fcs)

    def __len__(self):
        """
        :return: The number of FeatureClass objects in the FeatureDataset
        :rtype: int

        """
        return len(self._fcs)

    def __setitem__(self, key: str, value: FeatureClass, /):
        """
        Set a FeatureClass to the specified key in the FeatureDataset.

        This method prevents duplication of FeatureClass names and maintains consistency
        in coordinate reference systems (CRS) across the FeatureDataset.

        :param key: The name under which to store the FeatureClass. Must start with a non-digit,
                    and contain only alphanumeric characters and underscores
        :type key: str
        :param value: The FeatureClass instance to be associated with the given key
        :type value: FeatureClass

        :raises TypeError: If the value is not an instance of FeatureClass
        :raises ValueError: If the key starts with a digit or contains invalid characters
        :raises KeyError: If the key already exists in the FeatureDataset
        :raises AttributeError: If the CRS of the FeatureDataset and FeatureClass do not match

        """
        if not isinstance(value, FeatureClass):
            raise TypeError(f"Expected type ouroboros.FeatureClass: {value}")

        if key[0].isdigit():
            raise ValueError(f"FeatureClass name cannot start with a digit: {key} ")

        for letter in key:
            if not letter.isalpha() and not letter.isdigit() and not letter == "_":
                raise ValueError(
                    f"FeatureClass name can only contain letters, numbers, and underscores: {key}"
                )

        for gdb in self._gdbs:
            for fds_name, fds in gdb.items():
                for fc_name, fc in fds.items():
                    if key == fc_name:
                        raise KeyError(f"FeatureClass name already in use: {key}")

        self._fcs[key] = value

        if self.enforce_crs:
            if not self.crs:
                self.crs = value.crs
            else:
                try:
                    assert self.crs == value.crs
                except AssertionError:
                    raise AttributeError(
                        f"Feature dataset CRS ({self.crs} does not match FeatureClass CRS ({value.crs})"
                    )

    def feature_classes(self) -> dict[str, FeatureClass]:
        """
        :return: Return a dict of the FeatureClass names and their objects contained by the FeatureDataset
        :rtype: dict[str, FeatureClass]

        """
        return self._fcs


class GeoDatabase(MutableMapping):
    """
    A `dict`-like collection of FeatureDataset and FeatureClass objects.

    The GeoDatabase class is a mutable mapping that allows storing and managing spatial datasets
    organized into FeatureClass and FeatureDataset objects. It provides methods to interact with the stored
    spatial data, including access, iteration, modification, and saving data to disk.

    """

    def __init__(
        self,
        path: None | os.PathLike | str = None,
        contents: dict[str : FeatureClass | FeatureDataset] | None = None,
    ):
        """
        Initialize a new GeoDatabase instance.

        If a valid path is provided, attempts to load datasets and layers from the specified
        location on disk. If no path is provided, the instance starts with an empty collection
        of FeatureDatasets.

        :param path: The file path to load datasets and layers from
        :type path: None | os.PathLike | str

        :param contents: A dict of dataset names and their objects to initialize the GeoDatabase with
        :type contents: dict[str : FeatureClass | FeatureDataset] | None

        """
        self._fds: dict[str | None : FeatureDataset] = dict()
        self._uuid = uuid4()

        if path:  # load from disk
            datasets = list_datasets(path)
            lyrs = list_layers(path)
            for fds_name in datasets:
                if fds_name is None:
                    fds = FeatureDataset(enforce_crs=False)
                else:
                    fds = FeatureDataset(enforce_crs=True)
                for fc_name in lyrs:
                    if fc_name in datasets[fds_name]:
                        fds[fc_name] = FeatureClass(fc_to_gdf(path, fc_name))
                self.__setitem__(fds_name, fds)

        if contents:
            for name, ds in contents.items():
                self.__setitem__(name, ds)

    # noinspection PyProtectedMember
    def __delitem__(self, key: str, /):
        """
        Removes the specified FeatureDataset from the geodatabase.

        The FeatureDataset object itself is not deleted, and may be referenced by other
        FeatureClass or GeoDatabase objects.

        :param key: The key associated with the FeatureDataset to be removed
        :type key: str

        :raises KeyError: If the key does not exist in the GeoDatabase

        """

        fds = self._fds[key]
        del self._fds[key]
        fds._gdbs.remove(self)

    def __getitem__(self, key: int | str, /) -> FeatureClass | FeatureDataset:
        """
        Retrieve a FeatureClass or FeatureDataset from the GeoDatabase.

        Provides access to elements through indexing or key-based retrieval. Supports both
        FeatureClass and FeatureDataset using integer indexing or string-based keys.

        :param key: The key to retrieve an element
        :type key: int | str

        :return: The matched feature class or FeatureDataset
        :rtype: FeatureClass | FeatureDataset

        :raises KeyError: If key is neither an integer nor string, or if a non-existent string key is used
        :raises IndexError: If the integer-based index is out of range

        """
        if not isinstance(key, int) and not isinstance(key, str) and key is not None:
            raise KeyError(f"Expected key to be an integer or string: {key}")

        if key in self._fds:
            return self._fds[key]
        elif isinstance(key, int):
            for idx, fc_obj in enumerate(self.feature_classes().values()):
                if idx == key:
                    return fc_obj
            raise IndexError(f"Index out of range: {key}")
        else:
            for fc_name, fc in self.feature_classes().items():
                if fc_name == key:
                    return fc
        raise KeyError(f"'{key}' does not exist in the GeoDatabase")

    def __hash__(self) -> int:
        """
        Calculate and return the hash value for the GeoDatabase instance.

        This method ensures that objects with the same UUID have consistent hash values,
        making the GeoDatabase hashable and suitable for use in sets and as dictionary keys.

        :return: The hash value of the object based on its UUID
        :rtype: int

        """
        return hash(self._uuid)

    def __iter__(self) -> Iterator[dict[str, FeatureDataset]]:
        """
        Return an iterator over the FeatureDataset objects in the GeoDatabase.

        :return: Iterator yielding (name, dataset) pairs for each FeatureDataset
        :rtype: Iterator[dict[str, FeatureDataset]]

        """
        return iter(self._fds)

    def __len__(self):
        """
        :return: The count of FeatureClass objects contained in the GeoDatabase
        :rtype int:

        """
        count = 0
        for fds in self._fds.values():
            count += len(fds)
        return count

    # noinspection PyProtectedMember
    def __setitem__(self, key: str, value: FeatureClass | FeatureDataset, /):
        """
        Sets a key-value pair in the GeoDatabase.

        This method associates a key with either a FeatureClass or FeatureDataset value in the GeoDatabase.
        For FeatureClass values, it ensures an appropriate FeatureDataset exists. For FeatureDataset
        values, it validates and associates them directly.

        :param key: The key to associate with the object in the GeoDatabase
        :type key: str
        :param value: The object to be stored
        :type value: FeatureClass | FeatureDataset

        :raises TypeError: If the value is neither a FeatureClass nor a FeatureDataset
        :raises KeyError: If the key being added as a FeatureDataset already exists

        """
        if isinstance(value, FeatureClass):
            try:
                crs = value.to_geodataframe().crs
            except AttributeError:
                crs = None
            if None not in self._fds:
                self._fds[None] = FeatureDataset(crs=crs)
            self._fds[None]._gdbs.add(self)
            self._fds[None][key] = value
        elif isinstance(value, FeatureDataset):
            if key in self._fds:
                raise KeyError(f"Feature dataset name already in use: {key}")
            else:
                self._fds[key] = value
                self._fds[key]._gdbs.add(self)
        else:
            raise TypeError(f"Expected FeatureClass or FeatureDataset: {value}")

    def feature_classes(self) -> dict[str, FeatureClass]:
        """
        :return: A dict of the FeatureClass names and their objects contained by the GeoDatabase
        :rtype: dict[str, FeatureClass]

        """
        fcs = dict()
        for fds in self._fds.values():
            for fc_name, fc in fds.items():
                fcs[fc_name] = fc
        return fcs

    def feature_datasets(self) -> dict[str, FeatureDataset]:
        """
        :return: A dict of the FeatureDataset names and their objects contained by the GeoDatabase
        :rtype: dict[str, FeatureDataset]

        """
        return self._fds

    def save(self, path: os.PathLike | str, overwrite: bool = False):
        """Save the current contents of the GeoDatabase to a specified geodatabase (.gdb) file.

        :param path: The file system path where the file geodatabase will be saved
        :type path: os.PathLike | str
        :param overwrite: Whether to overwrite existing file geodatabase at the specified path, defaults to False
        :type overwrite: bool

        :note: If the provided path does not include `.gdb`, the extension will be automatically appended

        """
        path = str(path)
        if not path.endswith(".gdb"):
            path += ".gdb"

        if overwrite and os.path.exists(path):
            shutil.rmtree(path)
            assert not os.path.exists(path)

        for fds_name, fds in self._fds.items():
            for fc_name, fc in fds.items():
                gdf_to_fc(
                    fc.to_geodataframe(),
                    gdb_path=path,
                    fc_name=fc_name,
                    feature_dataset=fds_name,
                    overwrite=overwrite,
                )


def delete_fc(
    gdb_path: os.PathLike | str,
    fc_name: str,
) -> bool:
    """
    Delete a feature class from the specified file geodatabase if it exists.

    This function verifies the existence of the feature class within the
    geodatabase and removes it if found. It will not perform any operation
    if the feature class does not exist.

    :param gdb_path: The path to the geodatabase that contains the feature class
    :type gdb_path: os.PathLike | str
    :param fc_name: The name of the feature class to be deleted
    :type fc_name: str

    :returns: True if the feature class was successfully deleted, False otherwise
    :rtype: bool

    :raises TypeError: If the provided feature class name is not a string

    """
    if not isinstance(fc_name, str):
        raise TypeError("Feature class name must be a string")

    if fc_name in list_layers(gdb_path):
        fiona.remove(gdb_path, "OpenFileGDB", fc_name)
        return True
    else:
        return False


def fc_to_gdf(
    gdb_path: os.PathLike | str,
    fc_name: str,
) -> gpd.GeoDataFrame:
    """Convert a feature class in a geodatabase on disk to a GeoDataFrame.

    This function reads in a specific feature class stored on disk within a
    file geodatabase and converts it into a GeoDataFrame. It ensures the GeoDataFrame's
    index is set to "ObjectID", corresponding to the unique identifier of the feature class.

    :param gdb_path: Path to the File Geodatabase (.gdb file) containing the feature class
    :type gdb_path: os.PathLike | str
    :param fc_name: The name of the feature class to be read and converted
    :type fc_name: str

    :return: A GeoDataFrame representation of the feature class, with "ObjectID" set as the index
    :rtype: geopandas.GeoDataFrame

    :raises TypeError: If the feature class name (`fc_name`) is not a string

    """
    if not isinstance(fc_name, str):
        raise TypeError("Feature class name must be a string")

    with warnings.catch_warnings():  # hide pyogrio driver warnings
        warnings.simplefilter("ignore")
        gdf: gpd.GeoDataFrame = gpd.read_file(gdb_path, layer=fc_name)
    gdf = gdf.rename_axis("ObjectID")  # use ObjectID as dataframe index

    return gdf


def gdf_to_fc(
    gdf: gpd.GeoDataFrame | gpd.GeoSeries,
    gdb_path: os.PathLike | str,
    fc_name: str,
    feature_dataset: str = None,
    geometry_type: str = None,
    overwrite: bool = False,
    compatibility: bool = True,
    reindex: bool = False,
):
    """
    Convert a GeoDataFrame or GeoSeries to a feature class in a file geodatabase on disk.

    This function exports a GeoDataFrame or GeoSeries to a file geodatabase on disk as a feature class.
    It includes options for specifying feature datasets, geometry types, overwrite functionality,
    compatibility modes, and reindexing.

    :param gdf: The input GeoDataFrame or GeoSeries to be exported
    :type gdf: geopandas.GeoDataFrame | geopandas.GeoSeries
    :param gdb_path: File path to the geodatabase where the feature class will be created
    :type gdb_path: os.PathLike | str
    :param fc_name: Name of the feature class to create
    :type fc_name: str
    :param feature_dataset: Name of the feature dataset inside the geodatabase where the feature class will be stored
    :type feature_dataset: str, optional
    :param geometry_type: Defines the geometry type for the output
    :type geometry_type: str, optional
    :param overwrite: If True and the feature class already exists, it will be deleted and replaced
    :type overwrite: bool, optional
    :param compatibility: If True, compatibility settings such as ArcGIS version targeting will be applied, defaults to True
    :type compatibility: bool, optional
    :param reindex: If True, uses in-memory spatial indexing for optimization, defaults to False
    :type reindex: bool, optional

    :raises TypeError: If the input `gdf` is neither a GeoDataFrame nor a GeoSeries
    :raises FileExistsError: If the feature class already exists and `overwrite` is set to False
    :raises FileNotFoundError: If the specified geodatabase path does not exist or is invalid

    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        if isinstance(gdf, gpd.GeoSeries) or isinstance(gdf, pd.DataFrame):
            gdf = gpd.GeoDataFrame(gdf)
        else:
            raise TypeError(
                f"{fc_name} data must be geopandas.GeoDataFrame or geopandas.GeoSeries"
            )

    layer_options = {
        "TARGET_ARCGIS_VERSION": True if compatibility else False,
        "OPENFILEGDB_IN_MEMORY_SPI": True if reindex else False,
        "FEATURE_DATASET": feature_dataset,
    }

    if os.path.exists(gdb_path):
        if fc_name in list_layers(gdb_path):
            if overwrite:
                delete_fc(gdb_path, fc_name)
            else:
                raise FileExistsError(
                    f"{fc_name} already exists. To overwrite it use: gdf_to_fc(gdf, gdb_path, fc_name, overwrite=True"
                )

    # convert dataframe index back to ObjectID
    if "ObjectID" not in gdf.columns:
        gdf = gdf.rename_axis("ObjectID")
    gdf.reset_index(inplace=True)
    gdf["ObjectID"] = gdf["ObjectID"].astype(np.int32)
    gdf["ObjectID"] = gdf["ObjectID"] + 1

    # noinspection PyUnresolvedReferences
    try:
        with warnings.catch_warnings():  # hide pyogrio driver warnings
            warnings.simplefilter("ignore")
            gdf.to_file(
                gdb_path,
                driver="OpenFileGDB",
                layer=fc_name,
                layer_options=layer_options,
                geometry_type=geometry_type,
            )
    except DataSourceError:
        raise FileNotFoundError(gdb_path)


def get_info(gdb_path: os.PathLike | str) -> dict:
    """
    Return a dictionary view of the contents of a file geodatabase on disk.

    :param gdb_path: Path to the geodatabase
    :type gdb_path: os.PathLike | str
    :return: A dictionary where keys represent dataset types, and values are nested
        dictionaries with dataset names and their corresponding metadata.
    :rtype: dict

    """
    fc_info = {fc: pyogrio.read_info(gdb_path, fc) for fc in list_layers(gdb_path)}

    fds_info = {
        ds: {"contents": list(fcs)} for ds, fcs in list_datasets(gdb_path).items()
    }
    # remove placeholder None dataset
    if None in fds_info:
        del fds_info[None]
    # get crs of the first feature class
    for ds_name, ds_info in fds_info.items():
        if len(ds_info["contents"]) >= 1:
            ds_info["crs"] = fc_info[ds_info["contents"][0]]["crs"]

    result = {"FeatureClass": fc_info, "FeatureDataset": fds_info}

    raster_info = dict()
    if gdal_installed:
        for raster_name in list_rasters(gdb_path):
            raster: gdal.Dataset
            with gdal.Open(f"OpenFileGDB:{gdb_path}:{raster_name}") as raster:
                raster_info[raster_name] = {
                    "block_size": raster.GetRasterBand(1).GetBlockSize(),
                    "crs": f"EPSG:{CRS(raster.GetProjectionRef()).to_epsg()}",
                    "category_names": raster.GetRasterBand(1).GetRasterCategoryNames(),
                    "color_interpretation": raster.GetRasterBand(
                        1
                    ).GetRasterColorInterpretation(),
                    "dataset_metadata": raster.GetMetadata_Dict(),
                    "nodata_value": raster.GetRasterBand(1).GetNoDataValue(),
                    "raster_count": raster.RasterCount,
                    "unit": raster.GetRasterBand(1).GetUnitType(),
                    "x_size": raster.RasterXSize,
                    "y_size": raster.RasterYSize,
                }

    result["RasterDataset"] = raster_info

    return result


def list_datasets(gdb_path: os.PathLike | str) -> dict[str | None, list[str]]:
    """
    Lists the feature datasets and feature classes contained in a file geodatabase on disk.

    Processes the contents of a geodatabase file structure to identify feature datasets
    and their corresponding feature classes. It returns a dictionary mapping feature datasets
    to their feature classes. Feature classes that are not part of any dataset are listed under
    a `None` key.

    :param gdb_path: The file path to the geodatabase on disk
    :type gdb_path: os.PathLike | str

    :return: A dictionary containing feature datasets as keys (or `None` for feature
             classes without a dataset) and lists of feature classes as values
    :rtype: dict[str | None, list[str]]

    Reference:
        * https://github.com/rouault/dump_gdbtable/wiki/FGDB-Spec

    """
    gdbtable = os.path.join(gdb_path, "a00000004.gdbtable")

    fcs = list_layers(gdb_path)
    if len(fcs) == 0:  # no feature classes returns empty dict
        return dict()

    # get \feature_dataset\feature_class paths
    with open(gdbtable, "r", encoding="MacRoman") as f:
        contents = f.read()
    re_matches = re.findall(
        r"<CatalogPath>\\([a-zA-Z0-9_]+)\\([a-zA-Z0-9_]+)</CatalogPath>",
        contents,
    )
    # assemble output
    out = dict()
    for fds, fc in re_matches:
        if fds not in out:
            out[fds] = list()
        out[fds].append(fc)
        if fc in fcs:
            fcs.remove(fc)
    out[None] = fcs  # remainder fcs outside of feature datasets
    return out


def list_layers(gdb_path: os.PathLike | str) -> list[str]:
    """
    Lists all feature classes within a specified file geodatabase on disk.

    If the geodatabase is empty or not valid, an empty list is returned.

    :param gdb_path: The path to the geodatabase file
    :type gdb_path: os.PathLike | str
    :return: A list of feature classes in the specified geodatabase file
    :rtype: list[str]

    """
    try:
        lyrs = gpd.list_layers(gdb_path)
        return lyrs["name"].to_list()
    except DataSourceError:
        return list()


def list_rasters(gdb_path: os.PathLike | str) -> list[str]:
    """
    Lists all raster datasets within a specified file geodatabase on disk.

    If the geodatabase is empty or not valid, an empty list is returned.

    :param gdb_path: The path to the geodatabase file
    :type gdb_path: os.PathLike | str
    :return: A list of raster datasets in the specified geodatabase file
    :rtype: list[str]

    Reference:
        * https://github.com/rouault/dump_gdbtable/wiki/FGDB-Spec

    """
    gdbtable = os.path.join(gdb_path, "a00000004.gdbtable")
    fcs = list_layers(gdb_path)
    fds = list_datasets(gdb_path)

    # get \dataset paths
    with open(gdbtable, "r", encoding="MacRoman") as f:
        contents = f.read()
    rasters = re.findall(
        r"<CatalogPath>\\([a-zA-Z0-9_]+)</CatalogPath>",
        contents,
    )

    # remove the feature classes
    for fc in fcs:
        if fc in rasters:
            rasters.remove(fc)
    for fd in fds.keys():
        if fd in rasters:
            rasters.remove(fd)
    return rasters


def raster_to_tif(
    gdb_path: os.PathLike | str,
    raster_name: str,
    tif_path: None | os.PathLike | str = None,
    options: None | dict = None,
):
    """
    Converts a raster stored in a file geodatabase to a GeoTIFF file.

    Reads the raster from the input geodatabase, including masking data, and saves it as a GeoTIFF
    file at the specified output path.

    :param gdb_path: The path to the input file geodatabase containing the raster
    :type gdb_path: os.PathLike | str
    :param raster_name: The name of the raster in the geodatabase to be converted
    :type raster_name: str
    :param tif_path: The optional path where the GeoTIFF file should be saved. If not
        provided, the output GeoTIFF file will be saved with the same name as the raster
        in the GDB directory. Defaults to None.
    :type tif_path: None | os.PathLike | str
    :param options: Additional keyword arguments for writing the GeoTIFF file, see the documentation: https://gdal.org/en/stable/drivers/raster/gtiff.html#creation-options
    :type options: dict
    """
    if not gdal_installed:
        raise ImportError(
            "GDAL not installed, ouroboros cannot support raster operations"
        )

    if tif_path is None:
        tif_path = os.path.join(os.path.dirname(gdb_path), raster_name + ".tif")

    if not tif_path.endswith(".tif"):
        tif_path += ".tif"

    # with _open_gdb(gdb_path) as gdb:
    gdal.UseExceptions()
    with gdal.Open(f"OpenFileGDB:{gdb_path}:{raster_name}") as raster:
        tif_drv: gdal.Driver = gdal.GetDriverByName("GTiff")
        if options:
            tif_drv.CreateCopy(tif_path, raster, strict=0, options=options)
        else:
            tif_drv.CreateCopy(tif_path, raster, strict=0)
