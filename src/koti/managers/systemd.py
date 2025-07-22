from hashlib import sha256

from koti.core import ConfigManager, ExecutionModel
from koti.items.systemd import SystemdUnit
from koti.managers.pacman import shell
from koti.utils import shell_success
from koti.utils.confirm import confirm
from koti.utils.json_store import JsonCollection, JsonStore


class SystemdUnitManager(ConfigManager[SystemdUnit]):
  managed_classes = [SystemdUnit]
  store: JsonStore
  user_list_store: JsonCollection[str]

  def __init__(self):
    self.store = JsonStore("/var/cache/koti/SystemdUnitManager.json")
    self.user_list_store = self.store.collection("users")

  def check_configuration(self, item: SystemdUnit, model: ExecutionModel):
    pass

  def install(self, items: list[SystemdUnit], model: ExecutionModel):
    if len(items) > 0: shell(f"systemctl daemon-reload")
    users = set([item.user for item in items])
    for user in users:
      items_for_user = [item for item in items if item.user == user]
      confirm(
        message = f"confirm to activate units: {", ".join([item.name for item in items_for_user])}" if user is None
        else f"confirm to deactivate units for user {user}: {", ".join([item.name for item in items_for_user])}",
        destructive = True,
        mode = model.confirm_mode(*items_for_user),
      )
      shell(f"{self.systemctl_for_user(user)} enable --now {" ".join([item.name for item in items_for_user])}")

      if user is not None: self.user_list_store.add(user)
      units_store: JsonCollection[str] = self.store.collection(self.store_key_for_user(user))
      units_store.add_all([item.name for item in items])

  def list_installed_items(self) -> list[SystemdUnit]:
    result: list[SystemdUnit] = []
    previously_seen_users = self.user_list_store.elements()
    for user in [None, *previously_seen_users]:
      units_store: JsonCollection[str] = self.store.collection(self.store_key_for_user(user))
      result += [SystemdUnit(name, user) for name in units_store.elements()]
    return result

  def uninstall(self, items: list[SystemdUnit], model: ExecutionModel):
    distinct_users = {item.user for item in items}
    for user in distinct_users:
      units_store: JsonCollection[str] = self.store.collection(self.store_key_for_user(user))
      items_to_deactivate = [item for item in items if item.user == user]
      if len(items_to_deactivate) > 0:
        unit_names = [item.name for item in items_to_deactivate]
        confirm(
          message = f"confirm to deactivate units: {", ".join(unit_names)}" if user is None
          else f"confirm to deactivate units for user {user}: {", ".join(unit_names)}",
          destructive = True,
          mode = model.confirm_mode(*items_to_deactivate),
        )
        shell(f"{self.systemctl_for_user(user)} disable --now {" ".join(unit_names)}")
        units_store.remove_all(unit_names)

  def checksum_current(self, item: SystemdUnit) -> str:
    enabled: bool = shell_success(f"{self.systemctl_for_user(item.user)} is-enabled {item.name}")
    return sha256(str(enabled).encode()).hexdigest()

  def checksum_target(self, item: SystemdUnit, model: ExecutionModel) -> str:
    return sha256(str(True).encode()).hexdigest()

  def systemctl_for_user(self, user: str | None):
    return f"systemctl --user -M {user}@" if user is not None else "systemctl"

  def store_key_for_user(self, user: str | None):
    return user if user is not None else "$system"
