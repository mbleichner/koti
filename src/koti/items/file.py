from __future__ import annotations

from pathlib import Path
from typing import Callable

from koti import ConfigItem, ExecutionModel, ManagedConfigItem


class File(ManagedConfigItem):
  content: Callable[[ExecutionModel], bytes] | None
  permissions: int = 0o755
  owner: str = "root"
  filename: str

  def __init__(
    self,
    filename: str,
    content: str | Callable[[ExecutionModel], str] | None = None,
    source: str | None = None,
    permissions: int = 0o444,
    owner: str = "root"
  ):
    self.filename = filename
    if callable(content):
      self.content = lambda model: content(model).encode("utf-8")
    elif isinstance(content, str):
      self.content = lambda model: content.encode("utf-8")
    elif source is not None:
      self.content = lambda model: Path(source).read_bytes()
    else:
      self.content = None
    self.permissions = permissions
    self.owner = owner

  def identifier(self):
    return f"File('{self.filename}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, File)
    raise AssertionError(f"File('{self.filename}') may not be declared twice")
