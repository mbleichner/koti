import hashlib
import os
import pwd
from typing import TypedDict

from koti.core import ConfigManager, ConfirmModeValues, ExecutionState, Koti
from koti.items.file import File
from koti.utils.confirm import confirm
from koti.utils.json_store import JsonMapping, JsonStore


class FileStoreEntry(TypedDict):
  confirm_mode: ConfirmModeValues


class FileManager(ConfigManager[File]):
  managed_classes = [File]
  managed_files_store: JsonMapping[str, FileStoreEntry]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/FileManager.json")
    self.managed_files_store = store.mapping("managed_files")

  def check_configuration(self, item: File, core: Koti):
    if item.content is None:
      raise AssertionError("missing either content or content_from_file")

  def create_dir(self, dir: str, item: File):
    if os.path.exists(dir): return
    if not os.path.exists(os.path.dirname(dir)):
      self.create_dir(os.path.dirname(dir), item)
    os.mkdir(dir)
    getpwnam = pwd.getpwnam(item.owner)
    os.chown(dir, uid = getpwnam.pw_uid, gid = getpwnam.pw_gid)

  def execute_phase(self, items: list[File], core: Koti, state: ExecutionState):
    for item in items:
      getpwnam = pwd.getpwnam(item.owner)
      uid = getpwnam.pw_uid
      gid = getpwnam.pw_gid
      hash_before = file_hash(item.identifier)
      mode = item.permissions
      content = item.content

      directory = os.path.dirname(item.identifier)
      self.create_dir(directory, item)

      hash_after = virtual_file_hash(uid, gid, mode, content)
      if hash_before != hash_after:
        confirm(
          message = f"confirm {"changed" if hash_before is not None else "new"} file {item.identifier}",
          destructive = hash_before is not None,
          mode = core.get_confirm_mode_for_item(item),
        )
        state.updated_items += [item]

      with open(item.identifier, 'wb+') as fh:
        fh.write(content)
      os.chown(item.identifier, uid = uid, gid = gid)
      os.chmod(item.identifier, mode)

      new_mode = os.stat(item.identifier).st_mode & 0o777
      if mode != new_mode:
        raise AssertionError("cannot apply file permissions (incompatible file system?)")

      self.managed_files_store.put(item.identifier, {"confirm_mode": core.get_confirm_mode_for_item(item)})

  def cleanup(self, items: list[File], core: Koti, state: ExecutionState):
    currently_managed_files = [item.identifier for item in items]
    previously_managed_files = self.managed_files_store.keys()
    files_to_delete = [file for file in previously_managed_files if file not in currently_managed_files]
    for file in files_to_delete:
      if os.path.isfile(file):
        confirm(
          message = f"confirm to delete file: {file}",
          destructive = True,
          mode = self.managed_files_store.get(file, {}).get("confirm_mode", core.default_confirm_mode),
        )
        os.unlink(file)
      self.managed_files_store.remove(file)


def file_hash(filename) -> str | None:
  if not os.path.isfile(filename):
    return None
  stat = os.stat(filename)
  sha256_hash = hashlib.sha256()
  sha256_hash.update(str(stat.st_uid).encode())
  sha256_hash.update(str(stat.st_gid).encode())
  sha256_hash.update(str(stat.st_mode & 0o777).encode())
  with open(filename, "rb") as f:
    for byte_block in iter(lambda: f.read(4096), b""):
      sha256_hash.update(byte_block)
  return sha256_hash.hexdigest()


def virtual_file_hash(uid, gid, mode, content):
  sha256_hash = hashlib.sha256()
  sha256_hash.update(str(uid).encode())
  sha256_hash.update(str(gid).encode())
  sha256_hash.update(str(mode & 0o777).encode())
  sha256_hash.update(content)
  return sha256_hash.hexdigest()
