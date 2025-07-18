import os
import pwd
from hashlib import sha256
from typing import TypedDict

from koti.core import Checksums, ConfigManager, ConfirmModeValues, ExecutionModel
from koti.items.file import File
from koti.utils.confirm import confirm
from koti.utils.json_store import JsonMapping, JsonStore


class FileStoreEntry(TypedDict):
  confirm_mode: ConfirmModeValues


class FileManager(ConfigManager[File]):
  managed_classes = [File]
  managed_files_store: JsonMapping[str, FileStoreEntry]

  def __init__(self):
    store = JsonStore("/var/cache/koti/FileManager.json")
    self.managed_files_store = store.mapping("managed_files")

  def check_configuration(self, item: File, model: ExecutionModel):
    assert item.content is not None, "missing either content or content_from_file"

  def checksums(self, model: ExecutionModel) -> Checksums[File]:
    return FileChecksums(model)

  def create_dir(self, dir: str, item: File):
    if os.path.exists(dir): return
    if not os.path.exists(os.path.dirname(dir)):
      self.create_dir(os.path.dirname(dir), item)
    os.mkdir(dir)
    getpwnam = pwd.getpwnam(item.owner)
    os.chown(dir, uid = getpwnam.pw_uid, gid = getpwnam.pw_gid)

  def install(self, items: list[File], model: ExecutionModel):
    for item in items:
      assert item.content is not None
      getpwnam = pwd.getpwnam(item.owner)
      uid = getpwnam.pw_uid
      gid = getpwnam.pw_gid
      mode = item.permissions
      content = item.content(model)

      directory = os.path.dirname(item.filename)
      self.create_dir(directory, item)
      exists = os.path.exists(item.filename)
      confirm(
        message = f"confirm {"changed" if exists else "new"} file {item.filename}",
        destructive = exists,
        mode = model.get_confirm_mode(item),
      )

      with open(item.filename, 'wb+') as fh:
        fh.write(content)  # type: ignore
      os.chown(item.filename, uid = uid, gid = gid)
      os.chmod(item.filename, mode)

      new_mode = os.stat(item.filename).st_mode & 0o777
      if mode != new_mode:
        raise AssertionError("cannot apply file permissions (incompatible file system?)")

  def cleanup(self, items_to_keep: list[File], model: ExecutionModel):
    for item in items_to_keep:
      self.managed_files_store.put(item.filename, {"confirm_mode": model.get_confirm_mode(item)})

    currently_managed_files = [item.filename for item in items_to_keep]
    previously_managed_files = self.managed_files_store.keys()
    files_to_delete = [file for file in previously_managed_files if file not in currently_managed_files]
    for file in files_to_delete:
      if os.path.isfile(file):
        store_entry: FileStoreEntry = self.managed_files_store.get(file, {"confirm_mode": model.default_confirm_mode})
        confirm(
          message = f"confirm to delete file: {file}",
          destructive = True,
          mode = store_entry["confirm_mode"],
        )
        os.unlink(file)
      self.managed_files_store.remove(file)


class FileChecksums(Checksums[File]):
  model: ExecutionModel

  def __init__(self, model:ExecutionModel):
    self.model = model

  def current(self, item: File) -> str | None:
    if not os.path.isfile(item.filename):
      return None
    stat = os.stat(item.filename)
    sha256_hash = sha256()
    sha256_hash.update(str(stat.st_uid).encode())
    sha256_hash.update(str(stat.st_gid).encode())
    sha256_hash.update(str(stat.st_mode & 0o777).encode())
    with open(item.filename, "rb") as f:
      for byte_block in iter(lambda: f.read(4096), b""):
        sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

  def target(self, item: File) -> str | None:
    getpwnam = pwd.getpwnam(item.owner)
    (uid, gid) = (getpwnam.pw_uid, getpwnam.pw_gid)
    if item.content is None:
      raise AssertionError(f"{item}: content missing")
    sha256_hash = sha256()
    sha256_hash.update(str(uid).encode())
    sha256_hash.update(str(gid).encode())
    sha256_hash.update(str(item.permissions & 0o777).encode())
    sha256_hash.update(item.content(self.model))
    return sha256_hash.hexdigest()