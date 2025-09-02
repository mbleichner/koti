from __future__ import annotations

import os
import pwd
import shutil
from hashlib import sha256
from tempfile import NamedTemporaryFile
from typing import Sequence

from koti import ConfigItemToInstall, ConfigItemToUninstall, ExecutionPlan
from koti.utils.colors import *
from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.file import File
from koti.items.directory import Directory
from koti.utils.json_store import JsonCollection, JsonStore
from koti.utils.managers import GenericExecutionPlan


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
  def __init__(self, files: dict[str, FileState]):
    self.files = files

  def hash(self) -> str:
    sha256_hash = sha256()
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

  def plan_install(self, items: list[ConfigItemToInstall[File | Directory, FileState | DirectoryState]]) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []
    for item, current, target in items:
      if isinstance(item, File) and isinstance(target, FileState) and (current is None or isinstance(current, FileState)):
        result.extend(self.plan_file_install(item, current, target, from_dir_install = False))
    for item, current, target in items:
      if isinstance(item, Directory) and isinstance(target, DirectoryState) and (current is None or isinstance(current, DirectoryState)):
        result.extend(self.plan_dir_install(item, current, target))
    return result

  def plan_uninstall(self, items: list[ConfigItemToUninstall[File | Directory, FileState | DirectoryState]]) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []
    for item, current in items:
      if isinstance(item, File) and isinstance(current, FileState):
        result.extend(self.plan_file_uninstall(item, current))
    for item, current in items:
      if isinstance(item, Directory) and isinstance(current, DirectoryState):
        result.extend(self.plan_dir_uninstall(item, current))
    return result

  def plan_file_install(self, item: File, current: FileState | None, target: FileState, from_dir_install: bool) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []

    after_execute = (lambda: self.managed_files_store.add(item.filename)) if not from_dir_install else None

    if current is None:
      result.append(GenericExecutionPlan(
        items = [item],
        executable = lambda: self.update_file(item, target),
        description = f"{GREEN}creating new file",
        details = f"uid = {target.uid}, gid = {target.gid}, mode = {oct(target.mode)}",
        after_execute = after_execute,
      ))

    if current is not None and current.content_hash != target.content_hash:
      with NamedTemporaryFile(prefix = "koti.", delete = False) as tmp:
        tmp.write(target.content)
      result.append(GenericExecutionPlan(
        items = [item],
        executable = lambda: self.update_file(item, target),
        description = f"{YELLOW}updating file content",
        details = f"preview changes: {CYAN}sudo diff '{item.filename}' '{tmp.name}'",
        after_execute = after_execute,
      ))

    if current is not None and (current.uid != target.uid or current.gid != target.gid):
      result.append(GenericExecutionPlan(
        items = [item],
        executable = lambda: os.chown(item.filename, uid = target.uid, gid = target.gid),
        description = f"{YELLOW}updating file ownership",
        details = f"uid {current.uid} => {target.uid}, gid {current.gid} => {target.gid}",
        after_execute = after_execute,
      ))

    if current is not None and current.mode != target.mode:
      result.append(GenericExecutionPlan(
        items = [item],
        executable = lambda: os.chmod(item.filename, mode = target.mode),
        description = f"{YELLOW}updating file permissions",
        details = f"{oct(current.mode)} => {oct(target.mode)}",
        after_execute = after_execute,
      ))

    return result

  def plan_dir_install(self, item: Directory, current: DirectoryState | None, target: DirectoryState) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []

    for file in item.files:
      file_target = target.files[file.filename]
      file_current = self.file_state_current(file)
      result.extend(self.plan_file_install(file, file_current, file_target, from_dir_install = True))

    # remove files that should no longer be present
    files_current = [f"{base}/{subfile}" for base, subdirs, subfiles in os.walk(item.dirname) for subfile in subfiles]
    files_target = [file.filename for file in item.files]
    files_to_remove = [f for f in files_current if f not in files_target]
    if files_to_remove:
      result.append(GenericExecutionPlan(
        items = [File(filename) for filename in files_to_remove],
        description = f"{RED}remove orphan file(s)",
        executable = lambda: self.unlink_files(files_to_remove),
        after_execute = lambda: self.remove_leftover_empty_dirs(item),
        details = "leftover empty directories will be removed",
      ))

    return result

  def plan_file_uninstall(self, item: File, current: FileState) -> Sequence[ExecutionPlan]:
    return [GenericExecutionPlan(
      items = [item],
      executable = lambda: os.unlink(item.filename),
      description = f"{RED}deleting file",
      after_execute = lambda: self.managed_files_store.remove(item.filename),
    )]

  def plan_dir_uninstall(self, item: Directory, current: DirectoryState) -> Sequence[ExecutionPlan]:
    return [GenericExecutionPlan(
      items = [item],
      executable = lambda: shutil.rmtree(item.dirname),
      description = f"{RED}deleting directory",
      after_execute = lambda: self.managed_dirs_store.remove(item.dirname),
    )]

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

  def unlink_files(self, filenames: list[str]):
    for filename in filenames:
      os.unlink(filename)

  def remove_leftover_empty_dirs(self, item: Directory):
    # remove empty dirs (repeatedly, since they may be nested)
    while True:
      empty_dir = next((
        f"{base}/{subdir}" for base, subdirs, subfiles in os.walk(item.dirname) for subdir in subdirs
        if len(os.listdir(f"{base}/{subdir}")) == 0
      ), None)
      if empty_dir is None:
        break
      os.rmdir(empty_dir)

  def update_file(self, item: File, target: FileState):
    assert item.content is not None
    uid = target.uid
    gid = target.gid
    mode = target.mode
    content = target.content
    self.mkdirs(os.path.dirname(item.filename), item.owner)
    with open(item.filename, 'wb+') as fh:
      fh.write(content)  # type: ignore
    os.chown(item.filename, uid = uid, gid = gid)
    os.chmod(item.filename, mode)
    assert mode == (os.stat(item.filename).st_mode & 0o777), "cannot apply file permissions (incompatible file system?)"

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
    return DirectoryState(file_states)

  def dir_state_target(self, item: Directory, model: ConfigModel) -> DirectoryState:
    file_states = dict((file.filename, self.file_state_target(file, model)) for file in item.files)
    return DirectoryState(file_states)

  def mkdirs(self, dirname: str, owner: str):
    if os.path.exists(dirname): return
    if not os.path.exists(os.path.dirname(dirname)):
      self.mkdirs(os.path.dirname(dirname), owner)
    os.mkdir(dirname)
    getpwnam = pwd.getpwnam(owner)
    os.chown(dirname, uid = getpwnam.pw_uid, gid = getpwnam.pw_gid)

  def finalize(self, model: ConfigModel):
    filenames = [item.filename for phase in model.phases for item in phase.items if isinstance(item, File)]
    dirnames = [item.dirname for phase in model.phases for item in phase.items if isinstance(item, Directory)]
    self.managed_files_store.replace_all(filenames)
    self.managed_dirs_store.replace_all(dirnames)
