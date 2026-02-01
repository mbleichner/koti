from koti import *


def development() -> ConfigDict:
  return {
    Section("graphical development utils"): (
      Package("gitkraken"),
      Package("pycharm"),
    ),

    Section("misc python dev tools/libraries"): (
      Package("mypy"),
      Package("tk"),
      Package("python-uv"),
      Package("pyenv"),
      Package("kdiff3"),
    ),
  }
