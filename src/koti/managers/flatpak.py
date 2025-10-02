from hashlib import sha256
import re
from typing import Generator, Sequence

from koti import ExecutionPlan
from koti.utils.colors import *
from koti.utils.shell import ShellAction, shell, shell_output, shell_success
from koti.items.flatpak_package import FlatpakPackage
from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.flatpak_repo import FlatpakRepo


class FlatpakRepoState(ConfigItemState):
  def __init__(self, repo_url: str):
    self.repo_url = repo_url

  def hash(self) -> str:
    sha256_hash = sha256()
    sha256_hash.update(self.repo_url.encode())
    return sha256_hash.hexdigest()


class FlatpakPackageState(ConfigItemState):
  def hash(self) -> str:
    return "-"


class FlatpakManager(ConfigManager[FlatpakRepo | FlatpakPackage, FlatpakRepoState | FlatpakPackageState]):
  managed_classes = [FlatpakRepo, FlatpakPackage]

  def __init__(self):
    super().__init__()

  def assert_installable(self, item: FlatpakRepo | FlatpakPackage, model: ConfigModel):
    if isinstance(item, FlatpakRepo):
      assert item.spec_url is not None, "missing spec_url"
      assert item.repo_url is not None, "missing repo_url"

  def state_current(self, item: FlatpakRepo | FlatpakPackage) -> FlatpakRepoState | FlatpakPackageState | None:
    flatpak_available = shell_success("flatpak --version")
    if not flatpak_available:
      return None
    if isinstance(item, FlatpakRepo):
      url = self.get_installed_repo_url(item)
      return FlatpakRepoState(repo_url = url) if url else None
    else:
      installed = self.is_package_installed(item.id)
      return FlatpakPackageState() if installed else None

  def state_target(self, item: FlatpakRepo | FlatpakPackage, model: ConfigModel, dryrun: bool) -> FlatpakRepoState | FlatpakPackageState:
    if isinstance(item, FlatpakRepo):
      assert item.repo_url is not None
      return FlatpakRepoState(repo_url = item.repo_url)
    else:
      return FlatpakPackageState()

  def plan_install(self, items_to_check: Sequence[FlatpakRepo | FlatpakPackage], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    repo_items = [item for item in items_to_check if isinstance(item, FlatpakRepo)]
    package_items = [item for item in items_to_check if isinstance(item, FlatpakPackage)]

    if dryrun and not shell_success("flatpak --version"):
      if model.contains(lambda item: isinstance(item, FlatpakPackage)):
        self.warnings.append(f"{RED}could not plan installation of flatpak repos/packages due to (currently) missing flatpak installation")
      return None

    if repo_items:
      installed_remotes = shell_output("flatpak remotes --columns name").splitlines()
      for repo_item in repo_items:
        current, target = self.states(repo_item, model, dryrun)
        if current == target:
          continue
        already_installed = repo_item.name in installed_remotes
        yield ExecutionPlan(
          items = [repo_item],
          description = f"{YELLOW}update flatpak repo" if already_installed else f"{GREEN}install flatpak repo",
          actions = [
            lambda: self.update_remote(repo_item, already_installed = already_installed)
          ],
        )

    if package_items:
      items_to_install: list[FlatpakPackage] = []
      for item in package_items:
        current, target = self.states(item, model, dryrun)
        if current == target:
          continue
        items_to_install.append(item)
      if items_to_install:
        yield ExecutionPlan(
          items = items_to_install,
          description = f"{GREEN}install flatpak package(s)",
          actions = [
            ShellAction(f"flatpak install {" ".join(item.id for item in items_to_install)}")
          ],
        )

  def plan_cleanup(self, items_to_keep: Sequence[FlatpakRepo | FlatpakPackage], model: ConfigModel, dryrun: bool) -> Generator[ExecutionPlan]:
    if dryrun and not shell_success("flatpak --version"):
      if model.contains(lambda item: isinstance(item, FlatpakPackage)):
        self.warnings.append(f"{RED}could not plan cleanup of flatpak repos/packages due to (currently) missing flatpak installation")
      return None

    installed_packages = [FlatpakPackage(name) for name in shell_output("flatpak list --app --columns application").splitlines()]
    packages_to_remove = [item for item in installed_packages if item not in items_to_keep]
    if packages_to_remove:
      yield ExecutionPlan(
        items = packages_to_remove,
        description = f"{RED}uninstall flatpak package(s)",
        actions = [
          ShellAction(f"flatpak uninstall {" ".join(item.id for item in packages_to_remove)}")
        ],
      )

    installed_repos = [FlatpakRepo(name) for name in shell_output("flatpak remotes --columns name").splitlines()]
    repos_to_remove = [item for item in installed_repos if item not in items_to_keep]
    for item in repos_to_remove:
      yield ExecutionPlan(
        items = [item],
        description = f"{RED}uninstall flatpak remote",
        actions = [
          ShellAction(f"flatpak remote-delete --force '{item.name}'")
        ],
      )

    yield ExecutionPlan(
      items = [],
      description = f"{RED}prune unneeded flatpak packages",
      actions = [
        ShellAction(f"flatpak uninstall --unused")
      ],
    )

  def update_remote(self, item: FlatpakRepo, already_installed: bool):
    if already_installed:
      shell(f"flatpak remote-delete --force '{item.name}'")
    shell(f"flatpak remote-add '{item.name}' '{item.spec_url}'")

  def get_installed_repo_url(self, item: FlatpakRepo) -> str | None:
    for line in shell_output("flatpak remotes --columns name,url").splitlines():
      split = re.split("\\s+", line)
      if split[0] == item.name:
        return split[1]
    return None

  def is_package_installed(self, package: str) -> bool:
    return package in shell_output("flatpak list --app --columns application").splitlines()

  def finalize(self, model: ConfigModel):
    pass
