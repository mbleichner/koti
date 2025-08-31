from __future__ import annotations

import os
import pwd
import shutil
from hashlib import sha256
from tempfile import NamedTemporaryFile
from typing import cast

from koti.utils.colors import *
from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.file import File
from koti.items.directory import Directory
from koti.utils.json_store import JsonCollection, JsonStore


class FileState(ConfigItemState):
  def __init__(self, content: bytes, uid: int, gid: int, mode: int):
    self.content = content
    self.uid = uid
    self.gid = gid
    self.mode = mode
    sha256_hash = sha256()
    sha256_hash.update(content)
    self.content_hash = sha256_hash.hexdigest()

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

  def assert_installable(self, item: File | Directory, model: ConfigModel):
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

  def diff(self, current: FileState | DirectoryState | None, target: FileState | DirectoryState | None) -> list[str]:
    if isinstance(current, FileState) or isinstance(target, FileState):
      current = cast(FileState | None, current)
      target = cast(FileState, target)
      return self.file_diff(current, target)
    else:
      current = cast(DirectoryState | None, current)
      target = cast(DirectoryState | None, target)
      return self.dir_diff(current, target)

  def install(self, items: list[File | Directory], model: ConfigModel):
    for item in items:
      if isinstance(item, File):
        self.install_file(item, model)
      if isinstance(item, Directory):
        self.install_dir(item, model)

  def uninstall(self, items: list[File | Directory]):
    for item in items:
      if isinstance(item, File):
        self.uninstall_file(item)
      if isinstance(item, Directory):
        self.uninstall_dir(item)

  def installed_files(self, model: ConfigModel) -> list[File]:
    filenames = {
      *self.managed_files_store.elements(),
      *(item.filename for phase in model.phases for item in phase.items if isinstance(item, File))
    }
    return [File(filename) for filename in filenames]

  def installed_dirs(self, model: ConfigModel) -> list[Directory]:
    dirnames = {
      *self.managed_dirs_store.elements(),
      *(item.dirname for phase in model.phases for item in phase.items if isinstance(item, Directory))
    }
    return [Directory(dirname) for dirname in dirnames]

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

  def uninstall_file(self, item: File):
    if os.path.isfile(item.filename):
      os.unlink(item.filename)
    self.managed_files_store.remove(item.filename)

  def uninstall_dir(self, item: Directory):
    if os.path.isdir(item.dirname):
      shutil.rmtree(item.dirname)
    self.managed_dirs_store.remove(item.dirname)

  def file_state_current(self, item: File) -> FileState | None:
    if not os.path.isfile(item.filename):
      return None
    with open(item.filename, "rb") as f:
      content = f.read()
    stat = os.stat(item.filename)
    return FileState(
      content = content,
      uid = stat.st_uid,
      gid = stat.st_gid,
      mode = stat.st_mode & 0o777,
    )

  def file_state_target(self, item: File, model: ConfigModel) -> FileState:
    if item.content is None:
      raise AssertionError(f"{item.description()}: content missing")
    getpwnam = pwd.getpwnam(item.owner)
    return FileState(
      content = item.content(model),
      uid = getpwnam.pw_uid,
      gid = getpwnam.pw_gid,
      mode = item.permissions & 0o777,
    )

  def dir_state_current(self, item: Directory) -> DirectoryState | None:
    if not os.path.isdir(item.dirname):
      return None

    file_states: dict[str, FileState] = {}
    files_current = [f"{base}/{subfile}" for base, subdirs, subfiles in os.walk(item.dirname) for subfile in subfiles]
    for filename in files_current:
      file_state = self.file_state_current(File(filename))
      if file_state is not None:
        file_states[filename] = file_state

    stat = os.stat(item.dirname)
    return DirectoryState(
      uid = stat.st_uid,
      gid = stat.st_gid,
      files = file_states,
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

  def file_diff(self, current: FileState | None, target: FileState | None) -> list[str]:
    if current is None:
      return [f"{GREEN}file will be created"]
    if target is None:
      return [f"{RED}file will be deleted"]
    result = [change for change in [
      f"{YELLOW}change uid from {current.uid} to {target.uid}" if current.uid != target.uid else None,
      f"{YELLOW}change gid from {current.gid} to {target.gid}" if current.gid != target.gid else None,
      f"{YELLOW}change mode from {oct(current.mode)} to {oct(target.mode)}" if current.mode != target.mode else None,
    ] if change is not None]
    if current.content_hash != target.content_hash:
      with NamedTemporaryFile(prefix = "koti.", delete = False) as tmp:
        tmp.write(target.content)
      result.append(f"{YELLOW}file content changed{ENDC} - preview new content in {tmp.name}")
    return result

  def dir_diff(self, current: DirectoryState | None, target: DirectoryState | None) -> list[str]:
    if current is None:
      return [f"{GREEN}directory will be created"]
    if target is None:
      return [f"{RED}directory will be deleted"]
    filenames = set(current.files.keys()).union(target.files.keys())
    return [change for change in [
      f"{YELLOW}change uid from {current.uid} to {target.uid}" if current.uid != target.uid else None,
      f"{YELLOW}change gid from {current.gid} to {target.gid}" if current.gid != target.gid else None,
      *(
        f"{YELLOW}{filename}: {change}" for filename in filenames
        for change in self.diff(current.files.get(filename, None), target.files.get(filename, None))
      )
    ] if change is not None]

  def finalize(self, model: ConfigModel):
    filenames = [item.filename for phase in model.phases for item in phase.items if isinstance(item, File)]
    dirnames = [item.dirname for phase in model.phases for item in phase.items if isinstance(item, Directory)]
    self.managed_files_store.replace_all(filenames)
    self.managed_dirs_store.replace_all(dirnames)
