from __future__ import annotations

from typing import Iterable, Unpack

from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class PacmanKey(ManagedConfigItem):
  key_id: str

  def __init__(
    self,
    key_id: str,
    key_server = "keyserver.ubuntu.com",
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.key_id = key_id
    self.key_server = key_server

  def __str__(self):
    return f"PacmanKey('{self.key_id}')"

  def merge(self, other: ConfigItem) -> PacmanKey:
    assert isinstance(other, PacmanKey) and other == self
    assert other == self.key_server, f"Conflicting key_server in {self}"
    return PacmanKey(
      key_id = self.key_id,
      key_server = self.key_server,
      **self.merge_base_attrs(self, other),
    )
