from __future__ import annotations

from typing import Generator, Sequence

from koti.items.checkpoint import Checkpoint
from koti.model import Action, ConfigItemState, ConfigManager, ConfigModel, SystemState
from koti.utils.json_store import JsonCollection


class CheckpointState(ConfigItemState):
  def sha256(self) -> str:
    return "-"


class CheckpointManager(ConfigManager[Checkpoint, CheckpointState]):
  managed_classes = [Checkpoint]
  cleanup_order: float = 0
  managed_Checkpoints_store: JsonCollection[str]

  def assert_installable(self, item: Checkpoint, model: ConfigModel):
    pass

  def get_state_target(self, item: Checkpoint, model: ConfigModel, dryrun: bool) -> CheckpointState:
    return CheckpointState()

  def get_state_current(self, item: Checkpoint, system_state: SystemState) -> CheckpointState | None:
    return CheckpointState()

  def get_install_actions(self, items_to_check: Sequence[Checkpoint], model: ConfigModel, system_state: SystemState) -> Generator[Action]:
    yield from ()

  def get_cleanup_actions(self, items_to_keep: Sequence[Checkpoint], model: ConfigModel, system_state: SystemState) -> Generator[Action]:
    yield from ()

  def finalize(self, model: ConfigModel, dryrun: bool):
    pass
