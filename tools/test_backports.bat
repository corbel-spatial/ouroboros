pixi update

pixi run -e test-py310-pypi test
pixi run -e test-py311-pypi test
pixi run -e test-py312-pypi test

pixi run -e test-py310-conda test
pixi run -e test-py311-conda test
pixi run -e test-py312-conda test
