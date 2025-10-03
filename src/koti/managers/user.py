from __future__ import annotations

import os.path
import pwd
from hashlib import sha256
from typing import Generator, Sequence

from koti import ExecutionPlan
from koti.utils.shell import shell, shell_output
from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.user import User
from koti.utils.json_store import JsonCollection, JsonStore
from koti.utils.colors import *


class UserState(ConfigItemState):
  def __init__(
    self,
    shell: str,
    home_dir: str,
    home_exists: bool,
  ):
    self.shell = shell
    self.home_dir = home_dir
    self.home_exists = home_exists

  def hash(self) -> str:
    sha256_hash = sha256()
    sha256_hash.update(self.shell.encode())
    sha256_hash.update(self.home_dir.encode())
    sha256_hash.update(str(self.home_exists).encode())
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
    home = item.home or f"/home/{item.username}"
    shell = item.shell or "/usr/bin/nologin"
    return UserState(
      shell = shell,
      home_dir = home,
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
    return UserState(
      shell = shell,
      home_dir = home,
      home_exists = os.path.isdir(home),
    )

  def plan_install(self, items_to_check: Sequence[User], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    for user in items_to_check:
      current, target = self.states(user, model, dryrun)
      assert target is not None

      if current is None:
        yield ExecutionPlan(
          installs = [user],
          description = f"{GREEN}create new user",
          execute = lambda: self.create_user(user, target),
        )

      if current is not None and current.shell != target.shell:
        yield ExecutionPlan(
          updates = [user],
          description = f"{YELLOW}update user shell",
          execute = lambda: self.fix_user_shell(user, target),
        )

      if current is not None and current.home_dir != target.home_dir:
        yield ExecutionPlan(
          updates = [user],
          description = f"{YELLOW}update user homedir",
          execute = lambda: self.fix_user_home(user, target),
        )

      if current is not None and not current.home_exists:
        yield ExecutionPlan(
          updates = [user],
          description = f"{GREEN}create user homedir",
          additional_info = target.home_dir,
          execute = lambda: self.create_user_home(user, target),
        )

  def plan_cleanup(self, items_to_keep: Sequence[User], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    managed_users = [User(username) for username in self.managed_users_store.elements()]
    for user in managed_users:
      if user in items_to_keep:
        continue
      yield ExecutionPlan(
        removes = [user],
        description = f"{RED}user will be deleted",
        execute = lambda: self.delete_user(user),
      )

  def fix_user_home(self, user: User, target: UserState):
    shell(f"usermod --home {target.home_dir}")
    self.managed_users_store.add(user.username)

  def fix_user_shell(self, user: User, target: UserState):
    shell(f"usermod --shell {target.shell} {user.username}")
    self.managed_users_store.add(user.username)

  def create_user(self, user: User, target: UserState):
    shell(f"useradd -d {target.home_dir} -s {target.shell} {user.username}")
    self.managed_users_store.add(user.username)

  def delete_user(self, user: User):
    shell(f"userdel {user.username}")
    self.managed_users_store.remove(user.username)

  def create_user_home(self, user: User, target: UserState):
    getpwnam = pwd.getpwnam(user.username)
    uid = getpwnam.pw_uid
    gid = getpwnam.pw_gid
    os.mkdir(target.home_dir)
    os.chown(target.home_dir, uid, gid)
    self.managed_users_store.add(user.username)

  def finalize(self, model: ConfigModel, dryrun: bool):
    if not dryrun:
      self.managed_users_store.replace_all([item.username for phase in model.phases for item in phase.items if isinstance(item, User)])
