from __future__ import annotations

from copy import copy
from os import get_terminal_size, getuid
from typing import Iterator

import koti.utils.shell as shell_module
from koti.model import *
from koti.utils.colors import *
from koti.utils.confirm import confirm
from koti.utils.json_store import *
from koti.utils.logging import logger


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
    model = ConfigModel(
      managers = self.managers,
      phases = [self.create_install_phase(self.managers, groups_in_phase) for groups_in_phase in phases_without_duplicates],
    )

    self.assert_config_items_installable(model)
    return model

  def create_cleanup_phase(self, model: ConfigModel) -> CleanupPhase:
    items_to_install = [item for phase in model.phases for step in phase.steps for item in step.items_to_install]
    steps: list[CleanupStep] = []
    for manager in self.get_cleanup_phase_manager_order(self.managers):
      steps.append(CleanupStep(
        manager = manager,
        items_to_keep = [item for item in items_to_install if item.__class__ in manager.managed_classes],
      ))
    return CleanupPhase(steps)

  def plan(self, groups: bool = True, items: bool = False) -> ExecutionPlan:
    logger.clear()
    dryrun = True
    model = self.create_model()

    for manager in self.managers:
      manager.initialize(model, dryrun)

    # collect actions during installation phases
    actions: list[Action] = []
    items_total = [item for phase in model.phases for step in phase.steps for item in step.items_to_install]
    for phase in model.phases:
      for install_step in phase.steps:
        for plan in install_step.manager.plan_install(install_step.items_to_install, model, dryrun):
          actions.append(plan)

    # collect actions during  cleanup phase
    cleanup_phase = self.create_cleanup_phase(model)
    for cleanup_step in cleanup_phase.steps:
      for plan in cleanup_step.manager.plan_cleanup(cleanup_step.items_to_keep, model, dryrun):
        actions.append(plan)

    for manager in self.managers:
      manager.finalize(model, dryrun)

    # list all groups + items
    if groups or items:
      for phase_idx, phase in enumerate(model.phases):
        printc(f"{BOLD}Phase {phase_idx + 1}:")
        if groups:
          for group in phase.groups:
            prefix = self.get_change_prefix(actions, *(item for item in group.provides if isinstance(item, ManagedConfigItem)))
            printc(f"{prefix} {group.description}")
        if items:
          for install_step in phase.steps:
            for item in install_step.items_to_install:
              prefix = self.get_change_prefix(actions, item)
              printc(f"{prefix} {item.description()}")
        print()

    printc(f"{len(items_total)} items total")
    print()

    # print warnings generated during evaluation
    if logger.messages:
      printc(f"{BOLD}Messages logged during planning:")
      for message in set(logger.messages):
        printc(f"- {message}")
      print()

    # list all changed items
    if len(actions) > 0:
      printc(f"{BOLD}Actions that will be executed (in order):")
      for plan in actions:
        printc(f"- {plan.description}")
        for info in plan.additional_info:
          printc(f"  {info}")
      print()

    return ExecutionPlan(
      actions = actions,
      model = model,
    )

  def apply(self, plan: ExecutionPlan):
    logger.clear()
    dryrun = False
    model = plan.model

    for manager in self.managers:
      manager.initialize(model, dryrun)

    # execute install phases
    for phase_idx, phase in enumerate(model.phases):
      for install_step in phase.steps:
        for action in install_step.manager.plan_install(install_step.items_to_install, model, dryrun):
          self.execute_plan(action, plan)

    # execute cleanup phase
    cleanup_phase = self.create_cleanup_phase(model)
    for cleanup_step in cleanup_phase.steps:
      for action in cleanup_step.manager.plan_cleanup(cleanup_step.items_to_keep, model, dryrun):
        self.execute_plan(action, plan)

    # updating persistent data
    for manager in self.managers:
      manager.finalize(model, dryrun)

    self.print_divider_line()
    print("execution finished.")

    if logger.messages:
      print()
      printc(f"{BOLD}Messages logged during execution:")
      for message in set(logger.messages):
        printc(f"- {message}")

  def execute_plan(self, action: Action, plan: ExecutionPlan):
    try:
      shell_module.verbose_mode = True
      self.print_divider_line()
      printc(f"executing: {action.description}")
      for info in action.additional_info:
        printc(f"{info}")
      if action not in plan.expected_actions:
        confirm("This action was not predicted during planning phase - please confirm to continue")
      action.execute()
    finally:
      shell_module.verbose_mode = False

  @classmethod
  def print_divider_line(cls):
    printc(f"{"-" * (get_terminal_size().columns - 1)}")

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
        assert len(matching_managers) > 0, f"no manager found for class {item.__class__.__name__}"
        assert len(matching_managers) < 2, f"multiple managers found for class {item.__class__.__name__}"

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
      assert len(result[idx_phase]) > 0, "could not order dependencies (check for circular dependencies)"
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

  @classmethod
  def find_dependency_violation(cls, phases: list[list[ConfigGroup]]) -> tuple[int, ConfigGroup] | None:
    """Finds ConfigGroups that would be executed too late and need to be moved into an earlier phase."""
    for phase_idx, phase in enumerate(phases):
      for group in phase:

        # check "requires" dependencies
        for required_item in group.requires:
          required_phase_and_group = cls.find_required_group(required_item, phases)
          assert required_phase_and_group is not None, f"required item not found: {required_item.identifier()}"
          required_phase_idx, required_group = required_phase_and_group
          if required_phase_idx >= phase_idx:
            assert required_group is not group, f"group with requires-dependency to itself: {group.description}"
            return required_phase_idx, required_group

        # check "after" dependencies
        for item in group.provides:
          for other_phase_idx, other_phase in enumerate(phases):
            for other_group in other_phase:
              if other_group.after(item) and phase_idx >= other_phase_idx:
                assert other_group is not group, f"group with after-dependency to itself: {group.description}"
                return phase_idx, group

        # check "before" dependencies
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

  @classmethod
  def get_change_prefix(cls, plans: Sequence[Action], *items: ManagedConfigItem) -> str:
    changes: set[Literal["install", "update", "remove"]] = set()
    for item in items:
      for plan in plans:
        if item in plan.installs: changes.add("install")
        if item in plan.updates: changes.add("update")
        if item in plan.removes: changes.add("remove")
    if "remove" in changes: return f"{RED}~"
    if "update" in changes: return f"{YELLOW}~"
    if "install" in changes: return f"{GREEN}~"
    return "-"
