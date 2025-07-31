@echo off
SET env=ouroboros-dev
SET m=********************

ECHO %m% Make Docs %m%
CALL conda run -n %env% .\make html
CALL conda run -n %env% .\make html
ECHO %m% Open Docs %m%
START .\_build\html\index.html

ECHO %m% Run Coverage %m%
CALL conda run -n %env% coverage run -m pytest ..\tests\tests.py
CALL conda run -n %env% coverage html
CALL conda run -n %env% coverage json -o .\pytest_coverage.json --pretty-print
ECHO %m% Open Coverage %m%
START .\htmlcov\index.html
