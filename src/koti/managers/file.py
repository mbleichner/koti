from __future__ import annotations

import os
import pwd
import shutil
from hashlib import sha256
from typing import cast

from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.file import File
from koti.items.directory import Directory
from koti.utils import JsonCollection
from koti.utils.json_store import JsonStore


class FileState(ConfigItemState):
  def __init__(self, content_hash: str, uid: int, gid: int, mode: int):
    self.content_hash = content_hash
    self.uid = uid
    self.gid = gid
    self.mode = mode

  def hash(self) -> str:
    sha256_hash = sha256()
    sha256_hash.update(str(self.uid).encode())
    sha256_hash.update(str(self.gid).encode())
    sha256_hash.update(str(self.mode & 0o777).encode())
    sha256_hash.update(self.content_hash.encode())
    return sha256_hash.hexdigest()


class DirectoryState(ConfigItemState):
  def __init__(self, uid: int, gid: int, files: dict[str, FileState]):
    self.uid = uid
    self.gid = gid
    self.files = files

  def hash(self) -> str:
    sha256_hash = sha256()
    sha256_hash.update(str(self.uid).encode())
    sha256_hash.update(str(self.gid).encode())
    for filename in sorted(self.files.keys()):
      file_state = self.files[filename]
      sha256_hash.update(file_state.hash().encode())
    return sha256_hash.hexdigest()


