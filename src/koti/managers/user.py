from __future__ import annotations

import os.path
import pwd
from hashlib import sha256
from typing import Sequence

from koti import ConfigItemToInstall, ConfigItemToUninstall, ExecutionPlan
from koti.utils.shell import ShellAction, shell_output
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

  def installed(self, model: ConfigModel) -> list[User]:
    return [User(username) for username in self.managed_users_store.elements()]

  def state_target(self, item: User, model: ConfigModel, planning: bool) -> UserState:
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

  def plan_install(self, items: list[ConfigItemToInstall[User, UserState]]) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []
    for user, current, target in items:
      if current is None:
        result.append(ExecutionPlan(
          items = [user],
          description = f"{GREEN}create new user",
          actions = [
            ShellAction(f"useradd -d {target.home_dir} -s {target.shell} {user.username}"),
            lambda: self.managed_users_store.add(user.username)
          ]
        ))

      if current is not None and current.shell != target.shell:
        result.append(ExecutionPlan(
          items = [user],
          description = f"{YELLOW}update user shell",
          actions = [
            ShellAction(f"usermod --shell {target.shell} {user.username}"),
            lambda: self.managed_users_store.add(user.username)
          ]
        ))

      if current is not None and current.home_dir != target.home_dir:
        result.append(ExecutionPlan(
          items = [user],
          description = f"{YELLOW}update user homedir",
          actions = [
            ShellAction(f"usermod --home {target.home_dir}"),
            lambda: self.managed_users_store.add(user.username)
          ]
        ))

      if current is not None and not current.home_exists:
        result.append(ExecutionPlan(
          items = [user],
          description = f"{GREEN}create user homedir",
          details = target.home_dir,
          actions = [
            lambda: self.create_homedir(user, target.home_dir),
            lambda: self.managed_users_store.add(user.username)
          ]
        ))

    return result

  def plan_uninstall(self, items: list[ConfigItemToUninstall[User, UserState]]) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []
    for user, current in items:
      result.append(ExecutionPlan(
        items = [user],
        description = f"{RED}user will be deleted",
        actions = [ShellAction(f"userdel {user.username}"),
                   lambda: self.managed_users_store.remove(user.username)
                   ]
      ))
    return result

  def create_homedir(self, user: User, homedir: str):
    getpwnam = pwd.getpwnam(user.username)
    uid = getpwnam.pw_uid
    gid = getpwnam.pw_gid
    os.mkdir(homedir)
    os.chown(homedir, uid, gid)

  def finalize(self, model: ConfigModel):
    usernames = [item.username for phase in model.phases for item in phase.items if isinstance(item, User)]
    self.managed_users_store.replace_all(usernames)
