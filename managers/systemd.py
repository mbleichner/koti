from typing import TypedDict

from confirm import confirm, effective_confirm_mode, get_confirm_mode
from core import ArchUpdate, ConfigItem, ConfigManager, ConfirmModeValues, ExecutionState
from json_store import JsonCollection, JsonStore
from managers.pacman import shell_interactive


class SystemdUnit(ConfigItem):
  user: str = None

  def __init__(self, identifier: str, user: str = None):
    super().__init__(identifier)
    self.user = user

  def __str__(self):
    return f"SystemdUnit('{self.identifier}')"


def SystemdUnits(*identifiers: str) -> list[SystemdUnit]:
  return [SystemdUnit(identifier) for identifier in identifiers]


class SystemdUnitStoreEntry(TypedDict):
  confirm_mode: ConfirmModeValues


class SystemdUnitManager(ConfigManager[SystemdUnit]):
  store: JsonStore
  managed_classes = [SystemdUnit]
  user_list_store: JsonCollection[str]

  def __init__(self):
    super().__init__()
    self.store = JsonStore("/var/cache/arch-config/SystemdUnitManager.json")
    self.user_list_store = self.store.collection("users")

  def execute_phase(self, items: list[SystemdUnit], core: ArchUpdate, state: ExecutionState):
    if len(items) > 0:
      shell_interactive(f"systemctl daemon-reload")

    users = set([item.user for item in items])
    for user in users:
      items_for_user = [item for item in items if item.user == user]
      units_store = self.store.mapping(store_key_for_user(user))
      shell_interactive(f"{systemctl_for_user(user)} enable --now {" ".join([item.identifier for item in items_for_user])}")
      for item in items_for_user:
        mode = get_confirm_mode(item, core)
        units_store.put(item.identifier, {"confirm_mode": mode})
        if user is not None: self.user_list_store.add(user)

  def finalize(self, items: list[SystemdUnit], core: ArchUpdate, state: ExecutionState):
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
          mode = effective_confirm_mode([
            units_store.get(unit, {}).get("confirm_mode", core.default_confirm_mode) for unit in units_to_deactivate
          ], core),
        )
        shell_interactive(f"{systemctl_for_user(user)} disable --now {" ".join(units_to_deactivate)}")
        for identifier in units_to_deactivate:
          units_store.remove(identifier)


def systemctl_for_user(user):
  return f"systemctl --user -M {user}@" if user is not None else "systemctl"


def store_key_for_user(user):
  return f"user@{user}" if user is not None else "system"
