from __future__ import annotations

from koti import highest_confirm_mode
from koti.core import ConfigItem, ConfirmModeValues, ManagedConfigItem


class PacmanKey(ManagedConfigItem):
  key_id: str
  comment: str | None

  def __init__(self, key_id: str, key_server = "keyserver.ubuntu.com", comment: str | None = None, confirm_mode: ConfirmModeValues | None = None):
    self.confirm_mode = confirm_mode
    self.key_id = key_id
    self.key_server = key_server
    self.comment = comment

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
      confirm_mode = highest_confirm_mode(self.confirm_mode, other.confirm_mode),
    )
