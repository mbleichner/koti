from __future__ import annotations

import os
from typing import Iterable

from koti.items.file import File
from koti.model import ConfigItem, ManagedConfigItem


class Directory(ManagedConfigItem):
  dirname: str
  source: str | None
  mask: int | str
  owner: str = "root"

  def __init__(
    self,
    dirname: str,
    source: str | None = None,
    mask: int | str = "rwx",
    owner: str = "root",
    tags: Iterable[str] | None = None,
  ):
    self.dirname = dirname.removesuffix("/")
    self.source = source
    self.owner = owner
    self.mask = mask
    self.tags = set(tags or [])

  def files(self) -> list[File]:
    assert self.source is not None
    numeric_mask = File.parse_permissions(self.mask) if isinstance(self.mask, str) else self.mask
    source = self.source.removesuffix("/")
    return [
      File(
        filename = "/".join([part for part in (self.dirname, base.removeprefix(source).removeprefix("/"), subfile) if part]),
        permissions = os.stat(f"{base}/{subfile}").st_mode & 0xfff & numeric_mask,
        source = f"{base}/{subfile}",
      )
      for base, subdirs, subfiles in os.walk(source) for subfile in subfiles
    ]

  def __str__(self) -> str:
    return f"Directory('{self.dirname}')"

  def merge(self, other: ConfigItem) -> Directory:
    assert isinstance(other, Directory) and self == other
    if self.source is not None and other.source is not None:
      assert self.source == other.source, f"{self} has conflicting source parameter"
    assert self.owner == other.owner, f"{self} has conflicting owner parameter"
    assert self.mask == other.mask, f"{self} has conflicting mask parameter"
    return Directory(
      dirname = self.dirname,
      source = self.source or other.source,
      owner = self.owner,
      mask = self.mask,
      tags = self.tags.union(other.tags),
    )
