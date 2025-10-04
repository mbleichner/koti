from __future__ import annotations

import os.path
import pwd
from hashlib import sha256
from typing import Generator, Sequence

from koti import Action
from koti.utils.shell import shell, shell_output
from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.user import User
from koti.utils.json_store import JsonCollection, JsonStore
from koti.utils.logging import logger


class UserState(ConfigItemState):
  def __init__(
    self,
    shell: str,
    home_dir: str,
    home_exists: bool,
    has_password: bool,
  ):
    self.shell = shell
    self.home_dir = home_dir
    self.home_exists = home_exists
    self.has_password = has_password

  def sha256(self) -> str:
    sha256_hash = sha256()
    sha256_hash.update(self.shell.encode())
    sha256_hash.update(self.home_dir.encode())
    sha256_hash.update(str(self.home_exists).encode())
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
    return UserState(
      shell = item.shell or "/usr/bin/nologin",
      home_dir = item.home or f"/home/{item.username}",
      has_password = item.password or True,
      home_exists = True,
    )

  def state_current(self, item: User) -> UserState | None:
    user_shells: dict[str, str] = dict([line.split(":") for line in shell_output("getent passwd | cut -d: -f1,7").splitlines()])
    user_homes: dict[str, str] = dict([line.split(":") for line in shell_output("getent passwd | cut -d: -f1,6").splitlines()])
    if item.username not in user_homes.keys():
      return None  # user not in /etc/passwd
    groups: list[str] = []
    for line in shell_output("getent group | cut -d: -f1,4").splitlines():
      [group, users_csv] = line.split(":")
      if item.username in users_csv.split(","):
        groups.append(group)
    home = user_homes[item.username]
    shell = user_shells[item.username]
    pw_status = shell_output(f"passwd --status {item.username}").split(" ")[1]
    return UserState(
      shell = shell,
      home_dir = home,
      home_exists = os.path.isdir(home),
      has_password = pw_status == "P",
    )

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
          execute = lambda: self.create_user(user, target),
        )
        continue

      updates = [line for line in [
        f"shell: {current.shell} => {target.shell}" if current.shell != target.shell else None,
        f"homedir: {current.home_dir} => {target.home_dir}" if current.home_dir != target.home_dir else None,
        f"create homedir {user.home}" if target.home_exists and not current.home_exists else None,
        f"password: {current.has_password} => {target.has_password}" if current.has_password != target.has_password else None,
      ] if line is not None]

      if updates:
        yield Action(
          updates = [user],
          description = f"update user {user.username}",
          additional_info = updates,
          execute = lambda: self.update_user(user, current, target),
        )

  def plan_cleanup(self, items_to_keep: Sequence[User], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    managed_users = [User(username) for username in self.managed_users_store.elements()]
    for user in managed_users:
      if user in items_to_keep:
        continue
      yield Action(
        removes = [user],
        description = f"delete user {user.username}",
        additional_info = "to prevent accidental data loss, koti will not delete the user homedir",
        execute = lambda: self.delete_user(user, dryrun),
      )

  def create_user(self, user: User, target: UserState):
    shell(f"useradd --create-home --home-dir {target.home_dir} --shell {target.shell} {user.username}")
    shell(f"passwd {user.username}")
    self.managed_users_store.add(user.username)

  def update_user(self, user: User, current: UserState, target: UserState):
    if current.home_dir != target.home_dir:
      shell(f"usermod --home {target.home_dir}")
    if current.shell != target.shell:
      shell(f"usermod --shell {target.shell} {user.username}")
    if current.has_password != target.has_password:
      shell(f"passwd {user.username}" if target.has_password else f"passwd --lock {user.username}")
    if target.home_exists and not current.home_exists:
      pwnam = pwd.getpwnam(user.username)
      uid = pwnam.pw_uid
      gid = pwnam.pw_gid
      os.mkdir(target.home_dir)
      os.chown(target.home_dir, uid, gid)
    self.managed_users_store.add(user.username)

  def delete_user(self, user: User, dryrun: bool):
    shell(f"userdel {user.username}")
    self.managed_users_store.remove(user.username)
    if not dryrun:
      logger.warn(f"the homedir of user {user.username} has not been deleted to prevent accidental data loss - please do it manually")

  def finalize(self, model: ConfigModel, dryrun: bool):
    if not dryrun:
      self.managed_users_store.replace_all([item.username for phase in model.phases for item in phase.items if isinstance(item, User)])
