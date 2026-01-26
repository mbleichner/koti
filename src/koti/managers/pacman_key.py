from __future__ import annotations

from koti.model import *
from koti.items.pacman_key import PacmanKey
from koti.utils.shell import shell, shell_success


class PacmanKeyState(ConfigItemState):
  def sha256(self) -> str:
    return "-"


class PacmanKeyManager(ConfigManager[PacmanKey, PacmanKeyState]):
  managed_classes = [PacmanKey]
  cleanup_order = 70

  def assert_installable(self, item: PacmanKey, model: ConfigModel):
    pass

  def get_state_current(self, item: PacmanKey) -> PacmanKeyState | None:
    installed: bool = shell_success(f"pacman-key --list-keys | grep {item.key_id}")
    return PacmanKeyState() if installed else None

  def get_state_target(self, item: PacmanKey, model: ConfigModel, dryrun: bool) -> PacmanKeyState:
    return PacmanKeyState()

  def get_install_actions(self, items_to_check: Sequence[PacmanKey], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    for item in items_to_check:
      current, target = self.get_states(item, model, dryrun)
      if current == target:
        continue
      yield Action(
        installs = [item],
        description = f"install pacman-key {item.key_id} from {item.key_server}",
        execute = lambda: self.add_key(item),
      )

  def add_key(self, item: PacmanKey):
    shell(f"pacman-key --init")
    shell(f"pacman-key --recv-keys {item.key_id} --keyserver {item.key_server}")
    shell(f"pacman-key --lsign-key {item.key_id}")

  def get_cleanup_actions(self, items_to_keep: Sequence[PacmanKey], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    yield from ()
