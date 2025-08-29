from hashlib import sha256
import re
from typing import cast

from koti.utils.shell import shell, shell_output, shell_success
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

  def check_configuration(self, item: FlatpakRepo | FlatpakPackage, model: ConfigModel):
    if isinstance(item, FlatpakRepo):
      assert item.spec_url is not None, "missing spec_url"
      assert item.repo_url is not None, "missing repo_url"

  def install(self, items: list[FlatpakRepo | FlatpakPackage], model: ConfigModel):
    repo_items = [item for item in items if isinstance(item, FlatpakRepo)]
    package_items = [item for item in items if isinstance(item, FlatpakPackage)]

    if repo_items:
      installed_remotes = shell_output("flatpak remotes --columns name").splitlines()
      for item in repo_items:
        if item.name in installed_remotes:
          shell(f"flatpak remote-delete --force '{item.name}'")
        shell(f"flatpak remote-add '{item.name}' '{item.spec_url}'")

    if package_items:
      shell(f"flatpak install {" ".join(item.id for item in package_items)}")

  def uninstall(self, items: list[FlatpakRepo | FlatpakPackage], model: ConfigModel):
    repo_items = [item for item in items if isinstance(item, FlatpakRepo)]
    package_items = [item for item in items if isinstance(item, FlatpakPackage)]
    if package_items:
      shell(f"flatpak uninstall {" ".join(item.id for item in package_items)}")
      shell("flatpak uninstall --unused")
    for item in repo_items:
      shell(f"flatpak remote-delete --force '{item.name}'", check=False)

  def installed(self, model: ConfigModel) -> list[FlatpakRepo | FlatpakPackage]:
    if shell_success("flatpak --version"):
      installed_packages = [FlatpakPackage(name) for name in shell_output("flatpak list --app --columns application").splitlines()]
      installed_repos = [FlatpakRepo(name) for name in shell_output("flatpak remotes --columns name").splitlines()]
      return [*installed_repos, *installed_packages]
    else:
      return []

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

  def diff(self, state_current: FlatpakRepoState | FlatpakPackageState | None, state_target: FlatpakRepoState | FlatpakPackageState | None) -> list[str]:
    if isinstance(state_current, FlatpakRepoState) or isinstance(state_target, FlatpakRepoState):
      state_current = cast(FlatpakRepoState | None, state_current)
      state_target = cast(FlatpakRepoState | None, state_target)
      if state_current is None:
        return ["repo will be installed"]
      if state_target is None:
        return ["repo will be removed (TODO)"]
      return [change for change in [
        f"change repo_url from {state_current.repo_url} to {state_target.repo_url}" if state_current.repo_url != state_target.repo_url else None
      ] if change is not None]
    else:
      state_current = cast(FlatpakPackageState | None, state_current)
      state_target = cast(FlatpakPackageState | None, state_target)
      if state_current is None:
        return ["package will be installed"]
      if state_target is None:
        return ["package will be removed"]
      return []

  def get_installed_repo_url(self, item: FlatpakRepo) -> str | None:
    for line in shell_output("flatpak remotes --columns name,url").splitlines():
      split = re.split("\\s+", line)
      if split[0] == item.name:
        return split[1]
    return None

  def is_package_installed(self, package: str) -> bool:
    return package in shell_output("flatpak list --app --columns application").splitlines()
