import os.path
from hashlib import sha256
from typing import Generator, Sequence

from koti import Action
from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.swapfile import Swapfile
from koti.utils.json_store import JsonCollection, JsonStore
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

  def create_swapfile(self, item: Swapfile):
    shell(f"mkswap -U clear --size {item.size_bytes} --file {item.identifier}")
    shell(f"chmod 600 {item.identifier}")
    self.managed_files_store.add(item.filename)

  def recreate_swapfile(self, item: Swapfile):
    if self.is_mounted(item.filename):
      shell(f"swapoff {item.filename}")
      os.unlink(item.filename)
      self.create_swapfile(item)
      shell(f"swapon {item.filename}")
    else:
      shell(f"rm -f {item.filename}")
      self.create_swapfile(item)
    self.managed_files_store.add(item.filename)

  def delete_swapfile(self, item: Swapfile):
    if os.path.isfile(item.filename):
      if self.is_mounted(item.filename):
        shell(f"swapoff {item.filename}")
      os.unlink(item.filename)
    self.managed_files_store.remove(item.filename)

  def is_mounted(self, swapfile: str) -> bool:
    return shell_success(f"swapon --show | grep {swapfile}")

  def state_current(self, item: Swapfile) -> SwapfileState | None:
    if not os.path.isfile(item.filename):
      return None
    return SwapfileState(size_bytes = os.stat(item.filename).st_size)

  def state_target(self, item: Swapfile, model: ConfigModel, dryrun: bool) -> SwapfileState:
    assert item.size_bytes is not None
    return SwapfileState(size_bytes = item.size_bytes)

  def plan_install(self, items_to_check: Sequence[Swapfile], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    for item in items_to_check:
      current, target = self.states(item, model, dryrun)
      if current == target:
        continue

      assert target is not None
      assert item.size_bytes is not None

      if current is None:
        yield Action(
          installs = [item],
          description = f"{GREEN}create swapfile",
          additional_info = f"size = {target.size_bytes}",
          execute = lambda: self.create_swapfile(item),
        )

      if current is not None and current.size_bytes != target.size_bytes:
        yield Action(
          updates = [item],
          description = f"{YELLOW}resize swapfile",
          additional_info = f"{current.size_bytes} => {target.size_bytes}",
          execute = lambda: self.recreate_swapfile(item),
        )

  def plan_cleanup(self, items_to_keep: Sequence[Swapfile], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    currently_managed_swapfiles = [Swapfile(filename) for filename in self.managed_files_store.elements()]
    for item in currently_managed_swapfiles:
      if item in items_to_keep:
        continue
      yield Action(
        removes = [item],
        description = f"{RED}delete swapfile",
        additional_info = "please make sure the swapfile isn't referenced in fstab any more",
        execute = lambda: self.delete_swapfile(item),
      )

  def finalize(self, model: ConfigModel, dryrun: bool):
    if not dryrun:
      self.managed_files_store.replace_all([item.filename for phase in model.phases for item in phase.items if isinstance(item, Swapfile)])
