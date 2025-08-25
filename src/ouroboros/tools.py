from typing import Literal

import geopandas as gpd

from .ouroboros import FeatureClass


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
    gdf = fc.to_geodataframe()
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
