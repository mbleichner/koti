import os
import pwd
from pathlib import Path

from definitions import ConfigItem, ConfigManager, Triggerable
from utils import JsonStore, confirm, file_hash, virtual_file_hash


class File(ConfigItem):
  content: bytes | None
  permissions: int = 0o755
  owner: str = "root"
  on_file_change: Triggerable | None

  def __init__(
    self,
    identifier: str,
    content: str = None,
    path = None,
    permissions: int = 0o444,
    owner: str = "root",
    on_file_change: Triggerable | None = None
  ):
    super().__init__(identifier)
    if content is not None: self.content = content.encode("utf-8")
    if path is not None: self.content = Path(path).read_bytes()
    self.permissions = permissions
    self.owner = owner
    self.on_file_change = on_file_change

  def __str__(self):
    return f"File('{self.identifier}')"


class FileManager(ConfigManager[File]):
  managed_classes = [File]
  store: JsonStore

  def __init__(self):
    super().__init__()
    self.store = JsonStore("/var/cache/arch-config/FileManager.json")

  def check_configuration(self, item: File) -> str | None:
    if item.content is None:
      return "File() needs to define either content or content_from_file"

  def execute_phase(self, items: list[File]) -> list[File]:
    changed_items: list[File] = []
    for item in items:
      print(f"creating file {item.identifier}")
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
        confirm(f"Confirm changed file {item.identifier}")
        changed_items.append(item)

      with open(item.identifier, 'wb+') as fh:
        fh.write(content)
      os.chown(item.identifier, uid = uid, gid = gid)
      os.chmod(item.identifier, mode)

      new_mode = os.stat(item.identifier).st_mode & 0o777
      if mode != new_mode:
        raise AssertionError("cannot apply file permissions (incompatible file system?)")

      managed_files_set = set(self.store.get("managed_files", []))
      self.store.put("managed_files", list(managed_files_set.union({item.identifier})))

    return changed_items

  def finalize_phase(self, result_from_execute_phase: list[File]):
    for file in result_from_execute_phase:
      if file.on_file_change is not None:
        file.on_file_change.execute()

  def finalize(self, all_items: list[File]):
    currently_managed_files = [item.identifier for item in all_items]
    previously_managed_files = self.store.get("managed_files", [])
    files_to_delete = [file for file in previously_managed_files if file not in currently_managed_files]
    for file in files_to_delete:
      if os.path.isfile(file):
        confirm(f"Please confirm to delete file: {file}")
        os.unlink(file)
        print(f"deleted file {file}")
      managed_files_set = set(self.store.get("managed_files", []))
      self.store.put("managed_files", list(managed_files_set.difference({file})))
