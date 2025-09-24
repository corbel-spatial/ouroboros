pixi update

pixi run -e test-py313-conda coverage
pixi run -e test-py313-pypi test

pixi run -e dev build
pixi run -e dev lint
