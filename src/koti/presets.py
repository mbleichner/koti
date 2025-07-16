from koti import *

class KotiManagerPresets:

  @staticmethod
  def arch(pacman_adapter: PacmanAdapter = PacmanAdapter()) -> list[ConfigManager]:
    return [
      PacmanKeyManager(),
      PacmanPackageManager(pacman_adapter),
      SwapfileManager(),
      FileManager(),
      SystemdUnitManager(),
      PostHookManager(),
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
