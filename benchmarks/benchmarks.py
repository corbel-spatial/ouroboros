import os
from tempfile import mkdtemp
from time import sleep
from timeit import timeit
from uuid import uuid4
from zipfile import ZipFile

import arcpy
import geopandas as gpd
import ouroboros as ob
import pooch
import tqdm

tqdm_version = tqdm.version.__version__
tqdm = tqdm.tqdm


def arcpy_mem_path():
    return os.path.join("memory", "f" + str(uuid4()).strip("{}").replace("-", ""))


def load_shp_ob(input):
    ob.FeatureClass(gpd.read_file(input))


def load_shp_arcpy(input):
    arcpy.CopyFeatures_management(input, arcpy_mem_path())


def benchmark(name, task1, task2, input):
    print(name, end="\r")
    result_ob = round(timeit(lambda: task1(input), number=10), 3)
    print(f"\r{name}\t{result_ob}", end="")
    result_arcpy = round(timeit(lambda: task2(input), number=10), 3)

    if result_ob < result_arcpy:
        winner = "ob"
        factor = result_arcpy / result_ob
    elif result_ob > result_arcpy:
        winner = "arcpy"
        factor = result_ob / result_arcpy
    else:
        winner = "tie"
        factor = 0

    print(
        f"\r{name}\t{result_ob}\t{result_arcpy}\t{winner}\t{round(factor, 2)}x", end=""
    )


if __name__ == "__main__":
    gpd.show_versions()
    print(f"\nBENCHMARK DEPENDENCIES")
    print(f"----------------------")
    print(f"arcpy      : {arcpy.__version__}")  # noqa
    print(f"ouroboros  : {ob.version}")
    print(f"pooch      : {pooch.__version__.strip('v')}")
    print(f"tqdm       : {tqdm_version}")

    print("\nGetting datasets....")

    ds = pooch.retrieve(
        url="https://download.qgis.org/downloads/data/training_manual_exercise_data.zip",
        known_hash="md5:4513157e5f1d5eaec9dda4897a1ad3d2",
    )
    shp_stem = "exercise_data/more_analysis/Zoning/Generalised_Zoning_Dissolve_UTM33S"

    tempdir = mkdtemp()

    with ZipFile(ds, "r") as zz:
        for file in zz.namelist():
            if shp_stem in file:
                zz.extract(file, tempdir)

    shp = os.path.abspath(
        os.path.join(
            tempdir,
            shp_stem + ".shp",
        )
    )
    print("Loaded!")

    print("\n\nbenchmark\tob\tarcpy\twinner\tfactor")
    print("=" * 46, end="\n")

    benchmark("load shp", load_shp_ob, load_shp_arcpy, shp)

    print("\n")
