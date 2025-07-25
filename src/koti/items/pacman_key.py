from __future__ import annotations

from typing import Iterable

from koti.model import ConfigItem, ManagedConfigItem


class PacmanKey(ManagedConfigItem):
  key_id: str
  comment: str | None

  def __init__(
    self,
    key_id: str,
    key_server = "keyserver.ubuntu.com",
    comment: str | None = None,
    tags: Iterable[str] | None = None,
  ):
    self.key_id = key_id
    self.key_server = key_server
    self.comment = comment
    self.tags = set(tags or [])

  def identifier(self):
    return f"PacmanKey('{self.key_id}')"

  def description(self):
    if self.comment is not None:
      return f"PacmanKey('{self.key_id}', comment = '{self.comment}')"
    else:
      return f"PacmanKey('{self.key_id}')"

  def merge(self, other: ConfigItem) -> PacmanKey:
    assert isinstance(other, PacmanKey)
    assert other.identifier() == self.identifier()
    assert other.key_server == self.key_server, f"Conflicting key_server in {self.identifier()}"
    return PacmanKey(
      key_id = self.key_id,
      key_server = self.key_server,
      comment = " / ".join((x for x in {self.comment, other.comment} if x is not None)),
      tags = self.tags.union(other.tags),
    )
