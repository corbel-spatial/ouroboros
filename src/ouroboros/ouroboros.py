import os
import pathlib
import re
import warnings
from collections.abc import MutableMapping, MutableSequence
from os import PathLike
from typing import Iterator

import fiona
import geojson
import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyogrio


class FeatureClass(MutableSequence):
    """
    Loads a GDB Feature Class into a GeoDataFrame, and allows access like an arcpy.da cursor in memory.
    Must use 'save' method to write changes to disk.
    """

    def __init__(
        self,
        fc_name: str,
        src: None | os.PathLike | str | gpd.GeoDataFrame = None,
        feature_dataset: None | str = None,
    ):
        # parse fc_name
        if not isinstance(fc_name, str):
            raise TypeError("fc_name must be a string")
        if fc_name[0].isdigit():
            fc_name = (
                "_" + fc_name
            )  # fc name cannot start with a digit, mimicking ArcGIS Pro renaming behavior
        self.name = fc_name

        # parse src and load data from file
        self.gdb_path = None
        self.saved = False
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
                if len(self._data.shape) != 2:
                    raise ValueError("GeoDataFrame must be two-dimensional")
                self.fields = self._data.columns.to_list()
                self.saved = True
        else:
            self._data = gpd.GeoDataFrame()

        # parse path
        self.feature_dataset = feature_dataset
        if self.gdb_path:
            if self.feature_dataset:
                self.path = os.path.join(self.gdb_path, self.feature_dataset, self.name)
            # check if fc is in a feature dataset
            elif self.name not in list_datasets(self.gdb_path)[None]:
                for fds, fcs in list_datasets(self.gdb_path).items():
                    if self.name in fcs:
                        self.feature_dataset = fds
                        self.path = os.path.join(
                            self.gdb_path, self.feature_dataset, self.name
                        )
            else:
                self.path = os.path.join(self.gdb_path, self.name)
        else:
            self.path = self.name

        # parse geometry
        if "geometry" in self._data.columns:
            self._data.set_geometry("geometry", inplace=True)
            geoms = self._data.geom_type.unique()
            if len(geoms) > 1:
                raise TypeError(
                    f"Feature classes cannot have multiple geometries: {geoms}"
                )
            elif len(geoms) == 0:
                for fc, geom in pyogrio.list_layers(self.gdb_path):
                    if fc == self.name:
                        self.geom_type = geom
            else:
                self.geom_type = geoms[0]

    def __delitem__(self, index) -> None:
        """Delete row at index"""
        if not isinstance(index, int):
            raise TypeError("index must be an integer")
        self._data = pd.concat(
            [self._data.iloc[: index - 1], self._data.iloc[index:]]
        ).reset_index(drop=True)
        self.saved = False

    def __getitem__(self, index: int) -> gpd.GeoDataFrame:
        """Return row at index"""
        if not isinstance(index, int):
            raise TypeError("index must be an integer")
        return self._data.iloc[[index]]

    def __iter__(self) -> Iterator[tuple]:
        """Return iterator over rows (as tuples)"""
        return self._data.itertuples()

    def __len__(self) -> int:
        """Return count of rows"""
        return self._data.shape[0]

    def __repr__(self) -> str:
        """Representation of the object as a string that can be recreated with eval()"""
        return (
            f"ob.FeatureClass('{self.name}', gpd.GeoDataFrame({self._data.to_json()}))"
        )

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

        self.saved = False

    def __str__(self) -> str:
        """Return full path of feature class on disk"""
        return self.path

    def append(self, value: gpd.GeoDataFrame) -> None:
        """Append row(s) to the end of the GeoDataFrame. Schema must match."""
        self.insert(-1, value)

    def clear(self) -> None:
        """Delete all rows, leaving schema unchanged."""
        self._data = self._data[0:0]

    def describe(self) -> dict:
        """Return dict of useful information."""
        if self.saved:
            ogr_info = pyogrio.read_info(self.gdb_path, self.name)
        else:
            ogr_info = None
        return {
            "saved": self.saved,
            "name": self.name,
            "feature_dataset": self.feature_dataset,
            "gdb_path": str(self.gdb_path),
            "path": str(self.path),
            "geom_type": self.geom_type,
            "ogr_info": ogr_info,
        }

    def head(self, n: int = 10, silent: bool = False) -> gpd.GeoDataFrame:
        """Return a selection of rows. 'silent' prevents printing."""
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
        if not (value.columns == self._data.columns).all():
            raise ValueError("Schemas must match")

        # enforce geometry type
        simple_type = self.geom_type.strip("Multi")
        geoms = value.geom_type.unique()
        if (
            0 < len(geoms) > 1
            and geoms[0] is not None
            and geoms[0].strip("Multi") != simple_type
        ):
            raise TypeError(f"Geometry must be {simple_type} or Multi{simple_type}")

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
    ) -> None:
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
    ) -> None:
        """Sort by field name"""
        self._data.sort_values(by=field_name, ascending=ascending, inplace=True)

    def to_geodataframe(self) -> gpd.GeoDataFrame:
        """Return data as GeoDataFrame"""
        return self._data.copy(deep=True)

    def to_geojson(
        self, filename: PathLike | str = None
    ) -> None | geojson.FeatureCollection:
        """Save to GeoJSON file if filename is given, otherwise return GeoJSON FeatureCollection object"""
        if filename:
            if not filename.endswith(".geojson"):
                filename += ".geojson"
            self._data.to_file(filename, driver="GeoJSON", to_wgs84=True)
            return None
        else:
            gjs = self._data.to_json(to_wgs84=True)
            return geojson.loads(gjs)

    def to_pyarrow(self) -> pa.Table:
        """To PyArrow Table"""
        arrow_table = self._data.to_arrow()
        return pa.table(arrow_table)

    def to_shapefile(self, filename: PathLike | str) -> None:
        if not filename.endswith(".shp"):
            filename += ".shp"
        self._data.to_file(filename=filename, driver="ESRI Shapefile")


