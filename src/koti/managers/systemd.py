from hashlib import sha256
from typing import TypedDict

from koti.core import Checksums, ConfigManager, ConfirmModeValues, Koti
from koti.items.systemd import SystemdUnit
from koti.managers.pacman import shell
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
    self.store = JsonStore("/var/cache/koti/SystemdUnitManager.json")
    self.user_list_store = self.store.collection("users")

  def check_configuration(self, item: SystemdUnit, core: Koti):
    pass

  def checksums(self, core: Koti) -> Checksums[SystemdUnit]:
    return SystemdUnitChecksums()

  def install(self, items: list[SystemdUnit], core: Koti):
    if len(items) > 0: shell(f"systemctl daemon-reload")
    users = set([item.user for item in items])
    for user in users:
      items_for_user = [item for item in items if item.user == user]
      confirm(
        message = f"confirm to activate units: {", ".join([item.identifier for item in items_for_user])}" if user is None
        else f"confirm to deactivate units for user {user}: {", ".join([item.identifier for item in items_for_user])}",
        destructive = True,
        mode = core.get_confirm_mode(*items_for_user),
      )
      shell(f"{systemctl_for_user(user)} enable --now {" ".join([item.identifier for item in items_for_user])}")

  def uninstall(self, items_to_keep: list[SystemdUnit], core: Koti):
    shell(f"systemctl daemon-reload")
    self.store_all_seen_units(core, items_to_keep)
    self.deactivate_removed_units(core, items_to_keep)

  def deactivate_removed_units(self, core: Koti, items: list[SystemdUnit]):
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
          mode = core.get_confirm_mode(*(
            units_store.get(unit, {"confirm_mode": core.default_confirm_mode})["confirm_mode"] for unit in units_to_deactivate
          )),
        )
        shell(f"{systemctl_for_user(user)} disable --now {" ".join(units_to_deactivate)}")
        for identifier in units_to_deactivate:
          units_store.remove(identifier)

  def store_all_seen_units(self, core: Koti, items: list[SystemdUnit]):
    users = set([item.user for item in items])
    for user in users:
      items_for_user = [item for item in items if item.user == user]
      units_store: JsonMapping[str, SystemdUnitStoreEntry] = self.store.mapping(store_key_for_user(user))
      for item in items_for_user:
        units_store.put(item.identifier, {"confirm_mode": core.get_confirm_mode(item)})
        if user is not None: self.user_list_store.add(user)


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
