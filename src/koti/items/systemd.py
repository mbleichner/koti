from koti.core import ConfigItem, ConfirmModeValues


class SystemdUnit(ConfigItem):
  name: str
  user: str | None = None

  def __init__(self, name: str, user: str | None = None, confirm_mode: ConfirmModeValues | None = None):
    self.name = name
    self.user = user
    self.confirm_mode = confirm_mode

  def identifier(self):
    if self.user is not None:
      return f"SystemdUnit('{self.name}', user = '{self.user}')"
    else:
      return f"SystemdUnit('{self.name}')"


# noinspection PyPep8Naming
def SystemdUnits(*identifiers: str) -> list[SystemdUnit]:
  return [SystemdUnit(identifier) for identifier in identifiers]
