from koti import *
from koti.managers.file import FileOptionManager


class KotiManagerPresets:

  @staticmethod
  def arch(pacman_adapter: PacmanAdapter = PacmanAdapter()) -> list[ConfigManager]:
    return [
      PacmanKeyManager(),
      PacmanPackageManager(pacman_adapter),
      SwapfileManager(),
      FileOptionManager(),
      FileManager(),
      SystemdUnitManager(),
      PostHookManager(),
      CheckpointManager(),
    ]

  # @staticmethod
  # def debian() -> list[ConfigManager]:
  #   return [
  #     DebianPackageManager,
  #     SwapfileManager(),
  #     FileManager(),
  #     SystemdUnitManager(),
  #     PostHookManager(),
  #     CheckpointManager(),
  #   ]
