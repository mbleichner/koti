from koti import Checkpoint
from koti.core import Checksums, ConfigManager, Koti
from koti.items.file import File


class CheckpointManager(ConfigManager[Checkpoint]):
  managed_classes = [Checkpoint]

  def check_configuration(self, item: Checkpoint, core: Koti):
    pass

  def checksums(self, core: Koti) -> Checksums[Checkpoint]:
    return CheckpointChecksums()

  def install(self, items: list[Checkpoint], core: Koti):
    pass

  def uninstall(self, items_to_keep: list[Checkpoint], core: Koti):
    pass


class CheckpointChecksums(Checksums[Checkpoint]):

  def current(self, item: Checkpoint) -> str | None:
    return None

  def target(self, item: Checkpoint) -> str | None:
    return None
