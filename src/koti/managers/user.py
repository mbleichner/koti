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
    home = item.home or f"/home/{item.username}"
    shell = item.shell or "/usr/bin/nologin"

    return UserState(
      shell = shell,
      home_dir = home,
      home_exists = True,
      has_password = item.password or True,
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
      assert target is not None

      if current is None:
        yield Action(
          installs = [user],
          description = f"create new user {user.username}",
          execute = lambda: self.create_user(user, target),
        )

      # FIXME: zusammenlegen
      if current is not None and current.shell != target.shell:
        yield Action(
          updates = [user],
          description = f"update shell of user {user.username} to {user.shell}",
          execute = lambda: self.fix_user_shell(user, target),
        )

      # FIXME: zusammenlegen
      if current is not None and current.home_dir != target.home_dir:
        yield Action(
          updates = [user],
          description = f"update homedir of user {user.username} to {target.home_dir}",
          execute = lambda: self.fix_user_home(user, target),
        )

      # FIXME: zusammenlegen
      if current is not None and not current.home_exists:
        yield Action(
          updates = [user],
          description = f"create homedir for user {user.username} in {target.home_dir}",
          additional_info = target.home_dir,
          execute = lambda: self.create_user_home(user, target),
        )

      # FIXME: zusammenlegen
      if current is not None and current.has_password != target.has_password:
        yield Action(
          updates = [user],
          description = f"create homedir for user {user.username} in {target.home_dir}",
          execute = lambda: self.fix_user_password(user, target),
        )

  def plan_cleanup(self, items_to_keep: Sequence[User], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    managed_users = [User(username) for username in self.managed_users_store.elements()]
    for user in managed_users:
      if user in items_to_keep:
        continue
      yield Action(
        removes = [user],
        description = f"delete user {user.username}",
        execute = lambda: self.delete_user(user),
      )

  def fix_user_home(self, user: User, target: UserState):
    shell(f"usermod --home {target.home_dir}")
    self.managed_users_store.add(user.username)

  def fix_user_shell(self, user: User, target: UserState):
    shell(f"usermod --shell {target.shell} {user.username}")
    self.managed_users_store.add(user.username)

  def fix_user_password(self, user: User, target: UserState):
    if target.has_password:
      shell(f"passwd {user.username}")
    else:
      shell(f"passwd --lock {user.username}")
    self.managed_users_store.add(user.username)

  def create_user(self, user: User, target: UserState):
    shell(f"useradd --create-home --home-dir {target.home_dir} --shell {target.shell} {user.username}")
    shell(f"passwd {user.username}")
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
