import os
from collections.abc import MutableMapping, MutableSequence
from typing import Iterator
import pathlib

import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from pyogrio.errors import DataSourceError


class FeatureClass(
    MutableSequence
):  # TODO add geometry attribute and enforce; use feature datasets
    """
    Wraps a GeoDataFrame, and allows access like an arcpy.da cursor in memory.
    Must use 'save' method to write to disk.
    """

    def __init__(
        self,
        fc_name: str,
        src: None | os.PathLike | str | gpd.GeoDataFrame = None,
        feature_dataset: None | str = None,
    ):
        self.feature_dataset = feature_dataset
        self.gdb_path = None
        self.path = None
        self.saved = False

        # parse fc_name
        if not isinstance(fc_name, str):
            raise TypeError("fc_name must be a string")
        if fc_name[0].isdigit():
            fc_name = (
                "_" + fc_name
            )  # fc name cannot start with a digit, mimicking ArcGIS Pro renaming behavior
        self.name = fc_name

        # parse src
        if isinstance(src, gpd.GeoDataFrame):
            self._data = src
        elif isinstance(src, os.PathLike) or isinstance(src, str):
            if (
                not os.path.exists(src)
                or not os.path.isdir(src)
                or not src.endswith(".gdb")
            ):
                raise FileNotFoundError(src)
            else:
                self.gdb_path = pathlib.Path(os.path.abspath(src))
                self._data: gpd.GeoDataFrame = fc_to_gdf(self.gdb_path, self.name)
                self.saved = True
        else:
            self._data = gpd.GeoDataFrame()

        # parse path
        if self.gdb_path:
            if self.feature_dataset:
                self.path = os.path.join(self.gdb_path, self.feature_dataset, self.name)
            else:
                self.path = os.path.join(self.gdb_path, self.name)
        else:
            self.path = self.name

    def __delitem__(self, index):
        if not isinstance(index, int):
            raise TypeError("index must be an integer")
        self._data = pd.concat(
            [self._data.iloc[: index - 1], self._data.iloc[index:]]
        ).reset_index(drop=True)
        self.saved = False

    def __getitem__(self, index: int) -> gpd.GeoDataFrame:
        if not isinstance(index, int):
            raise TypeError("index must be an integer")
        return self._data.iloc[[index]]

    def __iter__(self):
        return self._data.itertuples()

    def __len__(self):
        if len(self._data.shape) != 2:
            raise ValueError("GeoDataFrame must be two-dimensional")
        return self._data.shape[0]

    def __repr__(self):
        return (
            f"ob.FeatureClass('{self.name}', gpd.GeoDataFrame({self._data.to_json()}))"
        )

    def __setitem__(
        self,
        index: tuple[int, int | str],
        value,
    ):
        """index is a tuple (row, column) where column can be int or str"""
        row, column = index

        if not isinstance(row, int):
            raise TypeError("Row index must be an integer")
        if not isinstance(column, int) and not isinstance(column, str):
            raise TypeError("Column index must be an integer or a column name string")

        if type(column) is int:
            self._data.iat[row, column] = value
        else:
            self._data.at[row, column] = value
        self.saved = False

    def __str__(self):
        return self.path

    def append(self, value):
        self.insert(-1, value)

    def clear(self):
        self._data = self._data[0:0]

    def count(self, value: shapely.Geometry):  # TODO
        raise NotImplementedError

    def describe(self):
        return {
            "feature_dataset": self.feature_dataset,
            "fields": self.get_fields(),
            "gdb_path": str(self.gdb_path),
            "name": self.name,
            "path": str(self.path),
            "row_count": len(self._data),
            "saved": self.saved,
        }

    def get_fields(self):
        return self._data.columns.to_list()

    def gdf(self, deep_copy: bool = True):
        return self._data.copy(deep=deep_copy)

    def head(self, n: int = 10, silent: bool = False) -> gpd.GeoDataFrame:
        h = self._data.head(n)
        if not silent:
            print(h)
        return h

    def index(self, oid, start=0, stop=None):  # TODO
        raise NotImplementedError

    def insert(self, index: int, value: gpd.GeoDataFrame):
        if not isinstance(index, int):
            raise TypeError("Index must be an integer")
        if not isinstance(value, gpd.GeoDataFrame):
            raise TypeError("Value must be an instance of gpd.GeoDataFrame")
        if not (value.columns == self._data.columns).all():
            raise ValueError("Schemas must match")

        match index:
            case 0:
                c = [value, self._data]
            case -1:
                c = [self._data, value]
            case _:
                c = [self._data.iloc[:index], value, self._data.iloc[index:]]
        self._data = pd.concat(c, ignore_index=True)
        self.saved = False

    def save(
        self,
    ):
        """Save to disk"""
        if not self.gdb_path:
            raise AttributeError("gdb_path not set")
        else:
            gdf_to_fc(
                self._data,
                self.gdb_path,
                self.name,
                self.feature_dataset,
                overwrite=True,
            )
            self.saved = True

    def sort(
        self,
        field_name: str,
        ascending: bool = True,
    ):
        self._data.sort_values(by=field_name, ascending=ascending, inplace=True)


