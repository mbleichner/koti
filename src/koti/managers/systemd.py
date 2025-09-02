from typing import Sequence

from koti import ConfigItemToInstall, ConfigItemToUninstall, ExecutionPlan
from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.systemd import SystemdUnit
from koti.managers.pacman import shell
from koti.utils.shell import ShellAction, shell_success
from koti.utils.json_store import JsonCollection, JsonStore
from koti.utils.colors import *


class SystemdUnitState(ConfigItemState):
  def hash(self) -> str:
    return "-"


class SystemdUnitManager(ConfigManager[SystemdUnit, SystemdUnitState]):
  managed_classes = [SystemdUnit]
  store: JsonStore

  def __init__(self):
    super().__init__()
    self.store = JsonStore("/var/cache/koti/SystemdUnitManager.json")

  def assert_installable(self, item: SystemdUnit, model: ConfigModel):
    pass

  def install(self, items: list[SystemdUnit], model: ConfigModel):
    if len(items) > 0: shell(f"systemctl daemon-reload")
    users = set([item.user for item in items])
    for username in users:
      items_for_user = [item for item in items if item.user == username]
      shell(f"{self.systemctl_for_user(username)} enable --now {" ".join([item.name for item in items_for_user])}")
      units_store: JsonCollection[str] = self.store.collection(username or "$system")
      units_store.add_all([item.name for item in items])

  def installed(self, model: ConfigModel) -> list[SystemdUnit]:
    result: list[SystemdUnit] = []
    managed_users = [(username if username != "$system" else None) for username in self.store.keys()]
    for username in managed_users:
      units_store: JsonCollection[str] = self.store.collection(username or "$system")
      result += [SystemdUnit(name, username) for name in units_store.elements()]
    return result

  def state_current(self, item: SystemdUnit) -> SystemdUnitState | None:
    enabled: bool = shell_success(f"{self.systemctl_for_user(item.user)} is-enabled {item.name}")
    return SystemdUnitState() if enabled else None

  def state_target(self, item: SystemdUnit, model: ConfigModel, planning: bool) -> SystemdUnitState:
    return SystemdUnitState()

  def plan_install(self, items: list[ConfigItemToInstall[SystemdUnit, SystemdUnitState]]) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []
    users = set([item.user for item, current, target in items])
    for username in users:
      items_for_user = [item for item, current, target in items if item.user == username]
      units_store: JsonCollection[str] = self.store.collection(username or "$system")
      result.append(ExecutionPlan(
        items = items_for_user,
        description = f"{GREEN}enable systemd unit(s)",
        actions = [
          ShellAction(f"systemctl daemon-reload"),
          ShellAction(f"{self.systemctl_for_user(username)} enable --now {" ".join([item.name for item in items_for_user])}"),
          lambda: units_store.add_all([item.name for item in items_for_user]),
        ]
      ))
    return result

  def plan_uninstall(self, items: list[ConfigItemToUninstall[SystemdUnit, SystemdUnitState]]) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []
    users = set([item.user for item, current in items])
    for username in users:
      items_for_user = [item for item, current in items if item.user == username]
      units_store: JsonCollection[str] = self.store.collection(username or "$system")
      result.append(ExecutionPlan(
        items = items_for_user,
        description = f"{RED}disable systemd units",
        actions = [
          ShellAction(f"systemctl daemon-reload"),
          ShellAction(f"{self.systemctl_for_user(username)} disable --now {" ".join([item.name for item in items_for_user])}"),
          lambda: units_store.remove_all([item.name for item in items_for_user])
        ]
      ))
    return result

  def systemctl_for_user(self, user: str | None):
    return f"systemctl --user -M {user}@" if user is not None else "systemctl"

  def finalize(self, model: ConfigModel):
    previously_managed_users = [(username if username != "$system" else None) for username in self.store.keys()]
    currently_managed_users = set([item.user for phase in model.phases for item in phase.items if isinstance(item, SystemdUnit)])
    for username in previously_managed_users:
      if username in currently_managed_users:
        units_for_user = [item.name for phase in model.phases for item in phase.items if isinstance(item, SystemdUnit) and item.user == username]
        units_store: JsonCollection[str] = self.store.collection(username or "$system")
        units_store.replace_all(units_for_user)
      else:
        self.store.remove(username)
