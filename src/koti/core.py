from __future__ import annotations

from copy import copy
from os import getuid
from typing import Iterator

from koti.model import *
from koti.utils import *


class Koti:
  store: JsonStore
  managers: list[ConfigManager]
  configs: list[ConfigGroup]

  def __init__(
    self,
    managers: Iterator[ConfigManager | None] | Iterable[ConfigManager | None],
    configs: Iterator[ConfigGroup | None] | Iterable[ConfigGroup | None],
  ):
    assert getuid() == 0, "this program must be run as root (or through sudo)"
    self.store = JsonStore("/var/cache/koti/Koti.json")
    self.configs = [c for c in configs if c is not None]
    self.managers = [m for m in managers if m is not None]

  def create_model(self) -> ConfigModel:
    merged_configs = self.merge_configs(self.configs)
    self.check_manager_consistency(self.managers, merged_configs)
    install_phases = self.create_install_phases(self.managers, merged_configs)
    tags_archive = self.load_tags(self.store)
    model = ConfigModel(self.managers, install_phases, tags_archive)
    self.check_config_item_consistency(model)
    return model

  def create_cleanup_phase(self, model: ConfigModel) -> CleanupPhase:
    items_to_install = [item for phase in model.phases for step in phase.steps for item in step.items_to_install]
    identifiers_to_install = [item.identifier() for item in items_to_install]
    steps: list[CleanupStep] = []
    for manager in self.get_cleanup_phase_manager_order(self.managers):
      installed_items = manager.installed(model)
      if not installed_items:
        continue  # only add the manager to the cleanup phase if there are any items that could potentially be uninstalled
      items_to_uninstall = [item for item in installed_items if item.identifier() not in identifiers_to_install]
      steps.append(CleanupStep(
        manager = manager,
        items_to_uninstall = items_to_uninstall,
        items_to_keep = [item for item in items_to_install if item.__class__ in manager.managed_classes],
      ))
    return CleanupPhase(steps)

  def plan(self, groups: bool = True, items: bool = False) -> bool:

    # clear warnings from previous runs
    for manager in self.managers:
      manager.warnings.clear()

    model = self.create_model()
    changes: list[tuple[ConfigItem, str]] = []

    # plan installation phases
    items_total = [item for phase in model.phases for step in phase.steps for item in step.items_to_install]
    items_outdated: list[ManagedConfigItem] = []
    for phase in model.phases:
      for step in phase.steps:
        manager = step.manager
        for item in step.items_to_install:
          current = manager.state_current(item)
          target = manager.state_target(item, model, planning = True)
          if current is None or current.hash() != target.hash():
            items_outdated.append(item)
            for change_text in (manager.diff(current, target) or ["item will be installed/updated"]):
              changes.append((item, change_text))

    # plan cleanup phase
    cleanup_phase = self.create_cleanup_phase(model)
    items_to_uninstall: list[ManagedConfigItem] = []
    for cleanup_step in cleanup_phase.steps:
      manager = cleanup_step.manager
      for item in cleanup_step.items_to_uninstall:
        items_to_uninstall.append(item)
        current = manager.state_current(item)
        for change_text in (manager.diff(current, None) or ["item will be uninstalled"]):
          changes.append((item, change_text))

    # list all groups
    if groups or items:
      for phase_idx, phase in enumerate(model.phases):
        printc(f"Phase {phase_idx + 1}:", BOLD)
        if groups:
          for group in phase.groups:
            needs_update = len([item for item in group.provides if item in items_outdated]) > 0
            printc(f"{"~" if needs_update else "-"} {group.description}", YELLOW if needs_update else None)
        if items:
          for install_step in phase.steps:
            for item in install_step.items_to_install:
              needs_update = item in items_outdated or item in items_outdated
              if needs_update:
                printc(f"~ {item.description()}", YELLOW)
              else:
                printc(f"- {item.description()}")
        print()

    # print warnings generated during evaluation
    warnings = [message for manager in self.managers for message in manager.warnings]
    if warnings:
      printc(f"Evaluation warnings:", BOLD)
      for message in warnings:
        printc(f"- {message}")
      print()

    # list all changed items
    count = len(items_outdated) + len(items_to_uninstall)
    if count > 0:
      printc(f"{len(items_total)} items total, {count} items to update:", BOLD)
      maxlen = max([len(item.description()) for item, change in changes])
      for changed_item, change_text in changes:
        printc(f"- {changed_item.description().ljust(maxlen)}  {change_text}")
    else:
      printc(f"{len(items_total)} items total, everything up to date", BOLD)
    print()

    return count > 0

  def apply(self):
    model = self.create_model()

    # clear warnings before execution
    for manager in self.managers:
      manager.warnings.clear()

    for phase_idx, phase in enumerate(model.phases):
      for install_step in phase.steps:
        manager = install_step.manager
        items_to_update: list[ManagedConfigItem] = []
        for item in install_step.items_to_install:
          current = manager.state_current(item)
          target = manager.state_target(item, model, planning = False)
          if current is None or current.hash() != target.hash():
            items_to_update.append(item)
        self.print_install_step_log(model, phase_idx, install_step, items_to_update)
        manager.install(items_to_update, model) or []

    cleanup_phase = self.create_cleanup_phase(model)
    for cleanup_step in cleanup_phase.steps:
      manager = cleanup_step.manager
      self.print_cleanup_step_log(model, cleanup_step)
      manager.uninstall(cleanup_step.items_to_uninstall)

    self.save_tags(self.store, model)

    warnings = [message for manager in self.managers for message in manager.warnings]
    if warnings:
      print()
      printc(f"Warnings during execution:", BOLD)
      for message in warnings:
        printc(f"- {message}")
      print()

  @classmethod
  def print_install_step_log(cls, model: ConfigModel, phase_idx: int, step: InstallStep, items_to_update: Sequence[ManagedConfigItem]):
    manager_name_maxlen = max([len(manager.__class__.__name__) for manager in model.managers])
    manager_name = step.manager.__class__.__name__
    if 0 < len(items_to_update) < 5:
      details = f"items to install or update: {", ".join([item.description() for item in items_to_update])}"
    else:
      details = f"{len(items_to_update) or "no"} outdated items"
    print(f"Phase {phase_idx + 1}  |  {manager_name.ljust(manager_name_maxlen)}  |  {str(len(step.items_to_install)).rjust(3)} items total  |  {details}")

  @classmethod
  def print_cleanup_step_log(cls, model: ConfigModel, step: CleanupStep):
    manager_name_maxlen = max([len(manager.__class__.__name__) for manager in model.managers])
    manager_name = step.manager.__class__.__name__
    if 0 < len(step.items_to_uninstall) < 5:
      details = f"items to uninstall: {", ".join([item.description() for item in step.items_to_uninstall])}"
    else:
      details = f"{len(step.items_to_uninstall) or "no"} items to uninstall"
    print(f"Cleanup  |  {manager_name.ljust(manager_name_maxlen)}  |  {str(len(step.items_to_keep)).rjust(3)} remaining    |  {details}")

  @classmethod
  def load_tags(cls, store: JsonStore) -> dict[str, set[str]]:
    stored: dict[str, list[str]] | None = store.get("item_tags")
    if stored is not None:
      return {identifier: set(tags) for identifier, tags in stored.items()}
    else:
      return {}

  @classmethod
  def save_tags(cls, store: JsonStore, model: ConfigModel):
    result: dict[str, list[str]] = {
      item.identifier(): list(item.tags)
      for phase in model.phases for install_step in phase.steps for item in install_step.items_to_install
    }
    store.put("item_tags", result)

  @classmethod
  def get_cleanup_phase_manager_order(cls, managers: Sequence[ConfigManager]) -> Sequence[ConfigManager]:
    return [
      *[manager for manager in managers if manager.order_in_cleanup_phase == "first"],
      *reversed([manager for manager in managers if manager.order_in_cleanup_phase == "reverse_install_order"]),
      *[manager for manager in managers if manager.order_in_cleanup_phase == "last"],
    ]

  @classmethod
  def create_install_phases(cls, managers: Sequence[ConfigManager], merged_groups: list[ConfigGroup]) -> list[InstallPhase]:
    return [
      cls.create_install_phase(managers, groups_in_phase)
      for groups_in_phase in cls.separate_into_phases(merged_groups)
    ]

  @classmethod
  def check_config_item_consistency(cls, model: ConfigModel):
    for phase in model.phases:
      for install_step in phase.steps:
        for item in install_step.items_to_install:
          try:
            install_step.manager.check_configuration(item, model)
          except Exception as e:
            raise AssertionError(f"{install_step.manager.__class__.__name__}: {e}")

  @classmethod
  def check_manager_consistency(cls, managers: Sequence[ConfigManager], configs: Sequence[ConfigGroup]):
    for group in configs:
      for item in (x for x in group.provides if x is not None and isinstance(x, ManagedConfigItem)):
        matching_managers = [manager for manager in managers if item.__class__ in manager.managed_classes]
        if len(matching_managers) == 0:
          raise AssertionError(f"no manager found for class {item.__class__.__name__}")
        if len(matching_managers) > 1:
          raise AssertionError(f"multiple managers found for class {item.__class__.__name__}")

  @classmethod
  def merge_configs(cls, configs: list[ConfigGroup]) -> list[ConfigGroup]:
    items_by_identifier: dict[str, ConfigItem] = {}
    result: list[ConfigGroup] = []
    for group in configs:
      provides = list(group.provides)  # copy for maniputation
      for idx, item in enumerate(provides):
        item_prev = items_by_identifier.get(item.identifier(), None)
        item_merged = item_prev.merge(item) if item_prev is not None else item
        items_by_identifier[item.identifier()] = item_merged
        provides[idx] = item_merged
      new_group = copy(group)
      new_group.provides = provides
      result.append(new_group)
    return result

  @classmethod
  def reduce_items(cls, items: list[ConfigItem]) -> ConfigItem:
    if len(items) == 1:
      return items[0]
    merged_item = items[0].merge(items[1])
    return cls.reduce_items([merged_item, *items[2:]])

  @classmethod
  def separate_into_phases(cls, groups: list[ConfigGroup]) -> list[list[ConfigGroup]]:
    result: list[list[ConfigGroup]] = [list(groups)]
    while True:
      violation = cls.find_dependency_violation(result)
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

  @classmethod
  def create_install_phase(cls, managers: Sequence[ConfigManager], merged_groups_in_phase: list[ConfigGroup]) -> InstallPhase:
    steps: list[InstallStep] = []
    for manager in managers:
      items_for_manager = [
        item for group in merged_groups_in_phase
        for item in group.provides
        if isinstance(item, ManagedConfigItem) and item.__class__ in manager.managed_classes
      ]
      if not items_for_manager:
        continue  # only add the manager to the install phase if it actually has items to check
      steps.append(InstallStep(manager = manager, items_to_install = items_for_manager))
    return InstallPhase(
      groups = merged_groups_in_phase,
      order = steps,
      items = [item for group in merged_groups_in_phase for item in group.provides],
    )

  # FIXME: Refactoring
  # FIXME: Zuerst mergen, dann Dependencies auflösen
  @classmethod
  def find_dependency_violation(cls, phases: list[list[ConfigGroup]]) -> tuple[int, ConfigGroup] | None:
    for phase_idx, phase in enumerate(phases):
      for group in phase:

        # check requires
        for required_item in group.requires:
          required_phase_and_group = cls.find_required_group(required_item, phases)
          if required_phase_and_group is None:
            raise AssertionError(f"required item not found: {required_item.identifier()}")
          required_phase_idx, required_group = required_phase_and_group
          if required_phase_idx >= phase_idx:
            assert required_group is not group, f"group with requires-dependency to itself: {group.description}"
            return required_phase_idx, required_group

        # check after
        for item in group.provides:
          for other_phase_idx, other_phase in enumerate(phases):
            for other_group in other_phase:
              if other_group.after(item) and phase_idx >= other_phase_idx:
                assert other_group is not group, f"group with after-dependency to itself: {group.description}"
                return phase_idx, group

        # check before
        for item in group.provides:
          for other_phase_idx, other_phase in enumerate(phases):
            for other_group in other_phase:
              if other_group.before(item) and other_phase_idx >= phase_idx:
                assert other_group is not group, f"group with before-dependency to itself: {group.description}"
                return other_phase_idx, other_group

    return None

  @classmethod
  def find_required_group(cls, required_item: ConfigItem, phases: list[list[ConfigGroup]]) -> tuple[int, ConfigGroup] | None:
    for idx_phase, phase in enumerate(phases):
      for group in phase:
        for group_item in group.provides:
          if group_item.identifier() == required_item.identifier():
            return idx_phase, group
    return None
