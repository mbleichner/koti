from __future__ import annotations

from typing import Unpack

from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class FlatpakPackage(ManagedConfigItem):
  id: str

  def __init__(
    self,
    id: str,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.id = id


  def __str__(self) -> str:
    return f"FlatpakPackage('{self.id}')"

  def merge(self, other: ConfigItem) -> FlatpakPackage:
    assert isinstance(other, FlatpakPackage) and self == other
    return FlatpakPackage(
      id = self.id,
      **self.merge_base_attrs(self, other),
    )


# noinspection PyPep8Naming
def FlatpakPackages(*names: str) -> list[FlatpakPackage]:
  return [FlatpakPackage(name) for name in names]
