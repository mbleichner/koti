from __future__ import annotations

from pathlib import Path
from typing import Callable

from koti import ConfigItem, Koti, ManagedConfigItem, UnmanagedConfigItem


class File(ManagedConfigItem):
  content: Callable[[Koti], bytes]
  permissions: int = 0o755
  owner: str = "root"
  filename: str

  def __init__(
    self,
    filename: str,
    content: str | Callable[[Koti], str] | None = None,
    source: str | None = None,
    permissions: int = 0o444,
    owner: str = "root"
  ):
    self.filename = filename
    if callable(content):
      self.content = lambda core: content(core).encode("utf-8")
    elif isinstance(content, str):
      self.content = lambda core: content.encode("utf-8")
    elif source is not None:
      self.content = lambda core: Path(source).read_bytes()
    else:
      self.content = lambda core: "".encode("utf-8")
    self.permissions = permissions
    self.owner = owner

  def identifier(self):
    return f"File('{self.filename}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, File)
    raise AssertionError(f"File('{self.filename}') may not be declared twice")


class FileOption(UnmanagedConfigItem):
  managed = False
  filename: str
  option: str
  value: str | None

  def __init__(self, filename: str, option: str, value: str | None = None):
    self.filename = filename
    self.option = option
    self.value = value

  def identifier(self):
    return f"FileOption('{self.filename}', '{self.option}')"

  def merge(self, other: ConfigItem) -> FileOption:
    assert isinstance(other, FileOption)
    assert other.identifier() == self.identifier()
    assert other.value == self.value, f"Conflicting {self.identifier()}"
    return self


class FileOptionList(UnmanagedConfigItem):
  managed = False
  filename: str
  option: str
  values: list[str]

  def __init__(self, filename: str, option: str, value: list[str] | str | None = None):
    self.filename = filename
    self.option = option
    if isinstance(value, list):
      self.values = value
    elif isinstance(value, str):
      self.values = [value]
    else:
      self.values = []

  def identifier(self):
    return f"FileOptionList('{self.filename}', '{self.option}')"

  def merge(self, other: ConfigItem) -> FileOptionList:
    assert isinstance(other, FileOptionList)
    assert other.identifier() == self.identifier()
    merged_values = list({*self.values, *other.values})
    return FileOptionList(self.filename, self.option, merged_values)
