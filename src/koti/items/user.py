from __future__ import annotations

from typing import Unpack

from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class User(ManagedConfigItem):
  username: str
  shell: str | None
  home: str | None
  password: bool | None

  def __init__(
    self,
    username: str,
    shell: str | None = None,  # FIXME: make into a separate item UserShell()
    home: str | None = None,  # FIXME: make optional
    password: bool | None = None,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.username = username
    self.shell = shell
    self.home = home
    self.password = password

  def __str__(self) -> str:
    return f"User('{self.username}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, User) and self == other
    if self.shell is not None and other.shell is not None:
      assert self.shell == other.shell, f"{self} has conflicting shell parameter"
    if self.home is not None and other.home is not None:
      assert self.home == other.home, f"{self} has conflicting home parameter"
    if self.password is not None and other.password is not None:
      assert self.password == other.password, f"{self} has conflicting password parameter"
    return User(
      username = self.username,
      shell = self.shell or other.shell or None,
      home = self.home or other.home or None,
      password = self.password or other.password or None,
      **self.merge_base_attrs(self, other),
    )
