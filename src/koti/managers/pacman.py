from __future__ import annotations

from typing import Sequence

from koti import ConfigItemToInstall, ConfigItemToUninstall, ExecutionPlan
from koti.model import ConfigItemState, ConfigManager, ConfigModel
from koti.items.package import Package
from koti.items.pacman_key import PacmanKey
from koti.utils.json_store import JsonCollection, JsonStore
from koti.utils.shell import ShellAction, shell, shell_output, shell_success
from koti.utils.colors import *


class PackageState(ConfigItemState):
  def hash(self) -> str:
    return "-"


class PacmanKeyState(ConfigItemState):
  def hash(self) -> str:
    return "-"


class PacmanPackageManager(ConfigManager[Package, PackageState]):
  managed_classes = [Package]
  ignore_manually_installed_packages: bool
  managed_packages_store: JsonCollection[str]
  explicit_packages_on_system: set[str]  # holds the list of explicitly installed packages on the system; will be updated whenever the manager adds/removes explicit packages.
  aur_helper: tuple[str, str] | None  # FIXME: besseren Type ausdenken

  def __init__(self, keep_unmanaged_packages: bool, aur_helper: tuple[str, str] | None = None):
    super().__init__()
    store = JsonStore("/var/cache/koti/PacmanPackageManager.json")
    self.aur_helper = aur_helper
    self.managed_packages_store = store.collection("managed_packages")
    self.ignore_manually_installed_packages = keep_unmanaged_packages
    self.explicit_packages_on_system = set(self.pacman_list_explicit_packages())

  def assert_installable(self, item: Package, model: ConfigModel):
    if item.url is not None:
      self.warnings.append(f"packages installed via URL might later get updated to a different version by pacman if also contained in a package repository")

  def state_current(self, item: Package) -> PackageState | None:
    installed: bool = item.name in self.explicit_packages_on_system
    return PackageState() if installed else None

  def state_target(self, item: Package, model: ConfigModel, planning: bool) -> PackageState:
    return PackageState()

  def plan_install(self, items: list[ConfigItemToInstall[Package, PackageState]]) -> Sequence[ExecutionPlan]:
    installed_packages = self.pacman_list_installed_packages()
    explicit_packages = self.pacman_list_explicit_packages()
    additional_items_from_urls: list[Package] = []
    additional_items_from_script: list[Package] = []
    additional_items_from_repo: list[Package] = []
    additional_explicit_items: list[Package] = []
    for item, current, target in items:
      if item.name not in installed_packages:
        if item.url is not None:
          additional_items_from_urls.append(item)
        elif item.script is not None:
          additional_items_from_script.append(item)
        else:
          additional_items_from_repo.append(item)
      elif item.name not in explicit_packages:
        additional_explicit_items.append(item)

    result: list[ExecutionPlan] = []
    if additional_explicit_items:
      result.append(ExecutionPlan(
        items = additional_explicit_items,
        description = f"{GREEN}marking package(s) explicitly installed",
        actions = [
          ShellAction(f"pacman -D --asexplicit {" ".join([item.name for item in additional_explicit_items])}"),
          lambda: self.add_managed_packages(additional_explicit_items),
          lambda: self.update_explicit_package_list(),
        ]
      ))
    for item in additional_items_from_script:
      assert item.script is not None, "illegal state"
      result.append(ExecutionPlan(
        items = additional_items_from_urls,
        description = f"{GREEN}installing package(s) from script",
        actions = [
          item.script,
          lambda: self.add_managed_packages(additional_items_from_urls),
          lambda: self.update_explicit_package_list(),
        ]
      ))
    if additional_items_from_urls:
      result.append(ExecutionPlan(
        items = additional_items_from_urls,
        description = f"{GREEN}installing package(s) from URL(s)",
        actions = [
          ShellAction(f"pacman -U {" ".join([item.url for item in additional_items_from_urls if item.url])}"),
          lambda: self.add_managed_packages(additional_items_from_urls),
          lambda: self.update_explicit_package_list(),
        ]
      ))
    if additional_items_from_repo:
      pacman_or_helper = self.aur_helper[0] if self.aur_helper else "pacman"
      result.append(ExecutionPlan(
        items = additional_items_from_repo,
        description = f"{GREEN}installing package(s) from repositories",
        actions = [
          ShellAction(
            f"{pacman_or_helper} -Syu {" ".join([item.name for item in additional_items_from_repo])}",
            user = self.aur_helper[1] if self.aur_helper else None,
          ),
          lambda: self.add_managed_packages(additional_items_from_repo),
          lambda: self.update_explicit_package_list(),
        ]
      ))
    return result

  def plan_uninstall(self, items: list[ConfigItemToUninstall[Package, PackageState]]) -> Sequence[ExecutionPlan]:
    items_to_remove = [item for (item, current) in items]
    return [
      ExecutionPlan(
        items = items_to_remove,
        description = f"{RED}marking package(s) non-explicitly installed",
        actions = [
          ShellAction(f"pacman -D --asdeps {" ".join([item.name for item in items_to_remove])}"),
          lambda: self.remove_managed_packages(items_to_remove),
          lambda: self.update_explicit_package_list(),
        ]
      ),
      ExecutionPlan(
        items = [],
        description = f"{RED}prune unneeded packages",
        details = f"pacman will additionally ask for confirmation before uninstalling any packages",
        actions = [
          lambda: self.pacman_prune_unneeded(),
        ],
      )
    ]

  def installed(self, model: ConfigModel) -> list[Package]:
    installed_by_koti = self.managed_packages_store.elements()
    package_names = {
      pkg for pkg in self.explicit_packages_on_system
      if not self.ignore_manually_installed_packages or pkg in installed_by_koti
    }
    return [Package(pkg) for pkg in package_names]

  def finalize(self, model: ConfigModel):
    packages = [item.name for phase in model.phases for item in phase.items if isinstance(item, Package)]
    self.managed_packages_store.replace_all(packages)

  def update_explicit_package_list(self):
    self.explicit_packages_on_system = set(self.pacman_list_explicit_packages())

  def add_managed_packages(self, items: list[Package]):
    self.managed_packages_store.add_all([item.name for item in items])

  def remove_managed_packages(self, items: list[Package]):
    self.managed_packages_store.remove_all([item.name for item in items])

  def pacman_list_explicit_packages(self) -> list[str]:
    return self.parse_pkgs(shell_output(f"pacman -Qqe", check = False))

  def pacman_list_installed_packages(self) -> list[str]:
    return self.parse_pkgs(shell_output(f"pacman -Qq", check = False))

  def pacman_prune_unneeded(self):
    unneeded_packages = self.parse_pkgs(shell_output(f"pacman -Qdttq", check = False))
    if len(unneeded_packages) > 0:
      shell(f"pacman -Rns {" ".join(unneeded_packages)}")

  def parse_pkgs(self, output: str) -> list[str]:
    if "there is nothing to do" in output: return []
    return [pkg for pkg in output.split("\n") if pkg]


