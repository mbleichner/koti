from __future__ import annotations

import os
import pwd
import shutil
from hashlib import sha256
from tempfile import NamedTemporaryFile
from typing import Generator, Sequence

from koti import ExecutionPlan
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

  def state_target(self, item: File | Directory, model: ConfigModel, dryrun: bool) -> FileState | DirectoryState:
    if isinstance(item, File):
      return self.file_state_target(item, model)
    else:
      return self.dir_state_target(item, model)

  def state_current(self, item: File | Directory) -> FileState | DirectoryState | None:
    if isinstance(item, File):
      return self.file_state_current(item)
    else:
      return self.dir_state_current(item)

  def plan_install(self, items_to_check: Sequence[File | Directory], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    yield from self.plan_file_install([item for item in items_to_check if isinstance(item, File)], model, dryrun, from_dir_install = False)
    yield from self.plan_dir_install([item for item in items_to_check if isinstance(item, Directory)], model, dryrun)

  def plan_cleanup(self, items_to_keep: Sequence[File | Directory], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    yield from self.plan_file_cleanup([item for item in items_to_keep if isinstance(item, File)], model, dryrun)
    yield from self.plan_dir_cleanup([item for item in items_to_keep if isinstance(item, Directory)], model, dryrun)

  def plan_file_install(self, items_to_check: Sequence[File], model: ConfigModel, dryrun: bool, from_dir_install: bool) -> Generator[ExecutionPlan]:
    for item in items_to_check:
      after_execute = lambda: self.managed_files_store.add(item.filename) if not from_dir_install else None
      current, target = self.states(item, model, dryrun)
      if current == target:
        continue

      assert current is None or isinstance(current, FileState)
      assert target is not None and isinstance(target, FileState)

      if current is None:
        yield ExecutionPlan(
          items = [item],
          description = f"{GREEN}create new file: {item.filename}",
          details = f"uid = {target.uid}, gid = {target.gid}, mode = {oct(target.mode)}",
          actions = [
            lambda: self.update_file(item, target),
            after_execute
          ],
        )

      if current is not None and current.content_hash != target.content_hash:
        with NamedTemporaryFile(prefix = "koti.", delete = False) as tmp:
          tmp.write(target.content)
          os.chown(tmp.name, uid = target.uid, gid = target.gid)
          os.chmod(tmp.name, mode = target.mode)
        yield ExecutionPlan(
          items = [item],
          description = f"{YELLOW}update file content: {item.filename}",
          details = [
            f"filesize {len(current.content)} => {len(target.content)} bytes",
            f"{CYAN}diff '{item.filename}' '{tmp.name}'{ENDC} to preview changes",
          ],
          actions = [
            lambda: self.update_file(item, target),
            after_execute,
          ]
        )

      if current is not None and (current.uid != target.uid or current.gid != target.gid):
        yield ExecutionPlan(
          items = [item],
          description = f"{YELLOW}update file ownership: {item.filename}",
          details = f"uid {current.uid} => {target.uid}, gid {current.gid} => {target.gid}",
          actions = [
            lambda: os.chown(item.filename, uid = target.uid, gid = target.gid),
            after_execute,
          ]
        )

      if current is not None and current.mode != target.mode:
        yield ExecutionPlan(
          items = [item],
          description = f"{YELLOW}update file permissions: {item.filename}",
          details = f"mode {oct(current.mode)} => {oct(target.mode)}",
          actions = [
            lambda: os.chmod(item.filename, mode = target.mode),
            after_execute,
          ]
        )

  def plan_dir_install(self, items_to_check: Sequence[Directory], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    for item in items_to_check:
      current, target = self.states(item, model, dryrun)
      if current == target:
        continue

      assert current is None or isinstance(current, DirectoryState)
      assert target is not None and isinstance(target, DirectoryState)

      # install all files belonging to the directory
      yield from self.plan_file_install(item.files, model, dryrun, from_dir_install = True)

      # remove files that should no longer be present
      files_current = [f"{base}/{subfile}" for base, subdirs, subfiles in os.walk(item.dirname) for subfile in subfiles]
      files_target = [file.filename for file in item.files]
      files_to_remove = [f for f in files_current if f not in files_target]
      if files_to_remove:
        yield ExecutionPlan(
          items = [File(filename) for filename in files_to_remove],
          description = f"{RED}remove orphan file(s)",
          details = "leftover empty directories will also be removed",
          actions = [
            lambda: self.unlink_files(files_to_remove),
            lambda: self.remove_leftover_empty_dirs(item),
          ]
        )

  def plan_file_cleanup(self, items_to_keep: Sequence[File], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    installed_files = self.installed_files()
    for item in installed_files:
      if item in items_to_keep:
        continue
      yield ExecutionPlan(
        items = [item],
        description = f"{RED}delete file: {item.filename}",
        actions = [
          lambda: os.unlink(item.filename),
          lambda: self.managed_files_store.remove(item.filename),
        ]
      )

  def plan_dir_cleanup(self, items_to_keep: Sequence[Directory], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    installed_dirs = self.installed_dirs()
    for item in installed_dirs:
      if item in items_to_keep:
        continue
      yield ExecutionPlan(
        items = [item],
        description = f"{RED}delete directory: {item.dirname}",
        actions = [
          lambda: shutil.rmtree(item.dirname),
          lambda: self.managed_dirs_store.remove(item.dirname),
        ]
      )

  def installed_files(self) -> list[File]:
    filenames = self.managed_files_store.elements()
    return [File(filename) for filename in filenames]

  def installed_dirs(self) -> list[Directory]:
    dirnames = self.managed_dirs_store.elements()
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
