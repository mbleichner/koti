from hashlib import sha256

from koti.core import ConfigManager, ConfirmMode, ExecutionModel
from koti.items.package import Package
from koti.items.pacman_key import PacmanKey
from koti.utils import JsonCollection, JsonStore, confirm
from koti.utils.shell import shell, shell_output, shell_success


class PacmanAdapter:
  pacman: str

  def __init__(self, pacman: str = "pacman"):
    self.pacman = pacman

  def confirm_args(self, destructive: bool, confirm_mode: ConfirmMode):
    if confirm_mode == "yolo":
      return "--noconfirm"
    elif confirm_mode == "paranoid":
      return "--confirm"
    return ""

  def update_system(self):
    shell_output(f"{self.pacman} -Syu")

  def list_explicit_packages(self) -> list[str]:
    return self.parse_pkgs(shell_output(f"{self.pacman} -Qqe", check = False))

  def list_installed_packages(self) -> list[str]:
    return self.parse_pkgs(shell_output(f"{self.pacman} -Qq", check = False))

  def install(self, packages: list[str], confirm_mode: ConfirmMode):
    if packages:
      confirm_args = self.confirm_args(destructive = False, confirm_mode = confirm_mode)
      shell(f"{self.pacman} -Syu {confirm_args} {" ".join(packages)}")

  def install_from_url(self, urls: list[str], confirm_mode: ConfirmMode):
    if urls:
      confirm_args = self.confirm_args(destructive = False, confirm_mode = confirm_mode)
      shell(f"{self.pacman} -U {confirm_args} {" ".join(urls)}")

  def mark_as_explicit(self, packages: list[str], confirm_mode: ConfirmMode):
    if packages:
      confirm_args = self.confirm_args(destructive = False, confirm_mode = confirm_mode)
      shell(f"{self.pacman} -D --asexplicit {confirm_args} {" ".join(packages)}")

  def mark_as_dependency(self, packages: list[str], confirm_mode: ConfirmMode):
    if packages:
      confirm_args = self.confirm_args(destructive = False, confirm_mode = confirm_mode)
      shell(f"{self.pacman} -D --asdeps {confirm_args} {" ".join(packages)}")

  def prune_unneeded(self, confirm_mode: ConfirmMode):
    unneeded_packages = self.parse_pkgs(shell_output(f"{self.pacman} -Qdttq", check = False))
    if len(unneeded_packages) > 0:
      confirm_args = self.confirm_args(destructive = True, confirm_mode = confirm_mode)
      shell(f"{self.pacman} -Rns {confirm_args} {" ".join(unneeded_packages)}")

  def parse_pkgs(self, output: str) -> list[str]:
    if "there is nothing to do" in output: return []
    return [pkg for pkg in output.split("\n") if pkg]


class PacmanPackageManager(ConfigManager[Package]):
  managed_classes = [Package]
  delegate: PacmanAdapter
  ignore_externally_installed: bool
  managed_packages_store: JsonCollection[str]
  explicit_packages_on_system: list[str]  # holds the list of explicitly installed packages on the system; will be updated whenever the manager adds/removes explicit packages.

  def __init__(self, delegate: PacmanAdapter, ignore_externally_installed: bool):
    store = JsonStore("/var/cache/koti/PacmanPackageManager.json")
    self.managed_packages_store = store.collection("managed_packages")
    self.delegate = delegate
    self.ignore_externally_installed = ignore_externally_installed
    self.explicit_packages_on_system = self.delegate.list_explicit_packages()

  def check_configuration(self, item: Package, model: ExecutionModel):
    pass

  def checksum_current(self, item: Package) -> str:
    installed: bool = item.name in self.explicit_packages_on_system
    return sha256(str(installed).encode()).hexdigest()

  def checksum_target(self, item: Package, model: ExecutionModel) -> str:
    return sha256(str(True).encode()).hexdigest()

  def install(self, items: list[Package], model: ExecutionModel):
    url_items = [item for item in items if item.url is not None]
    repo_items = [item for item in items if item.url is None]
    installed_packages = self.delegate.list_installed_packages()
    explicit_packages = self.delegate.list_explicit_packages()

    additional_items_from_urls = [item for item in url_items if item.name not in installed_packages]
    self.delegate.install_from_url(
      urls = [item.url for item in additional_items_from_urls if item.url is not None],
      confirm_mode = model.confirm_mode(*additional_items_from_urls)
    )

    additional_items_from_repo = [item for item in repo_items if item.name not in installed_packages]
    self.delegate.install(
      packages = [item.name for item in additional_items_from_repo],
      confirm_mode = model.confirm_mode(*additional_items_from_repo)
    )

    additional_explicit_items = [item for item in items if item.name not in explicit_packages]
    self.delegate.mark_as_explicit(
      packages = [item.name for item in additional_explicit_items],
      confirm_mode = model.confirm_mode(*additional_explicit_items)
    )

    self.explicit_packages_on_system = self.delegate.list_explicit_packages()
    self.managed_packages_store.add_all([item.name for item in items])

  def list_installed_items(self) -> list[Package]:
    if self.ignore_externally_installed:
      return [Package(pkg) for pkg in self.managed_packages_store.elements()]
    else:
      return [Package(pkg) for pkg in self.explicit_packages_on_system]

  def uninstall(self, items: list[Package], model: ExecutionModel):
    confirm_mode = model.confirm_mode(*items)
    package_names = [pkg.name for pkg in items]
    self.delegate.mark_as_dependency(package_names, confirm_mode = confirm_mode)
    self.managed_packages_store.remove_all(package_names)
    self.delegate.prune_unneeded(confirm_mode = confirm_mode)
    self.explicit_packages_on_system = self.delegate.list_explicit_packages()


class PacmanKeyManager(ConfigManager[PacmanKey]):
  managed_classes = [PacmanKey]

  def check_configuration(self, item: PacmanKey, model: ExecutionModel):
    pass

  def install(self, items: list[PacmanKey], model: ExecutionModel):
    for item in items:
      confirm(
        message = f"confirm installing pacman key {item.key_id}",
        destructive = False,
        mode = model.confirm_mode(item),
      )
      print(f"installing pacman-key {item.key_id} from {item.key_server}")
      shell(f"sudo pacman-key --recv-keys {item.key_id} --keyserver {item.key_server}")
      shell(f"sudo pacman-key --lsign-key {item.key_id}")

  def uninstall(self, items: list[PacmanKey], model: ExecutionModel):
    pass

  def list_installed_items(self) -> list[PacmanKey]:
    return []

  def checksum_current(self, item: PacmanKey) -> str:
    installed: bool = shell_success(f"pacman-key --list-keys | grep {item.key_id}")
    return sha256(str(installed).encode()).hexdigest()

  def checksum_target(self, item: PacmanKey, model: ExecutionModel) -> str:
    return sha256(str(True).encode()).hexdigest()
