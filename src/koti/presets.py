from __future__ import annotations

from typing import Sequence

from koti.model import ConfigManager
from koti.managers import *


# noinspection PyPep8Naming
def ArchPreset(
  *overrides: ConfigManager,
) -> list[ConfigManager]:
  defaults: Sequence[ConfigManager] = [
    UserManager(),
    UserShellManager(),
    UserHomeManager(),
    UserGroupManager(),
    PacmanKeyManager(),
    PacmanPackageManager(),
    SwapfileManager(),
    CheckpointManager(),
    FileManager(),
    FlatpakRepoManager(),
    FlatpakPackageManager(),
    SystemdUnitManager(),
    PostHookManager(),
  ]
  overridden_classes = [manager.__class__ for manager in overrides]
  return [
    *(manager for manager in defaults if manager.__class__ not in overridden_classes),
    *overrides,
  ]
