from hashlib import sha256
import re

from koti.utils.shell import shell, shell_output
from koti.items.flatpak_package import FlatpakPackage
from koti.core import ConfigManager, ConfigModel
from koti.items.flatpak_repo import FlatpakRepo


class FlatpakManager(ConfigManager[FlatpakRepo | FlatpakPackage]):
  managed_classes = [FlatpakRepo, FlatpakPackage]

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
      shell(f"flatpak install {" ".join(item.id for item in package_items)}", check = False)

  def uninstall(self, items: list[FlatpakRepo | FlatpakPackage], model: ConfigModel):
    repo_items = [item for item in items if isinstance(item, FlatpakRepo)]
    package_items = [item for item in items if isinstance(item, FlatpakPackage)]

    for item in repo_items:
      shell(f"flatpak remote-delete --force '{item.name}'", check = False)
    if package_items:
      shell(f"flatpak uninstall {" ".join(item.id for item in package_items)}")
      shell("flatpak uninstall --unused")

  def installed(self, model: ConfigModel) -> list[FlatpakRepo | FlatpakPackage]:
    installed_packages = [FlatpakPackage(name) for name in shell_output("flatpak list --app --columns application").splitlines()]
    installed_repos = [FlatpakRepo(name) for name in shell_output("flatpak remotes --columns name").splitlines()]
    return [*installed_repos, *installed_packages]

  def checksum_current(self, item: FlatpakRepo | FlatpakPackage) -> str:
    if isinstance(item, FlatpakRepo):
      url = self.get_installed_repo_url(item) or "<none>"
      return sha256(url.encode()).hexdigest()
    else:
      installed = self.is_package_installed(item.id)
      return sha256(str(installed).encode()).hexdigest()

  def checksum_target(self, item: FlatpakRepo | FlatpakPackage, model: ConfigModel) -> str:
    if isinstance(item, FlatpakRepo):
      assert item.repo_url is not None
      return sha256(item.repo_url.encode()).hexdigest()
    else:
      return sha256(str(True).encode()).hexdigest()

  def get_installed_repo_url(self, item: FlatpakRepo) -> str | None:
    for line in shell_output("flatpak remotes --columns name,url").splitlines():
      split = re.split("\\s+", line)
      if split[0] == item.name:
        return split[1]
    return None

  def is_package_installed(self, package: str) -> bool:
    return package in shell_output("flatpak list --app --columns application").splitlines()
