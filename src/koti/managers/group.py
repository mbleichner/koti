from __future__ import annotations

from typing import Generator, Sequence

from koti import ExecutionPlan
from koti.utils.shell import shell, shell_output
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

  def state_target(self, item: GroupAssignment, model: ConfigModel, dryrun: bool) -> GroupAssignmentState:
    return GroupAssignmentState()

  def state_current(self, item: GroupAssignment) -> GroupAssignmentState | None:
    for line in shell_output("getent group | cut -d: -f1,4").splitlines():
      [group, users_csv] = line.split(":")
      if group == item.group and item.username in users_csv.split(","):
        return GroupAssignmentState()
    return None

  def plan_install(self, items_to_check: Sequence[GroupAssignment], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    for item in items_to_check:
      current, target = self.states(item, model, dryrun)
      if current == target:
        continue
      yield ExecutionPlan(
        installs = [item],
        description = f"{GREEN}assign user {item.username} to group {item.group}",
        execute = lambda: self.assign_group(item),
      )

  def plan_cleanup(self, items_to_keep: Sequence[GroupAssignment], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    installed = self.installed(model)
    for item in installed:
      if item in items_to_keep:
        continue
      yield ExecutionPlan(
        removes = [item],
        description = f"{RED}unassign {item.username} from group {item.group}",
        execute = lambda: self.unassign_group(item),
      )

  def assign_group(self, item: GroupAssignment):
    shell(f"gpasswd --add {item.username} {item.group}")
    self.managed_users_store.add(item.username)

  def unassign_group(self, item: GroupAssignment):
    shell(f"gpasswd --delete {item.username} {item.group}")
    # do not delete user from list of managed users here, as there might be other assignments for this user

  def finalize(self, model: ConfigModel):
    usernames = set([item.username for phase in model.phases for item in phase.items if isinstance(item, GroupAssignment)])
    self.managed_users_store.replace_all(list(usernames))
