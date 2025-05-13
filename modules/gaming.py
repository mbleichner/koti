from definitions import ConfigItemGroup, ConfigModule, ConfigModuleGroups
from managers.package import Package


class GamingModule(ConfigModule):
  def provides(self) -> ConfigModuleGroups:
    return ConfigItemGroup(
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
