from __future__ import annotations

import os
import pwd
from hashlib import sha256
from typing import Generator, Sequence

from koti.utils.logging import logger
from koti.utils.shell import shell, shell_output
from koti.model import Action, ConfigItemState, ConfigManager, ConfigModel
from koti.items.user_home import UserHome
from koti.managers.user import UserManager
from koti.utils.json_store import JsonCollection, JsonStore


class UserHomeState(ConfigItemState):
  def __init__(self, home_dir: str, home_exists: bool):
    self.home_dir = home_dir
    self.home_exists = home_exists

  def sha256(self) -> str:
    sha256_hash = sha256()
    sha256_hash.update(self.home_dir.encode())
    sha256_hash.update(str(self.home_exists).encode())
    return sha256_hash.hexdigest()


class UserHomeManager(ConfigManager[UserHome, UserHomeState]):
  managed_classes = [UserHome]
  cleanup_order: float = UserManager.cleanup_order  # these should usually stick together
  managed_users_store: JsonCollection[str]
  cleanup_order_before = [UserManager]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/UserHomeManager.json")
    self.managed_users_store = store.collection("managed_users")

  def assert_installable(self, item: UserHome, model: ConfigModel):
    assert item.homedir is not None, f"{item}: no homedir specified"

  def get_state_target(self, item: UserHome, model: ConfigModel, dryrun: bool) -> UserHomeState:
    assert item.homedir is not None
    return UserHomeState(home_dir = item.homedir, home_exists = True)

  def get_state_current(self, item: UserHome) -> UserHomeState | None:
    user_homes: dict[str, str] = self.get_all_user_homes()
    if item.username not in user_homes.keys():
      return None  # user not in /etc/passwd
    user_home = user_homes[item.username]
    return UserHomeState(home_dir = user_home, home_exists = os.path.isdir(user_home))

  def get_install_actions(self, items_to_check: Sequence[UserHome], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    for item in items_to_check:
      current, target = self.get_states(item, model, dryrun)
      if current == target:
        continue

      if (current is None or not current.home_exists) and target.home_exists:
        yield Action(
          updates = [item],
          description = f"create homedir {target.home_dir} for user {item.username}",
          execute = lambda: self.create_user_home(item.username, target.home_dir),
        )
      elif current is not None and current.home_exists and not target.home_exists:
        logger.info("to prevent accidental data loss, koti will not remove user home directories")

      if current is not None and current.home_dir != target.home_dir:
        yield Action(
          updates = [item],
          description = f"change homedir to {target.home_dir} for user {item.username}",
          execute = lambda: self.update_user_home(item.username, target.home_dir),
        )

  def get_cleanup_actions(self, items_to_keep: Sequence[UserHome], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    for item in self.get_managed_items(model):
      if item in items_to_keep:
        continue
      yield Action(
        removes = [item],
        description = f"clear homedir from /etc/passwd for user {item.username}",
        execute = lambda: self.remove_user_home(item.username, dryrun),
      )

  def get_all_user_homes(self) -> dict[str, str]:
    return dict([line.split(":") for line in shell_output("getent passwd | cut -d: -f1,6").splitlines()])

  def create_user_home(self, username: str, homedir: str):
    pwnam = pwd.getpwnam(username)
    uid = pwnam.pw_uid
    gid = pwnam.pw_gid
    os.mkdir(homedir)
    os.chown(homedir, uid, gid)
    shell(f"usermod --home {homedir} {username}")
    self.managed_users_store.add(username)

  def update_user_home(self, username: str, new_home: str):
    shell(f"usermod --home {new_home} {username}")
    self.managed_users_store.add(username)

  def remove_user_home(self, username: str, dryrun: bool):
    shell(f"usermod --home /nonexistent {username}")
    self.managed_users_store.remove(username)
    if not dryrun:
      logger.warn(f"the homedir of user {username} has not been deleted to prevent accidental data loss - please do it manually")

  def get_managed_items(self, model: ConfigModel) -> list[UserHome]:
    result: list[UserHome] = []
    currently_managed_users = set([item.username for group in model.configs for item in group.provides if isinstance(item, UserHome)])
    previously_managed_users = self.managed_users_store.elements()
    all_user_homes = self.get_all_user_homes()
    for username in {*previously_managed_users, *currently_managed_users}:
      user_home = all_user_homes.get(username, None)
      if user_home is not None:
        result.append(UserHome(username, user_home))
    return result

  def finalize(self, model: ConfigModel, dryrun: bool):
    if not dryrun:
      usernames = set([item.username for group in model.configs for item in group.provides if isinstance(item, UserHome)])
      self.managed_users_store.replace_all(list(usernames))
