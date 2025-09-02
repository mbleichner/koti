from __future__ import annotations

from typing import Sequence

from koti import ConfigItemToInstall, ConfigItemToUninstall, ExecutionPlan
from koti.utils.shell import ShellAction, shell_output
from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.group import GroupAssignment
from koti.utils.json_store import JsonCollection, JsonStore
from koti.utils.colors import *


class GroupAssignmentState(ConfigItemState):
  def hash(self) -> str:
    return "-"


class GroupManager(ConfigManager[GroupAssignment, GroupAssignmentState]):
  managed_classes = [GroupAssignment]
  managed_users_store: JsonCollection[str]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/GroupManager.json")
    self.managed_users_store = store.collection("managed_users")

  def assert_installable(self, item: GroupAssignment, model: ConfigModel):
    pass

  def installed(self, model: ConfigModel) -> list[GroupAssignment]:
    result: list[GroupAssignment] = []
    currently_managed_users = set([item.username for phase in model.phases for item in phase.items if isinstance(item, GroupAssignment)])
    previously_managed_users = self.managed_users_store.elements()
    for username in {*previously_managed_users, *currently_managed_users}:
      for line in shell_output("getent group | cut -d: -f1,4").splitlines():
        [group, users_csv] = line.split(":")
        if username in users_csv.split(","):
          result.append(GroupAssignment(username, group))
    return result

  def state_target(self, item: GroupAssignment, model: ConfigModel, planning: bool) -> GroupAssignmentState:
    return GroupAssignmentState()

  def state_current(self, item: GroupAssignment) -> GroupAssignmentState | None:
    for line in shell_output("getent group | cut -d: -f1,4").splitlines():
      [group, users_csv] = line.split(":")
      if group == item.group and item.username in users_csv.split(","):
        return GroupAssignmentState()
    return None

  def plan_install(self, items: list[ConfigItemToInstall[GroupAssignment, GroupAssignmentState]]) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []
    for item, current, target in items:
      result.append(ExecutionPlan(
        items = [item],
        description = f"{GREEN}assign user to group",
        actions = [
          ShellAction(f"gpasswd --add {item.username} {item.group}"),
          lambda: self.managed_users_store.add(item.username),
        ]
      ))
    return result

  def plan_uninstall(self, items: list[ConfigItemToUninstall[GroupAssignment, GroupAssignmentState]]) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []
    for item, current in items:
      result.append(ExecutionPlan(
        items = [item],
        description = f"{RED}unassign user from group",
        actions = [
          ShellAction(f"gpasswd --delete {item.username} {item.group}"),
        ]
      ))
    return result

  def finalize(self, model: ConfigModel):
    usernames = set([item.username for phase in model.phases for item in phase.items if isinstance(item, GroupAssignment)])
    self.managed_users_store.replace_all(list(usernames))
