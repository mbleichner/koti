import os.path
from hashlib import sha256
from typing import TypedDict

from koti.core import Checksums, ConfigManager, ConfirmModeValues, Koti
from koti.items.swapfile import Swapfile
from koti.utils.confirm import confirm
from koti.utils.json_store import JsonMapping, JsonStore
from koti.utils.shell import shell, shell_success


class SwapfileStoreEntry(TypedDict):
  confirm_mode: ConfirmModeValues


class SwapfileManager(ConfigManager[Swapfile]):
  managed_classes = [Swapfile]
  managed_files_store: JsonMapping[str, SwapfileStoreEntry]

  def __init__(self):
    store = JsonStore("/var/cache/koti/SwapfileManager.json")
    self.managed_files_store = store.mapping("managed_files")

  def check_configuration(self, item: Swapfile, core: Koti):
    if item.size_bytes is None:
      raise AssertionError("missing size_bytes parameter")

  def checksums(self, core: Koti) -> Checksums[Swapfile]:
    return SwapfileChecksums()

  def apply_phase(self, items: list[Swapfile], core: Koti):
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
      elif current_size != item.size_bytes:
        if self.is_mounted(item.identifier):
          confirm(
            message = f"confirm resize of mounted swapfile {item.identifier}",
            destructive = True,
            mode = core.get_confirm_mode_for_item(item),
          )
          shell(f"swapoff {item.identifier}")
          os.unlink(item.identifier)
          self.create_swapfile(item)
          shell(f"swapon {item.identifier}")
        else:
          confirm(
            message = f"confirm resize of swapfile {item.identifier}",
            destructive = True,
            mode = core.get_confirm_mode_for_item(item),
          )
          shell(f"rm -f {item.identifier}")
          self.create_swapfile(item)

  def cleanup(self, items: list[Swapfile], core: Koti):
    for item in items:
      self.managed_files_store.put(item.identifier, {"confirm_mode": core.get_confirm_mode_for_item(item)})

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
          shell(f"swapoff {swapfile}")
        os.unlink(swapfile)
      self.managed_files_store.remove(swapfile)

  def create_swapfile(self, item: Swapfile):
    shell(f"mkswap -U clear --size {item.size_bytes} --file {item.identifier}")
    shell(f"chmod 600 {item.identifier}")

  def is_mounted(self, swapfile: str) -> bool:
    return shell_success(f"swapon --show | grep {swapfile}")


class SwapfileChecksums(Checksums[Swapfile]):

  def current(self, item: Swapfile) -> str | None:
    exists = os.path.isfile(item.identifier)
    current_size = os.stat(item.identifier).st_size if exists else 0
    sha256_hash = sha256()
    sha256_hash.update(str(exists).encode())
    sha256_hash.update(str(current_size).encode())
    return sha256_hash.hexdigest()

  def target(self, item: Swapfile) -> str | None:
    sha256_hash = sha256()
    sha256_hash.update(str(True).encode())
    sha256_hash.update(str(item.size_bytes).encode())
    return sha256_hash.hexdigest()
