from __future__ import annotations

from typing import Any, Callable, Unpack

from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class Package(ManagedConfigItem):
  name: str
  url: str | None

  def __init__(
    self,
    name: str,
    url: str | None = None,
    script: Callable[[], Any] | None = None,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.name = name
    self.url = url
    self.script = script

  def __eq__(self, other: Any) -> bool:
    return isinstance(other, Package) and self.name == other.name

  def __hash__(self):
    return hash(self.name)

  def __str__(self):
    if self.script is not None:
      return f"Package('{self.name}', script = '...')"
    elif self.url is not None:
      return f"Package('{self.name}', url = '{self.url}')"
    else:
      return f"Package('{self.name}')"

  def merge(self, other: ConfigItem) -> Package:
    assert isinstance(other, Package) and self == other
    if self.url is not None and other.url is not None:
      assert self.url == other.url, f"{self} has conflicting url parameter"
    if self.script is not None and other.script is not None:
      assert self.script == other.script, f"{self} has conflicting script parameter"
    return Package(
      name = self.name,
      url = self.url,
      script = self.script,
      **self.merge_base_attrs(self, other),
    )


# noinspection PyPep8Naming
def Packages(*names: str) -> list[Package]:
  return [Package(name) for name in names]
