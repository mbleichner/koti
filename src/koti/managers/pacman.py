from hashlib import sha256

from koti import DebugMessage
from koti.core import ConfigManager, ConfigModel
from koti.items.package import Package
from koti.items.pacman_key import PacmanKey
from koti.utils import JsonCollection, JsonStore
from koti.utils.shell import shell, shell_output, shell_success


class PacmanAdapter:
  extra_args: str
  pacman: str

  def __init__(self, pacman: str = "pacman", extra_args: str = ""):
    self.pacman = pacman
    self.extra_args = extra_args

  def list_explicit_packages(self) -> list[str]:
    return self.parse_pkgs(shell_output(f"{self.pacman} -Qqe", check = False))

  def list_installed_packages(self) -> list[str]:
    return self.parse_pkgs(shell_output(f"{self.pacman} -Qq", check = False))

  def install(self, packages: list[str]):
    if packages:
      shell(f"{self.pacman} -Syu {self.extra_args} {" ".join(packages)}")

  def install_from_url(self, urls: list[str]):
    if urls:
      shell(f"{self.pacman} -U {self.extra_args} {" ".join(urls)}")

  def mark_as_explicit(self, packages: list[str]):
    if packages:
      shell(f"{self.pacman} -D --asexplicit {self.extra_args} {" ".join(packages)}")

  def mark_as_dependency(self, packages: list[str]):
    if packages:
      shell(f"{self.pacman} -D --asdeps {self.extra_args} {" ".join(packages)}")

  def prune_unneeded(self):
    unneeded_packages = self.parse_pkgs(shell_output(f"{self.pacman} -Qdttq", check = False))
    if len(unneeded_packages) > 0:
      shell(f"{self.pacman} -Rns {self.extra_args} {" ".join(unneeded_packages)}")

  def parse_pkgs(self, output: str) -> list[str]:
    if "there is nothing to do" in output: return []
    return [pkg for pkg in output.split("\n") if pkg]


class PacmanPackageManager(ConfigManager[Package]):
  managed_classes = [Package]
  delegate: PacmanAdapter
  ignore_manually_installed_packages: bool
  managed_packages_store: JsonCollection[str]
  explicit_packages_on_system: set[str]  # holds the list of explicitly installed packages on the system; will be updated whenever the manager adds/removes explicit packages.

  def __init__(self, delegate: PacmanAdapter, keep_unmanaged_packages: bool):
    super().__init__()
    store = JsonStore("/var/cache/koti/PacmanPackageManager.json")
    self.managed_packages_store = store.collection("managed_packages")
    self.delegate = delegate
    self.ignore_manually_installed_packages = keep_unmanaged_packages
    self.explicit_packages_on_system = set(self.delegate.list_explicit_packages())

  def check_configuration(self, item: Package, model: ConfigModel):
    if item.url is not None:
      self.log.append(DebugMessage(f"{item.identifier()} is installed from URL and might be reverted if also present in repos"))

  def checksum_current(self, item: Package) -> str:
    installed: bool = item.name in self.explicit_packages_on_system
    return sha256(str(installed).encode()).hexdigest()

  def checksum_target(self, item: Package, model: ConfigModel, planning: bool) -> str:
    return sha256(str(True).encode()).hexdigest()

  def install(self, items: list[Package], model: ConfigModel):
    url_items = [item for item in items if item.url is not None]
    repo_items = [item for item in items if item.url is None]
    installed_packages = self.delegate.list_installed_packages()
    explicit_packages = self.delegate.list_explicit_packages()

    additional_items_from_urls = [item for item in url_items if item.name not in installed_packages]
    self.delegate.install_from_url(
      urls = [item.url for item in additional_items_from_urls if item.url is not None],
    )

    additional_items_from_repo = [item for item in repo_items if item.name not in installed_packages]
    self.delegate.install(
      packages = [item.name for item in additional_items_from_repo],
    )

    additional_explicit_items = [item for item in items if item.name not in explicit_packages]
    self.delegate.mark_as_explicit(
      packages = [item.name for item in additional_explicit_items],
    )

    self.explicit_packages_on_system = set(self.delegate.list_explicit_packages())
    self.managed_packages_store.add_all([item.name for item in items])

  def installed(self, model: ConfigModel) -> list[Package]:
    installed_by_koti = self.managed_packages_store.elements()
    package_names = {
      pkg for pkg in self.explicit_packages_on_system
      if not self.ignore_manually_installed_packages or pkg in installed_by_koti
    }
    return [Package(pkg) for pkg in package_names]

  def uninstall(self, items: list[Package], model: ConfigModel):
    package_names = [pkg.name for pkg in items]
    self.delegate.mark_as_dependency(package_names)
    self.managed_packages_store.remove_all(package_names)
    self.delegate.prune_unneeded()
    self.explicit_packages_on_system = set(self.delegate.list_explicit_packages())


class PacmanKeyManager(ConfigManager[PacmanKey]):
  managed_classes = [PacmanKey]

  def check_configuration(self, item: PacmanKey, model: ConfigModel):
    pass

  def install(self, items: list[PacmanKey], model: ConfigModel):
    for item in items:
      print(f"installing pacman-key {item.key_id} from {item.key_server}")
      shell(f"sudo pacman-key --recv-keys {item.key_id} --keyserver {item.key_server}")
      shell(f"sudo pacman-key --lsign-key {item.key_id}")

  def uninstall(self, items: list[PacmanKey], model: ConfigModel):
    pass

  def installed(self, model: ConfigModel) -> list[PacmanKey]:
    return []

  def checksum_current(self, item: PacmanKey) -> str:
    installed: bool = shell_success(f"pacman-key --list-keys | grep {item.key_id}")
    return sha256(str(installed).encode()).hexdigest()

  def checksum_target(self, item: PacmanKey, model: ConfigModel, planning: bool) -> str:
    return sha256(str(True).encode()).hexdigest()
