import os
import re
import shutil
import warnings
from collections.abc import MutableMapping, MutableSequence
from typing import Any, Iterator
from uuid import uuid4

import fiona
import geojson
import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyogrio
from pyproj.crs import CRS


class FeatureClass(MutableSequence):
    """
    Handles geospatial data as a mutable collection, allowing operations like accessing,
    modifying, appending, and deleting geospatial data while maintaining properties like
    CRS and geometry type.

    The FeatureClass acts as a custom container built on top of GeoPandas' GeoDataFrame,
    enabling fine-grained control and enhancements during manipulation of vector geospatial
    data. Typical use cases include creating, modifying, and managing geospatial features
    with attributes like coordinate systems and geometry types readily accessible.
    The class ensures robust handling of various input types when initializing or altering data.
    """

    def __init__(
        self,
        src: "None | os.PathLike | str | gpd.GeoDataFrame" = None,
    ):
        """
        Initializes the geospatial data container by parsing the source and extracting
        the necessary attributes, such as CRS (Coordinate Reference System) and
        geometry type. The source can be an existing GeoDataFrame, a file path to
        a geodatabase (GDB), or it can be empty.

        Parameters
        ----------
        src: None | os.PathLike | str | gpd.GeoDataFrame
            Source of the data. It can be:
              - A GeoDataFrame to initialize directly
              - A string or os.PathLike path pointing to a file or a geodatabase dataset
              - None for initializing an empty GeoDataFrame

        Raises
        ------
        TypeError
            Raised when the provided source type is unsupported or invalid.
        """
        self._data = None
        self.crs = None
        self.geom_type = None

        # parse src
        if isinstance(src, gpd.GeoDataFrame):
            self._data = src
            self._data.index.name = "ObjectID"
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
            raise TypeError(src)

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
        Deletes an item from the internal data structure by its index.

        The method removes a specified item from the associated data structure
        using the provided integer index. If the index is not of type int, a
        TypeError is raised. The internal data structure is managed using a
        pandas DataFrame, and the operation ensures that indices are properly
        reset post-deletion.

        Args:
            index (int): The position of the item to delete.

        Raises:
            TypeError: If the provided index is not an integer.
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
        Retrieves rows or slices of the GeoDataFrame based on the given index.

        The method supports indexing by integer, slice, list of integers or slices,
        and tuples of integers or slices. It allows extracting data in various formats
        depending on the provided index and returns the corresponding subset of the
        GeoDataFrame.

        Parameters:
        index: int | slice | Sequence[int | slice]
            The index or indices to retrieve rows or slices from the GeoDataFrame.
            - If an integer is provided, the corresponding row is retrieved.
            - If a slice is provided, the corresponding rows are retrieved as a slice.
            - If a list of integers or slices is given, multiple specific rows or slices
              are extracted.
            - If a tuple is provided containing integers or slices, multiple rows or
              slices are returned, concatenated as a single GeoDataFrame.

        Returns:
        gpd.GeoDataFrame
            A GeoDataFrame containing the rows or slices of data matching the provided
            index.

        Raises:
        KeyError
            Raised when the provided index is not of a valid type (i.e., not an integer,
            slice, list of integers or slices, or tuple containing these types).
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
        Returns an iterator over the rows of the internal data structure as tuples.

        The method provides a convenient way to iterate through each row of the
        stored data, represented as a tuple. It enables easy data access in an
        iterative context without directly exposing the underlying data.

        Returns:
            Iterator[tuple]: An iterator that provides each row of the data as a tuple.
        """
        return self._data.itertuples()

    def __len__(self) -> int:
        """
        Returns the number of elements or items in the object.

        This method allows retrieving the total count of elements contained
        within the object by leveraging the length of its internal data
        representation.

        Returns:
            int: The count of elements or items in the object.
        """
        return self._data.shape[0]

    def __setitem__(
        self,
        index: tuple[int, int | str],
        value: any,
    ) -> None:
        """
        Assign a value to the specified cell in a two-dimensional data structure.

        This method allows the user to specify a target cell using a tuple index
        composed of a row integer and a column integer or column name as a string.
        The value provided will overwrite the current content of the cell specified.

        Parameters:
            index (tuple[int, int | str]): A tuple where the first element is an
                integer representing the row index and the second element
                is either an integer for the column index or a string for the
                column name.
            value (any): The value to assign to the specified cell.

        Raises:
            TypeError: If the row index is not an integer.
            TypeError: If the column index is neither an integer nor a string.
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

    def append(self, value: gpd.GeoDataFrame) -> None:
        """
        Appends a value to the end of the collection.

        Parameters:
        value (gpd.GeoDataFrame): The value to append to the collection.

        Returns:
        None
        """
        self.insert(-1, value)

    def clear(self) -> None:
        """
        Clears all elements from the internal data structure.

        Once called, all
        previously stored data will no longer be accessible.

        Returns
        -------
        None
            This method does not return any value and modifies
            the internal data structure in-place.
        """
        self._data = self._data[0:0]

    def copy(self) -> "FeatureClass":
        """
        Creates and returns a deep copy of the current FeatureClass instance, duplicating
        its internal data to ensure the new object is independent of the original. This
        operation provides a new instance with its data replicated.

        Returns:
            FeatureClass: A new instance of FeatureClass containing a deep copy of the
                          internal data.
        """
        return FeatureClass(self._data.copy(deep=True))

    def describe(self) -> dict:
        """
        Provides a detailed description of the dataset, including its spatial reference
        system, fields, geometry type, index name, and row count.

        Returns
        -------
        dict
            A dictionary containing the following keys:
            - 'crs': The name of the Coordinate Reference System (CRS) if defined;
                     otherwise, None.
            - 'fields': A list of field names in the dataset.
            - 'geom_type': The geometry type of the dataset.
            - 'index_name': The name of the index column of the dataset.
            - 'row_count': The number of rows in the dataset.
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
        Returns the first `n` rows of the GeoDataFrame.

        This method is used to retrieve a subset of the first rows from the
        GeoDataFrame stored in the object's internal `_data` attribute.

        Parameters
        ----------
        n : int, default 10
            Number of rows to return from the GeoDataFrame.
        silent : bool, default False
            If True, suppresses printing the retrieved rows.

        Returns
        -------
        gpd.GeoDataFrame
            A GeoDataFrame containing the first `n` rows.
        """
        h = self._data.head(n)
        if not silent:
            print(h)
        return h

    def insert(self, index: int, value: gpd.GeoDataFrame) -> None:
        """
        Insert a GeoDataFrame into the current structure at a specified index, ensuring schema
        compatibility, geometry type consistency, and proper handling of mixed geometries.

        Parameters:
        index: int
            The position where the GeoDataFrame should be inserted. Must be an integer.
        value: gpd.GeoDataFrame
            The GeoDataFrame to insert. Must have the same schema as the current data.

        Raises:
        TypeError
            If `index` is not an integer.
            If `value` is not an instance of gpd.GeoDataFrame.
            If the geometry types within `value` are incompatible with the existing
            geometry type constraints.
        ValueError
            If the schema of `value` does not match the schema of the existing data.
        """
        if not isinstance(index, int):
            raise TypeError("Index must be an integer")
        if not isinstance(value, gpd.GeoDataFrame):
            raise TypeError("Value must be an instance of gpd.GeoDataFrame")

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

    def list_fields(self):
        """
        Returns a list of field names in the data.

        This method retrieves the column names of the underlying data and
        adds the index name as the first field in the list.

        Returns:
            list: A list of field names including the index name as the first item.
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
        Saves the current geodataframe to a file geodatabase within a specified feature class
        and feature dataset, optionally allowing overwriting of any existing data.

        Parameters:
        gdb_path : os.PathLike | str
            The path to the file geodatabase where the geodataframe will be saved.
        fc_name : str
            The name of the feature class within the geodatabase where the data will
            be written.
        feature_dataset : str, optional
            The name of the feature dataset within the geodatabase to contain the feature
            class. If not provided, the feature class will be saved at the root of the
            geodatabase.
        overwrite : bool, optional
            If True, existing data in the specified feature class will be overwritten.
            Defaults to False.

        Returns:
        None
        """
        gdf_to_fc(
            gdf=self._data,
            gdb_path=gdb_path,
            fc_name=fc_name,
            feature_dataset=feature_dataset,
            overwrite=overwrite,
        )

    def sort(
        self,
        field_name: str,
        ascending: bool = True,
    ) -> None:
        """
        Sorts the data in the dataset based on a specific field.

        This method orders the dataset according to the values of the specified
        field name. The sorting can be performed in either ascending or descending
        order based on the provided parameter.

        Parameters:
        field_name : str
            The name of the field in the dataset to sort by.
        ascending : bool, optional
            Determines the order of sorting. If True, the data will be sorted
            in ascending order. If False, the data will be sorted in descending
            order. Default is True.
        """
        self._data.sort_values(by=field_name, ascending=ascending, inplace=True)

    def to_geodataframe(self) -> gpd.GeoDataFrame:
        """
        Converts the internal data into a GeoDataFrame.

        This method returns a deep copy of the internal GeoDataFrame to ensure
        the original data remains unmodified.

        Returns:
            gpd.GeoDataFrame: A deep copy of the internal GeoDataFrame.
        """
        return self._data.copy(deep=True)

    def to_geojson(
        self, filename: os.PathLike | str = None
    ) -> "None | geojson.FeatureCollection":
        """
        Converts the spatial data to the GeoJSON format, with an optional capability to save it to a file.

        When a filename is provided, the GeoJSON output will be written to that file. If no filename is
        specified, the GeoJSON format will be returned as a FeatureCollection object. The filename
        is automatically suffixed with '.geojson' if not specified in the provided name. The data is
        projected to the WGS84 coordinate system if no filename is used.

        Parameters:
            filename (os.PathLike | str, optional): The name of the file where the GeoJSON output
                should be written. Defaults to None. If provided, the resulting GeoJSON data
                will be saved to this file.

        Returns:
            None | geojson.FeatureCollection: Returns None when a filename is provided and the GeoJSON
                data is written to disk. Otherwise, returns a GeoJSON FeatureCollection object.

        Raises:
            ValueError: Raised if specific conditions or constraints are violated (details omitted).
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
        Converts internal data representation to a PyArrow Table.

        This method transforms the internal data structure into a PyArrow Table
        format to facilitate compatibility with Apache Arrow ecosystem.

        Returns:
            pa.Table: A PyArrow Table object that represents the internal data.
        """
        arrow_table = self._data.to_arrow()
        return pa.table(arrow_table)

    def to_shapefile(self, filename: os.PathLike | str) -> None:
        if not filename.endswith(".shp"):
            filename += ".shp"
        self._data.to_file(filename=filename, driver="ESRI Shapefile")


