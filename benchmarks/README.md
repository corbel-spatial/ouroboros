# Benchmark ouroboros vs. arcpy

⚠️ Requires a licensed ArcGIS Pro installation. ⚠️

1. Open the [Python Command Prompt](https://developers.arcgis.com/python/latest/guide/install-and-set-up/arcgis-pro/#installation-using-python-command-prompt), which can be launched from the Start Menu > All Programs > ArcGIS > Python Command Prompt.

2. Clone a new environment:
    ```bash
    conda create -n ob-benchmark --clone arcgispro-py3
    ```

3. Activate the new environment:
    ```bash
    proswap ob-benchmark
    ```

4. Add channels and set channel priority:
    ```bash
    conda config --add channels esri
    conda config --append channels conda-forge
    conda config --set channel_priority flexible
    ```
    
5. Upgrade the environment:
    ```bash
    conda upgrade --all
    ```
   
6. Install `ouroboros` and `pooch` (for downloading sample datasets):
    ```bash
    conda install ouroboros-gis pooch
    ```

7. Run benchmarks:
    ```bash
    python benchmarks.py
    ```