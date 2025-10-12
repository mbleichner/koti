from __future__ import annotations

from typing import Unpack

from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class GroupAssignment(ManagedConfigItem):
  username: str
  group: str

  def __init__(
    self,
    username: str,
    group: str,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.username = username
    self.group = group

  def __str__(self) -> str:
    return f"GroupAssignment('{self.username}', '{self.group}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, GroupAssignment) and self == other
    return GroupAssignment(
      username = self.username,
      group = self.group,
      **self.merge_base_attrs(self, other),
    )
