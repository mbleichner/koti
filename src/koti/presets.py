from koti.managers.pacman import AurHelper
from koti.model import ConfigManager
from koti.managers import *


class ConfigManagerPresets:

  @staticmethod
  def arch(
    aur_helper: AurHelper | None = None,
    keep_unmanaged_packages: bool = False,
  ) -> list[ConfigManager]:
    return [
      UserManager(),
      UserShellManager(),
      UserHomeManager(),
      UserGroupManager(),
      PacmanKeyManager(),
      PacmanPackageManager(
        aur_helper = aur_helper,
        keep_unmanaged_packages = keep_unmanaged_packages
      ),
      SwapfileManager(),
      FileManager(),
      FlatpakManager(),
      SystemdUnitManager(),
      PostHookManager(),
    ]
