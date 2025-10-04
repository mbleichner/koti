from __future__ import annotations

from koti.model import ConfigItem, ManagedConfigItem


class GroupAssignment(ManagedConfigItem):
  username: str
  group: str

  def __init__(
    self,
    username: str,
    group: str,
  ):
    self.username = username
    self.group = group

  def __str__(self) -> str:
    return f"GroupAssignment('{self.username}', '{self.group}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, GroupAssignment) and self == other
    return self
