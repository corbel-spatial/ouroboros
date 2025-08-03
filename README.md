[![PyPI - Version](https://img.shields.io/pypi/v/ouroboros-gis?logo=pypi)](https://pypi.org/project/ouroboros-gis/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/ouroboros-gis)](https://pypistats.org/packages/ouroboros-gis)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg?logo=)](https://github.com/corbel-spatial/ouroboros/blob/main/LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ouroboros-gis?logo=python)](https://pypi.org/project/ouroboros-gis/)

[![Dynamic JSON Badge](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcorbel-spatial%2Fouroboros%2Frefs%2Fheads%2Fmain%2Fdocs%2Fpytest_coverage.json&query=%24.totals.percent_covered_display&suffix=%25&label=coverage)](https://raw.githubusercontent.com/corbel-spatial/ouroboros/refs/heads/main/docs/pytest_coverage.json)
[![GitHub Actions Workflow Status: Black](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/black.yml?label=Black&logo=black)](https://github.com/corbel-spatial/ouroboros/actions/workflows/black.yml)
[![GitHub Actions Workflow Status: Pylint](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pylint.yml?label=Pylint)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pylint.yml)
[![Read the Docs](https://img.shields.io/readthedocs/ouroboros-gis?logo=readthedocs)](https://ouroboros-gis.readthedocs.io/)

[![GitHub Actions Workflow Status: Linux](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pytest-linux.yml?label=Linux&logo=linux)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pytest-linux.yml)
[![GitHub Actions Workflow Status: macOS](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pytest-macos.yml?label=macOS&logo=apple)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pytest-macos.yml)
[![GitHub Actions Workflow Status: Windows](https://img.shields.io/github/actions/workflow/status/corbel-spatial/ouroboros/pytest-windows.yml?label=Windows)](https://github.com/corbel-spatial/ouroboros/actions/workflows/pytest-windows.yml)

# ouroboros

## Introduction

ouroboros is a Python module that provides helpful functions and classes for manipulating spatial data stored in a [File GeoDatabase](https://en.wikipedia.org/wiki/Geodatabase_(Esri)). 

The data (.gdb) are read from disk into memory as `FeatureClass` objects, using [GeoPandas](https://geopandas.org/en/stable/getting_started/introduction.html) 
under the hood for efficient analysis and easy conversion to other spatial data formats.
`FeatureClass` objects can exist on their own, or they can be grouped into `FeatureDataset` and `GeoDatabase` objects 
which can be accessed like dictionaries. For example:

```python
>>> import ouroboros as ob

# Explore an existing dataset

>>> gdb_file = "spam_and_eggs.gdb"
>>> ob.list_datasets(gdb_file)
{'egg_dataset': ['eggs_fc', 'bad_eggs_fc'],
{'spam_dataset': ['spam_fc'],
 None: ['ham_fc']}

# Load a feature class and convert to GeoPandas

>>> fc = ob.FeatureClass("spam_and_eggs.gdb/egg_dataset/eggs_fc")
>>> gdf = fc.to_geodataframe()
>>> type(gdf)
<class 'geopandas.geodataframe.GeoDataFrame'>

# Assemble a new geodatabase in memory

>>> gdb = ob.GeoDatabase()
>>> gdb['good_egg_dataset'] = ob.FeatureDataset()
>>> gdb['good_egg_dataset']['eggs_fc'] = ob.FeatureClass("spam_and_eggs.gdb/eggs_fc")

# Save geodatabase to disk

>>> gdb.save("good_eggs.gdb")
>>> ob.list_datasets("good_eggs.gdb")
{'good_egg_dataset': ['eggs_fc'], None: []}
```

## Getting Started

[Installation](https://ouroboros-gis.readthedocs.io/en/latest/installation.html)

[User Guide](https://ouroboros-gis.readthedocs.io/en/latest/user_guide.html)

## About

ouroboros is released under a permissive open source license, it builds on mature open source GIS projects like 
[GDAL](https://gdal.org/), and importantly it **does not use Esri's arcpy.**
Therefore, ouroboros does not require any paid licenses and it runs on macOS and Linux as well as Windows.

The main goal of this project is to allow traditional GIS users working primarily in the Esri/ArcGIS ecosystem to take
advantage of the features and speed offered by modern data science tools. Second, it will provide a no-cost and
user-friendly way to convert geodatabases to open data formats. And along the way, this project aims to develop a 
suite of tools that align with [pythonic](https://peps.python.org/pep-0020/) design principles, and also bring a
little more joy and beauty to the task of wrangling spatial data.

This project is under active development and beta releases will be provided for the time being. Feedback, suggestions, and questions are welcomed in the [Issues](https://github.com/corbel-spatial/ouroboros/issues) section.

## Notes

Tested on Python 3.10, 3.11, 3.12, and 3.13 on the latest Windows, Linux, and macOS (version info [here](https://github.com/actions/runner-images)).
