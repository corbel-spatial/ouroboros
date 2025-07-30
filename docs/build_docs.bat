call .\docs\make html
call .\docs\make html
start .\docs\_build\html\index.html

coverage run -m pytest .\tests\tests.py
coverage html
coverage json -o .\docs\pytest_coverage.json --pretty-print
start .\htmlcov\index.html
