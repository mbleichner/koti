from hashlib import sha256
from typing import TypedDict

from koti.core import Checksums, ConfigManager, ConfirmModeValues, Koti
from koti.items.systemd import SystemdUnit
from koti.managers.pacman import shell_interactive
from koti.utils import shell_success
from koti.utils.confirm import confirm
from koti.utils.json_store import JsonCollection, JsonMapping, JsonStore


class SystemdUnitStoreEntry(TypedDict):
  confirm_mode: ConfirmModeValues


class SystemdUnitManager(ConfigManager[SystemdUnit]):
  managed_classes = [SystemdUnit]
  store: JsonStore
  user_list_store: JsonCollection[str]

  def __init__(self):
    super().__init__()
    self.store = JsonStore("/var/cache/koti/SystemdUnitManager.json")
    self.user_list_store = self.store.collection("users")

  def check_configuration(self, item: SystemdUnit, core: Koti):
    pass

  def checksums(self, core: Koti) -> Checksums[SystemdUnit]:
    return SystemdUnitChecksums()

  def apply_phase(self, items: list[SystemdUnit], core: Koti):
    if len(items) > 0: shell_interactive(f"systemctl daemon-reload")
    users = set([item.user for item in items])
    for user in users:
      items_for_user = [item for item in items if item.user == user]
      confirm(
        message = f"confirm to activate units: {", ".join([item.identifier for item in items_for_user])}" if user is None
        else f"confirm to deactivate units for user {user}: {", ".join([item.identifier for item in items_for_user])}",
        destructive = True,
        mode = core.get_effective_confirm_mode([
          core.get_confirm_mode_for_item(item) for item in items_for_user
        ]),
      )
      shell_interactive(f"{systemctl_for_user(user)} enable --now {" ".join([item.identifier for item in items_for_user])}")

  def cleanup(self, items: list[SystemdUnit], core: Koti):
    shell_interactive(f"systemctl daemon-reload")

    users = set([item.user for item in items])
    for user in users:
      items_for_user = [item for item in items if item.user == user]
      units_store: JsonMapping[str, SystemdUnitStoreEntry] = self.store.mapping(store_key_for_user(user))
      for item in items_for_user:
        units_store.put(item.identifier, {"confirm_mode": core.get_confirm_mode_for_item(item)})
        if user is not None: self.user_list_store.add(user)

    previously_seen_users = self.user_list_store.elements()
    users = set([item.user for item in items] + previously_seen_users + [None])
    for user in users:
      items_for_user = [item for item in items if item.user == user]
      units_store: JsonMapping[str, SystemdUnitStoreEntry] = self.store.mapping(store_key_for_user(user))
      currently_managed_units = [item.identifier for item in items_for_user]
      previously_managed_units = units_store.keys()
      units_to_deactivate = [file for file in previously_managed_units if file not in currently_managed_units]
      if len(units_to_deactivate) > 0:
        confirm(
          message = f"confirm to deactivate units: {", ".join(units_to_deactivate)}" if user is None
          else f"confirm to deactivate units for user {user}: {", ".join(units_to_deactivate)}",
          destructive = True,
          mode = core.get_effective_confirm_mode([
            units_store.get(unit, {}).get("confirm_mode", core.default_confirm_mode) for unit in units_to_deactivate
          ]),
        )
        shell_interactive(f"{systemctl_for_user(user)} disable --now {" ".join(units_to_deactivate)}")
        for identifier in units_to_deactivate:
          units_store.remove(identifier)


def systemctl_for_user(user):
  return f"systemctl --user -M {user}@" if user is not None else "systemctl"


def store_key_for_user(user):
  return user if user is not None else "$system"


class SystemdUnitChecksums(Checksums[SystemdUnit]):

  def current(self, item: SystemdUnit) -> str | None:
    enabled: bool = shell_success(f"{systemctl_for_user(item.user)} is-enabled {item.identifier}")
    return sha256(str(enabled).encode()).hexdigest()

  def target(self, item: SystemdUnit) -> str | None:
    return sha256(str(True).encode()).hexdigest()
