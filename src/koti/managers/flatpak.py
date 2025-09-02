from hashlib import sha256
import re
from typing import Sequence

from koti import ConfigItemToInstall, ConfigItemToUninstall, ExecutionPlan
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

  def installed(self, model: ConfigModel) -> list[FlatpakRepo | FlatpakPackage]:
    if not shell_success("flatpak --version"):
      if model.contains(lambda item: isinstance(item, FlatpakPackage)):
        self.warnings.append(f"{RED}could not query installed flatpak packages due to missing flatpak installation")
      return []
    installed_packages = [FlatpakPackage(name) for name in shell_output("flatpak list --app --columns application").splitlines()]
    installed_repos = [FlatpakRepo(name) for name in shell_output("flatpak remotes --columns name").splitlines()]
    return [*installed_repos, *installed_packages]

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

  def state_target(self, item: FlatpakRepo | FlatpakPackage, model: ConfigModel, planning: bool) -> FlatpakRepoState | FlatpakPackageState:
    if isinstance(item, FlatpakRepo):
      assert item.repo_url is not None
      return FlatpakRepoState(repo_url = item.repo_url)
    else:
      return FlatpakPackageState()

  def plan_install(self, items: list[ConfigItemToInstall[FlatpakRepo | FlatpakPackage, FlatpakRepoState | FlatpakPackageState]]) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []
    repo_items = [item for item, current, target in items if isinstance(item, FlatpakRepo)]
    package_items = [item for item, current, target in items if isinstance(item, FlatpakPackage)]
    if repo_items:
      installed_remotes = shell_output("flatpak remotes --columns name").splitlines()
      for repo_item in repo_items:
        already_installed = repo_item.name in installed_remotes
        result.append(ExecutionPlan(
          items = [repo_item],
          description = f"{YELLOW}update flatpak repo" if already_installed else f"{GREEN}install flatpak repo",
          actions = [
            lambda: self.update_remote(repo_item, already_installed = already_installed)
          ],
        ))
    if package_items:
      result.append(ExecutionPlan(
        items = package_items,
        description = f"{GREEN}install flatpak package(s)",
        actions = [
          ShellAction(f"flatpak install {" ".join(item.id for item in package_items)}")
        ],
      ))
    return result

  def plan_uninstall(self, items: list[ConfigItemToUninstall[FlatpakRepo | FlatpakPackage, FlatpakRepoState | FlatpakPackageState]]) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []
    repo_items = [item for item, current in items if isinstance(item, FlatpakRepo)]
    package_items = [item for item, current in items if isinstance(item, FlatpakPackage)]
    if package_items:
      result.append(ExecutionPlan(
        items = package_items,
        description = f"{RED}uninstall flatpak package(s)",
        actions = [
          ShellAction(f"flatpak uninstall {" ".join(item.id for item in package_items)} && flatpak uninstall --unused")
        ],
      ))
    for item in repo_items:
      result.append(ExecutionPlan(
        items = package_items,
        description = f"{RED}uninstall flatpak remote",
        actions = [
          ShellAction(f"flatpak remote-delete --force '{item.name}'")
        ],
      ))
    return result

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
