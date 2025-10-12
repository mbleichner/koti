from __future__ import annotations

import sys
from copy import copy
from os import get_terminal_size, getuid
from time import sleep
from typing import Iterator

import koti.utils.shell as shell_module
from koti.model import *
from koti.optimizer import Optimizer
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
    optimizer = Optimizer(merged_configs, self.managers)
    model = optimizer.run()
    self.assert_config_items_installable(model)
    return model

  # FIXME: ins Model selbst integrieren?
  def create_cleanup_phase(self, model: ConfigModel) -> CleanupPhase:
    items_to_install = [item for step in model.steps for item in step.items_to_install]
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
    sys.stdout.write("calculating actions to perform...")
    sys.stdout.flush()
    actions: list[Action] = []
    items_total = [item for step in model.steps for item in step.items_to_install]
    for install_step in model.steps:
      sys.stdout.write(".")
      sys.stdout.flush()
      for action in install_step.manager.plan_install(install_step.items_to_install, model, dryrun):
        actions.append(action)

    # collect actions during  cleanup phase
    cleanup_phase = self.create_cleanup_phase(model)
    for cleanup_step in cleanup_phase.steps:
      sys.stdout.write(".")
      sys.stdout.flush()
      for action in cleanup_step.manager.plan_cleanup(cleanup_step.items_to_keep, model, dryrun):
        actions.append(action)

    print()
    print()

    for manager in self.managers:
      manager.finalize(model, dryrun)

    # list all groups + items
    if groups:
      printc(f"{BOLD}Config Group Summary:")
      for group in model.groups:
        prefix = self.prefix_for_item(actions, *(item for item in group.provides if isinstance(item, ManagedConfigItem)))
        printc(f"{prefix} {group.description}")
      print()

    if items:
      printc(f"{BOLD}Config Item Summary:")
      for install_step in model.steps:
        for idx, item in enumerate(install_step.items_to_install):
          prefix = self.prefix_for_item(actions, item)
          printc(f"{prefix} {item}")
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
      for action in actions:
        printc(f"- {self.color_for_action(action)}{action.description}")
        for info in action.additional_info:
          printc(f"  {info}")
      print()

    return ExecutionPlan(
      expected_actions = actions,
      model = model,
    )

  def apply(self, plan: ExecutionPlan):
    logger.clear()
    dryrun = False
    model = plan.model

    for manager in self.managers:
      manager.initialize(model, dryrun)

    # execute install phases
    for install_step in model.steps:
      for action in install_step.manager.plan_install(install_step.items_to_install, model, dryrun):
        self.execute_action(action, plan)

    # execute cleanup phase
    cleanup_phase = self.create_cleanup_phase(model)
    for cleanup_step in cleanup_phase.steps:
      for action in cleanup_step.manager.plan_cleanup(cleanup_step.items_to_keep, model, dryrun):
        self.execute_action(action, plan)

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

  def execute_action(self, action: Action, plan: ExecutionPlan):
    try:
      shell_module.verbose_mode = True
      self.print_divider_line()
      printc(f"executing: {self.color_for_action(action)}{action.description}")
      for info in action.additional_info:
        printc(f"{info}")
      if action not in plan.expected_actions:
        confirm("this action was not predicted during planning phase - please confirm to continue")
      action.execute()
      sleep(0.1)  # add a small delay so it's easier to follow when a lot of actions happen
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
    for install_step in model.steps:
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
    merged_items: dict[ConfigItem, ConfigItem] = {}
    for group in configs:
      for idx, item in enumerate(group.provides):
        item_prev = merged_items.get(item, None)
        item_merged = item_prev.merge(item) if item_prev is not None else item
        merged_items[item] = item_merged

    # create new groups with the items replaced by their merged versions
    result: list[ConfigGroup] = []
    for group in configs:
      provides_updated = list(group.provides)
      for idx, item in enumerate(provides_updated):
        provides_updated[idx] = merged_items[item]
      new_group = copy(group)
      new_group.provides = provides_updated
      result.append(new_group)
    return result

  @classmethod
  def remove_duplicates(cls, phases: list[list[ConfigGroup]]) -> list[list[ConfigGroup]]:
    seen_items: set[ConfigItem] = set()
    phases_filtered: list[list[ConfigGroup]] = []
    for phase in phases:
      phase_filtered: list[ConfigGroup] = []
      for group in phase:
        filtered_provides: list[ConfigItem] = []
        for item in group.provides:
          if item not in seen_items:
            filtered_provides.append(item)
            seen_items.add(item)
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
  def prefix_for_item(cls, actions: Sequence[Action], *items: ManagedConfigItem) -> str:
    changes: set[Literal["install", "update", "remove"]] = set()
    for item in items:
      for action in actions:
        if item in action.installs: changes.add("install")
        if item in action.updates: changes.add("update")
        if item in action.removes: changes.add("remove")
    if "remove" in changes: return f"{RED}~"
    if "update" in changes: return f"{YELLOW}~"
    if "install" in changes: return f"{GREEN}~"
    return "-"

  @classmethod
  def color_for_action(cls, action: Action) -> str:
    if action.removes:
      return RED
    elif action.updates:
      return YELLOW
    elif action.installs:
      return GREEN
    else:
      return PURPLE
