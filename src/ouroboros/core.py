import os
from collections.abc import MutableMapping, MutableSequence

import fiona
import geopandas as gpd
import pandas as pd


class FeatureClass(MutableSequence):
    """Wraps a GeoDataFrame, and allows access like an arcpy.da cursor in memory. Must use 'save' method to write to disk."""

    def __init__(self, gdb_path: os.PathLike | str, fc_name: str):
        self.gdb_path = gdb_path
        self.name = fc_name
        self._data: gpd.GeoDataFrame = gpd.read_file(gdb_path, layer=fc_name)
        self.saved = True

    def __delitem__(self, index):
        self.saved = False
        raise NotImplementedError

    def __getitem__(self, index: int | slice | list | tuple) -> pd.Series:
        return self._data.iloc[index]

    def __setitem__(self, index, value):
        self.saved = False
        raise NotImplementedError

    def __len__(self):
        if len(self._data.shape) != 2:
            raise ValueError("GeoDataFrame must be two-dimensional")
        return self._data.shape[1]

    def insert(self, index, value):
        self.saved = False
        raise NotImplementedError

    def save(
        self,
    ):
        """Save to disk"""
        self._data.to_file(
            self.gdb_path,
            layer=self.name,
            driver="OpenFileGDB",
        )
        self.saved = True

    def copy(self, fc_name: str, gdb_path: None | os.PathLike | str = None):
        self._data.to_file(
            gdb_path if gdb_path else self.gdb_path,
            layer=fc_name,
            driver="OpenFileGDB",
        )
        self.saved = True


class GeoDatabase(MutableMapping):
    """Dict of ouroboros.FeatureClass objects"""

    def __init__(self, gdb_path: os.PathLike | str):
        assert os.path.exists(gdb_path)
        self.path = os.path.abspath(gdb_path)
        self.names = set()
        self._data = dict()
        self.reload()

    def __delitem__(self, fc_name: str, /):
        if not isinstance(fc_name, str):
            raise TypeError("Feature class name must be a string")
        self.reload()
        if fc_name in self.names:
            fiona.remove(self.path, "OpenFileGDB", fc_name)
            self.reload()

    def __getitem__(self, fc_name: str, /):
        if not isinstance(fc_name, str):
            raise TypeError("Feature class name must be a string")
        self.reload()
        return self._data[fc_name]

    def __iter__(self):
        self.reload()
        return iter(self._data)

    def __len__(self):
        self.reload()
        return len(self._data)

    def __setitem__(self, fc_name: str, fc: FeatureClass, /):
        assert isinstance(fc, FeatureClass)
        self.reload()
        if fc_name in self.names:
            raise KeyError(f"Feature class '{fc_name}' already exists")
        else:
            self._data[fc_name] = fc
            self._data[fc_name].save()
            self.reload()

    def reload(self):
        try:
            self._data = dict()
            self.names = set(fiona.listlayers(self.path))
            for name in self.names:
                self._data[name] = FeatureClass(self.path, name)
        except fiona.errors.DriverError:  # empty gdb
            self.names = set()