class FeatureDataset(MutableMapping):
    """
    A dataset containing a collection of feature classes with support for spatial referencing.

    FeatureDataset is a mutable mapping that organizes feature classes and enforces consistency
    in their spatial referencing system (Coordinate Reference System, CRS). It provides methods
    for managing feature classes, ensuring naming conventions, and validating CRS compatibility.

    Attributes:
        crs: The coordinate reference system (CRS) associated with the feature dataset. This is
             expected to be an instance of the CRS class or None. If None, it will inherit the CRS
             from the first feature class added to the dataset.

    Raises:
        ValueError: Raised when attempting to set a feature class name that does not adhere to
                    naming rules (e.g., starts with a digit or contains invalid characters).
        TypeError: Raised when attempting to set a feature class with an invalid type.
        KeyError: Raised when naming conflicts are detected with existing feature classes.
        AttributeError: Raised when there is a mismatch between the CRS of the dataset and a
                        feature class being added.
    """

    def __init__(self, crs: Any | CRS = None):
        """
        Initializes an instance of the class, setting up the necessary attributes.

        Attributes
        ----------
        crs : Any | CRS
            The coordinate reference system associated with the object. It can
            either be an instance of the CRS class, a compatible value, or None.

        Parameters
        ----------
        crs : Any | CRS, optional
            The coordinate reference system to initialize the object with (default
            is None).
        """
        self._fcs = dict()
        self._gdbs = set()

        if isinstance(crs, CRS) or crs is None:
            self.crs = crs
        else:
            self.crs = CRS(crs)

    def __delitem__(self, key, /):
        """
        Removes the item associated with the given key from the internal storage.

        This method allows deletion of an item in the object using the specified key.
        It modifies the internal data structure by removing the key-value pair that
        matches the provided key.

        Parameters:
        key: The key identifying the item to be removed. Must be a valid key present in
        the internal storage.
        """
        del self._fcs[key]

    def __getitem__(self, key: int | str, /) -> FeatureClass:
        """
        Implements retrieval of a feature class instance by either integer index or
        string key. Provides access to elements within the feature classes collection.

        Parameters:
        key (int | str): The index or key to retrieve the feature class. If an integer
        is provided, it specifies the position of the feature class in the list. If a
        string is provided, it specifies the key of the feature class.

        Returns:
        FeatureClass: The feature class instance corresponding to the provided key or
        index.

        Raises:
        IndexError: If an integer index is provided and it is out of the range of the
        available feature classes.
        KeyError: If a string key is provided and does not exist in the collection.
        """
        if isinstance(key, int):
            for idx, fc_obj in enumerate(self.feature_classes()):
                fc_name, fc = fc_obj
                if idx == key:
                    return fc
            raise IndexError(f"Index out of range: {key}")
        else:
            return self._fcs[key]

    def __iter__(self):
        """
        Returns an iterator over the internal collection.

        This method provides an iterator over the elements within the internal
        collection structure, facilitating iteration in a standard Pythonic approach.

        Returns:
            Iterator: An iterator of the elements contained in the internal
            collection.
        """
        return iter(self._fcs)

    def __len__(self):
        """
        Returns the number of elements in the collection.

        This method provides a way to determine the size of the collection
        by returning the count of elements it contains.

        Returns:
            int: The number of elements in the collection.
        """
        return len(self._fcs)

    def __setitem__(self, key: str, value: FeatureClass, /):
        """
        Sets a feature class to the specified key in the data structure. This method ensures
        type validation and imposes strict rules on naming conventions for the feature class
        key. It prevents duplication of feature class names and maintains consistency in
        coordinate reference systems (CRS) across the dataset.

        Parameters:
        key: str
            The name under which the `FeatureClass` should be stored. It must follow specific
            naming rules including starting with a non-digit, and containing only alphanumeric
            characters and underscores.
        value: FeatureClass
            The `FeatureClass` instance to be associated with the given key.

        Raises:
        TypeError
            If the `value` is not an instance of `FeatureClass`.
        ValueError
            If the key starts with a digit or contains invalid characters.
        KeyError
            If the key already exists in the dataset.
        AttributeError
            If the CRS of the feature dataset and the feature class do not match.
        """
        if not isinstance(value, FeatureClass):
            raise TypeError(f"Expected type ouroboros.FeatureClass: {value}")

        if key[0].isdigit():
            raise ValueError(f"Feature class name cannot start with a digit: {key} ")

        for letter in key:
            if not letter.isalpha() and not letter.isdigit() and not letter == "_":
                raise ValueError(
                    f"Feature class name can only contain letters, numbers, and underscores: {key}"
                )

        for gdb in self._gdbs:
            for fds_name, fds in gdb.items():
                for fc_name, fc in fds.items():
                    if key == fc_name:
                        raise KeyError(f"Feature class name already in use: {key}")

        self._fcs[key] = value

        if not self.crs:
            self.crs = value.crs
        else:
            try:
                assert self.crs == value.crs
            except AssertionError:
                raise AttributeError(
                    f"Feature dataset CRS ({self.crs} does not match feature class CRS ({value.crs})"
                )

    def feature_classes(self) -> tuple[tuple[str | None, FeatureClass], ...]:
        """
        Returns a tuple of feature classes.

        This method compiles a list of all feature classes from the internal
        mapping and returns them as a tuple of tuples. Each tuple contains
        the feature class name and its corresponding feature class object.

        Returns:
            tuple[tuple[str | None, FeatureClass], ...]: A tuple of tuples
            where each inner tuple consists of a feature class name and its
            corresponding feature class object.
        """
        fc_list = list()
        for fc_name, fc in self._fcs.items():
            fc_list.append((fc_name, fc))
        return tuple(fc_list)


