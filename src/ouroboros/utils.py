from os import PathLike
from uuid import uuid4

from arcpy import Exists, ExportFeatures_conversion


def get_memory_path() -> [str, PathLike]:
    """Get in-memory path for feature class storage.

    This function generates a unique file path in the "memory" directory,
    prefixing it with "fc" and a randomly generated UUID. This ensures that each
    file has a unique name, preventing potential conflicts if devices share the same
    storage location.

    :return: A string representing the path to the new memory location.
    :rtype: str
    """
    return "memory\\fc_" + str(uuid4()).replace("-", "_")


def copy_to_memory(in_path: [str, PathLike]) -> [str, PathLike]:
    """
    Copies data from an input path to memory using ArcGIS's ExportFeatures_conversion method.

    :param in_path: The file path or object containing the input feature class
        that will be copied to memory.
    :type in_path: [str, PathLike]
    :return: The file path or object containing the output features that were
        copied to memory.
    :rtype: [str, PathLike]
    """
    assert Exists(in_path)
    out_path = get_memory_path()

    ExportFeatures_conversion(in_path, out_path)
    return out_path
