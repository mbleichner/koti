from definitions import ConfigItem, ConfigManager
from managers.package import get_output, interactive


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
  def execute_phase(self, items: list[PacmanKey]):
    for item in items:
      if len(get_output(f"pacman-key --list-keys | grep {item.key_id}")) > 0:
        print(f"pacman-key {item.key_id} already installed")
      else:
        print(f"installing pacman-key {item.key_id} from {item.key_server}")
        interactive(f"sudo pacman-key --recv-keys {item.key_id} --keyserver {item.key_server}")
        interactive("sudo pacman-key --lsign-keys {item.key_id}")
