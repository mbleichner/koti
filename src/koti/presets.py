from koti.managers.pacman import AurHelper, PaccacheOptions
from koti.model import ConfigManager
from koti.managers import *


class ConfigManagerPresets:

  @staticmethod
  def arch(
    aur_helper: AurHelper | None = None,
    keep_unmanaged_packages: bool = False,
    update_system = False,
    paccache: PaccacheOptions = PaccacheOptions(),
  ) -> list[ConfigManager]:
    return [
      UserManager(),
      UserShellManager(),
      UserHomeManager(),
      UserGroupManager(),
      PacmanKeyManager(),
      PacmanPackageManager(
        aur_helper = aur_helper,
        keep_unmanaged_packages = keep_unmanaged_packages,
        update_system = update_system,
        paccache = paccache,
      ),
      SwapfileManager(),
      CheckpointManager(),
      FileManager(),
      FlatpakManager(),
      SystemdUnitManager(),
      PostHookManager(),
    ]
