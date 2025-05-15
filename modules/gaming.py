from core import ConfigItemGroup, ConfigModule, ConfigModuleGroups
from managers.pacman import PacmanPackage


class GamingModule(ConfigModule):
  def provides(self) -> ConfigModuleGroups:
    return ConfigItemGroup(
      PacmanPackage("discord"),
      PacmanPackage("gamescope"),
      PacmanPackage("gpu-screen-recorder-ui"),
      PacmanPackage("proton-ge-custom-bin"),
      PacmanPackage("protontricks"),
      PacmanPackage("ryujinx"),
      PacmanPackage("steam"),
      PacmanPackage("nexusmods-app-bin"),
      PacmanPackage("r2modman-bin"),
      PacmanPackage("mangohud"),
    )
