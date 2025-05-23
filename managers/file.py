import hashlib
import os
import pwd
from pathlib import Path
from typing import TypedDict

from items.file import File
from utils.confirm import confirm, get_confirm_mode
from core import ArchUpdate, ConfigManager, ConfirmModeValues, ExecutionState
from utils.json_store import JsonMapping, JsonStore


class FileStoreEntry(TypedDict):
  confirm_mode: ConfirmModeValues


class FileManager(ConfigManager[File]):
  managed_classes = [File]
  managed_files_store: JsonMapping[str, FileStoreEntry]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/arch-config/FileManager.json")
    self.managed_files_store = store.mapping("managed_files")

  def check_configuration(self, item: File, core: ArchUpdate) -> str | None:
    if item.content is None:
      return "File() needs to define either content or content_from_file"

  def execute_phase(self, items: list[File], core: ArchUpdate, state: ExecutionState) -> list[File]:
    changed_items: list[File] = []
    for item in items:
      directory = os.path.dirname(item.identifier)
      Path(directory).mkdir(parents = True, exist_ok = True)

      getpwnam = pwd.getpwnam(item.owner)
      uid = getpwnam.pw_uid
      gid = getpwnam.pw_gid
      hash_before = file_hash(item.identifier)
      mode = item.permissions
      content = item.content

      hash_after = virtual_file_hash(uid, gid, mode, content)
      if hash_before != hash_after:
        confirm(
          message = f"confirm {"changed" if hash_before is not None else "new"} file {item.identifier}",
          destructive = hash_before is not None,
          mode = get_confirm_mode(item, core),
        )
        changed_items.append(item)

      with open(item.identifier, 'wb+') as fh:
        fh.write(content)
      os.chown(item.identifier, uid = uid, gid = gid)
      os.chmod(item.identifier, mode)

      new_mode = os.stat(item.identifier).st_mode & 0o777
      if mode != new_mode:
        raise AssertionError("cannot apply file permissions (incompatible file system?)")

      self.managed_files_store.put(item.identifier, {"confirm_mode": get_confirm_mode(item, core)})

    return changed_items

  def finalize(self, items: list[File], core: ArchUpdate, state: ExecutionState):
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
