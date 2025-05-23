from core import ConfigItem


class Package(ConfigItem):
  def __init__(self, identifier: str, url: str = None):
    super().__init__(identifier)
    self.url = url

  def __str__(self):
    if self.url is not None:
      return f"Package('{self.identifier}', url = ...)"
    return f"Package('{self.identifier}')"


def Packages(*identifiers: str) -> list[Package]:
  return [Package(identifier) for identifier in identifiers]
