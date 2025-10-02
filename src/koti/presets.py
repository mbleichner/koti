from koti.managers.pacman import AurHelper
from koti.managers.user import UserManager
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
      PacmanKeyManager(),
      PacmanPackageManager(
        aur_helper = aur_helper,
        keep_unmanaged_packages = keep_unmanaged_packages
      ),
      GroupManager(),
      SwapfileManager(),
      FlatpakManager(),
      FileManager(),
      SystemdUnitManager(),
      PostHookManager(),
    ]
