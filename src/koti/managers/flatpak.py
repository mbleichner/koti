from hashlib import sha256
import re
from typing import Generator, Sequence

from koti import Action
from koti.utils.logging import logger
from koti.utils.shell import shell, shell_output, shell_success
from koti.items.flatpak_package import FlatpakPackage
from koti.model import ConfigItemState, ConfigManager, ConfigModel, SystemState
from koti.items.flatpak_repo import FlatpakRepo


class FlatpakRepoState(ConfigItemState):
  def __init__(self, repo_url: str):
    self.repo_url = repo_url

  def sha256(self) -> str:
    sha256_hash = sha256()
    sha256_hash.update(self.repo_url.encode())
    return sha256_hash.hexdigest()


class FlatpakPackageState(ConfigItemState):
  def sha256(self) -> str:
    return "-"


class FlatpakManager(ConfigManager[FlatpakRepo | FlatpakPackage, FlatpakRepoState | FlatpakPackageState]):
  managed_classes = [FlatpakRepo, FlatpakPackage]
  cleanup_order = 20

  def __init__(self, perform_update: bool = False):
    super().__init__()
    self.perform_update = perform_update

  def assert_installable(self, item: FlatpakRepo | FlatpakPackage, model: ConfigModel):
    if isinstance(item, FlatpakRepo):
      assert item.spec_url is not None, "missing spec_url"
      assert item.repo_url is not None, "missing repo_url"

  def get_state_current(self, item: FlatpakRepo | FlatpakPackage, system_state: SystemState) -> FlatpakRepoState | FlatpakPackageState | None:
    flatpak_available = shell_success("flatpak --version")
    if not flatpak_available:
      return None
    if isinstance(item, FlatpakRepo):
      url = self.get_installed_repo_url(item)
      return FlatpakRepoState(repo_url = url) if url else None
    else:
      installed = self.is_package_installed(item.id)
      return FlatpakPackageState() if installed else None

  def get_install_actions(self, items_to_check: Sequence[FlatpakRepo | FlatpakPackage], model: ConfigModel, system_state: SystemState) -> Generator[Action]:
    flatpak_available = shell_success("flatpak --version")
    if not flatpak_available:
      logger.error("could not accurately plan installation/cleanup of flatpak repos + packages due to (currently) missing flatpak installation")
    repo_items = [item for item in items_to_check if isinstance(item, FlatpakRepo)]
    package_items = [item for item in items_to_check if isinstance(item, FlatpakPackage)]
    yield from self.get_repo_install_actions(repo_items, model, system_state, flatpak_available)
    yield from self.get_package_install_actions(package_items, model, system_state, flatpak_available)

  def get_repo_install_actions(self, items_to_check: Sequence[FlatpakRepo], model: ConfigModel, system_state: SystemState, flatpak_available: bool) -> Generator[Action]:
    if items_to_check:
      installed_remotes = shell_output("flatpak --system remotes --columns name").splitlines() if flatpak_available else []
      for item in items_to_check:
        assert item.repo_url is not None
        current = system_state.get_state(item, FlatpakRepoState)
        target = FlatpakRepoState(repo_url = item.repo_url)
        if current == target:
          continue
        already_installed = item.name in installed_remotes
        if not already_installed:
          yield Action(
            installs = {item: target},
            description = f"install flatpak repo {item.name}",
            execute = lambda: self.update_remote(item, remove_existing = False),
          )
        else:
          yield Action(
            updates = {item: target},
            description = f"update flatpak repo {item.name}",
            execute = lambda: self.update_remote(item, remove_existing = True),
          )

  def get_package_install_actions(self, items_to_check: Sequence[FlatpakPackage], model: ConfigModel, system_state: SystemState, flatpak_available: bool) -> Generator[Action]:
    if items_to_check:
      items_to_install: list[FlatpakPackage] = []
      for item in items_to_check:
        current = system_state.get_state(item, FlatpakPackageState)
        target = FlatpakPackageState()
        if current == target:
          continue
        items_to_install.append(item)
      if items_to_install:
        yield Action(
          installs = {item: FlatpakPackageState() for item in items_to_install},
          description = f"install flatpak(s): {", ".join(item.id for item in items_to_install)}",
          execute = lambda: shell(f"flatpak --system install --system {" ".join(item.id for item in items_to_install)}"),
        )

  def get_cleanup_actions(self, items_to_keep: Sequence[FlatpakRepo | FlatpakPackage], model: ConfigModel, system_state: SystemState) -> Generator[Action]:
    flatpak_available = shell_success("flatpak --version")
    if not flatpak_available:
      if model.contains(lambda item: isinstance(item, FlatpakPackage) or isinstance(item, FlatpakRepo)):
        logger.error("could not accurately plan installation/cleanup of flatpak repos + packages due to (currently) missing flatpak installation")
      return

    installed_packages = [FlatpakPackage(name) for name in shell_output("flatpak list --app --columns application").splitlines()]
    packages_to_remove = [item for item in installed_packages if item not in items_to_keep]
    if packages_to_remove:
      yield Action(
        removes = packages_to_remove,
        description = f"uninstall flatpak(s): {", ".join(item.id for item in packages_to_remove)}",
        execute = lambda: shell(f"flatpak --system uninstall {" ".join(item.id for item in packages_to_remove)}"),
      )

    installed_repos = [FlatpakRepo(name) for name in shell_output("flatpak --system remotes --columns name").splitlines()]
    repos_to_remove = [item for item in installed_repos if item not in items_to_keep]
    for item in repos_to_remove:
      yield Action(
        removes = [item],
        description = f"uninstall flatpak remote: {item.name}",
        execute = lambda: shell(f"flatpak --system remote-delete --force '{item.name}'"),
      )

    if self.perform_update:
      yield Action(
        description = f"update all flatpak packages",
        execute = lambda: shell(f"flatpak --system update"),
      )

    yield Action(
      description = f"prune unneeded flatpak runtimes",
      execute = lambda: shell(f"flatpak --system uninstall --unused"),
    )

  def update_remote(self, item: FlatpakRepo, remove_existing: bool):
    if remove_existing:
      shell(f"flatpak --system remote-delete --force '{item.name}'")
    shell(f"flatpak --system remote-add '{item.name}' '{item.spec_url}'")

  def get_installed_repo_url(self, item: FlatpakRepo) -> str | None:
    for line in shell_output("flatpak --system remotes --columns name,url").splitlines():
      split = re.split("\\s+", line)
      if split[0] == item.name:
        return split[1]
    return None

  def is_package_installed(self, package: str) -> bool:
    return package in shell_output("flatpak --system list --app --columns application").splitlines()
