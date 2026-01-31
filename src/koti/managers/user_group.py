from __future__ import annotations

from typing import Generator, Sequence

from koti.utils.shell import shell, shell_output
from koti.model import Action, ConfigItemState, ConfigManager, ConfigModel, SystemState
from koti.items.user_group import UserGroupAssignment
from koti.managers.user import UserManager
from koti.utils.json_store import JsonCollection, JsonStore


class UserGroupAssignmentState(ConfigItemState):
  def sha256(self) -> str:
    return "-"


class UserGroupManager(ConfigManager[UserGroupAssignment, UserGroupAssignmentState]):
  managed_classes = [UserGroupAssignment]
  cleanup_order: float = UserManager.cleanup_order  # these should usually stick together
  managed_users_store: JsonCollection[str]
  cleanup_order_before = [UserManager]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/UserGroupManager.json")
    self.managed_users_store = store.collection("managed_users")

  def assert_installable(self, item: UserGroupAssignment, model: ConfigModel):
    pass

  def get_state(self, item: UserGroupAssignment) -> UserGroupAssignmentState | None:
    for line in shell_output("getent group | cut -d: -f1,4").splitlines():
      [group, users_csv] = line.split(":")
      if group == item.group and item.username in users_csv.split(","):
        return UserGroupAssignmentState()
    return None

  def get_install_actions(self, items_to_check: Sequence[UserGroupAssignment], model: ConfigModel, system_state: SystemState) -> Generator[Action]:
    for item in items_to_check:
      current = system_state.get_state(item, UserGroupAssignmentState)
      target = UserGroupAssignmentState()
      if current == target:
        continue
      yield Action(
        installs = {item: target},
        description = f"assign user {item.username} to group {item.group}",
        execute = lambda: self.assign_group(item),
      )

  def get_cleanup_actions(self, items_to_keep: Sequence[UserGroupAssignment], model: ConfigModel, system_state: SystemState) -> Generator[Action]:
    for item in self.get_managed_items(model):
      if item in items_to_keep:
        continue
      yield Action(
        removes = [item],
        description = f"unassign {item.username} from group {item.group}",
        execute = lambda: self.unassign_group(item),
      )

  def get_managed_items(self, model: ConfigModel) -> list[UserGroupAssignment]:
    result: list[UserGroupAssignment] = []
    currently_managed_users = set([item.username for group in model.configs for item in group.provides if isinstance(item, UserGroupAssignment)])
    previously_managed_users = self.managed_users_store.elements()
    for username in {*previously_managed_users, *currently_managed_users}:
      for line in shell_output("getent group | cut -d: -f1,4").splitlines():
        [group, users_csv] = line.split(":")
        if username in users_csv.split(","):
          result.append(UserGroupAssignment(username, group))
    return result

  def assign_group(self, item: UserGroupAssignment):
    shell(f"gpasswd --add {item.username} {item.group}")
    self.managed_users_store.add(item.username)

  def unassign_group(self, item: UserGroupAssignment):
    shell(f"gpasswd --delete {item.username} {item.group}")
    # do not delete user from list of managed users here, as there might be other assignments for this user

  def finalize(self, model: ConfigModel, dryrun: bool):
    if not dryrun:
      usernames = set([item.username for group in model.configs for item in group.provides if isinstance(item, UserGroupAssignment)])
      self.managed_users_store.replace_all(list(usernames))
