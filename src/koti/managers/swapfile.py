import os.path
from hashlib import sha256

from koti.core import ConfigManager, ConfigModel, SystemState
from koti.items.swapfile import Swapfile
from koti.utils import JsonCollection
from koti.utils.json_store import JsonStore
from koti.utils.shell import shell, shell_success


class SwapfileManager(ConfigManager[Swapfile]):
  managed_classes = [Swapfile]
  managed_files_store: JsonCollection[str]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/SwapfileManager.json")
    self.managed_files_store = store.collection("managed_files")

  def check_configuration(self, item: Swapfile, model: ConfigModel):
    assert item.size_bytes is not None, "missing size_bytes parameter"

  def install(self, items: list[Swapfile], model: ConfigModel, state: SystemState):
    for item in items:
      assert item.size_bytes is not None
      exists = os.path.isfile(item.filename)
      current_size = os.stat(item.filename).st_size if exists else 0
      if not exists:
        self.create_swapfile(item)
      elif current_size != item.size_bytes:
        if self.is_mounted(item.filename):
          shell(f"swapoff {item.filename}")
          os.unlink(item.filename)
          self.create_swapfile(item)
          shell(f"swapon {item.filename}")
        else:
          shell(f"rm -f {item.filename}")
          self.create_swapfile(item)

      self.managed_files_store.add(item.filename)

  def create_swapfile(self, item: Swapfile):
    shell(f"mkswap -U clear --size {item.size_bytes} --file {item.identifier}")
    shell(f"chmod 600 {item.identifier}")

  def is_mounted(self, swapfile: str) -> bool:
    return shell_success(f"swapon --show | grep {swapfile}")

  def installed(self, model: ConfigModel) -> list[Swapfile]:
    return [Swapfile(filename) for filename in self.managed_files_store.elements()]

  def uninstall(self, items: list[Swapfile], model: ConfigModel):
    for item in items:
      if os.path.isfile(item.filename):
        if self.is_mounted(item.filename):
          shell(f"swapoff {item.filename}")
        os.unlink(item.filename)
      self.managed_files_store.remove(item.filename)

  def checksum_current(self, item: Swapfile) -> str:
    exists = os.path.isfile(item.filename)
    current_size = os.stat(item.filename).st_size if exists else 0
    sha256_hash = sha256()
    sha256_hash.update(str(exists).encode())
    sha256_hash.update(str(current_size).encode())
    return sha256_hash.hexdigest()

  def checksum_target(self, item: Swapfile, model: ConfigModel, state: SystemState) -> str:
    sha256_hash = sha256()
    sha256_hash.update(str(True).encode())
    sha256_hash.update(str(item.size_bytes).encode())
    return sha256_hash.hexdigest()
