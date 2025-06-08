from koti.core import ConfigManager, ConfirmModeValues, ExecutionState, Koti
from koti.items.package import Package
from koti.items.pacman_key import PacmanKey
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
    # https://wiki.archlinux.org/title/Pacman/Tips_and_tricks
    find_unneeded_packages_cmd = f"{self.pacman} -Qqd | {self.pacman} -Rsu --print --print-format '%e' -"
    unneeded_packages = self.parse_pkgs(shell_output(find_unneeded_packages_cmd, check = False))
    if len(unneeded_packages) > 0:
      confirm_args = self.confirm_args(destructive = True, confirm_mode = confirm_mode)
      shell_interactive(f"{self.pacman} -Rns {confirm_args} {" ".join(unneeded_packages)}")

  def parse_pkgs(self, output: str) -> list[str]:
    if "there is nothing to do" in output: return []
    return [pkg for pkg in output.split("\n") if pkg]


class PacmanPackageManager(ConfigManager[Package]):
  managed_classes = [Package]

  def __init__(self, delegate: PacmanAdapter):
    super().__init__()
    self.delegate = delegate

  def check_configuration(self, item: Package, core: Koti):
    pass

  def execute_phase(self, items: list[Package], core: Koti, state: ExecutionState):
    url_items = [item for item in items if item.url is not None]
    repo_items = [item for item in items if item.url is None]
    installed_packages = self.delegate.list_installed_packages()

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

    explicit_packages = self.delegate.list_explicit_packages()
    additional_explicit_items = [item for item in items if item.identifier not in explicit_packages]
    self.delegate.mark_as_explicit(
      packages = [item.identifier for item in additional_explicit_items],
      confirm_mode = core.get_confirm_mode_for_item(additional_explicit_items)
    )

    state.updated_items += list({*additional_items_from_urls, *additional_items_from_repo, *additional_explicit_items})

  def cleanup(self, items: list[Package], core: Koti, state: ExecutionState):
    desired = [pkg.identifier for pkg in items]
    explicit = self.delegate.list_explicit_packages()
    confirm_mode = core.get_confirm_mode_for_item(items)
    self.delegate.mark_as_dependency([pkg for pkg in explicit if pkg not in desired], confirm_mode = confirm_mode)
    self.delegate.prune_unneeded(confirm_mode = confirm_mode)


class PacmanKeyManager(ConfigManager[PacmanKey]):
  managed_classes = [PacmanKey]

  def check_configuration(self, item: PacmanKey, core: Koti):
    pass

  def execute_phase(self, items: list[PacmanKey], core: Koti, state: ExecutionState):
    for item in items:
      key_already_installed = shell_success(f"pacman-key --list-keys | grep {item.key_id}")
      if not key_already_installed:
        print(f"installing pacman-key {item.key_id} from {item.key_server}")
        shell_interactive(f"sudo pacman-key --recv-keys {item.key_id} --keyserver {item.key_server}")
        shell_interactive(f"sudo pacman-key --lsign-key {item.key_id}")
        state.updated_items += [item]

  def cleanup(self, items: list[PacmanKey], core: Koti, state: ExecutionState):
    pass
