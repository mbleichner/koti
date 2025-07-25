import os
import pwd
import shutil
from hashlib import sha256

from koti.core import ConfigManager, ConfigModel
from koti.items.file import File
from koti.items.directory import Directory
from koti.utils import JsonCollection
from koti.utils.confirm import confirm
from koti.utils.json_store import JsonStore


class FileManager(ConfigManager[File | Directory]):
  managed_classes = [File, Directory]
  managed_files_store: JsonCollection[str]
  managed_dirs_store: JsonCollection[str]

  def __init__(self):
    store = JsonStore("/var/cache/koti/FileManager.json")
    self.managed_files_store = store.collection("managed_files")
    self.managed_dirs_store = store.collection("managed_dirs")

  def check_configuration(self, item: File | Directory, model: ConfigModel):
    if isinstance(item, File):
      assert item.content is not None, "missing either content or content_from_file"
    if isinstance(item, Directory):
      assert len(item.files) > 0, "directory contains no files"

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

  def checksum_target(self, item: File | Directory, model: ConfigModel) -> str:
    return self.checksum_file_target(item, model) if isinstance(item, File) else self.checksum_dir_target(item, model)

  def checksum_current(self, item: File | Directory) -> str:
    return self.checksum_file_current(item) if isinstance(item, File) else self.checksum_dir_current(item)

  def installed(self, model: ConfigModel) -> list[File | Directory]:
    filenames = {
      *self.managed_files_store.elements(),
      *(item.filename for phase in model.phases for item in phase.items if isinstance(item, File))
    }
    dirnames = {
      *self.managed_dirs_store.elements(),
      *(item.dirname for phase in model.phases for item in phase.items if isinstance(item, Directory))
    }
    return [
      *(File(filename) for filename in filenames if os.path.isfile(filename)),
      *(Directory(dirname) for dirname in dirnames if os.path.isdir(dirname)),
    ]

  def install_file(self, item: File, model: ConfigModel):
    exists = os.path.exists(item.filename)
    confirm(
      message = f"confirm {"changed" if exists else "new"} file {item.filename}",
      destructive = exists,
      mode = model.confirm_mode(item),
    )
    self.update_file(item, model)
    self.managed_files_store.add(item.filename)

  def install_dir(self, item: Directory, model: ConfigModel):
    exists = os.path.isdir(item.dirname)
    confirm(
      message = f"confirm {"changed" if exists else "new"} directory {item.dirname}",
      destructive = exists,
      mode = model.confirm_mode(item),
    )

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
      confirm(
        message = f"confirm to delete file: {item.filename}",
        destructive = True,
        mode = model.confirm_mode(item),
      )
      os.unlink(item.filename)
    self.managed_files_store.remove(item.filename)

  def uninstall_dir(self, item: Directory, model: ConfigModel):
    if os.path.isdir(item.dirname):
      confirm(
        message = f"confirm to delete directory: {item.dirname}",
        destructive = True,
        mode = model.confirm_mode(item),
      )
      shutil.rmtree(item.dirname)
    self.managed_dirs_store.remove(item.dirname)

  def checksum_file_current(self, item: File) -> str:
    if not os.path.isfile(item.filename):
      return sha256("<file does not exist>".encode()).hexdigest()
    stat = os.stat(item.filename)
    sha256_hash = sha256()
    sha256_hash.update(str(stat.st_uid).encode())
    sha256_hash.update(str(stat.st_gid).encode())
    sha256_hash.update(str(stat.st_mode & 0o777).encode())
    with open(item.filename, "rb") as f:
      for byte_block in iter(lambda: f.read(4096), b""):
        sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

  def checksum_file_target(self, item: File, model: ConfigModel) -> str:
    getpwnam = pwd.getpwnam(item.owner)
    (uid, gid) = (getpwnam.pw_uid, getpwnam.pw_gid)
    if item.content is None:
      raise AssertionError(f"{item}: content missing")
    sha256_hash = sha256()
    sha256_hash.update(str(uid).encode())
    sha256_hash.update(str(gid).encode())
    sha256_hash.update(str(item.permissions & 0o777).encode())
    sha256_hash.update(item.content(model))
    return sha256_hash.hexdigest()

  def checksum_dir_current(self, item: Directory) -> str:
    if not os.path.isdir(item.dirname):
      return sha256("<directory does not exist>".encode()).hexdigest()
    sha256_hash = sha256()
    for file in item.files:
      sha256_hash.update(self.checksum_file_current(file).encode())
    return sha256_hash.hexdigest()

  def checksum_dir_target(self, item: Directory, model: ConfigModel) -> str:
    sha256_hash = sha256()
    for file in item.files:
      sha256_hash.update(self.checksum_file_target(file, model).encode())
    return sha256_hash.hexdigest()

  def mkdirs(self, dirname: str, owner: str):
    if os.path.exists(dirname): return
    if not os.path.exists(os.path.dirname(dirname)):
      self.mkdirs(os.path.dirname(dirname), owner)
    os.mkdir(dirname)
    getpwnam = pwd.getpwnam(owner)
    os.chown(dirname, uid = getpwnam.pw_uid, gid = getpwnam.pw_gid)
