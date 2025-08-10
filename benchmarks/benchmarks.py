print("Importing dependencies....")

import os
from tempfile import mkdtemp
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


TIMEIT_ITERATIONS = 10


def arcpy_mem_path():
    return os.path.join("memory", "f" + str(uuid4()).strip("{}").replace("-", ""))


def load_shp_ob(input: str):
    return ob.FeatureClass(gpd.read_file(input))


def load_shp_arcpy(input: str):
    return arcpy.CopyFeatures_management(input, arcpy_mem_path())


# noinspection PyProtectedMember
def buffer_ob(input: ob.FeatureClass):
    # return input._data.buffer(10)
    pass


def buffer_arcpy(input: str):
    return arcpy.analysis.Buffer(input, arcpy_mem_path(), "10 Meters")


# noinspection PyProtectedMember
def get_ith_row_ob(input: ob.FeatureClass):
    gdf = input._data
    idx = int(len(gdf) / 2)
    return gdf.iloc[idx]


def get_ith_row_arcpy(input: str):
    idx = int(int(arcpy.management.GetCount(input).getOutput(0)) / 2)
    with arcpy.da.SearchCursor(input, "*") as s_cursor:
        for i, row in enumerate(s_cursor):
            if i == idx:
                return row
    return None


def benchmark(name, task1, input1, task2, input2):
    result_ob = timeit(lambda: task1(input1), number=TIMEIT_ITERATIONS)
    result_arcpy = timeit(lambda: task2(input2), number=TIMEIT_ITERATIONS)

    if result_ob < result_arcpy:
        winner = "ob"
        factor = result_arcpy / result_ob
    elif result_ob > result_arcpy:
        winner = "arcpy"
        factor = result_ob / result_arcpy
    else:
        winner = "tie"
        factor = 0

    return f"{name}\t{round(result_ob, 3)}\t{round(result_arcpy, 3)}\t{winner}\t{round(factor, 2)}x"


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
    # shp_stem = "exercise_data/more_analysis/Zoning/Generalised_Zoning_Dissolve_UTM33S"
    shp_stem = "exercise_data/more_analysis/Western_Cape_UTM33S/Western_Cape_UTM33S"

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
    shp_ob = ob.FeatureClass(gpd.read_file(shp))
    shp_arcpy = arcpy_mem_path()
    arcpy.CopyFeatures_management(shp, shp_arcpy)
    print("Loaded!")

    benchmarks = (
        ("load shp    ", load_shp_ob, shp, load_shp_arcpy, shp),
        ("get i-th row", get_ith_row_ob, shp_ob, get_ith_row_arcpy, shp_arcpy),
        ("buffer      ", buffer_ob, shp_ob, buffer_arcpy, shp_arcpy),
    )
    results = list()
    print("Benchmarking....")
    for bmark in tqdm(benchmarks):
        name, task1, input1, task2, input2 = bmark
        results.append(
            benchmark(name=name, task1=task1, input1=input1, task2=task2, input2=input2)
        )

    print("\n\nbenchmark\tob\tarcpy\twinner\tfactor")
    print("=" * 46, end="\n")
    print("\n".join(results))
    print("\n")
