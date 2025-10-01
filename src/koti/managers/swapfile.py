import os.path
from hashlib import sha256
from typing import Generator, Sequence

from koti import ExecutionPlan
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

  def recreate_swapfile(self, item: Swapfile):
    if self.is_mounted(item.filename):
      shell(f"swapoff {item.filename}")
      os.unlink(item.filename)
      self.create_swapfile(item)
      shell(f"swapon {item.filename}")
    else:
      shell(f"rm -f {item.filename}")
      self.create_swapfile(item)

  def delete_swapfile(self, item: Swapfile):
    if os.path.isfile(item.filename):
      if self.is_mounted(item.filename):
        shell(f"swapoff {item.filename}")
      os.unlink(item.filename)

  def is_mounted(self, swapfile: str) -> bool:
    return shell_success(f"swapon --show | grep {swapfile}")

  def installed(self) -> list[Swapfile]:
    return [Swapfile(filename) for filename in self.managed_files_store.elements()]

  def state_current(self, item: Swapfile) -> SwapfileState | None:
    if not os.path.isfile(item.filename):
      return None
    return SwapfileState(size_bytes = os.stat(item.filename).st_size)

  def state_target(self, item: Swapfile, model: ConfigModel, dryrun: bool) -> SwapfileState:
    assert item.size_bytes is not None
    return SwapfileState(size_bytes = item.size_bytes)

  def plan_install(self, items_to_check: Sequence[Swapfile], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    for item in items_to_check:
      current, target = self.states(item, model, dryrun)
      if current == target:
        continue

      assert target is not None
      assert item.size_bytes is not None

      if current is None:
        yield ExecutionPlan(
          items = [item],
          description = f"{GREEN}create swapfile",
          details = f"size = {target.size_bytes}",
          actions = [
            lambda: self.create_swapfile(item),
            lambda: self.managed_files_store.add(item.filename),
          ],
        )

      if current is not None and current.size_bytes != target.size_bytes:
        yield ExecutionPlan(
          items = [item],
          description = f"{YELLOW}resize swapfile",
          details = f"{current.size_bytes} => {target.size_bytes}",
          actions = [
            lambda: self.recreate_swapfile(item),
            lambda: self.managed_files_store.add(item.filename)
          ]
        )

  def plan_cleanup(self, items_to_keep: Sequence[Swapfile], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    installed_items = self.installed()
    for item in installed_items:
      if item in items_to_keep:
        continue
      yield ExecutionPlan(
        items = [item],
        description = f"{RED}delete swapfile",
        details = "please make sure the swapfile isn't referenced in fstab any more",
        actions = [
          lambda: self.delete_swapfile(item),
          lambda: self.managed_files_store.add(item.filename),
        ]
      )

  def finalize(self, model: ConfigModel):
    swapfiles = [item.filename for phase in model.phases for item in phase.items if isinstance(item, Swapfile)]
    self.managed_files_store.replace_all(swapfiles)
