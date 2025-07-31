@echo off
SET env_name=ouroboros-dev
SET activate_bat="C:\Users\%USERNAME%\miniconda3\Scripts\activate.bat"
SET conda="C:\Users\%USERNAME%\miniconda3\Scripts\conda.exe"
SET env="C:\Users\workstation\miniconda3\envs\%env_name%"
SET m=********************
GOTO :main


:install
SETLOCAL
ECHO %m% Installing miniconda3 %m%

rem Silent install instructions from https://www.anaconda.com/docs/getting-started/miniconda/install
curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe -o .\miniconda.exe
start /wait "" .\miniconda.exe /S
del .\miniconda.exe
%conda% init powershell
ENDLOCAL
GOTO :EOF


:acceptTOS
SETLOCAL
CALL %conda% tos accept --override-channels --channel "https://repo.anaconda.com/pkgs/main"
CALL %conda% tos accept --override-channels --channel "https://repo.anaconda.com/pkgs/r"
CALL %conda% tos accept --override-channels --channel "https://repo.anaconda.com/pkgs/msys2"
ENDLOCAL
GOTO :EOF


:create
SETLOCAL
ECHO %m% Create %env_name% %m%
CALL :acceptTOS
CALL %conda% create -n %env_name% python=3.13 conda-build conda-index "gdal>=3.8" "libsqlite>=3.37" "sqlite>=3.37" uv -c conda-forge -y
ENDLOCAL
GOTO :EOF


:main
IF NOT EXIST %activate_bat% CALL :install

ECHO %m% Update base %m%
CALL :acceptTOS
CALL %conda% update --all -y -n base

IF NOT EXIST %env% CALL :create

ECHO %m% Update %env_name% %m%
CALL :acceptTOS
CALL %conda% update --all -c conda-forge -y -n %env_name%

ECHO %m% pip install other dependencies %m%
CALL %conda% run -n %env_name% uv pip install --upgrade -e . --group dev
CALL %conda% run -n %env_name% uv pip uninstall ouroboros-gis

ECHO %m% Set project source as an editable install %m%
CALL %conda% run -n %env_name% conda develop .\src

ECHO %m% Create venv without GDAL %m%
IF NOT EXIST .venv CALL python -m venv .venv
CALL .venv\Scripts\activate.bat
CALL python -m pip install --upgrade -e . --group dev
