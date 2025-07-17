[![PyPI - Version](https://img.shields.io/pypi/v/ouroboros-arcpy)](https://pypi.org/project/ouroboros-arcpy/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ouroboros-arcpy)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](https://github.com/corbel-spatial/ouroboros?tab=MIT-1-ov-file)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/ouroboros-arcpy)](https://pypistats.org/packages/ouroboros-arcpy)
![PyPI - Format](https://img.shields.io/pypi/format/ouroboros-arcpy)

[![GitHub Actions Workflow Status: Pytest](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pytest.yml?label=pytest)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pytest.yml)
[![GitHub Actions Workflow Status: Black](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pytest.yml?label=black)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pytest.yml)
[![Read the Docs Status](https://img.shields.io/readthedocs/ouroboros-arcpy)](https://ouroboros-arcpy.readthedocs.io/)

# ouroboros

A module that provides classes to manipulate File GeoDatabase feature classes in a more pythonic way. 

Uses GDAL wrappers under the hood (GeoPandas, Fiona, Pyogrio) and does not depend on arcpy. Thus it builds on a completely open stack and is cross-platform.

Tested on Python 3.10 - 3.13 on Windows, Linux, and macOS. (Version info [here](https://github.com/actions/runner-images).)

NOTE: Under active development, see the [beta release](https://github.com/corbel-spatial/ouroboros/releases/tag/v1.0.0b2) for a proof of concept that relies on arcpy.
