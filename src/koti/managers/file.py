from __future__ import annotations

import os
import pwd
import shutil
from hashlib import sha256
from pwd import getpwnam, getpwuid
from typing import Generator, Sequence

from koti.model import Action, ConfigItemState, ConfigManager, ConfigModel
from koti.items.file import File
from koti.items.directory import Directory
from koti.utils.json_store import JsonCollection, JsonStore


class FileState(ConfigItemState):
  def __init__(self, content: bytes, owner: str, mode: int):
    self.content = content
    self.owner = owner
    self.mode = mode
    sha256_hash = sha256()
    sha256_hash.update(content)
    self.content_hash = sha256_hash.hexdigest()

  def sha256(self) -> str:
    sha256_hash = sha256()
    sha256_hash.update(self.owner.encode())
    sha256_hash.update(str(self.mode & 0o777).encode())
    sha256_hash.update(self.content_hash.encode())
    return sha256_hash.hexdigest()


class DirectoryState(ConfigItemState):
  def __init__(self, files: dict[str, FileState]):
    self.files = files

  def sha256(self) -> str:
    sha256_hash = sha256()
    for filename in sorted(self.files.keys()):
      file_state = self.files[filename]
      sha256_hash.update(file_state.sha256().encode())
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

  def installed_files(self) -> list[File]:
    filenames = self.managed_files_store.elements()
    return [File(filename) for filename in filenames]

  def installed_dirs(self) -> list[Directory]:
    dirnames = self.managed_dirs_store.elements()
    return [Directory(dirname) for dirname in dirnames]

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

  def plan_install(self, items_to_check: Sequence[File | Directory], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    yield from self.plan_file_install([item for item in items_to_check if isinstance(item, File)], model, dryrun, register_file = True)
    yield from self.plan_dir_install([item for item in items_to_check if isinstance(item, Directory)], model, dryrun)

  def plan_cleanup(self, items_to_keep: Sequence[File | Directory], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    yield from self.plan_file_cleanup([item for item in items_to_keep if isinstance(item, File)], model, dryrun)
    yield from self.plan_dir_cleanup([item for item in items_to_keep if isinstance(item, Directory)], model, dryrun)

  def plan_file_install(self, items_to_check: Sequence[File], model: ConfigModel, dryrun: bool, register_file: bool) -> Generator[Action]:
    for item in items_to_check:
      current, target = self.states(item, model, dryrun)
      if current == target:
        continue

      assert current is None or isinstance(current, FileState)
      assert target is not None and isinstance(target, FileState)

      if current is None:
        yield Action(
          installs = [item],
          description = f"create new file: {item.filename}",
          additional_info = f"owner = {target.owner}, mode = {oct(target.mode)}",
          execute = lambda: self.create_or_update_file(item, target, register_file),
        )

      if current is not None and current.content_hash != target.content_hash:
        tmpfile = f"/tmp/koti.{target.sha256()[:8]}"
        if os.path.exists(tmpfile):
          os.unlink(tmpfile)
        with open(tmpfile, "wb+") as fh:
          fh.write(target.content)
          pwnam = getpwnam(target.owner)
          os.chown(fh.name, uid = pwnam.pw_uid, gid = pwnam.pw_gid)
          os.chmod(fh.name, mode = target.mode)
        yield Action(
          updates = [item],
          description = f"update file content: {item.filename}",
          additional_info = [
            f"filesize {len(current.content)} => {len(target.content)} bytes",
            f"preview changes: diff '{item.filename}' '{tmpfile}'",
          ],
          execute = lambda: self.create_or_update_file(item, target, register_file),
        )

      # FIXME: zusammenlegen
      if current is not None and current.owner != target.owner:
        yield Action(
          updates = [item],
          description = f"update file ownership: {item.filename}",
          additional_info = f"owner {current.owner} => {target.owner}",
          execute = lambda: self.fix_file_owner(item, target, register_file),
        )

      # FIXME: zusammenlegen
      if current is not None and current.mode != target.mode:
        yield Action(
          updates = [item],
          description = f"update file permissions: {item.filename}",
          additional_info = f"mode {oct(current.mode)} => {oct(target.mode)}",
          execute = lambda: self.fix_file_mode(item, target, register_file),
        )

  def plan_dir_install(self, items_to_check: Sequence[Directory], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    for item in items_to_check:
      current, target = self.states(item, model, dryrun)
      if current == target:
        continue

      assert current is None or isinstance(current, DirectoryState)
      assert target is not None and isinstance(target, DirectoryState)

      # install all files belonging to the directory
      yield from self.plan_file_install(item.files, model, dryrun, register_file = False)

      # remove files that should no longer be present
      files_current = [f"{base}/{subfile}" for base, subdirs, subfiles in os.walk(item.dirname) for subfile in subfiles]
      files_target = [file.filename for file in item.files]
      files_to_remove = [f for f in files_current if f not in files_target]
      for filename in files_to_remove:
        orphan_file = File(filename)
        yield Action(
          removes = [orphan_file],
          updates = [item],
          description = f"remove orphan file {filename}",
          additional_info = "leftover empty directories will also be removed",
          execute = lambda: self.remove_orphaned_file_and_clean_leftover_dirs(orphan_file, item),
        )

  def remove_orphaned_file_and_clean_leftover_dirs(self, file: File, directory: Directory):
    os.unlink(file.filename)
    print(f"file {file.filename} deleted")

    # remove empty dirs (repeatedly, since they may be nested)
    while True:
      empty_dir = next((
        f"{base}/{subdir}" for base, subdirs, subfiles in os.walk(directory.dirname) for subdir in subdirs
        if len(os.listdir(f"{base}/{subdir}")) == 0
      ), None)
      if empty_dir is None:
        break
      os.rmdir(empty_dir)
      print(f"leftover directory {empty_dir} removed")

  def plan_file_cleanup(self, items_to_keep: Sequence[File], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    installed_files = self.installed_files()
    for item in installed_files:
      if item in items_to_keep:
        continue
      yield Action(
        removes = [item],
        description = f"delete file: {item.filename}",
        execute = lambda: self.delete_file(item)
      )

  def delete_file(self, item: File):
    os.unlink(item.filename)
    self.managed_files_store.remove(item.filename)
    print(f"file {item.filename} deleted")

  def plan_dir_cleanup(self, items_to_keep: Sequence[Directory], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    installed_dirs = self.installed_dirs()
    for item in installed_dirs:
      if item in items_to_keep:
        continue
      yield Action(
        removes = [item],
        description = f"delete directory: {item.dirname}",
        execute = lambda: self.delete_dir(item),
      )

  def delete_dir(self, item: Directory):
    shutil.rmtree(item.dirname)
    self.managed_dirs_store.remove(item.dirname),
    print(f"directory {item.dirname} deleted")

  def create_or_update_file(self, item: File, target: FileState, register_file: bool):
    assert item.content is not None
    pwnam = getpwnam(target.owner)
    mode = target.mode
    content = target.content
    self.mkdirs(os.path.dirname(item.filename), item.owner)
    with open(item.filename, 'wb+') as fh:
      fh.write(content)  # type: ignore
    os.chown(item.filename, uid = pwnam.pw_uid, gid = pwnam.pw_gid)
    os.chmod(item.filename, mode)
    assert mode == (os.stat(item.filename).st_mode & 0o777), "cannot apply file permissions (incompatible file system?)"
    if register_file:
      self.managed_files_store.add(item.filename)
    print(f"file {item.filename} successfully created/updated")

  def fix_file_owner(self, item: File, target: FileState, register_file: bool):
    pwnam = getpwnam(target.owner)
    os.chown(item.filename, uid = pwnam.pw_uid, gid = pwnam.pw_gid)
    if register_file:
      self.managed_files_store.add(item.filename)
    print(f"file owner of {item.filename} successfully updated")

  def fix_file_mode(self, item: File, target: FileState, register_file: bool):
    os.chmod(item.filename, mode = target.mode)
    if register_file:
      self.managed_files_store.add(item.filename)
    print(f"permissions of {item.filename} successfully updated")

  def file_state_current(self, item: File) -> FileState | None:
    if not os.path.isfile(item.filename):
      return None
    with open(item.filename, "rb") as f:
      content = f.read()
    stat = os.stat(item.filename)
    return FileState(
      content = content,
      owner = getpwuid(stat.st_uid).pw_name,
      mode = stat.st_mode & 0o777,
    )

  def file_state_target(self, item: File, model: ConfigModel) -> FileState:
    assert item.content is not None
    return FileState(
      content = item.content(model),
      owner = item.owner,
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

  def finalize(self, model: ConfigModel, dryrun: bool):
    if not dryrun:
      self.managed_files_store.replace_all([item.filename for phase in model.phases for item in phase.items if isinstance(item, File)])
      self.managed_dirs_store.replace_all([item.dirname for phase in model.phases for item in phase.items if isinstance(item, Directory)])
