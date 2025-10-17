from __future__ import annotations

from typing import Unpack

from koti.items.user import User
from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class UserGroupAssignment(ManagedConfigItem):
  username: str
  group: str

  def __init__(
    self,
    username: str,
    group: str,
    add_user_as_dependency = True,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.username = username
    self.group = group

    if add_user_as_dependency:
      self.after = ManagedConfigItem.merge_functions(
        self.after,
        lambda item: isinstance(item, User) and item.username == username,
      )

  def __str__(self) -> str:
    return f"UserGroupAssignment('{self.username}', '{self.group}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, UserGroupAssignment) and self == other
    return UserGroupAssignment(
      username = self.username,
      group = self.group,
      **self.merge_base_attrs(self, other),
    )
