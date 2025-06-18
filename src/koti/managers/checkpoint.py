from koti import Checkpoint
from koti.core import Checksums, ConfigManager, Koti
from koti.items.file import File


class CheckpointManager(ConfigManager[Checkpoint]):
  managed_classes = [Checkpoint]

  def check_configuration(self, item: File, core: Koti):
    pass

  def checksums(self, core: Koti) -> Checksums[Checkpoint]:
    return CheckpointChecksums()

  def apply_phase(self, items: list[Checkpoint], core: Koti):
    pass

  def cleanup(self, items: list[Checkpoint], core: Koti):
    pass


class CheckpointChecksums(Checksums[Checkpoint]):

  def current(self, item: Checkpoint) -> str | None:
    return None

  def target(self, item: Checkpoint) -> str | None:
    return None