class GeoDatabase(MutableMapping):
    """Dict of ouroboros.FeatureClass objects, loaded into memory"""

    def __init__(self, gdb_path: os.PathLike | str):
        if not os.path.exists(gdb_path):
            raise FileNotFoundError(gdb_path)

        self.path = os.path.abspath(gdb_path)
        self._data = dict()
        self.feature_classes = list()
        self.feature_datasets = list()
        self.saved = False
        self.reload()

    def __delitem__(self, fc_name: str, /) -> None:
        """Delete feature class from object in memory. Must use 'save' method to actually delete from disk."""
        if not isinstance(fc_name, str):
            raise TypeError("Feature class name must be a string")
        if fc_name in self._data:
            del self._data[fc_name]
            self.saved = False

    def __getitem__(self, index: int | str, /) -> FeatureClass:
        """Return feature class object by name or by index."""
        if isinstance(index, str):
            return self._data.get(index)
        elif isinstance(index, int):
            fc_name = self.feature_classes[index]
            return self._data.get(fc_name)
        else:
            raise TypeError(index)

    def __iter__(self) -> Iterator[FeatureClass]:
        """Return iterator over feature class objects."""
        return iter(self._data.values())

    def __len__(self) -> int:
        """Return count of feature classes in the GeoDatabase object."""
        return len(self._data)

    def __setitem__(self, fc_name: str, fc: FeatureClass, /) -> None:
        """Set feature class object by name. Cannot overwrite existing features."""
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

    def reload(self) -> None:  # TODO test zipped gdbs as inputs
        """Load from disk, overwriting data in memory"""
        self.feature_classes = sorted(list_layers(self.path))
        self._data = dict()
        for fc_name in self.feature_classes:
            self._data[fc_name] = FeatureClass(fc_name, self.path)

        fds = list(list_datasets(self.path).keys())
        if None in fds:
            fds.remove(None)
        self.feature_datasets = sorted(fds)

        self.saved = True

    def save(self) -> None:
        """
        Save in-memory object data to disk, and delete any feature classes on disk that have been removed from the object.
        """
        # Delete fcs that are not in _data
        gdb_fcs = list_layers(self.path)
        for fc_name in gdb_fcs:
            if fc_name not in self._data:
                delete_fc(self.path, fc_name)

        # Add or overwrite feature classes on disk from _data
        for fc in self._data.values():
            # noinspection PyProtectedMember
            gdf_to_fc(fc._data, self.path, fc.name, fc.feature_dataset, overwrite=True)
        self.saved = True


def delete_fc(
    gdb_path: os.PathLike | str,
    fc_name: str,
) -> bool:
    """Delete feature class from disk, returns False if feature class doesn't exist"""
    if not os.path.exists(gdb_path):
        raise FileNotFoundError(gdb_path)

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
    if not os.path.exists(gdb_path):
        raise FileNotFoundError(gdb_path)

    if not isinstance(fc_name, str):
        raise TypeError("Feature class name must be a string")

    with warnings.catch_warnings():  # hide pyogrio driver warnings
        warnings.simplefilter("ignore")
        gdf: gpd.GeoDataFrame = gpd.read_file(gdb_path, layer=fc_name)
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

    gdf.to_file(
        gdb_path,
        driver="OpenFileGDB",
        layer=fc_name,
        layer_options=layer_options,
    )


def list_datasets(gdb_path: os.PathLike | str) -> dict[str | None, list[str]]:
    """
    Lists feature datasets and their child feature classes

    Returns a dict of {feature_dataset: [feature_class, ...]}

    Feature classes outside of a feature dataset will have a key of None
    """
    gdbtable = os.path.join(gdb_path, "a00000004.gdbtable")
    if not os.path.exists(gdbtable) or "a00000004.gdbtable" not in os.listdir(gdb_path):
        raise FileNotFoundError(gdbtable)

    fcs = list_layers(gdb_path)
    if len(fcs) == 0:  # no feature classes returns empty dict
        return dict()

    # get \feature_dataset\feature_class paths
    with open(gdbtable, "r", encoding="ansi") as f:
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
    if not os.path.exists(gdb_path):
        raise FileNotFoundError(gdb_path)

    try:
        return [fc[0] for fc in pyogrio.list_layers(gdb_path)]
    except pyogrio.errors.DataSourceError:  # noqa # empty GeoDatabase
        return list()