class GeoDatabase(MutableMapping):
    """
    Represents a geodatabase that supports create, read, update, and delete operations on feature datasets
    and feature classes.

    The GeoDatabase class is a mutable mapping that allows storing and managing spatial datasets
    organized into feature classes and feature datasets. It provides methods to interact with the stored
    spatial data, including access, iteration, modification, and saving data to disk. The class is
    designed to facilitate the organization and manipulation of spatial data within a geodatabase structure.
    """

    def __init__(self, path: None | os.PathLike | str = None):
        """
        Initializes a new instance of the class. If a valid path is provided, it attempts to load
        datasets and layers from the specified location on disk. This process involves creating
        FeatureClasses and filling the FeatureDatasets accordingly. If no path is provided, the
        instance starts with an empty collection of FeatureDatasets.

        Args:
            path: Optional; The file path as None, a string, or os.PathLike object. If provided, it will
                  load datasets and layers from the given path.
        """
        self._fds: dict[str | None : FeatureDataset] = dict()
        self._uuid = uuid4()

        if path:  # load from disk
            datasets = list_datasets(path)
            lyrs = list_layers(path)
            for fds_name in datasets:
                fds = FeatureDataset()
                for fc_name in lyrs:
                    if fc_name in datasets[fds_name]:
                        fds[fc_name] = FeatureClass(fc_to_gdf(path, fc_name))
                self.__setitem__(fds_name, fds)

    # noinspection PyProtectedMember
    def __delitem__(self, key, /):
        """
        Removes the specified key and its associated value from the internal data structure.

        The method deletes an item identified by the given key from the internal collection
        and also ensures to remove the association of the current object from the referenced
        resource in the removed item's context.

        Parameters
        ----------
        key : Any
            The key associated with the item to be deleted.

        Raises
        ------
        KeyError
            If the key does not exist in the collection.
        """
        fds = self._fds[key]
        del self._fds[key]
        fds._gdbs.remove(self)

    def __getitem__(self, key: int | str, /) -> FeatureClass | FeatureDataset:
        """
        Provides access to elements of the GeoDatabase through indexing or key-based
        retrieval. Supports retrieval of both feature classes and feature datasets
        using either integer indexing or string-based keys.

        Parameters:
            key (int | str): The key to retrieve an element, where an integer refers
                to the index of a feature class and a string refers to the name of
                a feature class or dataset.

        Raises:
            KeyError: Raised if the key provided is neither an integer nor string, or
                if a non-existent string key is used.
            IndexError: Raised if the integer-based index is out of range.

        Returns:
            FeatureClass | FeatureDataset: Returns the matched feature class or
                feature dataset based on the provided key.
        """
        if not isinstance(key, int) and not isinstance(key, str) and key is not None:
            raise KeyError(f"Expected key to be an integer or string: {key}")

        if key in self._fds:
            return self._fds[key]
        elif isinstance(key, int):
            for idx, fc_obj in enumerate(self.feature_classes()):
                fc_name, fc = fc_obj
                if idx == key:
                    return fc
            raise IndexError(f"Index out of range: {key}")
        else:
            for fc_name, fc in self.feature_classes():
                if fc_name == key:
                    return fc
        raise KeyError(f"'{key}' does not exist in the GeoDatabase")

    def __hash__(self) -> int:
        """
        Calculates and returns the hash value for the object, ensuring that objects with
        the same UUID have the same hash value.

        Returns:
            int: The hash value of the object, generated from its UUID.
        """
        return hash(self._uuid)

    def __iter__(self):
        """
        Returns an iterator over the internal collection.

        Returns:
            Iterator: An iterator over the internal collection.
        """
        return iter(self._fds)

    def __len__(self):
        """
        Returns the total number of file descriptors being tracked.

        This method calculates and returns the total number of file descriptors
        by iterating over internal tracking storage and summing up their counts.

        Returns:
            int: The total count of file descriptors.
        """
        count = 0
        for fds in self._fds.values():
            count += len(fds)
        return count

    # noinspection PyProtectedMember
    def __setitem__(self, key: str, value: FeatureClass | FeatureDataset, /):
        """
        Sets a key-value pair in the container, where the key is a string and the value must be
        either a FeatureClass or a FeatureDataset. If the value is a FeatureClass, it ensures
        an appropriate FeatureDataset exists and associates the key with the value. If the
        value is a FeatureDataset, it associates the key with the FeatureDataset after validating
        it. Type checks are performed to ensure the validity of the provided value.

        Raises:
            TypeError: If the value is neither a FeatureClass nor a FeatureDataset.
            KeyError: If the key being added as a FeatureDataset already exists.

        Args:
            key (str): The key to associate with the value in the container.
            value (FeatureClass | FeatureDataset): The value, which must be either a FeatureClass
                                                   or a FeatureDataset.
        """
        if isinstance(value, FeatureClass):
            crs = value.to_geodataframe().crs
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

    def feature_classes(self) -> tuple[tuple[str | None, FeatureClass], ...]:
        """
        Returns a tuple of all feature classes and their names within the dataset.

        This method compiles all feature classes from the internal dataset structure
        and returns them as a tuple of tuples, where each inner tuple contains the
        feature class name and the feature class object.

        Returns:
            tuple[tuple[str | None, FeatureClass], ...]: A tuple containing all
            feature classes and their corresponding names within the dataset.
        """
        fc_list = list()
        for fds in self._fds.values():
            for fc_name, fc in fds.items():
                fc_list.append((fc_name, fc))
        return tuple(fc_list)

    def feature_datasets(self) -> tuple[[str | None, FeatureDataset], ...]:
        """
        Returns a tuple containing datasets and their corresponding names.

        This method processes internal dataset storage and retrieves all datasets along with
        their respective names as a tuple of name-dataset pairs. It ensures that all available
        datasets are included in the returned collection.

        Returns:
            tuple: A tuple containing pairs of datasets' names and their FeatureDataset objects.
        """
        fds_list = list()
        for fds_name in self._fds:
            fds_list.append((fds_name, self._fds[fds_name]))
        return tuple(fds_list)

    def save(self, path: os.PathLike | str, overwrite: bool = False):
        """
        Saves the current data to a specified geodatabase (.gdb) file at the given path.

        Parameters:
        path (os.PathLike | str): The file system path where the geodatabase will be
            saved. If the provided path does not include `.gdb`, the extension will
            be automatically appended.
        overwrite (bool): Flag indicating whether to overwrite the existing
            geodatabase if it already exists at the specified path. Defaults to False.

        Raises:
        AssertionError: If overwrite is enabled and the path still exists after
            attempting to remove it.
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
    Deletes a feature class from the specified geodatabase if it exists.

    This function verifies the existence of the feature class within the
    geodatabase and removes it if found. It will not perform any operation
    if the feature class does not exist.

    Parameters:
    gdb_path : os.PathLike | str
        The path to the geodatabase that contains the feature class.
    fc_name : str
        The name of the feature class to be deleted.

    Returns:
    bool
        True if the feature class was successfully deleted, False otherwise.

    Raises:
    TypeError
        If the provided feature class name is not a string.
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
    """
    Convert a feature class in a File Geodatabase (GDB) to a GeoDataFrame.

    This function reads in a specific feature class stored within a File Geodatabase
    and converts it into a GeoDataFrame which can be used for geospatial analysis.
    It ensures the GeoDataFrame's index is set to "ObjectID", corresponding to
    the unique identifier of the feature class.

    Parameters:
    gdb_path : os.PathLike | str
        Path to the File Geodatabase (.gdb file) containing the feature class.
    fc_name : str
        The name of the feature class to be read and converted.

    Returns:
    gpd.GeoDataFrame
        A GeoDataFrame representation of the feature class, with "ObjectID" set
        as the index.

    Raises:
    TypeError
        If the feature class name (`fc_name`) is not a string.
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
    Converts a GeoDataFrame or GeoSeries to a feature class in a geodatabase.

    This function allows for exporting a GeoDataFrame or GeoSeries to a file geodatabase
    as a feature class. It includes options for specifying feature datasets, geometry types,
    overwrite functionality, compatibility modes, and reindexing. When compatibility is enabled,
    it ensures compatibility with specific ArcGIS versions. Reindexing can help optimize memory usage.

    Attributes:
        gdf (gpd.GeoDataFrame | gpd.GeoSeries): The input GeoDataFrame or GeoSeries to
            be exported.
        gdb_path (os.PathLike | str): File path to the geodatabase where the feature
            class will be created.
        fc_name (str): Name of the feature class to create.
        feature_dataset (str, optional): Name of the feature dataset inside the geodatabase
            where the feature class will be stored.
        geometry_type (str, optional): Defines the geometry type for the output. It can be
            used to enforce specific geometry constraints.
        overwrite (bool, optional): If True and the feature class already exists, it will be
            deleted and replaced.
        compatibility (bool, optional): If True, compatibility settings such as
            ArcGIS version targeting will be applied.
        reindex (bool, optional): If True, uses in-memory spatial indexing for optimization.

    Raises:
        TypeError: If the input `gdf` is neither a GeoDataFrame nor a GeoSeries.
        FileExistsError: If the feature class already exists and `overwrite` is set to False.
        FileNotFoundError: If the specified geodatabase path does not exist or is invalid.

    Parameters:
        gdf: The input GeoDataFrame or GeoSeries to be exported.
        gdb_path: File path to the geodatabase where the feature class will be created.
        fc_name: Name of the feature class to create.
        feature_dataset: Name of the feature dataset inside the geodatabase
            (optional).
        geometry_type: Defines the geometry type for the output (optional).
        overwrite: Flag to overwrite an existing feature class (optional).
        compatibility: Flag to apply compatibility settings for ArcGIS (optional).
        reindex: Flag to use in-memory spatial indexing for optimization (optional).
    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        if isinstance(gdf, gpd.GeoSeries):
            gdf = gpd.GeoDataFrame(gdf)
        else:
            raise TypeError("Input must be a GeoDataFrame or GeoSeries")

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
        gdf.to_file(
            gdb_path,
            driver="OpenFileGDB",
            layer=fc_name,
            layer_options=layer_options,
            geometry_type=geometry_type,
        )
    except pyogrio.errors.DataSourceError:
        raise FileNotFoundError(gdb_path)


