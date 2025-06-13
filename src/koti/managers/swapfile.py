import hashlib
import os.path
from typing import TypedDict

from koti.core import ConfigManager, ConfirmModeValues, ExecutionState, Koti
from koti.items.swapfile import Swapfile
from koti.utils.confirm import confirm
from koti.utils.json_store import JsonMapping, JsonStore
from koti.utils.shell import shell_interactive, shell_success


class SwapfileStoreEntry(TypedDict):
  confirm_mode: ConfirmModeValues


class SwapfileManager(ConfigManager[Swapfile]):
  managed_classes = [Swapfile]
  managed_files_store: JsonMapping[str, SwapfileStoreEntry]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/SwapfileManager.json")
    self.managed_files_store = store.mapping("managed_files")

  def check_configuration(self, item: Swapfile, core: Koti):
    if item.size_bytes is None:
      raise AssertionError("missing size_bytes parameter")

  def checksum_current(self, items: list[Swapfile], core: Koti, state: ExecutionState) -> list[str | int | None]:
    return [self.checksum_current_single(item, core, state) for item in items]

  def checksum_target(self, items: list[Swapfile], core: Koti, state: ExecutionState) -> list[str | int | None]:
    return [self.checksum_target_single(item, core, state) for item in items]

  def checksum_current_single(self, item: Swapfile, core: Koti, state: ExecutionState) -> str | int | None:
    exists = os.path.isfile(item.identifier)
    current_size = os.stat(item.identifier).st_size if exists else 0
    sha256_hash = hashlib.sha256()
    sha256_hash.update(str(exists).encode())
    sha256_hash.update(str(current_size).encode())
    return sha256_hash.hexdigest()

  def checksum_target_single(self, item: Swapfile, core: Koti, state: ExecutionState) -> str | int | None:
    sha256_hash = hashlib.sha256()
    sha256_hash.update(str(True).encode())
    sha256_hash.update(str(item.size_bytes).encode())
    return sha256_hash.hexdigest()

  def apply_phase(self, items: list[Swapfile], core: Koti, state: ExecutionState):
    for item in items:
      exists = os.path.isfile(item.identifier)
      current_size = os.stat(item.identifier).st_size if exists else 0
      if not exists:
        confirm(
          message = f"confirm to create swapfile {item.identifier}",
          destructive = False,
          mode = core.get_confirm_mode_for_item(item),
        )
        self.create_swapfile(item)
        state.updated_items += [item]
      elif current_size != item.size_bytes:
        if self.is_mounted(item.identifier):
          confirm(
            message = f"confirm resize of mounted swapfile {item.identifier}",
            destructive = True,
            mode = core.get_confirm_mode_for_item(item),
          )
          shell_interactive(f"swapoff {item.identifier}")
          os.unlink(item.identifier)
          self.create_swapfile(item)
          shell_interactive(f"swapon {item.identifier}")
          state.updated_items += [item]
        else:
          confirm(
            message = f"confirm resize of swapfile {item.identifier}",
            destructive = True,
            mode = core.get_confirm_mode_for_item(item),
          )
          shell_interactive(f"rm -f {item.identifier}")
          self.create_swapfile(item)
          state.updated_items += [item]
      self.managed_files_store.put(item.identifier, {"confirm_mode": core.get_confirm_mode_for_item(item)})

  def cleanup(self, items: list[Swapfile], core: Koti, state: ExecutionState):
    currently_managed_files = [item.identifier for item in items]
    previously_managed_files = self.managed_files_store.keys()
    files_to_delete = [file for file in previously_managed_files if file not in currently_managed_files]
    for swapfile in files_to_delete:
      if os.path.isfile(swapfile):
        confirm(
          message = f"confirm to delete swapfile {swapfile}",
          destructive = True,
          mode = self.managed_files_store.get(swapfile, {}).get("confirm_mode", core.default_confirm_mode),
        )
        if self.is_mounted(swapfile):
          shell_interactive(f"swapoff {swapfile}")
        os.unlink(swapfile)
      self.managed_files_store.remove(swapfile)

  def create_swapfile(self, item: Swapfile):
    shell_interactive(f"mkswap -U clear --size {item.size_bytes} --file {item.identifier}")
    shell_interactive(f"chmod 600 {item.identifier}")

  def is_mounted(self, swapfile: str) -> bool:
    return shell_success(f"swapon --show | grep {swapfile}")
