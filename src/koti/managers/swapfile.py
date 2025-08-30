import os.path
from hashlib import sha256

from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.swapfile import Swapfile
from koti.utils import JsonCollection
from koti.utils.json_store import JsonStore
from koti.utils.shell import shell, shell_success
from koti.utils.colors import *


class SwapfileState(ConfigItemState):
  def __init__(self, size_bytes: int):
    self.size_bytes = size_bytes

  def hash(self) -> str:
    sha256_hash = sha256()
    sha256_hash.update(str(self.size_bytes).encode())
    return sha256_hash.hexdigest()


class SwapfileManager(ConfigManager[Swapfile, SwapfileState]):
  managed_classes = [Swapfile]
  managed_files_store: JsonCollection[str]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/SwapfileManager.json")
    self.managed_files_store = store.collection("managed_files")

  def assert_installable(self, item: Swapfile, model: ConfigModel):
    assert item.size_bytes is not None, "missing size_bytes parameter"

  def install(self, items: list[Swapfile], model: ConfigModel):
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

  def uninstall(self, items: list[Swapfile]):
    for item in items:
      if os.path.isfile(item.filename):
        if self.is_mounted(item.filename):
          shell(f"swapoff {item.filename}")
        os.unlink(item.filename)
      self.managed_files_store.remove(item.filename)

  def state_current(self, item: Swapfile) -> SwapfileState | None:
    if not os.path.isfile(item.filename):
      return None
    return SwapfileState(size_bytes = os.stat(item.filename).st_size)

  def state_target(self, item: Swapfile, model: ConfigModel, planning: bool) -> SwapfileState:
    assert item.size_bytes is not None
    return SwapfileState(size_bytes = item.size_bytes)

  def diff(self, current: SwapfileState | None, target: SwapfileState | None) -> list[str]:
    if current is None:
      return [f"{GREEN}swapfile will be created"]
    if target is None:
      return [f"{RED}swapfile will be deleted"]
    return [change for change in (
      f"{YELLOW}change size from {current.size_bytes} to {target.size_bytes}" if current.size_bytes != target.size_bytes else None,
    ) if change is not None]

  def finalize(self, model: ConfigModel):
    swapfiles = [item.filename for phase in model.phases for item in phase.items if isinstance(item, Swapfile)]
    self.managed_files_store.replace_all(swapfiles)
