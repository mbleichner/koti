from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Unpack
from re import match

from urllib3 import request

from koti.model import ConfigItem, ConfigModel, ManagedConfigItem, ManagedConfigItemBaseArgs


class File(ManagedConfigItem):
  content: Callable[[ConfigModel], bytes] | None
  permissions: int
  owner: str = "root"
  # FIXME: group?
  filename: str

  def __init__(
    self,
    filename: str,
    content: str | bytes | Callable[[ConfigModel], str | bytes] | None = None,
    source: str | None = None,
    permissions: int | str | None = None,
    owner: str = "root",
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.filename = filename
    if callable(content):
      self.content = lambda model: self.bytes(content(model))
    elif isinstance(content, str):
      self.content = lambda model: self.bytes(content)
    elif source is not None:
      if source.startswith("http://") or source.startswith("https://"):
        self.content = lambda model: self.bytes(self.download(source))
      else:
        self.content = lambda model: Path(source).read_bytes()
        self.permissions = os.stat(source).st_mode & 0o777
    else:
      self.content = None
    if isinstance(permissions, str):
      self.permissions = File.parse_permissions(permissions)
    elif isinstance(permissions, int):
      self.permissions = permissions
    elif permissions is None:
      self.permissions = 0o644  # rw-r--r--
    self.owner = owner

  def __eq__(self, other: Any) -> bool:
    return isinstance(other, File) and self.filename == other.filename

  def __hash__(self):
    return hash(self.filename)

  def __str__(self):
    return f"File('{self.filename}')"

  def merge(self, other: ConfigItem) -> File:
    assert isinstance(other, File) and self == other
    if self.content is not None and other.content is not None:
      assert False, f"{self} may not be declared twice"
    if self.permissions is not None and other.permissions is not None:
      assert self.permissions == other.permissions, f"{self} has conflicting permissions parameter"
    if self.owner is not None and other.owner is not None:
      assert self.owner == other.owner, f"{self} has conflicting owner parameter"
    return File(
      filename = self.filename,
      content = self.content or other.content,
      permissions = self.permissions or other.permissions,
      owner = self.owner or other.owner,
      **self.merge_base_attrs(self, other),
    )

  @staticmethod
  def parse_permissions(permissions: str) -> int:
    assert len(permissions) == 3 or len(permissions) == 9, f"permission string must have exactly 3 or 9 digits: {permissions}"
    if len(permissions) == 9:
      return File.parse_permissions_9digit(permissions)
    else:
      return File.parse_permissions_3digit(permissions)

  @staticmethod
  def parse_permissions_3digit(permissions: str) -> int:
    assert match("([r-][w-][x-])", permissions), f"malformed permission string: {permissions}"
    result = 0
    result += 0o444 if permissions[0] == "r" else 0
    result += 0o222 if permissions[1] == "w" else 0
    result += 0o111 if permissions[2] == "x" else 0
    return result

  @staticmethod
  def parse_permissions_9digit(permissions: str) -> int:
    assert match("([r-][w-][x-]){3}", permissions), f"malformed permission string: {permissions}"
    result = 0
    result += 0o400 if permissions[0] == "r" else 0
    result += 0o200 if permissions[1] == "w" else 0
    result += 0o100 if permissions[2] == "x" else 0
    result += 0o040 if permissions[3] == "r" else 0
    result += 0o020 if permissions[4] == "w" else 0
    result += 0o010 if permissions[5] == "x" else 0
    result += 0o004 if permissions[6] == "r" else 0
    result += 0o002 if permissions[7] == "w" else 0
    result += 0o001 if permissions[8] == "x" else 0
    return result

  def download(self, url: str) -> str:
    response = request("GET", url)
    assert response.status == 200
    return response.data.decode("utf-8")

  @classmethod
  def bytes(cls, content: str | bytes) -> bytes:
    if isinstance(content, str):
      return content.encode("utf-8")
    else:
      return content
