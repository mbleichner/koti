from __future__ import annotations

import os.path
import pwd
from hashlib import sha256

from koti.utils.shell import shell, shell_output
from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.user import User
from koti.utils.json_store import JsonCollection, JsonStore
from koti.utils.colors import *


class UserState(ConfigItemState):
  def __init__(
    self,
    groups: list[str],
    shell: str,
    home_dir: str,
    home_exists: bool,
  ):
    self.groups = groups
    self.shell = shell
    self.home_dir = home_dir
    self.home_exists = home_exists

  def hash(self) -> str:
    sha256_hash = sha256()
    for group in self.groups:
      sha256_hash.update(group.encode())
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
      groups = item.groups,
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
      groups = groups,
      shell = shell,
      home_dir = home,
      home_exists = os.path.isdir(home),
    )

  def diff(self, current: UserState | None, target: UserState | None) -> list[str]:
    if current is None:
      return [f"{GREEN}user will be created"]
    if target is None:
      return [f"{RED}user will be removed from the system {ENDC}(home directory will not be touched to prevent accidental data loss)"]

    result: list[str] = []
    groups_to_remove = set(current.groups).difference(target.groups)
    if len(groups_to_remove) > 0:
      result.append(f"{RED}group(s) will be removed from user: {", ".join(groups_to_remove)}")
    groups_to_add = set(target.groups).difference(current.groups)
    if len(groups_to_add) > 0:
      result.append(f"{GREEN}group(s) will be added to user: {", ".join(groups_to_add)}")
    if current.shell != target.shell:
      result.append(f"{YELLOW}shell will be changed to {target.shell}")
    if current.home_exists != target.home_exists:
      result.append(f"{GREEN}home directory will be created in {target.home_dir}")
    if current.home_dir != target.home_dir:
      result.append(f"{YELLOW}home directory will be set to {target.home_dir}")
    return result

  def install(self, items: list[User], model: ConfigModel):
    for user in items:
      target = self.state_target(user, model, planning = False)
      current = self.state_current(user)

      # create user if necessary
      if current is None:
        shell(f"useradd -d {target.home_dir} -s {target.shell} {user.username}")
      current = self.state_current(user)
      assert current is not None, f"user {user.username} could not be created"

      # update homedir and/or shell
      if current.shell != target.shell or current.home_dir != target.home_dir:
        shell(f"usermod --home {target.home_dir} --shell {target.shell} {user.username}")

      # update groups
      groups_to_add = set(target.groups).difference(current.groups)
      groups_to_remove = set(current.groups).difference(target.groups)
      for group in groups_to_add:
        shell(f"gpasswd --add {user.username} {group}")
      for group in groups_to_remove:
        shell(f"gpasswd --delete {user.username} {group}")

      # create homedir if missing
      if not os.path.isdir(target.home_dir):
        getpwnam = pwd.getpwnam(user.username)
        uid = getpwnam.pw_uid
        gid = getpwnam.pw_gid
        os.mkdir(target.home_dir)
        os.chown(target.home_dir, uid, gid)

      self.managed_users_store.add(user.username)

  def uninstall(self, items: list[User]):
    for user in items:
      current = self.state_current(user)
      if current is None: return
      self.warnings.append(f"{YELLOW}home directory of user '{user.username}' won't get removed by koti to prevent accidental data loss - please delete it manually")
      shell(f"userdel {user.username}")
      self.managed_users_store.remove(user.username)

  def finalize(self, model: ConfigModel):
    usernames = [item.username for phase in model.phases for item in phase.items if isinstance(item, User)]
    self.managed_users_store.replace_all(usernames)
