from koti import ConfirmModeValues
from koti.core import ConfigItem


class Checkpoint(ConfigItem):

  def __init__(self, identifier: str, confirm_mode: ConfirmModeValues | None = None):
    super().__init__(identifier = identifier, confirm_mode = confirm_mode)

  def __str__(self):
    return f"Checkpoint('{self.identifier}')"
