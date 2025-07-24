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
    Loads a GDB Feature Class into a GeoDataFrame, and allows access like an arcpy.da cursor in memory.
    Must use 'save' method to write changes to disk.
    """

    def __init__(
        self,
        src: "None | os.PathLike | str | gpd.GeoDataFrame" = None,
    ):
        """
        src: None, path to .gdb, or a GeoDataFrame
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
        """Delete row at index"""
        if not isinstance(index, int):
            raise TypeError("index must be an integer")
        self._data = pd.concat(
            [self._data.iloc[: index - 1], self._data.iloc[index:]]
        ).reset_index(drop=True)

    def __getitem__(
        self, index: "int | slice | Sequence[int | slice]"
    ) -> gpd.GeoDataFrame:
        """Return row at index"""
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
        """Return iterator over rows (as tuples)"""
        return self._data.itertuples()

    def __len__(self) -> int:
        """Return count of rows"""
        return self._data.shape[0]

    def __setitem__(
        self,
        index: tuple[int, int | str],
        value: any,
    ) -> None:
        """
        Set the value of a single cell at row, column

        index is a tuple (row, column) where column can be int or str
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
        """Append row(s) to the end of the GeoDataFrame. Schema must match."""
        self.insert(-1, value)

    def clear(self) -> None:
        """Delete all rows, leaving schema unchanged."""
        self._data = self._data[0:0]

    def copy(self) -> "FeatureClass":
        """Return a copy of the Feature Class"""
        return FeatureClass(self._data.copy(deep=True))

    def describe(self) -> dict:
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
        """Print and return a selection of rows. 'silent' prevents printing."""
        h = self._data.head(n)
        if not silent:
            print(h)
        return h

    def insert(self, index: int, value: gpd.GeoDataFrame) -> None:
        """
        Insert row(s) at an index, extending the dataframe. Schema must match.
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
        """Sort by field name"""
        self._data.sort_values(by=field_name, ascending=ascending, inplace=True)

    def to_geodataframe(self) -> gpd.GeoDataFrame:
        """Return data as GeoDataFrame"""
        return self._data.copy(deep=True)

    def to_geojson(
        self, filename: os.PathLike | str = None
    ) -> "None | geojson.FeatureCollection":
        """Save to GeoJSON file if filename is given, otherwise return GeoJSON FeatureCollection object"""
        if filename:
            if not filename.endswith(".geojson"):
                filename += ".geojson"
            self._data.to_file(filename, driver="GeoJSON")
            return None
        else:
            gjs = self._data.to_json(to_wgs84=True)
            return geojson.loads(gjs)

    def to_pyarrow(self) -> pa.Table:
        """To PyArrow Table"""
        arrow_table = self._data.to_arrow()
        return pa.table(arrow_table)

    def to_shapefile(self, filename: os.PathLike | str) -> None:
        if not filename.endswith(".shp"):
            filename += ".shp"
        self._data.to_file(filename=filename, driver="ESRI Shapefile")


class FeatureDataset(MutableMapping):
    def __init__(self, crs: Any | CRS = None):
        self._fcs = dict()
        self._gdbs = set()

        if isinstance(crs, CRS) or crs is None:
            self.crs = crs
        else:
            self.crs = CRS(crs)

    def __delitem__(self, key, /):
        del self._fcs[key]

    def __getitem__(self, key: int | str, /) -> FeatureClass:
        if isinstance(key, int):
            for idx, fc_obj in enumerate(self.feature_classes()):
                fc_name, fc = fc_obj
                if idx == key:
                    return fc
            raise IndexError(f"Index out of range: {key}")
        else:
            return self._fcs[key]

    def __iter__(self):
        return iter(self._fcs)

    def __len__(self):
        return len(self._fcs)

    def __setitem__(self, key: str, value: FeatureClass, /):
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
        fc_list = list()
        for fc_name, fc in self._fcs.items():
            fc_list.append((fc_name, fc))
        return tuple(fc_list)


class GeoDatabase(MutableMapping):

    def __init__(self, path: None | os.PathLike | str = None):
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
        fds = self._fds[key]
        del self._fds[key]
        fds._gdbs.remove(self)

    def __getitem__(self, key: int | str, /) -> FeatureClass | FeatureDataset:
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
        return hash(self._uuid)

    def __iter__(self):
        """Return iterator of fds_name, fds_object"""
        return iter(self._fds)

    def __len__(self):
        """Return count of feature classes"""
        count = 0
        for fds in self._fds.values():
            count += len(fds)
        return count

    # noinspection PyProtectedMember
    def __setitem__(self, key: str, value: FeatureClass | FeatureDataset, /):
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
        fc_list = list()
        for fds in self._fds.values():
            for fc_name, fc in fds.items():
                fc_list.append((fc_name, fc))
        return tuple(fc_list)

    def feature_datasets(self) -> tuple[[str | None, FeatureDataset], ...]:
        fds_list = list()
        for fds_name in self._fds:
            fds_list.append((fds_name, self._fds[fds_name]))
        return tuple(fds_list)

    def save(self, path: os.PathLike | str, overwrite: bool = False):
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
    """Delete feature class from disk, returns False if feature class doesn't exist"""
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
    """Load Feature Class to GeoDataFrame"""
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
    Save GeoDataFrame to Feature Class on disk

    References:
    - https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.to_file.html
    - https://gdal.org/en/stable/drivers/vector/openfilegdb.html
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
    Lists names of feature datasets and their child feature classes

    Returns a dict of {feature_dataset: [feature_class, ...]}

    Feature classes outside of a feature dataset will have a key of None

    References:
    - https://github.com/rouault/dump_gdbtable/wiki/FGDB-Spec
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
    List feature classes in geodatabase
    """
    # noinspection PyUnresolvedReferences
    try:
        return [fc[0] for fc in pyogrio.list_layers(gdb_path)]
    except pyogrio.errors.DataSourceError:  # empty GeoDatabase
        return list()