class GeoDatabase(MutableMapping):
    """Dict of ouroboros.FeatureClass objects, loaded into memory"""

    def __init__(self, gdb_path: os.PathLike | str):
        if not os.path.exists(gdb_path):
            raise FileNotFoundError(gdb_path)

        self.path = os.path.abspath(gdb_path)
        self._data = dict()
        self.saved = False
        self.reload()

    def __delitem__(self, fc_name: str, /):
        if not isinstance(fc_name, str):
            raise TypeError("Feature class name must be a string")
        if fc_name in self._data:
            del self._data[fc_name]
            self.saved = False

    def __getitem__(self, fc_name: str, /) -> FeatureClass:
        if not isinstance(fc_name, str):
            raise TypeError("Feature class name must be a string")
        return self._data.get(fc_name)

    def __iter__(self) -> Iterator[FeatureClass]:
        return iter(self._data.values())

    def __len__(self) -> int:
        return len(self._data)

    def __setitem__(self, fc_name: str, fc: FeatureClass, /):
        if not isinstance(fc_name, str):
            raise TypeError("Feature class name must be a string")
        if not isinstance(fc, FeatureClass):
            raise TypeError("Input must be an ouroboros.FeatureClass object")

        if fc_name in self._data:
            raise KeyError(f"Feature class '{fc_name}' already exists")
        else:
            self._data[fc_name] = fc
            self._data[fc_name].name = fc_name
            self.saved = False

    def reload(self):
        """Load from disk, overwriting data in memory"""
        self._data = dict()
        gdb_fcs = list_fcs(self.path)
        for fc_name in gdb_fcs:
            self._data[fc_name] = FeatureClass(fc_name, self.path)
        self.saved = True

    def save(self):
        """
        Save in-memory object data to disk
        """
        # Delete fcs that are not in _data
        gdb_fcs = list_fcs(self.path)
        for fc_name in gdb_fcs:
            if fc_name not in self._data:
                delete_fc(self.path, fc_name)

        # Add or overwrite feature classes on disk from _data
        # TODO feature dataset support
        for fc_name, fc in self._data.items():
            # noinspection PyProtectedMember
            gdf_to_fc(fc._data, self.path, fc_name, overwrite=True)
        self.saved = True


def delete_fc(
    gdb_path: os.PathLike | str,
    fc_name: str,
) -> bool:
    if not os.path.exists(gdb_path):
        raise FileNotFoundError(gdb_path)

    if not isinstance(fc_name, str):
        raise TypeError("Feature class name must be a string")

    if fc_name in list_fcs(gdb_path):
        fiona.remove(gdb_path, "OpenFileGDB", fc_name)
        return True
    else:
        return False


def fc_to_gdf(
    gdb_path: os.PathLike | str,
    fc_name: str,
) -> gpd.GeoDataFrame:
    """Feature Class to GeoDataFrame"""
    if not os.path.exists(gdb_path):
        raise FileNotFoundError(gdb_path)

    if not isinstance(fc_name, str):
        raise TypeError("Feature class name must be a string")
    gdf: gpd.GeoDataFrame = gpd.read_file(gdb_path, layer=fc_name, driver="OpenFileGDB")
    gdf = gdf.rename_axis("ObjectID")  # use ObjectID as dataframe index
    return gdf


def gdf_to_fc(
    gdf: gpd.GeoDataFrame,
    gdb_path: os.PathLike | str,
    fc_name: str,
    feature_dataset: str = None,
    overwrite: bool = False,
    compatibility: bool = True,
    reindex: bool = False,
):
    """
    GeoDataFrame to Feature Class

    References:
    - https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.to_file.html
    - https://gdal.org/en/stable/drivers/vector/openfilegdb.html
    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        if isinstance(gdf, gpd.GeoSeries):
            gdf = gpd.GeoDataFrame(gdf)
        else:
            raise TypeError("Input must be a GeoDataFrame or GeoSeries")

    if not isinstance(fc_name, str):
        raise TypeError("Feature class name must be a string")

    if feature_dataset and not isinstance(feature_dataset, str):
        raise TypeError("Feature dataset name must be a string")

    for param in (overwrite, compatibility, reindex):
        if not isinstance(param, bool):
            raise TypeError(f"Parameter {param} must be a boolean")

    layer_options = {
        "TARGET_ARCGIS_VERSION": True if compatibility else False,
        "OPENFILEGDB_IN_MEMORY_SPI": True if reindex else False,
        "FEATURE_DATASET": feature_dataset,
    }

    if os.path.exists(gdb_path):
        if fc_name in list_fcs(gdb_path):
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

    gdf.to_file(
        gdb_path,
        driver="OpenFileGDB",
        layer=fc_name,
        layer_options=layer_options,
    )


def list_fcs(gdb_path: os.PathLike | str) -> list:
    """
    List feature classes in geodatabase
    """
    if not os.path.exists(gdb_path):
        raise FileNotFoundError(gdb_path)

    try:
        return gpd.list_layers(gdb_path)["name"].values.tolist()
    except DataSourceError:  # empty GeoDatabase
        return list()
