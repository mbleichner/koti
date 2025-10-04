from __future__ import annotations

from koti.model import ConfigItem, ManagedConfigItem


class User(ManagedConfigItem):
  username: str
  shell: str | None
  home: str | None
  # FIXME: password prompt

  def __init__(
    self,
    username: str,
    shell: str | None = None,
    home: str | None = None,
  ):
    self.username = username
    self.shell = shell
    self.home = home

  def __str__(self) -> str:
    return f"User('{self.username}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, User) and self == other
    if self.shell is not None and other.shell is not None:
      assert self.shell == other.shell, f"User('{self.username}') has conflicting shell parameter"
    if self.home is not None and other.home is not None:
      assert self.home == other.home, f"User('{self.username}') has conflicting home parameter"
    return User(
      username = self.username,
      shell = self.shell or other.shell or None,
      home = self.home or other.home or None,
    )
