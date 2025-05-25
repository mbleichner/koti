from koti.core import Koti, ConfigManager, ExecutionState
from koti.items.checkpoint import Checkpoint


class CheckpointManager(ConfigManager[Checkpoint]):
  managed_classes = [Checkpoint]

  def execute_phase(self, items: list[Checkpoint], core: Koti, state: ExecutionState):
    print(f"checkpoint reached: {", ".join([item.identifier for item in items])}")
