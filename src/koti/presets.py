from __future__ import annotations

from typing import TypedDict, Unpack, reveal_type

from koti.model import ConfigManager
from koti.managers import *


class ArchPresetArgs(TypedDict, total = False):
  UserManager: UserManager | None
  UserShellManager: UserShellManager | None
  UserHomeManager: UserHomeManager | None
  UserGroupManager: UserGroupManager | None
  PacmanKeyManager: PacmanKeyManager | None
  PacmanPackageManager: PacmanPackageManager | None
  SwapfileManager: SwapfileManager | None
  CheckpointManager: CheckpointManager | None
  FileManager: FileManager | None
  FlatpakRepoManager: FlatpakRepoManager | None
  FlatpakPackageManager: FlatpakPackageManager | None
  SystemdUnitManager: SystemdUnitManager | None
  PostHookManager: PostHookManager | None


# noinspection PyPep8Naming
def ArchPreset(
  *overrides: ConfigManager,
  **kwargs: Unpack[ArchPresetArgs],
) -> list[ConfigManager]:
  print(reveal_type(list(kwargs)))

  def effective(manager: ConfigManager) -> ConfigManager | None:
    if manager.__class__.__name__ in kwargs:
      return kwargs[manager.__class__.__name__]  # type: ignore
    for override in overrides:
      if override.__class__ == manager.__class__:
        return override
    return manager

  return [manager for manager in (
    effective(UserManager()),
    effective(UserShellManager()),
    effective(UserHomeManager()),
    effective(UserGroupManager()),
    effective(PacmanKeyManager()),
    effective(PacmanPackageManager()),
    effective(SwapfileManager()),
    effective(CheckpointManager()),
    effective(FileManager()),
    effective(FlatpakRepoManager()),
    effective(FlatpakPackageManager()),
    effective(SystemdUnitManager()),
    effective(PostHookManager()),
  ) if manager is not None]
