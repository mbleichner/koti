from core import Core, ConfigManager, ExecutionState
from items.checkpoint import Checkpoint


class CheckpointManager(ConfigManager[Checkpoint]):
  managed_classes = [Checkpoint]

  def execute_phase(self, items: list[Checkpoint], core: Core, state: ExecutionState):
    print(f"checkpoint reached: {", ".join([item.identifier for item in items])}")
