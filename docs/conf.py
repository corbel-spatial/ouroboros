import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join("..", "src")))

# -- Project information -----------------------------------------------------

project = "ouroboros"
copyright = "2025"
author = "Corbel"


# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "myst_parser",
    "nbsphinx",
]

intersphinx_mapping = {
    "rtd": ("https://docs.readthedocs.io/en/stable/", None),
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
    "geopandas": ("https://geopandas.org/en/stable/", None),
    # "geojson": ("https://geojson.readthedocs.io/en/latest/", None),
    "pyarrow": ("https://pyarrow.readthedocs.io/en/latest/", None),
    "pyproj": ("https://pyproj4.github.io/pyproj/stable/", None),
    "rasterio": ("https://rasterio.readthedocs.io/en/stable/", None),
}
intersphinx_disabled_domains = ["std"]

templates_path = ["_templates"]

html_title = "ouroboros"

html_theme_options = {
    # "style_external_links": True,
    "show_nav_level": 2,
    "navigation_depth": 2,
    "show_toc_level": 2,
    # "external_links": [
    #     {"name": "GitHub", "url": "https://github.com/corbel-spatial/ouroboros"},
    #     {"name": "PyPI", "url": "https://pypi.org/project/ouroboros-gis/"},
    # ],
}

html_sidebars = {
    "**": [
        # "globaltoc.html",
    ]
}

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

html_theme = "pydata_sphinx_theme"
# html_theme = "sphinx_rtd_theme"

html_static_path = ["_static"]
