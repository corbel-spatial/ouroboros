#!/bin/bash
git clone https://github.com/corbel-spatial/ouroboros.git
cd ouroboros
uv pip install . pytest --system
python3 -m pytest -vv