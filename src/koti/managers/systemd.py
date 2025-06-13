from typing import TypedDict

from koti.core import ConfigManager, ConfirmModeValues, ExecutionState, Koti
from koti.items.systemd import SystemdUnit
from koti.managers.pacman import shell_interactive
from koti.utils import shell_success
from koti.utils.confirm import confirm
from koti.utils.json_store import JsonCollection, JsonStore


class SystemdUnitStoreEntry(TypedDict):
  confirm_mode: ConfirmModeValues


class SystemdUnitManager(ConfigManager[SystemdUnit]):
  store: JsonStore
  managed_classes = [SystemdUnit]
  user_list_store: JsonCollection[str]

  def __init__(self):
    super().__init__()
    self.store = JsonStore("/var/cache/koti/SystemdUnitManager.json")
    self.user_list_store = self.store.collection("users")

  def check_configuration(self, item: SystemdUnit, core: Koti):
    pass

  def checksum_current(self, items: list[SystemdUnit], core: Koti, state: ExecutionState) -> list[str | int | None]:
    return [self.checksum_current_single(item, core, state) for item in items]

  def checksum_target(self, items: list[SystemdUnit], core: Koti, state: ExecutionState) -> list[str | int | None]:
    return [self.checksum_target_single(item, core, state) for item in items]

  def checksum_current_single(self, item: SystemdUnit, core: Koti, state: ExecutionState) -> str | int | None:
    return 1 if shell_success(f"{systemctl_for_user(item.user)} is-enabled {item.identifier}") else 0

  def checksum_target_single(self, item: SystemdUnit, core: Koti, state: ExecutionState) -> str | int | None:
    return 1

  def apply_phase(self, items: list[SystemdUnit], core: Koti, state: ExecutionState):
    if len(items) > 0:
      shell_interactive(f"systemctl daemon-reload")

    users = set([item.user for item in items])
    for user in users:
      items_for_user = [item for item in items if item.user == user]
      units_store = self.store.mapping(store_key_for_user(user))
      shell_interactive(f"{systemctl_for_user(user)} enable --now {" ".join([item.identifier for item in items_for_user])}")
      for item in items_for_user:
        mode = core.get_confirm_mode_for_item(item)
        units_store.put(item.identifier, {"confirm_mode": mode})
        if user is not None: self.user_list_store.add(user)

  def cleanup(self, items: list[SystemdUnit], core: Koti, state: ExecutionState):
    shell_interactive(f"systemctl daemon-reload")

    previously_seen_users = self.user_list_store.elements()
    users = set([item.user for item in items] + previously_seen_users + [None])
    for user in users:
      items_for_user = [item for item in items if item.user == user]
      units_store = self.store.mapping(store_key_for_user(user))
      currently_managed_units = [item.identifier for item in items_for_user]
      previously_managed_units = units_store.keys()
      units_to_deactivate = [file for file in previously_managed_units if file not in currently_managed_units]
      if len(units_to_deactivate) > 0:
        confirm(
          message = f"confirm to deactivate units: {", ".join(units_to_deactivate)}" if user is None
          else f"confirm to deactivate user units for {user}: {", ".join(units_to_deactivate)}",
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
  return f"user@{user}" if user is not None else "system"
