from koti.core import ConfigItem


class SystemdUnit(ConfigItem):
  user: str | None = None

  def __init__(self, identifier: str, user: str | None = None):
    super().__init__(identifier)
    self.user = user

  def __str__(self):
    return f"SystemdUnit('{self.identifier}')"


# noinspection PyPep8Naming
def SystemdUnits(*identifiers: str) -> list[SystemdUnit]:
  return [SystemdUnit(identifier) for identifier in identifiers]
