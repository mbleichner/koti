from __future__ import annotations

from koti.core import ConfigItem, ManagedConfigItem


class Swapfile(ManagedConfigItem):
  size_bytes: int | None
  filename: str

  def __init__(self, filename: str, size_bytes: int | None = None):
    self.filename = filename
    self.size_bytes = size_bytes

  def identifier(self):
    return f"Swapfile('{self.filename}')"

  def merge(self, other: ConfigItem) -> Swapfile:
    assert isinstance(other, Swapfile)
    assert other.identifier() == self.identifier()
    assert other.size_bytes == self.size_bytes, f"Conflicting size_bytes in {self.identifier()}"
    return self
