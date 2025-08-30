from koti.managers.user import UserManager
from koti.model import ConfigManager
from koti.managers import *


class ConfigManagerPresets:

  @staticmethod
  def arch(
    pacman_adapter: PacmanAdapter = PacmanAdapter(),
    keep_unmanaged_packages: bool = False,
  ) -> list[ConfigManager]:
    return [
      UserManager(),
      PacmanKeyManager(),
      PacmanPackageManager(
        delegate = pacman_adapter,
        keep_unmanaged_packages = keep_unmanaged_packages
      ),
      SwapfileManager(),
      FlatpakManager(),
      FileManager(),
      SystemdUnitManager(),
      PostHookManager(),
    ]
