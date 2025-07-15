from koti.core import ConfigItem, ConfirmModeValues


class Swapfile(ConfigItem):
  size_bytes: int | None
  filename: str

  def __init__(self, filename: str, size_bytes: int | None = None, confirm_mode: ConfirmModeValues | None = None):
    self.filename = filename
    self.size_bytes = size_bytes
    self.confirm_mode = confirm_mode

  def identifier(self):
    return f"Swapfile('{self.filename}')"
