from koti.core import ConfigItem


class PacmanKey(ConfigItem):
  key_id: str | None
  key_server: str

  def __init__(self, identifier: str, key_id: str | None = None, key_server = "keyserver.ubuntu.com"):
    super().__init__(identifier)
    self.key_server = key_server
    self.key_id = key_id

  def __str__(self):
    return f"PacmanKey('{self.identifier}')"
