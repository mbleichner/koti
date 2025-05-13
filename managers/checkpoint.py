from definitions import ConfigItem, ConfigManager


class Checkpoint(ConfigItem):
  def __init__(self, identifier: str):
    super().__init__(identifier)

  def __str__(self):
    return f"Checkpoint('{self.identifier}')"


class CheckpointManager(ConfigManager[Checkpoint]):
  managed_classes = [Checkpoint]

  def execute_phase(self, items: list[Checkpoint]):
    print(f"checkpoint reached: {", ".join([item.identifier for item in items])}")