class FileManager(ConfigManager[File | Directory, FileState | DirectoryState]):
  managed_classes = [File, Directory]
  managed_files_store: JsonCollection[str]
  managed_dirs_store: JsonCollection[str]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/FileManager.json")
    self.managed_files_store = store.collection("managed_files")
    self.managed_dirs_store = store.collection("managed_dirs")

  def check_configuration(self, item: File | Directory, model: ConfigModel):
    if isinstance(item, File):
      assert item.content is not None, "missing either content or content_from_file"
    if isinstance(item, Directory):
      assert len(item.files) > 0, "directory contains no files"

  def installed(self, model: ConfigModel) -> list[File | Directory]:
    return [*self.installed_files(model), *self.installed_dirs(model)]

  def state_target(self, item: File | Directory, model: ConfigModel, planning: bool) -> FileState | DirectoryState:
    if isinstance(item, File):
      return self.file_state_target(item, model)
    else:
      return self.dir_state_target(item, model)

  def state_current(self, item: File | Directory) -> FileState | DirectoryState | None:
    if isinstance(item, File):
      return self.file_state_current(item)
    else:
      return self.dir_state_current(item)

  def describe_change(self, item: File | Directory, state_current: ConfigItemState | None, state_target: ConfigItemState) -> list[str]:
    if isinstance(item, File):
      return self.describe_file_change(item, state_current, state_target)
    else:
      return self.describe_dir_change(item, state_current, state_target)

  def install(self, items: list[File | Directory], model: ConfigModel):
    for item in items:
      if isinstance(item, File):
        self.install_file(item, model)
      if isinstance(item, Directory):
        self.install_dir(item, model)

  def uninstall(self, items: list[File | Directory], model: ConfigModel):
    for item in items:
      if isinstance(item, File):
        self.uninstall_file(item, model)
      if isinstance(item, Directory):
        self.uninstall_dir(item, model)

  def installed_files(self, model: ConfigModel) -> list[File]:
    filenames = {
      *self.managed_files_store.elements(),
      *(item.filename for phase in model.phases for item in phase.items if isinstance(item, File))
    }
    return [File(filename) for filename in filenames if os.path.isfile(filename)]

  def installed_dirs(self, model: ConfigModel) -> list[Directory]:
    dirnames = {
      *self.managed_dirs_store.elements(),
      *(item.dirname for phase in model.phases for item in phase.items if isinstance(item, Directory))
    }
    return [Directory(dirname) for dirname in dirnames if os.path.isdir(dirname)]

  def install_file(self, item: File, model: ConfigModel):
    self.update_file(item, model)
    self.managed_files_store.add(item.filename)

  def install_dir(self, item: Directory, model: ConfigModel):
    # install all files in their current version
    for file in item.files:
      self.update_file(file, model)

    # remove files that should no longer be present
    files_current = [f"{base}/{subfile}" for base, subdirs, subfiles in os.walk(item.dirname) for subfile in subfiles]
    files_target = [file.filename for file in item.files]
    files_to_remove = [f for f in files_current if f not in files_target]
    for filename in files_to_remove:
      os.unlink(filename)

    # remove empty dirs (repeatedly, since they may be nested)
    while True:
      empty_dir = next((
        f"{base}/{subdir}" for base, subdirs, subfiles in os.walk(item.dirname) for subdir in subdirs
        if len(os.listdir(f"{base}/{subdir}")) == 0
      ), None)
      if empty_dir is None:
        break
      os.rmdir(empty_dir)

    self.managed_dirs_store.add(item.dirname)

  def update_file(self, item: File, model: ConfigModel):
    assert item.content is not None
    getpwnam = pwd.getpwnam(item.owner)
    uid = getpwnam.pw_uid
    gid = getpwnam.pw_gid
    mode = item.permissions
    content = item.content(model)
    self.mkdirs(os.path.dirname(item.filename), item.owner)
    with open(item.filename, 'wb+') as fh:
      fh.write(content)  # type: ignore
    os.chown(item.filename, uid = uid, gid = gid)
    os.chmod(item.filename, mode)
    assert mode == (os.stat(item.filename).st_mode & 0o777), "cannot apply file permissions (incompatible file system?)"

  def uninstall_file(self, item: File, model: ConfigModel):
    if os.path.isfile(item.filename):
      os.unlink(item.filename)
    self.managed_files_store.remove(item.filename)

  def uninstall_dir(self, item: Directory, model: ConfigModel):
    if os.path.isdir(item.dirname):
      shutil.rmtree(item.dirname)
    self.managed_dirs_store.remove(item.dirname)

  def file_state_current(self, item: File) -> FileState | None:
    if not os.path.isfile(item.filename):
      return None
    sha256_hash = sha256()
    with open(item.filename, "rb") as f:
      for byte_block in iter(lambda: f.read(4096), b""):
        sha256_hash.update(byte_block)
    stat = os.stat(item.filename)
    return FileState(
      content_hash = sha256_hash.hexdigest(),
      uid = stat.st_uid,
      gid = stat.st_gid,
      mode = stat.st_mode & 0o777,
    )

  def file_state_target(self, item: File, model: ConfigModel) -> FileState:
    if item.content is None:
      raise AssertionError(f"{item.description()}: content missing")
    getpwnam = pwd.getpwnam(item.owner)
    sha256_hash = sha256()
    sha256_hash.update(item.content(model))
    return FileState(
      content_hash = sha256_hash.hexdigest(),
      uid = getpwnam.pw_uid,
      gid = getpwnam.pw_gid,
      mode = item.permissions & 0o777,
    )

  def dir_state_current(self, item: Directory) -> DirectoryState | None:
    if not os.path.isdir(item.dirname):
      return None
    stat = os.stat(item.dirname)
    files: dict[str, FileState] = {}
    for file in item.files:
      state = self.file_state_current(file)
      if state is not None:
        files[file.filename] = state
    return DirectoryState(
      uid = stat.st_uid,
      gid = stat.st_gid,
      files = files,
    )

  def dir_state_target(self, item: Directory, model: ConfigModel) -> DirectoryState:
    getpwnam = pwd.getpwnam(item.owner)
    return DirectoryState(
      uid = getpwnam.pw_uid,
      gid = getpwnam.pw_gid,
      files = dict(
        (file.filename, self.file_state_target(file, model))
        for file in item.files
      ),
    )

  def mkdirs(self, dirname: str, owner: str):
    if os.path.exists(dirname): return
    if not os.path.exists(os.path.dirname(dirname)):
      self.mkdirs(os.path.dirname(dirname), owner)
    os.mkdir(dirname)
    getpwnam = pwd.getpwnam(owner)
    os.chown(dirname, uid = getpwnam.pw_uid, gid = getpwnam.pw_gid)

  def describe_file_change(self, item: File, state_current: ConfigItemState | None, state_target: ConfigItemState) -> list[str]:
    state_current = cast(FileState | None, state_current)
    state_target = cast(FileState, state_target)
    if state_current is None:
      return ["file will be created"]
    return [change for change in [
      f"change uid from {state_current.uid} to {state_target.uid}" if state_current.uid != state_current.uid else None,
      f"change gid from {state_current.gid} to {state_target.gid}" if state_current.gid != state_current.gid else None,
      f"change mode from {oct(state_current.mode)} to {oct(state_target.mode)}" if state_current.mode != state_current.mode else None,
      f"update file content" if state_current.content_hash != state_current.content_hash else None,
    ] if change is not None]

  def describe_dir_change(self, item: Directory, state_current: ConfigItemState | None, state_target: ConfigItemState) -> list[str]:
    state_current = cast(DirectoryState | None, state_current)
    state_target = cast(DirectoryState, state_target)
    if state_current is None:
      return ["directory will be created"]
    return [change for change in [
      f"change uid from {state_current.uid} to {state_target.uid}" if state_current.uid != state_current.uid else None,
      f"change gid from {state_current.gid} to {state_target.gid}" if state_current.gid != state_current.gid else None,
      *(
        f"{file.filename}: {change}" for file in item.files
        for change in self.describe_change(file, state_current.files.get(file.filename, None), state_target.files[file.filename])
      )
    ] if change is not None]