class PacmanKeyManager(ConfigManager[PacmanKey, PacmanKeyState]):
  managed_classes = [PacmanKey]

  def assert_installable(self, item: PacmanKey, model: ConfigModel):
    pass

  def installed(self, model: ConfigModel) -> list[PacmanKey]:
    return []

  def state_current(self, item: PacmanKey) -> PacmanKeyState | None:
    installed: bool = shell_success(f"pacman-key --list-keys | grep {item.key_id}")
    return PacmanKeyState() if installed else None

  def state_target(self, item: PacmanKey, model: ConfigModel, planning: bool) -> PacmanKeyState:
    return PacmanKeyState()

  def plan_install(self, items: list[ConfigItemToInstall[PacmanKey, PacmanKeyState]]) -> Sequence[ExecutionPlan]:
    result: list[ExecutionPlan] = []
    for item, current, target in items:
      result.append(ExecutionPlan(
        items = [item],
        description = f"{GREEN}assign user to group",
        actions = [
          ShellAction(f"pacman-key --init"),
          ShellAction(f"pacman-key --recv-keys {item.key_id} --keyserver {item.key_server}"),
          ShellAction(f"pacman-key --lsign-key {item.key_id}"),
        ]
      ))
    return result

  def plan_uninstall(self, items: list[ConfigItemToUninstall[PacmanKey, PacmanKeyState]]) -> Sequence[ExecutionPlan]:
    return []  # FIXME

  def finalize(self, model: ConfigModel):
    pass
