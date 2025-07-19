from __future__ import annotations

from koti import highest_confirm_mode
from koti.core import ConfigItem, ConfirmModeValues, ManagedConfigItem


class Swapfile(ManagedConfigItem):
  size_bytes: int | None
  filename: str

  def __init__(self, filename: str, size_bytes: int | None = None, confirm_mode: ConfirmModeValues | None = None):
    self.confirm_mode = confirm_mode
    self.filename = filename
    self.size_bytes = size_bytes

  def identifier(self):
    return f"Swapfile('{self.filename}')"

  def merge(self, other: ConfigItem) -> Swapfile:
    assert isinstance(other, Swapfile)
    assert other.identifier() == self.identifier()
    assert other.size_bytes == self.size_bytes, f"Conflicting size_bytes in {self.identifier()}"
    return Swapfile(
      filename = self.filename,
      size_bytes = self.size_bytes,
      confirm_mode = highest_confirm_mode(self.confirm_mode, other.confirm_mode),
    )
