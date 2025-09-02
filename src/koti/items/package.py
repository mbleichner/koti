from __future__ import annotations

from typing import Any, Callable, Iterable

from koti.model import ConfigItem, ManagedConfigItem


class Package(ManagedConfigItem):
  name: str
  url: str | None

  def __init__(
    self,
    name: str,
    url: str | None = None,
    script: Callable[[], Any] | None = None,
    tags: Iterable[str] | None = None
  ):
    self.name = name
    self.url = url
    self.script = script
    self.tags = set(tags or [])

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
    if self.url is not None and other.url is not None:
      assert self.url == other.url, f"Package('{self.name}') has conflicting url parameter"
    if self.script is not None and other.script is not None:
      assert self.script == other.script, f"Package('{self.name}') has conflicting script parameter"
    return Package(
      name = self.name,
      url = self.url,
      script = self.script,
      tags = self.tags.union(other.tags),
    )


# noinspection PyPep8Naming
def Packages(*names: str) -> list[Package]:
  return [Package(name) for name in names]
