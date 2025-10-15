from __future__ import annotations

from typing import Unpack

from koti.items.user import User
from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class SystemdUnit(ManagedConfigItem):
  name: str
  user: str | None = None

  def __init__(
    self,
    name: str,
    user: str | None = None,
    add_user_as_dependency = True,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.name = name
    self.user = user

    if add_user_as_dependency:
      self.after = ManagedConfigItem.merge_functions(
        self.after,
        lambda item: isinstance(item, User) and item.username == user,
      )

  def __str__(self) -> str:
    if self.user is not None:
      return f"SystemdUnit('{self.name}', user = '{self.user}')"
    else:
      return f"SystemdUnit('{self.name}')"

  def merge(self, other: ConfigItem) -> SystemdUnit:
    assert isinstance(other, SystemdUnit) and self == other
    return SystemdUnit(
      name = self.name,
      user = self.user,
      **self.merge_base_attrs(self, other),
    )


# noinspection PyPep8Naming
def SystemdUnits(*names: str) -> list[SystemdUnit]:
  return [SystemdUnit(identifier) for identifier in names]
