from koti import *


class KotiManagerPresets:

  @staticmethod
  def arch(pacman_adapter: PacmanAdapter = PacmanAdapter()) -> list[ConfigManager]:
    return [
      PreHookManager(),
      PacmanKeyManager(),
      PacmanPackageManager(pacman_adapter),
      SwapfileManager(),
      FileManager(),
      SystemdUnitManager(),
      PostHookManager(),
    ]

  @staticmethod
  def debian() -> list[ConfigManager]:
    return [
      PreHookManager(),
      DebianPackageManager,
      SwapfileManager(),
      FileManager(),
      SystemdUnitManager(),
      PostHookManager(),
    ]
