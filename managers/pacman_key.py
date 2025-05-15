from definitions import ConfigItem, ConfigManager, ExecutionState
from managers.pacman import shell_interactive
from utils import shell_success


class PacmanKey(ConfigItem):
  def __init__(
    self,
    identifier: str = None,
    key_id: str = None,
    key_server = "keyserver.ubuntu.com",
  ):
    super().__init__(identifier)
    self.key_server = key_server
    self.key_id = key_id

  def __str__(self):
    return f"PacmanKey('{self.identifier}')"


class PacmanKeyManager(ConfigManager[PacmanKey]):
  managed_classes = [PacmanKey]

  def execute_phase(self, items: list[PacmanKey], state: ExecutionState):
    for item in items:
      key_already_installed = shell_success(f"pacman-key --list-keys | grep {item.key_id}")
      if not key_already_installed:
        print(f"installing pacman-key {item.key_id} from {item.key_server}")
        shell_interactive(f"sudo pacman-key --recv-keys {item.key_id} --keyserver {item.key_server}")
        shell_interactive("sudo pacman-key --lsign-keys {item.key_id}")
