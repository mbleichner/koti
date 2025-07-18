from __future__ import annotations

from koti import ConfigItem, highest_confirm_mode
from koti.core import ManagedConfigItem, ConfirmModeValues


class SystemdUnit(ManagedConfigItem):
  name: str
  user: str | None = None

  def __init__(self, name: str, user: str | None = None, confirm_mode: ConfirmModeValues | None = None):
    self.confirm_mode = confirm_mode
    self.name = name
    self.user = user

  def identifier(self):
    if self.user is not None:
      return f"SystemdUnit('{self.name}', user = '{self.user}')"
    else:
      return f"SystemdUnit('{self.name}')"

  def merge(self, other: ConfigItem) -> SystemdUnit:
    assert isinstance(other, SystemdUnit)
    assert self.identifier() == other.identifier()
    return SystemdUnit(
      name = self.name,
      user = self.user,
      confirm_mode = highest_confirm_mode(self.confirm_mode, other.confirm_mode),
    )


# noinspection PyPep8Naming
def SystemdUnits(*names: str) -> list[SystemdUnit]:
  return [SystemdUnit(identifier) for identifier in names]
