from koti import ConfirmModeValues
from koti.core import ConfigItem


class Package(ConfigItem):
  name: str
  url: str | None

  def __init__(self, name: str, url: str | None = None, confirm_mode: ConfirmModeValues | None = None):
    self.confirm_mode = confirm_mode
    self.name = name
    self.url = url

  def identifier(self):
    return f"Package('{self.name}')"


# noinspection PyPep8Naming
def Packages(*names: str) -> list[Package]:
  return [Package(name) for name in names]
