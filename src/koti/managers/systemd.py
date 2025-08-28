from hashlib import sha256

from koti.core import ConfigManager, ConfigModel, SystemState
from koti.items.systemd import SystemdUnit
from koti.managers.pacman import shell
from koti.utils import shell_success
from koti.utils.json_store import JsonCollection, JsonStore


class SystemdUnitManager(ConfigManager[SystemdUnit]):
  managed_classes = [SystemdUnit]
  store: JsonStore
  user_list_store: JsonCollection[str]

  def __init__(self):
    super().__init__()
    self.store = JsonStore("/var/cache/koti/SystemdUnitManager.json")
    self.user_list_store = self.store.collection("users")

  def check_configuration(self, item: SystemdUnit, model: ConfigModel):
    pass

  def install(self, items: list[SystemdUnit], model: ConfigModel, state: SystemState):
    if len(items) > 0: shell(f"systemctl daemon-reload")
    users = set([item.user for item in items])
    for user in users:
      items_for_user = [item for item in items if item.user == user]
      shell(f"{self.systemctl_for_user(user)} enable --now {" ".join([item.name for item in items_for_user])}")

      if user is not None: self.user_list_store.add(user)
      units_store: JsonCollection[str] = self.store.collection(self.store_key_for_user(user))
      units_store.add_all([item.name for item in items])

  def installed(self, model: ConfigModel) -> list[SystemdUnit]:
    result: list[SystemdUnit] = []
    previously_seen_users = self.user_list_store.elements()
    for user in [None, *previously_seen_users]:
      units_store: JsonCollection[str] = self.store.collection(self.store_key_for_user(user))
      result += [SystemdUnit(name, user) for name in units_store.elements()]
    return result

  def uninstall(self, items: list[SystemdUnit], model: ConfigModel):
    distinct_users = {item.user for item in items}
    for user in distinct_users:
      units_store: JsonCollection[str] = self.store.collection(self.store_key_for_user(user))
      items_to_deactivate = [item for item in items if item.user == user]
      if len(items_to_deactivate) > 0:
        unit_names = [item.name for item in items_to_deactivate]
        shell(f"{self.systemctl_for_user(user)} disable --now {" ".join(unit_names)}")
        units_store.remove_all(unit_names)

  def checksum_current(self, item: SystemdUnit) -> str:
    enabled: bool = shell_success(f"{self.systemctl_for_user(item.user)} is-enabled {item.name}")
    return sha256(str(enabled).encode()).hexdigest()

  def checksum_target(self, item: SystemdUnit, model: ConfigModel, state: SystemState) -> str:
    return sha256(str(True).encode()).hexdigest()

  def systemctl_for_user(self, user: str | None):
    return f"systemctl --user -M {user}@" if user is not None else "systemctl"

  def store_key_for_user(self, user: str | None):
    return user if user is not None else "$system"
