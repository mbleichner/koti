from __future__ import annotations

from typing import Iterable

from koti.model import ConfigItem, ManagedConfigItem


class FlatpakPackage(ManagedConfigItem):
  id: str

  def __init__(
    self,
    id: str,
    tags: Iterable[str] | None = None,
  ):
    self.id = id
    self.tags = set(tags or [])

  def __str__(self) -> str:
    return f"FlatpakPackage('{self.id}')"

  def merge(self, other: ConfigItem) -> FlatpakPackage:
    assert isinstance(other, FlatpakPackage) and self == other
    return FlatpakPackage(
      id = self.id,
      tags = self.tags.union(other.tags),
    )


# noinspection PyPep8Naming
def FlatpakPackages(*names: str) -> list[FlatpakPackage]:
  return [FlatpakPackage(name) for name in names]
