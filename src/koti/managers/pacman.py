from koti import Checksums
from koti.core import ConfigManager, ConfirmModeValues, Koti
from koti.items.package import Package
from koti.items.pacman_key import PacmanKey
from koti.utils import confirm
from koti.utils.shell import shell_interactive, shell_output, shell_success


class PacmanAdapter:
  pacman: str

  def __init__(self, pacman: str = "pacman"):
    self.pacman = pacman

  def confirm_args(self, destructive: bool, confirm_mode: ConfirmModeValues):
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

  def install(self, packages: list[str], confirm_mode: ConfirmModeValues):
    if packages:
      confirm_args = self.confirm_args(destructive = False, confirm_mode = confirm_mode)
      shell_interactive(f"{self.pacman} -S {confirm_args} {" ".join(packages)}")

  def install_from_url(self, urls: list[str], confirm_mode: ConfirmModeValues):
    if urls:
      confirm_args = self.confirm_args(destructive = False, confirm_mode = confirm_mode)
      shell_interactive(f"{self.pacman} -U {confirm_args} {" ".join(urls)}")

  def mark_as_explicit(self, packages: list[str], confirm_mode: ConfirmModeValues):
    if packages:
      confirm_args = self.confirm_args(destructive = False, confirm_mode = confirm_mode)
      shell_interactive(f"{self.pacman} -D --asexplicit {confirm_args} {" ".join(packages)}")

  def mark_as_dependency(self, packages: list[str], confirm_mode: ConfirmModeValues):
    if packages:
      confirm_args = self.confirm_args(destructive = False, confirm_mode = confirm_mode)
      shell_interactive(f"{self.pacman} -D --asdeps {confirm_args} {" ".join(packages)}")

  def prune_unneeded(self, confirm_mode: ConfirmModeValues):
    unneeded_packages = self.parse_pkgs(shell_output(f"{self.pacman} -Qdttq", check = False))
    if len(unneeded_packages) > 0:
      confirm_args = self.confirm_args(destructive = True, confirm_mode = confirm_mode)
      shell_interactive(f"{self.pacman} -Rns {confirm_args} {" ".join(unneeded_packages)}")

  def parse_pkgs(self, output: str) -> list[str]:
    if "there is nothing to do" in output: return []
    return [pkg for pkg in output.split("\n") if pkg]


class PacmanPackageManager(ConfigManager[Package]):
  managed_classes = [Package]
  delegate: PacmanAdapter

  def __init__(self, delegate: PacmanAdapter):
    super().__init__()
    self.delegate = delegate

  def check_configuration(self, item: Package, core: Koti):
    pass

  def checksums(self, core: Koti) -> Checksums[Package]:
    return PackageChecksums(self.delegate)

  def apply_phase(self, items: list[Package], core: Koti):
    url_items = [item for item in items if item.url is not None]
    repo_items = [item for item in items if item.url is None]
    installed_packages = self.delegate.list_installed_packages()
    explicit_packages = self.delegate.list_explicit_packages()

    additional_items_from_urls = [item for item in url_items if item.identifier not in installed_packages]
    self.delegate.install_from_url(
      urls = [item.url for item in additional_items_from_urls],
      confirm_mode = core.get_confirm_mode_for_item(additional_items_from_urls)
    )

    additional_items_from_repo = [item for item in repo_items if item.identifier not in installed_packages]
    self.delegate.install(
      packages = [item.identifier for item in additional_items_from_repo],
      confirm_mode = core.get_confirm_mode_for_item(additional_items_from_repo)
    )

    additional_explicit_items = [item for item in items if item.identifier not in explicit_packages]
    self.delegate.mark_as_explicit(
      packages = [item.identifier for item in additional_explicit_items],
      confirm_mode = core.get_confirm_mode_for_item(additional_explicit_items)
    )

  def cleanup(self, items: list[Package], core: Koti):
    desired = [pkg.identifier for pkg in items]
    explicit = self.delegate.list_explicit_packages()
    confirm_mode = core.get_confirm_mode_for_item(items)
    self.delegate.mark_as_dependency([pkg for pkg in explicit if pkg not in desired], confirm_mode = confirm_mode)
    self.delegate.prune_unneeded(confirm_mode = confirm_mode)


class PackageChecksums(Checksums[Package]):
  delegate: PacmanAdapter

  def __init__(self, delegate: PacmanAdapter):
    super().__init__()
    self.delegate = delegate
    self.explicit_packages = self.delegate.list_explicit_packages()

  def current(self, item: Package) -> str | int | None:
    return 1 if item.identifier in self.explicit_packages else 0

  def target(self, item: Package) -> str | int | None:
    return 1


class PacmanKeyManager(ConfigManager[PacmanKey]):
  managed_classes = [PacmanKey]

  def check_configuration(self, item: PacmanKey, core: Koti):
    pass

  def checksums(self, core: Koti) -> Checksums[PacmanKey]:
    return PacmanKeyChecksums()

  def apply_phase(self, items: list[PacmanKey], core: Koti):
    for item in items:
      confirm(
        message = f"confirm installing pacman key {item.identifier}",
        destructive = False,
        mode = core.get_confirm_mode_for_item(item),
      )
      print(f"installing pacman-key {item.key_id} from {item.key_server}")
      shell_interactive(f"sudo pacman-key --recv-keys {item.key_id} --keyserver {item.key_server}")
      shell_interactive(f"sudo pacman-key --lsign-key {item.key_id}")

  def cleanup(self, items: list[PacmanKey], core: Koti):
    pass


class PacmanKeyChecksums(Checksums[PacmanKey]):

  def current(self, item: PacmanKey) -> str | int | None:
    return 1 if shell_success(f"pacman-key --list-keys | grep {item.key_id}") else 0

  def target(self, item: PacmanKey) -> str | int | None:
    return 1
