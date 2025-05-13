from subprocess import DEVNULL

from definitions import ConfigItem, ConfigManager
from utils import get_output, interactive


class Package(ConfigItem):
  def __init__(self, identifier: str, url: str = None):
    super().__init__(identifier)
    self.url = url

  def __str__(self):
    if self.url is not None:
      return f"Package('{self.identifier}', url = ...)"
    return f"Package('{self.identifier}')"


class PacmanAdapter:
  def update_system(self):
    pass

  def list_explicit_packages(self) -> list[str]:
    pass

  def list_installed_packages(self) -> list[str]:
    pass

  def install(self, packages: list[str]):
    pass

  def install_from_url(self, urls: list[str]):
    pass

  def mark_as_explicit(self, packages: list[str]):
    pass

  def mark_as_dependency(self, packages: list[str]):
    pass

  def prune_unneeded(self):
    pass


class PacmanLikeSyntax(PacmanAdapter):
  command: str

  def __init__(self, command: str):
    self.command = command

  def update_system(self):
    get_output(f"{self.command} -Syu")

  def list_explicit_packages(self) -> list[str]:
    return self.parse_pkgs(get_output(f"{self.command} -Qqe", check = False))

  def list_installed_packages(self) -> list[str]:
    return self.parse_pkgs(get_output(f"{self.command} -Qq", check = False))

  def install(self, packages: list[str]):
    if packages:
      interactive(f"{self.command} -S {" ".join(packages)}")

  def install_from_url(self, urls: list[str]):
    if urls:
      interactive(f"{self.command} -U {" ".join(urls)}")

  def mark_as_explicit(self, packages: list[str]):
    if packages:
      interactive(f"{self.command} -D --asexplicit {" ".join(packages)}")

  def mark_as_dependency(self, packages: list[str]):
    if packages:
      interactive(f"{self.command} -D --asdeps {" ".join(packages)}")

  def prune_unneeded(self):
    # https://wiki.archlinux.org/title/Pacman/Tips_and_tricks
    # Produziert sonst nen Haufen Warnmeldungen, deshalb wird stderr unterdrückt
    interactive(f"{self.command} -Qqd | {self.command} -Rsu -", stderr = DEVNULL)

  def parse_pkgs(self, output: str) -> list[str]:
    return [pkg for pkg in output.split("\n") if pkg]


class PackageManager(ConfigManager[Package]):
  managed_classes = [Package]

  def __init__(self, delegate: PacmanAdapter):
    super().__init__()
    self.delegate = delegate

  def check_configuration(self, item: Package) -> str | None:
    return ""

  def execute_phase(self, items: list[Package]):
    url_items = [item for item in items if item.url is not None]
    repo_items = [item for item in items if item.url is None]
    installed_packages = self.delegate.list_installed_packages()

    additional_urls = [item.url for item in url_items if item.identifier not in installed_packages]
    self.delegate.install_from_url(additional_urls)

    additional_repo_packages = [item.identifier for item in repo_items]
    self.delegate.install([pkg for pkg in additional_repo_packages if pkg not in installed_packages])

    explicit_packages = self.delegate.list_explicit_packages()
    desired_packages = [item.identifier for item in items]
    self.delegate.mark_as_explicit([pkg for pkg in desired_packages if pkg not in explicit_packages])

  def finalize(self, all_items: list[Package]):
    desired = [pkg.identifier for pkg in all_items]
    explicit = self.delegate.list_explicit_packages()
    self.delegate.mark_as_dependency([pkg for pkg in explicit if pkg not in desired])
    self.delegate.prune_unneeded()
