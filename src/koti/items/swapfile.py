from __future__ import annotations

from typing import Iterable, Unpack

from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class Swapfile(ManagedConfigItem):
  size_bytes: int | None
  filename: str

  def __init__(
    self,
    filename: str,
    size_bytes: int | None = None,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.filename = filename
    self.size_bytes = size_bytes

  def __str__(self) -> str:
    return f"Swapfile('{self.filename}')"

  def merge(self, other: ConfigItem) -> Swapfile:
    assert isinstance(other, Swapfile) and self == other
    if self.size_bytes is not None and other.size_bytes is not None:
      assert other.size_bytes == self.size_bytes, f"Conflicting size_bytes in {self}"
    return Swapfile(
      filename = self.filename,
      size_bytes = self.size_bytes,
      tags = self.tags.union(other.tags),
    )
