from __future__ import annotations

from typing import Unpack

from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class User(ManagedConfigItem):
  username: str
  password: bool | None

  def __init__(
    self,
    username: str,
    password: bool | None = None,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.username = username
    self.password = password

  def __str__(self) -> str:
    return f"User('{self.username}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, User) and self == other
    if self.password is not None and other.password is not None:
      assert self.password == other.password, f"{self} has conflicting password parameter"
    return User(
      username = self.username,
      password = self.password or other.password or None,
      **self.merge_base_attrs(self, other),
    )
