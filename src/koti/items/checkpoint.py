from __future__ import annotations

from typing import Any

from koti.model import ConfigItem, UnmanagedConfigItem


class Checkpoint(UnmanagedConfigItem):
  """Helper item that can be used to declare dependencies."""

  name: str

  def __init__(self, name: str):
    self.name = name

  def __str__(self) -> str:
    return f"Checkpoint('{self.name}')"

  def merge(self, other: ConfigItem) -> Checkpoint:
    assert isinstance(other, Checkpoint) and self == other
    return self
