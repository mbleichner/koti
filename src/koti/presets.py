from koti.model import ConfigManager
from koti.managers import *


class ConfigManagerPresets:

  @staticmethod
  def arch(
    pacman_adapter: PacmanAdapter = PacmanAdapter(),
    ignore_manually_installed_packages: bool = False,
  ) -> list[ConfigManager]:
    return [
      PacmanKeyManager(),
      PacmanPackageManager(
        delegate = pacman_adapter,
        ignore_manually_installed_packages = ignore_manually_installed_packages
      ),
      SwapfileManager(),
      FileManager(),
      SystemdUnitManager(),
      PostHookManager(),
    ]
