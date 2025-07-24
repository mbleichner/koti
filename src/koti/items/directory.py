from __future__ import annotations

import os

from koti.items.file import File
from koti import ConfigItem, ConfirmMode, ManagedConfigItem


class Directory(ManagedConfigItem):
  files: list[File]
  owner: str = "root"
  dirname: str

  def __init__(
    self,
    dirname: str,
    source: str | None = None,
    mask: int | str = "rwx",
    owner: str = "root",
    confirm_mode: ConfirmMode | None = None,
  ):
    dirname = dirname.removesuffix("/")
    self.dirname = dirname

    numeric_mask: int
    if isinstance(mask, str):
      numeric_mask = File.parse_permissions(mask)
    elif isinstance(mask, int):
      numeric_mask = mask
    else:
      numeric_mask = 0xfff

    if source is not None:
      source = source.removesuffix("/")
      self.files = [
        File(
          filename = "/".join([part for part in (dirname, base.removeprefix(source).removeprefix("/"), subfile) if part]),
          permissions = os.stat(f"{base}/{subfile}").st_mode & 0xfff & numeric_mask,
          source = f"{base}/{subfile}",
        )
        for base, subdirs, subfiles in os.walk(source) for subfile in subfiles
      ]
    else:
      self.files = []

    self.owner = owner
    self.confirm_mode = confirm_mode

  def identifier(self):
    return f"Directory('{self.dirname}')"

  def merge(self, other: ConfigItem):
    assert isinstance(other, Directory)
    raise AssertionError(f"Directory('{self.dirname}') may not be declared twice")
