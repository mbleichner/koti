from koti.core import ConfigItem, ConfirmModeValues


class PacmanKey(ConfigItem):
  key_id: str | None
  comment: str | None

  def __init__(self, key_id: str, key_server = "keyserver.ubuntu.com", comment: str | None = None, confirm_mode: ConfirmModeValues | None = None):
    self.key_id = key_id
    self.key_server = key_server
    self.comment = comment
    self.confirm_mode = confirm_mode

  def identifier(self):
    return f"PacmanKey('{self.key_id}')"

  def description(self):
    if self.comment is not None:
      return f"PacmanKey('{self.key_id}', comment = '{self.comment}')"
    else:
      return f"PacmanKey('{self.key_id}')"
