from koti import *


def gaming() -> ConfigGroups:
  return ConfigGroup(
    Package("discord"),
    Package("gamescope"),
    Package("gpu-screen-recorder-ui"),
    Package("proton-ge-custom-bin"),
    Package("protontricks"),
    Package("ryujinx"),
    Package("steam"),
    Package("nexusmods-app-bin"),
    Package("r2modman-bin"),
    Package("mangohud"),
  )
