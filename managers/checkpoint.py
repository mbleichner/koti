from core import ArchUpdate, ConfigManager, ExecutionState
from items.checkpoint import Checkpoint


class CheckpointManager(ConfigManager[Checkpoint]):
  managed_classes = [Checkpoint]

  def execute_phase(self, items: list[Checkpoint], core: ArchUpdate, state: ExecutionState):
    print(f"checkpoint reached: {", ".join([item.identifier for item in items])}")
