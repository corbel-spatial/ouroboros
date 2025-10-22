import os
import re
import warnings
from typing import Literal

import geojson
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import xmltodict
from pyogrio.errors import DataSourceError

# Check for optional install of GDAL>=3.8 for raster support
try:
    from osgeo import gdal  # noqa # fmt: skip

    gdal_version = gdal.__version__
    if int(gdal_version.split(".")[0]) < 3 or int(gdal_version.split(".")[1]) < 8:
        raise ImportError(
            "GDAL version must be >=3.8, please upgrade to a newer version"
        )
except ModuleNotFoundError:
    gdal_version = None


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


def fc_to_json(
    gdb_path: os.PathLike | str,
    fc_name: str,
    fp: None | os.PathLike | str = None,
    indent: None | int = None,
    **kwargs: dict,
) -> None | geojson.FeatureCollection:
    """Wraps geopandas.GeoDataFrame.to_json()"""
    gdf = fc_to_gdf(gdb_path=gdb_path, fc_name=fc_name)
    gjs = geojson.loads(gdf.to_json(**kwargs))

    if fp:
        fp = str(fp)
        if not fp.endswith(".geojson") or not fp.endswith(".json"):
            fp += ".geojson"
        with open(fp, "w") as f:
            geojson.dump(gjs, f, indent=indent)
        return None
    else:
        return gjs


def fc_to_parquet(
    gdb_path: os.PathLike | str, fc_name: str, fp: os.PathLike | str, **kwargs: dict
):
    """Wraps geopandas.GeoDataFrame.to_parquet()"""
    gdf = fc_to_gdf(gdb_path=gdb_path, fc_name=fc_name)

    if not fp.endswith(".parquet"):
        fp += ".parquet"

    gdf.to_parquet(fp, **kwargs)


def fc_to_shp(
    gdb_path: os.PathLike | str,
    fc_name: str,
    fp: None | os.PathLike | str,
    **kwargs: dict,
) -> None:
    """Wraps geopandas.GeoDataFrame.to_file(filename, driver="ESRI Shapefile")"""
    gdf = fc_to_gdf(gdb_path=gdb_path, fc_name=fc_name)

    if not fp.endswith(".shp"):
        fp += ".shp"

    if "driver" in kwargs:
        del kwargs["driver"]

    gdf.to_file(fp, **kwargs)


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
    if not gdal_version:
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
