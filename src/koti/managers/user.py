from __future__ import annotations

from hashlib import sha256
from typing import Generator, Sequence

from koti import Action
from koti.utils.shell import shell, shell_output
from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.user import User
from koti.utils.json_store import JsonCollection, JsonStore


class UserState(ConfigItemState):
  def __init__(self, has_password: bool):
    self.has_password = has_password

  def sha256(self) -> str:
    sha256_hash = sha256()
    sha256_hash.update(str(self.has_password).encode())
    return sha256_hash.hexdigest()


class UserManager(ConfigManager[User, UserState]):
  managed_classes = [User]
  managed_users_store: JsonCollection[str]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/UserManager.json")
    self.managed_users_store = store.collection("managed_users")

  def assert_installable(self, item: User, model: ConfigModel):
    pass

  def state_target(self, item: User, model: ConfigModel, dryrun: bool) -> UserState:
    return UserState(has_password = item.password or True)

  def state_current(self, item: User) -> UserState | None:
    user_shells: dict[str, str] = dict([line.split(":") for line in shell_output("getent passwd | cut -d: -f1,7").splitlines()])
    if item.username not in user_shells.keys():
      return None  # user not in /etc/passwd
    groups: list[str] = []
    for line in shell_output("getent group | cut -d: -f1,4").splitlines():
      [group, users_csv] = line.split(":")
      if item.username in users_csv.split(","):
        groups.append(group)
    pw_status = shell_output(f"passwd --status {item.username}").split(" ")[1]
    return UserState(has_password = pw_status == "P")

  def plan_install(self, items_to_check: Sequence[User], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    for user in items_to_check:
      current, target = self.states(user, model, dryrun)
      if current == target:
        continue
      assert target is not None

      if current is None:
        yield Action(
          installs = [user],
          description = f"create new user {user.username}",
          execute = lambda: self.create_user(user.username, target.has_password),
        )
      elif not current.has_password and target.has_password:
        yield Action(
          installs = [user],
          description = f"set new password for {user.username}",
          execute = lambda: self.update_password(user.username),
        )
      elif current.has_password and not target.has_password:
        yield Action(
          installs = [user],
          description = f"remove password for {user.username}",
          execute = lambda: self.remove_password(user.username),
        )

  def plan_cleanup(self, items_to_keep: Sequence[User], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    managed_users = [User(username) for username in self.managed_users_store.elements()]
    for user in managed_users:
      if user in items_to_keep:
        continue
      yield Action(
        removes = [user],
        description = f"delete user {user.username}",
        additional_info = "the homedir will not be touched by this operation",
        execute = lambda: self.delete_user(user),
      )

  def create_user(self, username: str, with_password: bool):
    shell(f"useradd {username}")
    if with_password:
      shell(f"passwd {username}")
    self.managed_users_store.add(username)

  def update_password(self, username: str):
    shell(f"passwd {username}")
    self.managed_users_store.add(username)

  def remove_password(self, username: str):
    shell(f"passwd --lock {username}")
    self.managed_users_store.add(username)

  def delete_user(self, user: User):
    shell(f"userdel {user.username}")
    self.managed_users_store.remove(user.username)

  def finalize(self, model: ConfigModel, dryrun: bool):
    if not dryrun:
      self.managed_users_store.replace_all([item.username for group in model.configs for item in group.provides if isinstance(item, User)])
