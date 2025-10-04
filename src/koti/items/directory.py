from __future__ import annotations

import os
from typing import Iterable
from zipfile import ZipFile

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
    mask: int | str = 0o755,
    owner: str = "root",
    tags: Iterable[str] | None = None,
  ):
    self.dirname = dirname.removesuffix("/")
    self.source = source.removesuffix("/") if source is not None else None
    self.owner = owner
    self.mask = mask
    self.tags = set(tags or [])

  def files(self) -> list[File]:
    assert self.source is not None
    source = self.source
    numeric_mask = File.parse_permissions(self.mask) if isinstance(self.mask, str) else self.mask
    if os.path.isfile(self.source) and self.source.endswith(".zip"):
      result: list[File] = []
      with ZipFile(self.source, "r") as zip:
        for entry in zip.namelist():
          result.append(self.file_from_zip_entry(dirname = self.dirname, zipfile = self.source, entry = entry, mask = numeric_mask))
      return result
    elif os.path.isdir(self.source):
      return [
        self.file_from_directory(source_basedir = self.source, source_subdir = base, source_file = subfile, mask = numeric_mask)
        for base, subdirs, subfiles in os.walk(self.source) for subfile in subfiles
      ]
    else:
      raise AssertionError(f"{self}: source is not a directory or zipfile")

  def file_from_directory(self, source_basedir: str, source_subdir: str, source_file: str, mask: int) -> File:
    return File(
      filename = "/".join([part for part in (self.dirname, source_subdir.removeprefix(source_basedir).removeprefix("/"), source_file) if part]),
      permissions = os.stat(f"{source_subdir}/{source_file}").st_mode & 0xfff & mask,
      source = f"{source_subdir}/{source_file}",
    )

  @classmethod
  def file_from_zip_entry(cls, dirname: str, zipfile: str, entry: str, mask: int) -> File:
    # !!! this function is necessary to bind the correct value of "entry" in the lambda !!!
    return File(
      filename = dirname + "/" + entry,
      permissions = 0xfff & mask,
      content = lambda model: cls.read_zip_entry(zipfile, entry),
    )

  @classmethod
  def read_zip_entry(cls, zipfile: str, entry: str) -> bytes:
    with ZipFile(zipfile, "r") as zip:
      return zip.read(entry)

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
