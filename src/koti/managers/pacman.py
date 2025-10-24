from __future__ import annotations

from koti.model import *
from koti.items.package import Package
from koti.utils.json_store import JsonCollection, JsonStore
from koti.utils.logging import logger
from koti.utils.shell import shell, shell_output, shell_success


class PackageState(ConfigItemState):
  def sha256(self) -> str:
    return "-"


class AurHelper:
  command: str
  user: str | None

  def __init__(self, command: str, user: str | None = None):
    self.command = command
    self.user = user


class PaccacheOptions:
  enabled: bool
  options: Sequence[str]

  def __init__(self, enabled: bool = False, options: str | Sequence[str] = "-ruvk2"):
    self.options = [options] if isinstance(options, str) else options
    self.enabled = enabled


class PacmanPackageManager(ConfigManager[Package, PackageState]):
  managed_classes = [Package]
  cleanup_order = 70
  ignore_manually_installed_packages: bool
  managed_packages_store: JsonCollection[str]
  explicit_packages_on_system: set[str]  # holds the list of explicitly installed packages on the system; will be updated whenever the manager adds/removes explicit packages.
  aur_helper: AurHelper | None

  def __init__(
    self,
    keep_unmanaged_packages: bool,
    aur_helper: AurHelper | None = None,
    update_system = False,
    paccache: PaccacheOptions = PaccacheOptions(),
  ):
    super().__init__()
    store = JsonStore("/var/cache/koti/PacmanPackageManager.json")
    self.aur_helper = aur_helper
    self.managed_packages_store = store.collection("managed_packages")
    self.ignore_manually_installed_packages = keep_unmanaged_packages
    self.explicit_packages_on_system = set()
    self.update_system = update_system
    self.paccache = paccache

  def initialize(self, model: ConfigModel, dryrun: bool):
    self.explicit_packages_on_system = set(self.pacman_list_explicit_packages())

  def finalize(self, model: ConfigModel, dryrun: bool):
    if not dryrun:
      packages = [item.name for group in model.configs for item in group.provides if isinstance(item, Package)]
      self.managed_packages_store.replace_all(packages)

  def assert_installable(self, item: Package, model: ConfigModel):
    pass

  def state_current(self, item: Package) -> PackageState | None:
    installed: bool = item.name in self.explicit_packages_on_system
    return PackageState() if installed else None

  def state_target(self, item: Package, model: ConfigModel, dryrun: bool) -> PackageState:
    return PackageState()

  def reorder_for_install(self, items: Sequence[Package]) -> list[Package]:
    return [
      *[item for item in items if item.script is not None],
      *[item for item in items if item.url is not None],
      *[item for item in items if item.script is None and item.url is None],
    ]

  def plan_install(self, items_to_check: Sequence[Package], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    installed_packages = self.pacman_list_installed_packages()
    explicit_packages = self.pacman_list_explicit_packages()

    additional_explicit_items: list[Package] = []
    additional_items_from_script: list[Package] = []
    additional_items_from_urls: list[Package] = []
    additional_items_from_repo: list[Package] = []

    count = 0
    for item in items_to_check:
      current, target = self.states(item, model, dryrun)
      if current == target:
        continue
      count += 1
      if item.name not in installed_packages:
        if item.url is not None:
          additional_items_from_urls.append(item)
        elif item.script is not None:
          additional_items_from_script.append(item)
        else:
          additional_items_from_repo.append(item)
      elif item.name not in explicit_packages:
        additional_explicit_items.append(item)

    if count:
      logger.info("When installing new packages, Arch always needs to do a full system update (partial updates are unsupported).")

    additional_explicit_items.sort(key = lambda x: x.name)
    additional_items_from_script.sort(key = lambda x: x.name)
    additional_items_from_urls.sort(key = lambda x: x.name)
    additional_items_from_repo.sort(key = lambda x: x.name)

    if additional_explicit_items:
      yield Action(
        updates = additional_explicit_items,
        description = f"mark package(s) explicitly installed: {", ".join([item.name for item in additional_explicit_items])}",
        execute = lambda: self.mark_explicit(additional_explicit_items)
      )

    for item in additional_items_from_script:
      yield Action(
        installs = additional_items_from_script,
        description = f"install package from script: {item.name}",
        execute = lambda: self.install_from_script(item)
      )

    if additional_items_from_urls:
      logger.info(f"Packages installed via URL might later get updated to a different version by pacman if also contained in a package repository.")
      yield Action(
        installs = additional_items_from_urls,
        description = f"install package(s) from URL(s): {", ".join([item.name for item in additional_items_from_urls if item.url])}",
        execute = lambda: self.install_from_url(additional_items_from_urls)
      )

    if additional_items_from_repo:
      yield Action(
        installs = additional_items_from_repo,
        description = f"install package(s): {" ".join([item.name for item in additional_items_from_repo])}",
        execute = lambda: self.install_from_repo(additional_items_from_repo)
      )

  def install_from_repo(self, additional_items_from_repo: list[Package]):
    pacman_or_helper = self.aur_helper.command if self.aur_helper else "pacman"
    user = self.aur_helper.user if self.aur_helper else None
    shell(f"{pacman_or_helper} -Syu {" ".join([item.name for item in additional_items_from_repo])}", user = user)
    self.add_managed_packages(additional_items_from_repo)
    self.update_explicit_package_list()

  def install_from_url(self, additional_items_from_urls: list[Package]):
    shell(f"pacman -U {" ".join([item.url for item in additional_items_from_urls if item.url])}")
    self.add_managed_packages(additional_items_from_urls)
    self.update_explicit_package_list()

  def install_from_script(self, item: Package):
    assert item.script is not None, "illegal state"
    item.script()
    self.add_managed_packages([item])
    self.update_explicit_package_list()

  def mark_explicit(self, additional_explicit_items: list[Package]):
    shell(f"pacman -D --asexplicit {" ".join([item.name for item in additional_explicit_items])}")
    self.add_managed_packages(additional_explicit_items)
    self.update_explicit_package_list()

  def plan_cleanup(self, items_to_keep: Sequence[Package], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    installed_items = self.installed_packages()
    items_to_remove = [item for item in installed_items if item not in items_to_keep]
    if items_to_remove:
      yield Action(
        removes = items_to_remove,
        description = f"mark package(s) non-explicitly installed: {", ".join([item.name for item in items_to_remove])}",
        execute = lambda: self.mark_dependency(items_to_remove)
      )

    if self.update_system:
      yield Action(
        description = f"update all pacman packages",
        execute = lambda: self.update_all_packages(),
      )

    yield Action(
      description = f"prune unneeded pacman packages",
      execute = lambda: self.pacman_prune_unneeded(),
    )

    if self.paccache.enabled:
      if dryrun or shell_success("paccache --version"):
        yield Action(
          description = f"cleanup pacman package cache",
          execute = lambda: self.cleanup_package_cache(self.paccache.options),
        )
      else:
        logger.warn("paccache not available, cleanup of the package cache was skipped (install pacman-contrib to use this feature)")

  def mark_dependency(self, items_to_remove: list[Package]):
    shell(f"pacman -D --asdeps {" ".join([item.name for item in items_to_remove])}")
    self.remove_managed_packages(items_to_remove)

  def installed_packages(self) -> list[Package]:
    installed_by_koti = self.managed_packages_store.elements()
    package_names = {
      pkg for pkg in self.explicit_packages_on_system
      if not self.ignore_manually_installed_packages or pkg in installed_by_koti
    }
    return [Package(pkg) for pkg in package_names]

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
    else:
      print("no unneeded packages found")

  def update_all_packages(self):
    pacman_or_helper = self.aur_helper.command if self.aur_helper else "pacman"
    user = self.aur_helper.user if self.aur_helper else None
    shell(f"{pacman_or_helper} -Syu", user = user)

  def cleanup_package_cache(self, options: Sequence[str]):
    shell(f"paccache {" ".join(options)}")

  def parse_pkgs(self, output: str) -> list[str]:
    if "there is nothing to do" in output: return []
    return [pkg for pkg in output.split("\n") if pkg]
