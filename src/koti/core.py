from __future__ import annotations

from copy import copy
from os import getuid
from typing import Iterator

from tabulate import tabulate

from koti.model import *
from koti.utils.colors import *
from koti.utils.json_store import *
from koti.utils.shell import ShellAction


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
    self.assert_manager_consistency(self.managers, self.configs)

  def create_model(self) -> ConfigModel:
    merged_configs = self.merge_configs(self.configs)
    phases_with_duplicates = self.resolve_dependencies(merged_configs)
    phases_without_duplicates = self.remove_duplicates(phases_with_duplicates)
    tags_archive = self.load_tags(self.store)
    model = ConfigModel(
      managers = self.managers,
      phases = [self.create_install_phase(self.managers, groups_in_phase) for groups_in_phase in phases_without_duplicates],
      tags_archive = tags_archive
    )

    self.assert_config_items_installable(model)
    return model

  def create_cleanup_phase(self, model: ConfigModel) -> CleanupPhase:
    items_to_install = [item for phase in model.phases for step in phase.steps for item in step.items_to_install]
    identifiers_to_install = [item.identifier() for item in items_to_install]
    steps: list[CleanupStep] = []
    for manager in self.get_cleanup_phase_manager_order(self.managers):
      installed_items = [item for item in manager.installed(model) if manager.state_current(item) is not None]
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
    execution_plans: list[ExecutionPlan] = []

    # plan installation phases
    items_total = [item for phase in model.phases for step in phase.steps for item in step.items_to_install]
    items_to_install: list[ManagedConfigItem] = []
    items_to_update: list[ManagedConfigItem] = []
    for phase in model.phases:
      for step in phase.steps:
        manager = step.manager
        changed_items: list[ConfigItemToInstall] = []
        for item in step.items_to_install:
          current = manager.state_current(item)
          target = manager.state_target(item, model, planning = True)
          if current is None or current.hash() != target.hash():
            changed_items.append((item, current, target))
            if current is None:
              items_to_install.append(item)
            else:
              items_to_update.append(item)
        if changed_items:
          execution_plans.extend(manager.plan_install(changed_items))

    # plan cleanup phase
    cleanup_phase = self.create_cleanup_phase(model)
    items_to_uninstall: list[ManagedConfigItem] = []
    for cleanup_step in cleanup_phase.steps:
      manager = cleanup_step.manager
      removed_items: list[ConfigItemToUninstall] = []
      for item in cleanup_step.items_to_uninstall:
        items_to_uninstall.append(item)
        current = manager.state_current(item)
        removed_items.append((item, current))
      if removed_items:
        execution_plans.extend(manager.plan_uninstall(removed_items))

    # list all groups
    if groups or items:
      for phase_idx, phase in enumerate(model.phases):
        printc(f"Phase {phase_idx + 1}:", BOLD)
        if groups:
          for group in phase.groups:
            group_contains_change = len([item for item in group.provides if item in items_to_install or item in items_to_update]) > 0
            printc(f"{"~" if group_contains_change else "-"} {group.description}", YELLOW if group_contains_change else None)
        if items:
          for install_step in phase.steps:
            for item in install_step.items_to_install:
              if item in items_to_install:
                printc(f"+ {item.description()}", GREEN)
              elif item in items_to_update:
                printc(f"~ {item.description()}", YELLOW)
              else:
                printc(f"- {item.description()}")
        print()

    changed_item_count = len(items_to_install) + len(items_to_update) + len(items_to_uninstall)
    printc(f"{len(items_total)} items total, {changed_item_count or "no"} items with changes", BOLD)
    print()

    # print warnings generated during evaluation
    warnings = [message for manager in self.managers for message in manager.warnings]
    if warnings:
      printc(f"Evaluation warnings:", BOLD)
      for message in set(warnings):
        printc(f"- {message}")
      print()

    # list all changed items
    if len(execution_plans) > 0:
      printc(f"Actions that will be executed (in order):", BOLD)
      table: list[list[str | None]] = []
      for plan in execution_plans:
        table.append([
          f"- {plan.description}",
          "\n".join([item.description() for item in plan.items]),
          "\n".join([f"{CYAN}{action.command}{ENDC}" for action in plan.actions if isinstance(action, ShellAction)] + plan.details)
        ])
      table = [[f"{cell}{ENDC}" for cell in row] for row in table]
      if table:
        print(tabulate(table, tablefmt = "plain", maxcolwidths = [60]))
      print()

    return changed_item_count > 0

  def apply(self):
    model = self.create_model()

    # clear warnings before execution
    for manager in self.managers:
      manager.warnings.clear()

    # execute install phases
    for phase_idx, phase in enumerate(model.phases):
      for install_step in phase.steps:
        manager = install_step.manager
        items_to_update: list[ManagedConfigItem] = []
        items_to_update_with_state: list[ConfigItemToInstall] = []
        for item in install_step.items_to_install:
          current = manager.state_current(item)
          target = manager.state_target(item, model, planning = False)
          if current is None or current.hash() != target.hash():
            items_to_update.append(item)
            items_to_update_with_state.append((item, current, target))
        self.print_install_step_log(model, phase_idx, install_step, items_to_update)
        if items_to_update:
          execution_plans = manager.plan_install(items_to_update_with_state)
          # FIXME: Double check if all items of the plan have been reviewed
          for plan in execution_plans:
            for action in plan.actions:
              action()

    # execute cleanup phase
    cleanup_phase = self.create_cleanup_phase(model)
    for cleanup_step in cleanup_phase.steps:
      manager = cleanup_step.manager
      self.print_cleanup_step_log(model, cleanup_step)
      items_to_uninstall_with_state: list[ConfigItemToUninstall] = []
      for item in cleanup_step.items_to_uninstall:
        current = manager.state_current(item)
        items_to_uninstall_with_state.append((item, current))
      if items_to_uninstall_with_state:
        execution_plans = manager.plan_uninstall(items_to_uninstall_with_state)
        # FIXME: Double check if all items of the plan have been reviewed
        for plan in execution_plans:
          for action in plan.actions:
            action()

    # updating persistent data
    self.save_tags(self.store, model)
    for manager in self.managers:
      manager.finalize(model)

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
      details = f"{len(items_to_update) or "no"} items to update/install"
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
  def assert_config_items_installable(cls, model: ConfigModel):
    """Checks that every item is actually installable (fully configured according to their manager)"""
    for phase in model.phases:
      for install_step in phase.steps:
        for item in install_step.items_to_install:
          try:
            install_step.manager.assert_installable(item, model)
          except Exception as e:
            raise AssertionError(f"{install_step.manager.__class__.__name__}: {e}")

  @classmethod
  def assert_manager_consistency(cls, managers: Sequence[ConfigManager], configs: Sequence[ConfigGroup]):
    """Checks that every item has a manager and only one manager"""
    for group in configs:
      for item in (x for x in group.provides if x is not None and isinstance(x, ManagedConfigItem)):
        matching_managers = [manager for manager in managers if item.__class__ in manager.managed_classes]
        if len(matching_managers) == 0:
          raise AssertionError(f"no manager found for class {item.__class__.__name__}")
        if len(matching_managers) > 1:
          raise AssertionError(f"multiple managers found for class {item.__class__.__name__}")

  @classmethod
  def merge_configs(cls, configs: list[ConfigGroup]) -> list[ConfigGroup]:
    # merge all items with the same identifier
    merged_items: dict[str, ConfigItem] = {}
    for group in configs:
      for idx, item in enumerate(group.provides):
        item_prev = merged_items.get(item.identifier(), None)
        item_merged = item_prev.merge(item) if item_prev is not None else item
        merged_items[item.identifier()] = item_merged

    # create new groups with the items replaced by their merged versions
    result: list[ConfigGroup] = []
    for group in configs:
      provides_updated = list(group.provides)
      for idx, item in enumerate(provides_updated):
        provides_updated[idx] = merged_items[item.identifier()]
      new_group = copy(group)
      new_group.provides = provides_updated
      result.append(new_group)
    return result

  @classmethod
  def remove_duplicates(cls, phases: list[list[ConfigGroup]]) -> list[list[ConfigGroup]]:
    seen_item_identifiers: set[str] = set()
    phases_filtered: list[list[ConfigGroup]] = []
    for phase in phases:
      phase_filtered: list[ConfigGroup] = []
      for group in phase:
        filtered_provides: list[ConfigItem] = []
        for item in group.provides:
          if item.identifier() not in seen_item_identifiers:
            filtered_provides.append(item)
            seen_item_identifiers.add(item.identifier())
        group_filtered = copy(group)
        group_filtered.provides = filtered_provides
        phase_filtered.append(group_filtered)
      phases_filtered.append(phase_filtered)
    return phases_filtered

  @classmethod
  def reduce_items(cls, items: list[ConfigItem]) -> ConfigItem:
    if len(items) == 1:
      return items[0]
    merged_item = items[0].merge(items[1])
    return cls.reduce_items([merged_item, *items[2:]])

  @classmethod
  def resolve_dependencies(cls, groups: list[ConfigGroup]) -> list[list[ConfigGroup]]:
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
