from __future__ import annotations

from koti import ConfigItem, UnmanagedConfigItem


class Checkpoint(UnmanagedConfigItem):
  name: str

  def __init__(self, name: str):
    self.name = name

  def identifier(self):
    return f"Checkpoint('{self.name}')"

  def merge(self, other: ConfigItem) -> Checkpoint:
    assert isinstance(other, Checkpoint)
    assert other.identifier() == self.identifier()
    return self
