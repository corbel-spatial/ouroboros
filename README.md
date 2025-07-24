[![PyPI - Version](https://img.shields.io/pypi/v/ouroboros-arcpy?logo=pypi)](https://pypi.org/project/ouroboros-arcpy/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/ouroboros-arcpy)](https://pypistats.org/packages/ouroboros-arcpy)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg?logo=)](https://github.com/corbel-spatial/ouroboros?tab=MIT-1-ov-file)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ouroboros-arcpy?logo=python)

[![Dynamic JSON Badge](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcorbel-spatial%2Fouroboros%2Frefs%2Fheads%2Fmain%2Fdocs%2Fpytest_coverage.json&query=%24.totals.percent_covered_display&suffix=%25&label=coverage)](https://raw.githubusercontent.com/corbel-spatial/ouroboros/refs/heads/main/docs/pytest_coverage.json)
[![GitHub Actions Workflow Status: Black](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/black.yml?label=Black&logo=black)](https://github.com/corbel-spatial/ouroboros/actions/workflows/black.yml)
[![GitHub Actions Workflow Status: Pylint](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pylint.yml?label=Pylint)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pylint.yml)
[![Read the Docs](https://img.shields.io/readthedocs/ouroboros-arcpy?logo=readthedocs)](https://ouroboros-arcpy.readthedocs.io/)

[![GitHub Actions Workflow Status: Linux](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pytest-linux.yml?label=Linux&logo=linux)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pytest-linux.yml)
[![GitHub Actions Workflow Status: macOS](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pytest-macos.yml?label=macOS&logo=apple)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pytest-macos.yml)
[![GitHub Actions Workflow Status: Windows](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pytest-windows.yml?label=Windows)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pytest-windows.yml)

# ouroboros

A module that provides classes to manipulate File GeoDatabase feature classes in a more pythonic way. 

Uses GDAL wrappers under the hood (GeoPandas, Fiona, Pyogrio) and does not depend on arcpy. Thus it builds on a completely open stack and is cross-platform.

Tested on Python 3.10 - 3.13 on Windows, Linux, and macOS (version info [here](https://github.com/actions/runner-images)).

## Installation

For a standard Python package installation in a terminal via pip:

    python -m pip install ouroboros-gis --user

To install in an ArcGIS Pro conda environment, run the above command in the [Python Command Prompt](https://developers.arcgis.com/python/latest/guide/install-and-set-up/arcgis-pro/#installation-using-python-command-prompt), which can be launched from the Start Menu > All Programs > ArcGIS > Python Command Prompt.

## Resources

 - [Documentation](https://ouroboros-gis.readthedocs.io/latest/)
 - [GitHub Repository](https://github.com/corbel-spatial/ouroboros)
 - [Python Package Index](https://pypi.org/project/ouroboros-gis/)