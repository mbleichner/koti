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

  def identifier(self):
    return f"GroupAssignment('{self.username}', '{self.group}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, GroupAssignment)
    return self
