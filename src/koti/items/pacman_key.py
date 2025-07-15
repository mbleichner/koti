from koti.core import ConfigItem, ConfirmModeValues


class PacmanKey(ConfigItem):
  key_id: str | None

  def __init__(self, key_id: str, key_server = "keyserver.ubuntu.com", confirm_mode: ConfirmModeValues | None = None):
    self.key_id = key_id
    self.key_server = key_server
    self.confirm_mode = confirm_mode

  def identifier(self):
    return f"PacmanKey('{self.key_id}')"
