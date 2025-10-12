from __future__ import annotations

from typing import Unpack

from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class Checkpoint(ManagedConfigItem):
  """Helper item that can be used to declare dependencies."""
  name: str

  def __init__(self, name: str, **kwargs: Unpack[ManagedConfigItemBaseArgs]):
    super().__init__(**kwargs)
    self.name = name

  def __str__(self) -> str:
    return f"Checkpoint('{self.name}')"

  def merge(self, other: ConfigItem) -> Checkpoint:
    assert isinstance(other, Checkpoint) and self == other
    return Checkpoint(
      name = self.name,
      **self.merge_base_attrs(self, other)
    )
