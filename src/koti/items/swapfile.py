from __future__ import annotations

from typing import Iterable

from koti.model import ConfigItem, ManagedConfigItem


class Swapfile(ManagedConfigItem):
  size_bytes: int | None
  filename: str

  def __init__(
    self,
    filename: str,
    size_bytes: int | None = None,
    tags: Iterable[str] | None = None,
  ):
    self.tags = set(tags or [])
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
      tags = self.tags.union(other.tags),
    )
