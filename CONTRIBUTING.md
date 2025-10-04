# Contributing

Questions and suggestions are welcomed in the [Issues section](https://github.com/corbel-spatial/ouroboros/issues). The information below will help you set up a 
development environment if you wish to submit pull requests.

## Development Environment Setup

First, install the [Pixi](https://pixi.sh/latest/installation/) package management tool. Then,

```shell
git clone https://github.com/corbel-spatial/ouroboros.git
cd ouroboros
pixi install
pixi install -e dev
```

## IDE Support

Pixi has extenions that support various code editing applications. By default `pixi install` will install `pixi-pycharm` for [JetBrains PyCharm](https://pixi.sh/latest/integration/editor/jetbrains/).

Pixi also supports 
[VSCode](https://pixi.sh/latest/integration/editor/vscode/),
[Zed](https://pixi.sh/latest/integration/editor/zed/),
[RStudio](https://pixi.sh/latest/integration/editor/r_studio/), and
[JupyterLab](https://pixi.sh/latest/integration/editor/jupyterlab/).
