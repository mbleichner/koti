from __future__ import annotations

from koti import ConfirmMode, highest_confirm_mode
from koti.core import ConfigItem, ManagedConfigItem


class Package(ManagedConfigItem):
  name: str
  url: str | None

  def __init__(
    self,
    name: str,
    url: str | None = None,
    confirm_mode: ConfirmMode | None = None
  ):
    self.name = name
    self.url = url
    self.confirm_mode = confirm_mode

  def identifier(self):
    return f"Package('{self.name}')"

  def description(self):
    if self.url is not None:
      return f"Package('{self.name}', url = '{self.url}')"
    else:
      return f"Package('{self.name}')"

  def merge(self, other: ConfigItem) -> Package:
    assert isinstance(other, Package)
    assert other.identifier() == self.identifier()
    assert self.url == other.url, f"Package('{self.name}') has conflicting url parameter"
    return Package(
      name = self.name,
      url = self.url,
      confirm_mode = highest_confirm_mode(self.confirm_mode, other.confirm_mode),
    )


# noinspection PyPep8Naming
def Packages(*names: str) -> list[Package]:
  return [Package(name) for name in names]
