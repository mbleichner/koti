from __future__ import annotations

from typing import Unpack

from koti.items.user import User
from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class UserShell(ManagedConfigItem):
  username: str
  shell: str | None

  def __init__(
    self,
    username: str,
    shell: str | None,
    add_user_as_dependency = True,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.username = username
    self.shell = shell

    if add_user_as_dependency:
      self.after = [*self.after, User(username)]

  def __str__(self) -> str:
    return f"UserShell('{self.username}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, UserShell) and self == other
    if self.shell is not None and other.shell is not None:
      assert self.shell == other.shell, f"{self} has conflicting shell parameter"
    return UserShell(
      username = self.username,
      shell = self.shell or other.shell,
      **self.merge_base_attrs(self, other),
    )
