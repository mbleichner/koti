from __future__ import annotations

from hashlib import sha256
from typing import Generator, Sequence

from koti.utils.shell import shell, shell_output
from koti.model import Action, ConfigItemState, ConfigManager, ConfigModel, Phase
from koti.items.user_shell import UserShell
from koti.utils.json_store import JsonCollection, JsonStore
from koti.managers.user import UserManager


class UserShellState(ConfigItemState):
  def __init__(self, shell: str, ):
    self.shell = shell

  def sha256(self) -> str:
    sha256_hash = sha256()
    sha256_hash.update(self.shell.encode())
    return sha256_hash.hexdigest()


class UserShellManager(ConfigManager[UserShell, UserShellState]):
  managed_classes = [UserShell]
  cleanup_order:float = UserManager.cleanup_order  # these should usually stick together
  managed_users_store: JsonCollection[str]
  cleanup_order_before = [UserManager]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/UserShellManager.json")
    self.managed_users_store = store.collection("managed_users")

  def assert_installable(self, item: UserShell, model: ConfigModel):
    assert item.shell is not None, f"{item}: no shell specified"

  def get_state_target(self, item: UserShell, model: ConfigModel, phase: Phase) -> UserShellState:
    assert item.shell is not None
    return UserShellState(shell = item.shell)

  def get_state_current(self, item: UserShell) -> UserShellState | None:
    user_shells: dict[str, str] = self.get_all_user_shells()
    if item.username not in user_shells.keys():
      return None  # user not in /etc/passwd
    return UserShellState(shell = user_shells[item.username])

  def get_install_actions(self, items_to_check: Sequence[UserShell], model: ConfigModel, phase: Phase) -> Generator[Action]:
    for item in items_to_check:
      current, target = self.get_states(item, model, phase)
      if current == target:
        continue
      yield Action(
        updates = [item],
        description = f"update shell for user {item.username} to {target.shell}",
        execute = lambda: self.update_user_shell(item, target.shell),
      )

  def get_cleanup_actions(self, items_to_keep: Sequence[UserShell], model: ConfigModel, phase: Phase) -> Generator[Action]:
    for item in self.get_managed_items(model):
      if item in items_to_keep:
        continue
      yield Action(
        removes = [item],
        description = f"reset shell for user {item.username} to /usr/bin/nologin",
        execute = lambda: self.update_user_shell(item, "/usr/bin/nologin"),
      )

  def get_all_user_shells(self) -> dict[str, str]:
    return dict([line.split(":") for line in shell_output("getent passwd | cut -d: -f1,7").splitlines()])

  def update_user_shell(self, user: UserShell, new_shell: str | None):
    shell(f"usermod --shell {new_shell or "/usr/bin/nologin"} {user.username}")
    self.managed_users_store.add(user.username)

  def get_managed_items(self, model: ConfigModel) -> list[UserShell]:
    result: list[UserShell] = []
    currently_managed_users = set([item.username for group in model.configs for item in group.provides if isinstance(item, UserShell)])
    previously_managed_users = self.managed_users_store.elements()
    all_user_shells = self.get_all_user_shells()
    for username in {*previously_managed_users, *currently_managed_users}:
      user_shell = all_user_shells.get(username, None)
      if user_shell is not None:
        result.append(UserShell(username, user_shell))
    return result

  def finalize(self, model: ConfigModel, phase: Phase):
    if phase == "execution":
      usernames = set([item.username for group in model.configs for item in group.provides if isinstance(item, UserShell)])
      self.managed_users_store.replace_all(list(usernames))
