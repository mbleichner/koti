from __future__ import annotations

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
    self.check_manager_consistency(self.managers, self.configs)
    result = ConfigModel(
      managers = self.managers,
      phases = self.create_install_phases(self.managers, self.configs),
      tags_archive = self.load_tags(self.store),
    )
    self.check_config_item_consistency(result)
    return result

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
    planning = True
    for manager in self.managers:
      manager.log.clear()

    model = self.create_model()

    # plan installation phases
    items_total = [item for phase in model.phases for step in phase.steps for item in step.items_to_install]
    installed_identifiers = [item.identifier() for manager in model.managers for item in manager.installed(model)]
    items_outdated: list[ManagedConfigItem] = []
    for phase in model.phases:
      for step in phase.steps:
        manager = step.manager
        for item in step.items_to_install:
          changes = manager.describe_change(
            item = item,
            state_current = manager.state_current(item),
            state_target = manager.state_target(item, model, planning)
          )
          if changes:
            items_outdated.append(item)
            for change in changes:
              printc(f"~~ {item.description()}: {change}", CYAN)

    # plan cleanup phase
    cleanup_phase = self.create_cleanup_phase(model)
    items_to_uninstall = cleanup_phase.items_to_uninstall

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
                new = item.identifier() not in installed_identifiers
                printc(f"{"~" if new else "+"} {item.description()}", GREEN if new else YELLOW)
              else:
                printc(f"- {item.description()}")
        print()

    logs = [message for manager in self.managers for message in manager.log]
    if logs:
      printc(f"Logs:", BOLD)
      for message in logs:
        if message.level == "error":
          printc(f"- {message.text}", RED)
        if message.level == "warn":
          printc(f"- {message.text}", YELLOW)
        if message.level == "info":
          printc(f"- {message.text}")
        if message.level == "debug":
          printc(f"- {message.text}")
      print()

    count = len(items_outdated) + len(items_to_uninstall)
    if count > 0:
      maxlen = max((len(item.identifier()) for item in [*items_outdated, *items_to_uninstall]))
      print(f"{len(items_total)} items total, {count} items to update:")
      for item in items_outdated:
        if item.identifier() in installed_identifiers:
          printc(f"~ {item.description().ljust(maxlen)}  update   {", ".join(item.tags)}", YELLOW)
        else:
          printc(f"+ {item.description().ljust(maxlen)}  install  {", ".join(item.tags)}", GREEN)
      for item in items_to_uninstall:
        printc(f"- {item.description().ljust(maxlen)}  remove   {", ".join(item.tags)}", RED)
      print()
      print("// additional updates may be triggered by PostHooks")
    else:
      print(f"{len(items_total)} items total, everything up to date")

    return count > 0

  def apply(self):
    planning = False
    for manager in self.managers:
      manager.log.clear()

    model = self.create_model()

    for phase_idx, phase in enumerate(model.phases):
      for step in phase.steps:
        manager = step.manager
        items_to_update = [
          item for item in step.items_to_install if manager.describe_change(
            item = item,
            state_current = manager.state_current(item),
            state_target = manager.state_target(item, model, planning)
          )
        ]
        self.print_install_step_log(model, phase_idx, step, items_to_update)
        manager.install(items_to_update, model) or []

    cleanup_phase = self.create_cleanup_phase(model)
    for step in cleanup_phase.steps:
      manager = step.manager
      self.print_cleanup_step_log(model, step)
      manager.uninstall(step.items_to_uninstall, model)

    self.save_tags(self.store, model)

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
  def create_install_phases(cls, managers: Sequence[ConfigManager], configs: Sequence[ConfigGroup]) -> list[InstallPhase]:
    groups = cls.get_all_provided_groups(configs)
    groups_separated_into_phases = cls.separate_into_phases(groups)
    merged_items_grouped_by_phase: list[list[ConfigItem]] = cls.merge_items([
      [item for group in phase for item in group.provides]
      for phase in groups_separated_into_phases
    ])
    return [
      cls.create_install_phase(managers, groups_in_phase, items_in_phase) for groups_in_phase, items_in_phase in
      zip(groups_separated_into_phases, merged_items_grouped_by_phase)
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
    for group in cls.get_all_provided_groups(configs):
      for item in (x for x in group.provides if x is not None and isinstance(x, ManagedConfigItem)):
        matching_managers = [manager for manager in managers if item.__class__ in manager.managed_classes]
        if len(matching_managers) == 0:
          raise AssertionError(f"no manager found for class {item.__class__.__name__}")
        if len(matching_managers) > 1:
          raise AssertionError(f"multiple managers found for class {item.__class__.__name__}")

  @classmethod
  def merge_items(cls, items_grouped_by_phase: list[list[ConfigItem]]) -> list[list[ConfigItem]]:
    flattened = [item for phase in items_grouped_by_phase for item in phase]
    processed_identifiers: set[str] = set()
    result: list[list[ConfigItem]] = []
    for phase in items_grouped_by_phase:
      phase_new: list[ConfigItem] = []
      result.append(phase_new)
      for item in phase:
        if item.identifier() in processed_identifiers: continue
        others = [other for other in flattened if other.identifier() == item.identifier()]
        merged = cls.reduce_items(others)
        phase_new.append(merged)
        processed_identifiers.add(item.identifier())
    return result

  @classmethod
  def reduce_items(cls, items: list[ConfigItem]) -> ConfigItem:
    if len(items) == 1:
      return items[0]
    merged_item = items[0].merge(items[1])
    return cls.reduce_items([merged_item, *items[2:]])

  @classmethod
  def separate_into_phases(cls, groups: Sequence[ConfigGroup]) -> list[list[ConfigGroup]]:
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
  def get_all_provided_groups(cls, configs: Sequence[ConfigGroup]) -> Sequence[ConfigGroup]:
    result: list[ConfigGroup] = []
    for config_group in configs:
      config_group_list = config_group if isinstance(config_group, list) else [config_group]
      result += [group for group in config_group_list if group is not None]
    return result

  @classmethod
  def create_install_phase(cls, managers: Sequence[ConfigManager], groups_in_phase: list[ConfigGroup], merged_items_in_phase: list[ConfigItem]) -> InstallPhase:
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

  @classmethod
  def find_dependency_violation(cls, phases: list[list[ConfigGroup]]) -> tuple[int, ConfigGroup] | None:
    for phase_idx, phase in enumerate(phases):
      for group in phase:
        for required_item in group.requires:
          required_phase_and_group = cls.find_required_group(required_item, phases)
          if required_phase_and_group is None:
            raise AssertionError(f"required item not found: {required_item.identifier()}")
          required_phase_idx, required_group = required_phase_and_group
          if required_phase_idx >= phase_idx:
            if group == required_group: raise AssertionError(f"group with dependency to itself")
            return required_phase_idx, required_group
    return None

  @classmethod
  def find_required_group(cls, required_item: ConfigItem, phases: list[list[ConfigGroup]]) -> tuple[int, ConfigGroup] | None:
    for idx_phase, phase in enumerate(phases):
      for group in phase:
        for group_item in group.provides:
          if group_item.identifier() == required_item.identifier():
            return idx_phase, group
    return None
