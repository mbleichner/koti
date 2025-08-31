from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.package import Package
from koti.items.pacman_key import PacmanKey
from koti.utils import JsonCollection, JsonStore
from koti.utils.shell import shell, shell_output, shell_success
from koti.utils.colors import *


class PacmanAdapter:
  extra_args: str
  pacman: str

  def __init__(self, pacman: str = "pacman", extra_args: str = ""):
    self.pacman = pacman
    self.extra_args = extra_args

  def list_explicit_packages(self) -> list[str]:
    return self.parse_pkgs(shell_output(f"pacman -Qqe", check = False))

  def list_installed_packages(self) -> list[str]:
    return self.parse_pkgs(shell_output(f"pacman -Qq", check = False))

  def install(self, packages: list[str]):
    if packages:
      shell(f"{self.pacman} -Syu {self.extra_args} {" ".join(packages)}")

  def install_from_url(self, urls: list[str]):
    if urls:
      shell(f"pacman -U {self.extra_args} {" ".join(urls)}")

  def mark_as_explicit(self, packages: list[str]):
    if packages:
      shell(f"pacman -D --asexplicit {self.extra_args} {" ".join(packages)}")

  def mark_as_dependency(self, packages: list[str]):
    if packages:
      shell(f"pacman -D --asdeps {self.extra_args} {" ".join(packages)}")

  def prune_unneeded(self):
    unneeded_packages = self.parse_pkgs(shell_output(f"{self.pacman} -Qdttq", check = False))
    if len(unneeded_packages) > 0:
      shell(f"pacman -Rns {self.extra_args} {" ".join(unneeded_packages)}")

  def parse_pkgs(self, output: str) -> list[str]:
    if "there is nothing to do" in output: return []
    return [pkg for pkg in output.split("\n") if pkg]


class PackageState(ConfigItemState):
  def hash(self) -> str:
    return "-"


class PacmanKeyState(ConfigItemState):
  def hash(self) -> str:
    return "-"


class PacmanPackageManager(ConfigManager[Package, PackageState]):
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

  def assert_installable(self, item: Package, model: ConfigModel):
    if item.url is not None:
      self.warnings.append(f"the package '{item.name}' is installed via URL, but might later get {CYAN}updated to a different version by pacman{ENDC} if also contained in a package repository")

  def state_current(self, item: Package) -> PackageState | None:
    installed: bool = item.name in self.explicit_packages_on_system
    return PackageState() if installed else None

  def state_target(self, item: Package, model: ConfigModel, planning: bool) -> PackageState:
    return PackageState()

  def diff(self, current: PackageState | None, target: PackageState | None) -> list[str]:
    if current is None:
      return [f"{GREEN}package will be installed (--asexplicit)"]
    if target is None:
      return [f"{RED}package will be removed (--asdeps)"]
    return []

  def install(self, items: list[Package], model: ConfigModel):
    installed_packages = self.delegate.list_installed_packages()
    explicit_packages = self.delegate.list_explicit_packages()

    additional_items_from_urls: list[Package] = []
    additional_items_from_script: list[Package] = []
    additional_items_from_repo: list[Package] = []
    for item in items:
      if item.name in installed_packages:
        continue
      if item.url is not None:
        additional_items_from_urls.append(item)
      elif item.script is not None:
        additional_items_from_script.append(item)
      else:
        additional_items_from_repo.append(item)

    for item in additional_items_from_script:
      if item.script: item.script(model)

    self.delegate.install_from_url(
      urls = [item.url for item in additional_items_from_urls if item.url is not None],
    )

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

  def uninstall(self, items: list[Package]):
    package_names = [pkg.name for pkg in items]
    self.delegate.mark_as_dependency(package_names)
    self.managed_packages_store.remove_all(package_names)
    self.delegate.prune_unneeded()
    self.explicit_packages_on_system = set(self.delegate.list_explicit_packages())

  def finalize(self, model: ConfigModel):
    packages = [item.name for phase in model.phases for item in phase.items if isinstance(item, Package)]
    self.managed_packages_store.replace_all(packages)


class PacmanKeyManager(ConfigManager[PacmanKey, PacmanKeyState]):
  managed_classes = [PacmanKey]

  def assert_installable(self, item: PacmanKey, model: ConfigModel):
    pass

  def install(self, items: list[PacmanKey], model: ConfigModel):
    for item in items:
      print(f"installing pacman-key {item.key_id} from {item.key_server}")
      shell(f"sudo pacman-key --recv-keys {item.key_id} --keyserver {item.key_server}")
      shell(f"sudo pacman-key --lsign-key {item.key_id}")

  def uninstall(self, items: list[PacmanKey]):
    pass

  def installed(self, model: ConfigModel) -> list[PacmanKey]:
    return []

  def state_current(self, item: PacmanKey) -> PacmanKeyState | None:
    installed: bool = shell_success(f"pacman-key --list-keys | grep {item.key_id}")
    return PacmanKeyState() if installed else None

  def state_target(self, item: PacmanKey, model: ConfigModel, planning: bool) -> PacmanKeyState:
    return PacmanKeyState()

  def diff(self, current: PacmanKeyState | None, target: PacmanKeyState | None) -> list[str]:
    if current is None:
      return [f"{GREEN}pacman key will be installed"]
    if target is None:
      return [f"{CYAN}pacman key has been removed from the config, but will remain on the system"]
    return []

  def finalize(self, model: ConfigModel):
    pass