def list_datasets(gdb_path: os.PathLike | str) -> dict[str | None, list[str]]:
    """
    Lists the datasets contained in a given geodatabase path.

    This function processes the contents of a geodatabase file structure to identify
    feature datasets and their corresponding feature classes. It returns a dictionary
    mapping feature datasets to their feature classes. Feature classes that are not part
    of any dataset are listed under a `None` key.

    Parameters:
        gdb_path (os.PathLike | str): The file path to the geodatabase.

    Returns:
        dict[str | None, list[str]]: A dictionary containing feature datasets as keys
        (or `None` for feature classes without a dataset) and lists of feature classes
        as values.
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


def list_layers(gdb_path: os.PathLike | str) -> list:
    """
    Lists all layers within a specified GeoDatabase.

    This function utilizes the `pyogrio` library to enumerate the layers present in
    the given GeoDatabase file. If the GeoDatabase is empty or not valid,
    an empty list is returned.

    Args:
        gdb_path (os.PathLike | str): The path to the GeoDatabase file to query.

    Returns:
        list: A list of layer names available in the specified GeoDatabase.
    """
    # noinspection PyUnresolvedReferences
    try:
        return [fc[0] for fc in pyogrio.list_layers(gdb_path)]
    except pyogrio.errors.DataSourceError:  # empty GeoDatabase
        return list()
