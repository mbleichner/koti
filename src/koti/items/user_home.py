from __future__ import annotations

from typing import Unpack

from koti.items.user import User
from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class UserHome(ManagedConfigItem):
  username: str
  home: str | None

  def __init__(
    self,
    username: str,
    homedir: str | None,
    add_user_as_dependency = True,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.username = username
    self.homedir = homedir

    if add_user_as_dependency:
      self.after = ManagedConfigItem.merge_functions(
        self.after,
        lambda item: isinstance(item, User) and item.username == username,
      )

  def __str__(self) -> str:
    return f"UserHome('{self.username}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, UserHome) and self == other
    if self.homedir is not None and other.homedir is not None:
      assert self.homedir == other.homedir, f"{self} has conflicting homedir parameter"
    return UserHome(
      username = self.username,
      homedir = self.homedir or other.homedir,
      **self.merge_base_attrs(self, other),
    )
