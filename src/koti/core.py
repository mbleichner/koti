from __future__ import annotations

from os import getuid
from typing import Iterable, Iterator

from koti.types import *
from koti.utils import JsonStore


class Koti:
  store: JsonStore
  default_confirm_mode: ConfirmMode
  managers: list[ConfigManager]
  configs: list[ConfigGroup]

  def __init__(
    self,
    managers: Iterator[ConfigManager | None] | Iterable[ConfigManager | None],
    configs: Iterator[ConfigGroup | None] | Iterable[ConfigGroup | None],
    default_confirm_mode: ConfirmMode = "cautious"
  ):
    assert getuid() == 0, "this program must be run as root (or through sudo)"
    self.default_confirm_mode = default_confirm_mode
    self.store = JsonStore("/var/cache/koti/Koti.json")
    self.configs = [c for c in configs if c is not None]
    self.managers = [m for m in managers if m is not None]

  def plan(self, groups: bool = True, items: bool = False) -> bool:

    # plan installation phases
    model = Koti.create_model(self.managers, self.configs, self.default_confirm_mode, self.store)
    items_total = [item for phase in model.phases for step in phase.steps for item in step.items_to_install]
    installed_identifiers = [item.identifier() for manager in model.managers for item in manager.installed()]
    items_outdated = [
      item for phase in model.phases for step in phase.steps for item in step.items_to_install
      if step.manager.checksum_current(item) != step.manager.checksum_target(item, model)
    ]

    # plan cleanup phase
    cleanup_phase = Koti.create_cleanup_phase(model)
    items_to_uninstall = cleanup_phase.items_to_uninstall

    if groups or items:
      for phase_idx, phase in enumerate(model.phases):
        print(f"Phase {phase_idx + 1}:")
        if groups:
          for group in phase.groups:
            needs_update = len([item for item in group.provides if item in items_outdated]) > 0
            print(f"{"*" if needs_update else "-"} {group.description}")
        if items:
          for install_step in phase.steps:
            for item in install_step.items_to_install:
              needs_update = item in items_outdated or item in items_outdated
              print(f"{"*" if needs_update else "-"} {item.description()}")
        print()

    count = len(items_outdated) + len(items_to_uninstall)
    if count > 0:
      print(f"{len(items_total)} items total, {count} items to update:")
      for item in items_outdated:
        action = "upd" if item.identifier() in installed_identifiers else "add"
        print(f"- {action} {item.description()}")
      for item in items_to_uninstall:
        print(f"- del {item.description()}")
      print()
      print("// additional updates may be triggered by PostHooks")
    else:
      print(f"{len(items_total)} items total, everything up to date")

    return count > 0

  def apply(self):
    model = Koti.create_model(self.managers, self.configs, self.default_confirm_mode, self.store)
    for phase_idx, phase in enumerate(model.phases):
      for step in phase.steps:
        manager = step.manager
        items_to_update = [item for item in step.items_to_install if manager.checksum_current(item) != manager.checksum_target(item, model)]
        Koti.print_install_step_log(model, phase_idx, step, items_to_update)
        manager.install(items_to_update, model) or []

    cleanup_phase = Koti.create_cleanup_phase(model)
    for step in cleanup_phase.steps:
      manager = step.manager
      Koti.print_cleanup_step_log(model, step)
      manager.uninstall(step.items_to_uninstall, model)

    Koti.save_confirm_modes(self.store, model)

  @staticmethod
  def create_model(
    managers: Sequence[ConfigManager],
    configs: Sequence[ConfigGroup],
    default_confirm_mode: ConfirmMode,
    store: JsonStore,
  ) -> ConfigModel:

    Koti.check_manager_consistency(managers, configs)

    groups = Koti.get_all_provided_groups(configs)
    groups_separated_into_phases = Koti.separate_into_phases(groups)
    merged_items_grouped_by_phase: list[list[ConfigItem]] = Koti.merge_items([
      [item for group in phase for item in group.provides]
      for phase in groups_separated_into_phases
    ])

    model = ConfigModel(
      managers = managers,
      phases = [Koti.create_install_phase(managers, groups_in_phase, items_in_phase) for groups_in_phase, items_in_phase in
                zip(groups_separated_into_phases, merged_items_grouped_by_phase)],
      confirm_mode_fallback = default_confirm_mode,
      confirm_mode_archive = Koti.load_confirm_modes(store)
    )

    Koti.check_config_item_consistency(model)
    return model

  @staticmethod
  def print_install_step_log(model: ConfigModel, phase_idx: int, step: InstallStep, items_to_update: Sequence[ManagedConfigItem]):
    manager_name_maxlen = max([len(manager.__class__.__name__) for manager in model.managers])
    manager_name = step.manager.__class__.__name__
    if 0 < len(items_to_update) < 5:
      details = f"items to install or update: {", ".join([item.description() for item in items_to_update])}"
    else:
      details = f"{len(items_to_update) or "no"} outdated items"
    print(f"Phase {phase_idx + 1}  |  {manager_name.ljust(manager_name_maxlen)}  |  {str(len(step.items_to_install)).rjust(3)} items total  |  {details}")

  @staticmethod
  def print_cleanup_step_log(model: ConfigModel, step: CleanupStep):
    manager_name_maxlen = max([len(manager.__class__.__name__) for manager in model.managers])
    manager_name = step.manager.__class__.__name__
    if 0 < len(step.items_to_uninstall) < 5:
      details = f"items to uninstall: {", ".join([item.description() for item in step.items_to_uninstall])}"
    else:
      details = f"{len(step.items_to_uninstall) or "no"} items to uninstall"
    print(f"Cleanup  |  {manager_name.ljust(manager_name_maxlen)}  |  {str(len(step.items_to_keep)).rjust(3)} remaining    |  {details}")

  @staticmethod
  def get_cleanup_phase_manager_order(managers: Sequence[ConfigManager]) -> Sequence[ConfigManager]:
    return [
      *[manager for manager in managers if manager.order_in_cleanup_phase == "first"],
      *reversed([manager for manager in managers if manager.order_in_cleanup_phase == "reverse_install_order"]),
      *[manager for manager in managers if manager.order_in_cleanup_phase == "last"],
    ]

  @staticmethod
  def load_confirm_modes(store: JsonStore) -> dict[str, ConfirmMode]:
    result = store.get("confirm_modes")
    return result if isinstance(result, dict) else {}

  @staticmethod
  def save_confirm_modes(store: JsonStore, model: ConfigModel):
    result: dict[str, ConfirmMode] = {}
    for phase in model.phases:
      for install_step in phase.steps:
        for item in install_step.items_to_install:
          result[item.identifier()] = model.confirm_mode(item)
    store.put("confirm_modes", result)

  @staticmethod
  def merge_items(items_grouped_by_phase: list[list[ConfigItem]]) -> list[list[ConfigItem]]:
    flattened = [item for phase in items_grouped_by_phase for item in phase]
    processed_identifiers: set[str] = set()
    result: list[list[ConfigItem]] = []
    for phase in items_grouped_by_phase:
      phase_new: list[ConfigItem] = []
      result.append(phase_new)
      for item in phase:
        if item.identifier() in processed_identifiers: continue
        others = [other for other in flattened if other.identifier() == item.identifier()]
        merged = Koti.reduce_items(others)
        phase_new.append(merged)
        processed_identifiers.add(item.identifier())
    return result

  @staticmethod
  def reduce_items(items: list[ConfigItem]) -> ConfigItem:
    if len(items) == 1:
      return items[0]
    merged_item = items[0].merge(items[1])
    return Koti.reduce_items([merged_item, *items[2:]])

  @staticmethod
  def check_manager_consistency(managers: Sequence[ConfigManager], configs: Sequence[ConfigGroup]):
    for group in Koti.get_all_provided_groups(configs):
      for item in (x for x in group.provides if x is not None and isinstance(x, ManagedConfigItem)):
        matching_managers = [manager for manager in managers if item.__class__ in manager.managed_classes]
        if len(matching_managers) == 0:
          raise AssertionError(f"no manager found for class {item.__class__.__name__}")
        if len(matching_managers) > 1:
          raise AssertionError(f"multiple managers found for class {item.__class__.__name__}")

  @staticmethod
  def check_config_item_consistency(model: ConfigModel):
    for phase in model.phases:
      for install_step in phase.steps:
        for item in install_step.items_to_install:
          try:
            install_step.manager.check_configuration(item, model)
          except Exception as e:
            raise AssertionError(f"{install_step.manager.__class__.__name__}: {e}")

  @staticmethod
  def separate_into_phases(groups: Sequence[ConfigGroup]) -> list[list[ConfigGroup]]:
    result: list[list[ConfigGroup]] = [list(groups)]
    while True:
      violation = Koti.find_dependency_violation(result)
      if violation is None: break
      idx_phase, group = violation
      result[idx_phase].remove(group)
      if len(result[idx_phase]) == 0:
        raise AssertionError(f"could not order dependencies (check for circular dependencies))")
      if idx_phase > 0:
        result[idx_phase - 1].append(group)
      else:
        result = [[group]] + result
    return result

  @staticmethod
  def get_all_provided_groups(configs: Sequence[ConfigGroup]) -> Sequence[ConfigGroup]:
    result: list[ConfigGroup] = []
    for config_group in configs:
      config_group_list = config_group if isinstance(config_group, list) else [config_group]
      result += [group for group in config_group_list if group is not None]
    return result

  @staticmethod
  def create_install_phase(managers: Sequence[ConfigManager], groups_in_phase: list[ConfigGroup], merged_items_in_phase: list[ConfigItem]) -> InstallPhase:
    steps: list[InstallStep] = []
    for manager in managers:
      items_for_manager = [
        item for item in merged_items_in_phase
        if isinstance(item, ManagedConfigItem) and item.__class__ in manager.managed_classes
      ]
      if not items_for_manager:
        continue  # only add the manager to the install phase if it actually has items to check
      steps.append(InstallStep(manager = manager, items_to_install = items_for_manager))
    return InstallPhase(
      groups = groups_in_phase,
      order = steps,
      items = merged_items_in_phase
    )

  @staticmethod
  def create_cleanup_phase(model: ConfigModel) -> CleanupPhase:
    items_to_install = [item for phase in model.phases for step in phase.steps for item in step.items_to_install]
    identifiers_to_install = [item.identifier() for item in items_to_install]
    steps: list[CleanupStep] = []
    for manager in Koti.get_cleanup_phase_manager_order(model.managers):
      installed_items = manager.installed()
      if not installed_items:
        continue  # only add the manager to the cleanup phase if there are any items that could potentially be uninstalled
      items_to_uninstall = [item for item in installed_items if item.identifier() not in identifiers_to_install]
      steps.append(CleanupStep(
        manager = manager,
        items_to_uninstall = items_to_uninstall,
        items_to_keep = [item for item in items_to_install if item.__class__ in manager.managed_classes],
      ))
    return CleanupPhase(steps)

  @staticmethod
  def find_dependency_violation(phases: list[list[ConfigGroup]]) -> tuple[int, ConfigGroup] | None:
    for phase_idx, phase in enumerate(phases):
      for group in phase:
        for required_item in group.requires:
          required_phase_and_group = Koti.find_required_group(required_item, phases)
          if required_phase_and_group is None:
            raise AssertionError(f"required item not found: {required_item.identifier()}")
          required_phase_idx, required_group = required_phase_and_group
          if required_phase_idx >= phase_idx:
            if group == required_group: raise AssertionError(f"group with dependency to itself")
            return required_phase_idx, required_group
    return None

  @staticmethod
  def find_required_group(required_item: ConfigItem, phases: list[list[ConfigGroup]]) -> tuple[int, ConfigGroup] | None:
    for idx_phase, phase in enumerate(phases):
      for group in phase:
        for group_item in group.provides:
          if group_item.identifier() == required_item.identifier():
            return idx_phase, group
    return None
