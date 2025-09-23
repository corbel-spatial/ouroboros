import os
import re
import shutil
import uuid
import warnings
from collections.abc import MutableMapping, MutableSequence
from importlib import metadata
from typing import Any, Iterator, Sequence, Literal
from uuid import uuid4

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import shapely
import xmltodict
from matplotlib import pyplot as plt


__version__ = metadata.version("ouroboros-gis")

from pyogrio.errors import DataSourceError

# Check for optional install of GDAL>=3.8 for raster support
try:
    from osgeo import gdal  # noqa # fmt: skip

    _gdal_installed = True
    _gdal_version = gdal.__version__
except ModuleNotFoundError:
    _gdal_installed = False
    _gdal_version = None
if _gdal_version:
    _version_split = _gdal_version.split(".")
    if int(_version_split[0]) < 3 or int(_version_split[1]) < 8:
        raise ImportError(
            "GDAL version must be >=3.8, please upgrade to a newer version"
        )


pd.options.mode.copy_on_write = True  # See https://pandas.pydata.org/pandas-docs/stable/user_guide/copy_on_write.html#copy-on-write
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_colwidth", None)


class FeatureClass(MutableSequence):
    """
    The FeatureClass acts as a custom container built on top of geopandas.GeoDataFrame,
    allowing operations like accessing, modifying, appending, and deleting geospatial data
    while maintaining properties like CRS (Coordinate Reference System) and geometry type.
    """

    # noinspection PyTypeHints
    def __init__(
        self,
        src: "None | os.PathLike | str | FeatureClass | geopandas.GeoDataFrame | geopandas.GeoSeries | pandas.DataFrame | pandas.Series" = None,  # noqa
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
        :type src: DataFrame, optional

        :raises TypeError: Raised when the provided source type is unsupported or invalid

        """
        self._data: gpd.GeoDataFrame | None = None
        self._geom_type: type[shapely.Geometry] | None = None

        # parse src
        if isinstance(src, gpd.GeoDataFrame):
            self._data = src.copy(deep=True)

        elif isinstance(src, gpd.GeoSeries):
            self._data = gpd.GeoDataFrame(geometry=src.copy(deep=True))

        elif isinstance(src, pd.DataFrame) or isinstance(src, pd.Series):
            self._data = gpd.GeoDataFrame(src.copy(deep=True))

        elif isinstance(src, FeatureClass):
            self._data = src.gdf

        elif isinstance(src, os.PathLike) or isinstance(
            src, str
        ):  # on load data from gdb
            src = os.path.abspath(src)

            if not os.path.splitext(src)[1] == "":  # path cannot have a file extension
                raise TypeError(f"Expected a path to a feature class: {src}")

            # parse path to handle Feature Dataset pathing (spam.gdb/egg_fds/ham_fc)
            split_path = src.split(os.sep)
            fc_name = split_path[-1]
            if not split_path[-2].endswith(".gdb"):
                gdb_path = os.sep.join(split_path[:-2])
            else:
                gdb_path = os.sep.join(split_path[:-1])

            # check that gdb exists
            if not os.path.exists(gdb_path):
                raise FileNotFoundError(src)

            # convert to GeoDataFrame
            self._data: gpd.GeoDataFrame = fc_to_gdf(gdb_path, fc_name)

        elif src is None:
            self._data = gpd.GeoDataFrame()

        else:
            raise TypeError((src, type(src)))

        self._geom_type, self._data = sanitize_gdf_geometry(self._data)

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
            * If an integer is provided, the corresponding row is retrieved
            * If a slice is provided, the corresponding rows are retrieved
            * If a list or tuple of integers or slices is given, multiple specific rows or slices are retrieved
        :type index: int | slice | Sequence[int | slice]

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
        :return: The number of rows in the FeatureClass
        :rtype int:

        """
        return self._data.shape[0]

    def __setitem__(
        self,
        index: tuple[int, int | str],
        value: Any,
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
        :type value: Any

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

    @property
    def crs(self) -> pyproj.crs.CRS | None:
        """
        :return: The Coordinate Reference System (CRS) of the FeatureClass, defaults to :code:`None`

        """
        try:
            return self._data.crs
        except AttributeError:
            return None

    @property
    def gdf(self) -> gpd.GeoDataFrame:
        return self._data

    @property
    def geom_type(self) -> None | shapely.Geometry:
        """
        The geometry type of the FeatureClass, e.g., :class:`shapely.Point`, :class:`shapely.LineString`, :class:`shapely.Polygon`; defaults to :code:`None`

        :return:
        """
        return self._geom_type

    @property
    def geometry(self) -> None | gpd.GeoSeries:
        """
        Accessor for the geometry of the FeatureClass

        :rtype: None | geopandas.GeoSeries

        """
        if self._data.active_geometry_name:
            return self._data.geometry
        else:
            return None

    # noinspection PyTypeHints
    def append(self, value: "gpd.GeoDataFrame | FeatureClass") -> None:
        """
        Appends rows to the end of the FeatureClass.

        The appended data must be compatible with the GeoDataFrame data structure.

        :param value: The value to append to the collection.
        :type value: geopandas.GeoDataFrame | FeatureClass

        """
        if isinstance(value, gpd.GeoDataFrame):
            self.insert(-1, value)
        elif isinstance(value, FeatureClass):
            self.insert(-1, value.gdf)
        else:
            raise TypeError(
                f"Invalid type: {type(value)}, expected geopandas.GeoDataFrame or FeatureClass"
            )

    def calculate(
        self,
        column: str,
        expression: str | Any,
        dt: None | np.dtype | Any = None,
    ) -> None:
        """
        Performs calculations on a column in the dataset based on the provided expression.

        The :code:`expression` is stringified Python code that will be evaluated for each row.
        If :code:`column` does not exist, a new column will be created.
        Other columns can be referenced using the syntax: :code:`$column_name$`

        Example::

            fc.calculate(column="new_col", expression="int($existing_col$) * 42", dtype=numpy.uint8)

        :param column: Name of the column to calculate, will be created if it does not exist
        :type column: str
        :param expression: Expression to evaluate for each value in the input column, will be evaluated by the method call and then stringified
        :type expression: str | Any
        :param dt: Type to convert the results to
        :type dt: type | np.dtype, optional

        """
        columns = self._data.columns
        if not isinstance(expression, str):
            expression = str(expression)

        if column in columns:
            result: pd.Series = self._data[
                column
            ].convert_dtypes()  # .convert_dtypes() copies
        else:
            result = pd.Series(index=np.arange(len(self._data)), dtype=dt)

        if "$" not in expression:
            # don't parse, just evaluate
            result: pd.Series = result.map(lambda x: expression)
        else:
            # parse an expression that contains column names
            col_names = str()  # parsed names of DataFrame columns
            col_names_n = 0
            parsed_expression = (
                str()
            )  # all parts of the expression that are not column names
            col_name_mode = False  # whether we're currently parsing a column name
            for char in expression:
                if char == "$" and not col_name_mode:  # start escaped sequence
                    col_name_mode = True
                    col_names_n += 1
                elif char == "$" and col_name_mode:  # end escaped sequence
                    col_name_mode = False
                    col_names += "$"
                    parsed_expression += f"{{{col_names_n - 1}}}"
                elif col_name_mode:
                    col_names += char
                else:
                    parsed_expression += char
            col_names = col_names.strip("$").split("$")
            try:
                other_col_series = [self._data[col] for col in col_names]
            except KeyError as e:
                raise KeyError(f"Column not found in data: {e}")

            # evaluate expression on each row
            for row_idx in range(len(result)):
                # get row values
                other_values = [f"'{other[row_idx]}'" for other in other_col_series]
                # insert values and evaluate
                result.loc[row_idx] = eval(parsed_expression.format(*other_values))

        if dt and result.dtype != dt:
            result.astype(dt, copy=False)

        # save results
        if column in columns:
            # update in place
            self._data.update(result)
        else:
            # append new column
            loc = len(columns) - 1
            self._data.insert(loc, column, result)

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

    # noinspection PyTypeHints
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
            value = value.gdf
        value: gpd.GeoDataFrame

        if len(self._data.columns) >= 1:
            try:
                assert (value.columns == self._data.columns).all()
            except ValueError:
                raise ValueError("Schemas must match")

        # validate incoming geometry
        new_geom_type, value = sanitize_gdf_geometry(value)
        if self._geom_type is None:
            self._geom_type = new_geom_type
        elif self._geom_type != new_geom_type:
            raise TypeError(
                f"Geometry type must be {self._geom_type}, not {new_geom_type}"
            )
        else:
            assert self._geom_type == new_geom_type

        # insert features into dataframe
        if index == 0:
            c = [value, self._data]
        elif index == -1:
            c = [self._data, value]
        else:
            c = [self._data.iloc[:index], value, self._data.iloc[index:]]
        self._data = pd.concat(
            c, ignore_index=True
        )  # pandas will automatically reindex after concatenating

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

    def show(self, block: bool = True):
        """
        Display the geometry in a simple Matplotlib plot

        :param block: If True, waits for user to close the plot, defaults to True
        :type block: bool, optional
        """
        fig, ax = plt.subplots()
        self._data.geometry.plot(ax=ax)
        plt.show(block=block)
        plt.close()

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
        # check all columns exist and turn into a list
        if not isinstance(columns, str):
            for col in columns:
                if col not in self._data.columns:
                    raise KeyError(f"Column '{col}' not found in data.")
            columns = list(columns)
        else:
            columns = [columns]

        # only geometry was requested
        if columns == "geometry" or (len(columns) == 1 and columns[0] == "geometry"):
            return FeatureClass(self._data.geometry)

        # geometry and other columns requested
        if len(columns) >= 1 and "geometry" in columns:
            columns.remove("geometry")
            geometry = True

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

        Examples::

            fc.select_rows("colA > colB")

            ObjectID    colA    colB
            42          10      9
            99          201     0


            fc.select_rows("colA == 'spam'")

            ObjectID    colA
            1           spam
            2           spam

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


class FeatureDataset(MutableMapping):
    """
    A `dict`-like collection of FeatureClass objects with an enforced CRS.

    A FeatureDataset is a mutable mapping that organizes feature classes and enforces consistency
    in their coordinate reference system (CRS).

    """

    def __init__(
        self,
        contents: None | dict[str, FeatureClass] = None,
        crs: None | pyproj.crs.CRS | Any = None,
        enforce_crs: bool = True,
    ):
        """
        Initialize a new FeatureDataset instance with an optional coordinate reference system (CRS).

        The CRS can be specified as any value compatible with the CRS class constructor.

        :param contents: A dict of FeatureClass names and their objects to initialize the FeatureDataset with
        :type contents: dict[str, FeatureClass], optional

        :param crs: The coordinate reference system to initialize the FeatureDataset with
        :type crs: pyproj.crs.CRS | Any, optional

        :param enforce_crs: Whether to enforce the CRS in the FeatureDataset, defaults to True
        :type enforce_crs: bool

        :raises TypeError: If the provided CRS value cannot be converted to a valid CRS object

        """
        self._data: dict[str, dict[str, FeatureClass] | set[GeoDatabase]] = {
            "fcs": dict(),
            "gdbs": set(),
        }
        self._crs: pyproj.crs.CRS | None = None
        self._enforce_crs: bool = enforce_crs

        if self._enforce_crs:
            if isinstance(crs, pyproj.crs.CRS) or crs is None:
                self._crs = crs
            else:
                self._crs = pyproj.crs.CRS(crs)
        else:
            self._crs = None

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
        del self._data["fcs"][key]

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
            for idx, fc_obj in enumerate(self.fc_dict.values()):
                if idx == key:
                    return fc_obj
            raise IndexError(f"Index out of range: {key}")
        else:
            return self._data["fcs"][key]

    def __iter__(self) -> Iterator[str]:
        """
        Return an iterator over the FeatureDataset.

        :return: An iterator of a dict with the structure {FeatureClass name: FeatureClass object}
        :rtype: Iterator[dict[str, FeatureClass]]

        """
        return iter(self._data["fcs"])

    def __len__(self):
        """
        :return: The number of FeatureClass objects in the FeatureDataset
        :rtype: int

        """
        return len(self._data["fcs"])

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

        for gdb in self._data["gdbs"]:
            for fds_name, fds in gdb.items():
                for fc_name, fc in fds.items():
                    if key == fc_name:
                        raise KeyError(f"FeatureClass name already in use: {key}")

        key: str
        value: FeatureClass
        self._data["fcs"][key] = value

        if self._enforce_crs:
            if not self.crs:
                self._crs = value.crs
            else:
                try:
                    assert self.crs == value.crs
                except AssertionError:
                    raise AttributeError(
                        f"Feature dataset CRS ({self.crs} does not match FeatureClass CRS ({value.crs})"
                    )

    @property
    def crs(self) -> pyproj.crs.CRS | None:
        """
        :return: The ordinate Reference System (CRS) of the FeatureDataset
        :rtype: pyproj.crs.CRS

        """
        return self._crs

    @property
    def enforce_crs(self) -> bool:
        """
        :return: A boolean value indicating whether CRS enforcement is enabled.
        :rtype: bool

        """
        return self._enforce_crs

    @property
    def fc_dict(self) -> dict[str, FeatureClass]:
        """
        :return: Return a :code:`dict` of the :class:`FeatureClass` names and their objects contained by the FeatureDataset
        :rtype: dict[str, FeatureClass]

        """
        return self._data["fcs"]

    @property
    def fc_names(self) -> list[str]:
        """
        :return: Return a :code:`list` of the :class:`FeatureClass` names contained by the FeatureDataset
        :rtype: list[str]

        Equivalent to :code:`FeatureDataset.fc_dict().keys()`

        """
        return list(self._data["fcs"].keys())

    @property
    def fcs(self) -> list[FeatureClass]:
        """
        :return: Return a :code:`list` of the :class:`FeatureClass` objects and contained by the FeatureDataset
        :rtype: list[FeatureClass]

        Equivalent to :code:`FeatureDataset.fc_dict().values()`

        """
        return list(self._data["fcs"].values())


class GeoDatabase(MutableMapping):
    """
    A :code:`dict`-like collection of :class:`FeatureDataset` and :class:`FeatureClass` objects.

    The GeoDatabase class is a mutable mapping that allows storing and managing spatial datasets
    organized into FeatureClass and FeatureDataset objects. It provides methods to interact with the stored
    spatial data, including access, iteration, modification, and saving data to disk.

    """

    def __init__(
        self,
        path: None | os.PathLike | str = None,
        contents: dict[str, FeatureClass | FeatureDataset] | None = None,
    ):
        """
        Initialize a new GeoDatabase instance.

        If a valid path is provided, attempts to load datasets and layers from the specified
        location on disk. If no path is provided, the instance starts with an empty collection
        of :class:`FeatureDataset` objects.

        :param path: The file path to load datasets and layers from
        :type path: os.PathLike | str, optional

        :param contents: A dict of dataset names and their objects to initialize the GeoDatabase with
        :type contents: dict[str : FeatureClass | FeatureDataset], optional

        """
        self._data: dict[str | None, FeatureDataset] = dict()
        self._uuid: uuid.UUID = uuid4()  # for self.__hash__()

        if path:  # load from disk
            if not os.path.exists(path):
                raise FileNotFoundError(f"File not found: {path}")
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

        fds = self._data[key]
        del self._data[key]
        fds._data["gdbs"].remove(self)

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

        if key in self._data:
            return self._data[key]
        elif isinstance(key, int):
            for idx, fc_obj in enumerate(self.fc_dict.values()):
                if idx == key:
                    return fc_obj
            raise IndexError(f"Index out of range: {key}")
        else:
            for fc_name, fc in self.fc_dict.items():
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

    def __iter__(self) -> Iterator[str | None]:
        """
        Return an iterator over the FeatureDataset objects in the GeoDatabase.

        :return: Iterator yielding (name, dataset) pairs for each FeatureDataset
        :rtype: Iterator[dict[str, FeatureDataset]]

        """
        return iter(self._data)

    def __len__(self):
        """
        :return: The count of FeatureClass objects contained in the GeoDatabase
        :rtype int:

        """
        count = 0
        for fds in self._data.values():
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
                crs = value.gdf.crs
            except AttributeError:
                crs = None
            if None not in self._data:
                self._data[None] = FeatureDataset(crs=crs)
            self._data[None]._data["gdbs"].add(self)
            self._data[None][key] = value
        elif isinstance(value, FeatureDataset):
            if key in self._data:
                raise KeyError(f"Feature dataset name already in use: {key}")
            else:
                self._data[key] = value
                self._data[key]._data["gdbs"].add(self)
        else:
            raise TypeError(f"Expected FeatureClass or FeatureDataset: {value}")

    @property
    def fc_dict(self) -> dict[str, FeatureClass]:
        """
        :return: A :code:`dict` of the :class:`FeatureClass` names and their objects contained by the GeoDatabase
        :rtype: dict[str, FeatureClass]

        """
        fcs = dict()
        for fds in self._data.values():
            for fc_name, fc in fds.items():
                fcs[fc_name] = fc
        return fcs

    @property
    def fc_names(self) -> list[str]:
        """
        :return: A :code:`list` of the :class:`FeatureClass` names contained by the GeoDatabase
        :rtype: list[str]

        Equivalent to :code:`GeoDatabase.fc_dict.keys()`

        """
        fc_names = list()
        for fds in self._data.values():
            for fc_name in fds.keys():
                fc_names.append(fc_name)
        return fc_names

    @property
    def fcs(self) -> list[FeatureClass]:
        """
        :return: A :code:`list` of the :class:`FeatureClass` objects contained by the GeoDatabase
        :rtype: list[str]

        Equivalent to :code:`GeoDatabase.fc_dict.values()`
        """
        fcs = list()
        for fds in self._data.values():
            for fc in fds.values():
                fcs.append(fc)
        return fcs

    @property
    def fds_dict(self) -> dict[str, FeatureDataset]:
        """
        :return: A :code:`dict` of the :class:`FeatureDataset` names and their objects contained by the GeoDatabase
        :rtype: dict[str, FeatureDataset]

        """
        return self._data

    @property
    def fds_names(self) -> list[str]:
        """
        :return: A :code:`list` of the :class:`FeatureDataset` names contained by the GeoDatabase
        :rtype: list[str]

        Equivalent to :code:`GeoDatabase.fds_dict.keys()`

        """
        return list(self._data.keys())

    @property
    def fds(self) -> list[FeatureDataset]:
        """
        :return: A :code:`list` of the :class:`FeatureDataset` objects contained by the GeoDatabase
        :rtype: list[FeatureDataset]

        Equivalent to :code:`GeoDatabase.fds_dict.values()`

        """
        return list(self._data.values())

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

        for fds_name, fds in self._data.items():
            for fc_name, fc in fds.items():
                gdf_to_fc(
                    fc.gdf,
                    gdb_path=path,
                    fc_name=fc_name,
                    feature_dataset=fds_name,
                    overwrite=overwrite,
                )


def buffer(fc: FeatureClass, distance: float, **kwargs: dict) -> FeatureClass:
    """
    Buffer a feature class by a specified distance

    Wraps geopandas.GeoSeries.buffer()

    :param fc: Input feature class to buffer
    :type fc: FeatureClass
    :param distance: Buffer distance in the units of the feature class's CRS
    :type distance: float
    :param kwargs: Keyword arguments of `geopandas.GeoSeries.buffer <https://geopandas.org/docs/reference/api/geopandas.GeoSeries.buffer.html>`__
    :type kwargs: dict

    :return: The buffered feature class
    :rtype: FeatureClass

    """
    gdf = fc.gdf
    new_geom = gdf.buffer(distance=distance, **kwargs)
    gdf.set_geometry(new_geom, inplace=True)
    return FeatureClass(gdf)


# noinspection PyProtectedMember
def clip(fc: FeatureClass, mask_fc: FeatureClass, **kwargs: dict) -> FeatureClass:
    """
    Clip a feature class by a mask feature class.

    Wraps geopandas.clip()

    :param fc: Input feature class to be clipped
    :type fc: FeatureClass
    :param mask_fc: Feature class to use as the clipping boundary
    :type mask_fc: FeatureClass
    :param kwargs: Keyword arguments of `geopandas.clip <https://geopandas.org/docs/reference/api/geopandas.clip.html>`__
    :type kwargs: dict
    :return: The clipped feature class
    :rtype: FeatureClass
    """
    gdf = gpd.clip(gdf=fc._data, mask=mask_fc._data, **kwargs)
    return FeatureClass(gdf)


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

    :raises TypeError: If `fc_name` is not a string

    """
    if not isinstance(fc_name, str):
        raise TypeError("Feature class name must be a string")

    with warnings.catch_warnings():  # hide pyogrio driver warnings
        warnings.simplefilter("ignore")
        gdf: gpd.GeoDataFrame = gpd.read_file(gdb_path, layer=fc_name)
    gdf = gdf.rename_axis("ObjectID")  # use ObjectID as dataframe index

    return gdf


def gdf_to_fc(
    gdf: gpd.GeoDataFrame | gpd.GeoSeries,  # noqa
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
        if fc_name in list_layers(gdb_path) and not overwrite:
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
    gdb_path = os.path.abspath(gdb_path)
    if not os.path.exists(gdb_path):
        raise FileNotFoundError(gdb_path)
    if not os.path.isdir(gdb_path):
        raise TypeError(f"{gdb_path} is not a directory")

    result = dict()

    with open(os.path.join(os.path.abspath(gdb_path), "a00000004.gdbtable"), "rb") as f:
        gdbtable = f.read()

        for root_name in [
            "DEFeatureClassInfo",
            "DEFeatureDataset",
            "DERasterDataset",
            "DETableInfo",
            "DEWorkspace",
            "ESRI_ItemInformation",
            "metadata",
            "typens:DEFeatureClassInfo",
            "typens:DEFeatureDataset",
            "typens:DERasterDataset",
            "typens:DETableInfo",
            "typens:DEWorkspace",
            "typens:ESRI_ItemInformation",
            "typens:metadata",
        ]:
            start_pos = 0
            while True:
                start_pos = gdbtable.find(bytes(f"<{root_name} ", "utf-8"), start_pos)
                end_pos = gdbtable.find(bytes(f"</{root_name}>", "utf-8"), start_pos)
                if start_pos == -1 or end_pos == -1:  # stop loop at the end of the file
                    break
                end_pos = end_pos + len(f"</{root_name}>")
                match = gdbtable[start_pos:end_pos].decode("utf-8")
                start_pos = end_pos

                xml_dict = xmltodict.parse(match)[root_name]

                root_name = (
                    root_name.replace("typens:", "")
                    .replace("DE", "")
                    .replace("Table", "")
                    .replace("Info", "")
                )
                if root_name not in result:
                    result[root_name] = list()
                result[root_name].append(xml_dict)

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
    gdb_path = os.path.abspath(gdb_path)
    if not os.path.exists(gdb_path):
        raise FileNotFoundError(gdb_path)
    if not os.path.isdir(gdb_path):
        raise TypeError(f"{gdb_path} is not a directory")

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
    gdb_path = os.path.abspath(gdb_path)
    if not os.path.exists(gdb_path):
        raise FileNotFoundError(gdb_path)
    if not os.path.isdir(gdb_path):
        raise TypeError(f"{gdb_path} is not a directory")

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
    gdb_path = os.path.abspath(gdb_path)
    if not os.path.exists(gdb_path):
        raise FileNotFoundError(gdb_path)
    if not os.path.isdir(gdb_path):
        raise TypeError(f"{gdb_path} is not a directory")

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


# noinspection PyProtectedMember
def overlay(
    fc1: FeatureClass,
    fc2: FeatureClass,
    how: Literal[
        "intersection", "union", "identity", "symmetric_difference", "difference"
    ] = "intersection",
    **kwargs: dict,
) -> FeatureClass:
    """
    Perform a spatial overlay between two FeatureClasses

    Wraps geopandas.overlay(), see the documentation for more details on the different `overlay methods <https://geopandas.org/en/stable/docs/user_guide/set_operations.html>`__

    :param fc1: First input feature class to be used in the overlay operation
    :type fc1: FeatureClass
    :param fc2: Second input feature class
    :type fc2: FeatureClass
    :param how: Method of spatial overlay
    :type how: str, defaults to :code:`intersection`
    :param kwargs: Keyword arguments of `geopandas.overlay <https://geopandas.org/docs/reference/api/geopandas.overlay.html>`__
    :type kwargs: dict
    :return: The clipped feature class
    :rtype: FeatureClass
    """
    gdf = gpd.overlay(fc1._data, fc2._data, how=how, **kwargs)
    return FeatureClass(gdf)


# PYNoinspection
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
    :type tif_path: os.PathLike | str, optional
    :param options: Additional keyword arguments for writing the GeoTIFF file, see the documentation: https://gdal.org/en/stable/drivers/raster/gtiff.html#creation-options
    :type options: dict, optional
    """
    if not _gdal_installed:
        raise ImportError(
            "GDAL not installed, ouroboros cannot support raster operations"
        )

    gdb_path = os.path.abspath(gdb_path)
    if not os.path.exists(gdb_path):
        raise FileNotFoundError(gdb_path)
    if not os.path.isdir(gdb_path):
        raise TypeError(f"{gdb_path} is not a directory")

    if tif_path is None:
        tif_path = os.path.join(os.path.dirname(gdb_path), raster_name + ".tif")

    if not tif_path.endswith(".tif"):
        tif_path += ".tif"

    gdal.UseExceptions()
    with gdal.Open(f"OpenFileGDB:{gdb_path}:{raster_name}") as raster:
        tif_drv: gdal.Driver = gdal.GetDriverByName("GTiff")
        if options:
            tif_drv.CreateCopy(tif_path, raster, strict=0, options=options)
        else:
            tif_drv.CreateCopy(tif_path, raster, strict=0)


def sanitize_gdf_geometry(
    gdf: gpd.GeoDataFrame,
) -> tuple[
    Literal[
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
        None,
    ],
    gpd.GeoDataFrame,
]:
    """
    Sanitizes the geometry column of a GeoDataFrame for compatibility with feature class geometries.

    This function accepts a GeoDataFrame and attempts to standardize the geometry types
    within the active geometry column. If the geometry column has only one consistent geometry
    type, it returns that type. Alternately, the function resolves simple two-type geometries
    (e.g., `Polygon` and `MultiPolygon`) to a multi-type geometry.

    :param gdf: The GeoDataFrame whose geometries need to be sanitized
    :type gdf: geopandas.GeoDataFrame

    :return: A tuple containing the resolved geometry type (e.g., `Point`, `MultiLineString`,
      etc.) or `None` and the modified GeoDataFrame with sanitized geometries
    :rtype: tuple[Literal["Point", "MultiPoint", "LineString", "MultiLineString", "Polygon",
      "MultiPolygon", None], geopandas.GeoDataFrame]

    :raises TypeError: If the input is not a GeoDataFrame or if the GeoDataFrame contains unsupported or too many geometry types
    :rtype: tuple[Literal["Point", "MultiPoint", "LineString", "MultiLineString", "Polygon",
      "MultiPolygon", None], geopandas.GeoDataFrame]

    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise TypeError("Input must be a GeoDataFrame")

    gdf.index.name = "ObjectID"

    if len(gdf) == 0 or gdf.active_geometry_name is None:
        return None, gdf

    geoms: list = gdf.geom_type.unique().tolist()
    if None in geoms:
        geoms.remove(None)

    if "GeometryCollection" in geoms:
        raise TypeError(
            "Cannot sanitize a GeoDataFrame with GeometryCollection geometries"
        )

    if len(geoms) == 0:
        return None, gdf

    elif len(geoms) == 1:
        return geoms[0], gdf

    elif len(geoms) == 2:
        if "Point" in geoms and "MultiPoint" in geoms:
            new_geom = list()
            for feature in gdf[gdf.active_geometry_name]:
                if feature is None:
                    new_geom.append(shapely.MultiPoint())
                elif isinstance(feature, shapely.Point):
                    try:
                        new_geom.append(shapely.MultiPoint([feature]))
                    except shapely.errors.EmptyPartError:
                        new_geom.append(shapely.MultiPoint())
                else:
                    new_geom.append(feature)
            gdf[gdf.active_geometry_name] = new_geom
            return "MultiPoint", gdf

        elif "LineString" in geoms and "LinearRing" in geoms:
            new_geom = list()
            for feature in gdf[gdf.active_geometry_name]:
                if feature is None:
                    new_geom.append(shapely.LineString())
                elif isinstance(feature, shapely.LinearRing):
                    new_geom.append(shapely.LineString(feature))
                else:
                    new_geom.append(feature)
            gdf[gdf.active_geometry_name] = new_geom
            return "LineString", gdf

        elif "MultiLineString" in geoms and (
            "LineString" in geoms or "LinearRing" in geoms
        ):
            new_geom = list()
            for feature in gdf[gdf.active_geometry_name]:
                if feature is None:
                    new_geom.append(shapely.MultiLineString())
                elif isinstance(feature, shapely.LineString) or isinstance(
                    feature, shapely.LinearRing
                ):
                    try:
                        new_geom.append(shapely.MultiLineString({feature}))
                    except shapely.errors.EmptyPartError:
                        new_geom.append(shapely.MultiLineString())
                else:
                    new_geom.append(feature)
            gdf[gdf.active_geometry_name] = new_geom
            return "MultiLineString", gdf

        elif "Polygon" in geoms and "MultiPolygon" in geoms:
            new_geom = list()
            for feature in gdf[gdf.active_geometry_name]:
                if feature is None:
                    new_geom.append(shapely.MultiPolygon())
                elif isinstance(feature, shapely.Polygon):
                    try:
                        new_geom.append(shapely.MultiPolygon([{feature}]))
                    except (shapely.errors.EmptyPartError, TypeError):
                        new_geom.append(shapely.MultiPolygon())
                else:
                    new_geom.append(feature)
            gdf[gdf.active_geometry_name] = new_geom
            return "MultiPolygon", gdf

        else:
            raise TypeError(
                f"Cannot sanitize a GeoDataFrame with mixed geometry types: {geoms}"
            )
    elif len(geoms) == 3:
        if (
            "LineString" in geoms
            and "MultiLineString" in geoms
            and "LinearRing" in geoms
        ):
            new_geom = list()
            for feature in gdf[gdf.active_geometry_name]:
                if feature is None:
                    new_geom.append(shapely.MultiLineString())
                elif isinstance(feature, shapely.LineString) or isinstance(
                    feature, shapely.LinearRing
                ):
                    try:
                        new_geom.append(shapely.MultiLineString([feature]))
                    except shapely.errors.EmptyPartError:
                        new_geom.append(shapely.MultiLineString())
                else:
                    new_geom.append(feature)
            gdf[gdf.active_geometry_name] = new_geom
            return "MultiLineString", gdf
        else:
            raise TypeError(
                f"Cannot sanitize a GeoDataFrame with incompatible geometries: {geoms}"
            )

    else:  # len(geoms) >= 4:
        raise TypeError(f"Too many geometry types to sanitize: {geoms}")
