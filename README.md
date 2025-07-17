[![PyPI - Version](https://img.shields.io/pypi/v/ouroboros-arcpy?logo=pypi)](https://pypi.org/project/ouroboros-arcpy/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/ouroboros-arcpy)](https://pypistats.org/packages/ouroboros-arcpy)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg?logo=)](https://github.com/corbel-spatial/ouroboros?tab=MIT-1-ov-file)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ouroboros-arcpy?logo=python)

[![GitHub Actions Workflow Status: Black](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/black.yml?label=Black&logo=black)](https://github.com/corbel-spatial/ouroboros/actions/workflows/black.yml)
[![GitHub Actions Workflow Status: Pylint](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pylint.yml?label=Pylint)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pylint.yml)
[![GitHub Actions Workflow Status: Linux](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pytest-linux.yml?label=Linux&logo=linux)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pytest-linux.yml)
[![GitHub Actions Workflow Status: macOS](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pytest-macos.yml?label=macOS&logo=apple)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pytest-macos.yml)
[![GitHub Actions Workflow Status: Windows](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pytest-windows.yml?label=Windows)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pytest-windows.yml)
[![Read the Docs](https://img.shields.io/readthedocs/ouroboros-arcpy?logo=readthedocs)](https://ouroboros-arcpy.readthedocs.io/)

# ouroboros

A module that provides classes to manipulate File GeoDatabase feature classes in a more pythonic way. 

Uses GDAL wrappers under the hood (GeoPandas, Fiona, Pyogrio) and does not depend on arcpy. Thus it builds on a completely open stack and is cross-platform.

Tested on Python 3.10 - 3.13 on Windows, Linux, and macOS. (Version info [here](https://github.com/actions/runner-images).)

NOTE: Under active development with a new beta release soon. See the previous [beta release](https://github.com/corbel-spatial/ouroboros/releases/tag/v1.0.0b2) for a proof of concept that relies on arcpy.
