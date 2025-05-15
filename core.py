from __future__ import annotations

from collections import defaultdict
from typing import Literal, Type


class ArchUpdate:
  managers: list[ConfigManager]
  modules: list[ConfigModule]
  execution_phases: list[ExecutionPhase]
  default_confirm_mode: ConfirmModeValues

  def __init__(
    self,
    managers: list[ConfigManager],
    modules: list[ConfigModule],
    default_confirm_mode: ConfirmModeValues,
  ):
    super().__init__()
    self.default_confirm_mode = default_confirm_mode
    self.modules = modules
    self.managers = managers
    self.execution_phases = self.prepare_execution_phases()

  def plan(self):
    for phase_idx, phase in enumerate(self.execution_phases):
      print(f"Phase {phase_idx + 1}:")
      for manager, items in phase.execution_order:
        for item in items:
          print(f" - {item}")

  def apply(self):
    state = ExecutionState()
    for phase in self.execution_phases:
      for manager, items in phase.execution_order:
        state.updated_items += manager.execute_phase(items, self, state) or []
        state.processed_items += items
    for manager in self.managers:
      all_items_for_manager = [
        item for phase in self.execution_phases
        for phase_manager, phase_items in phase.execution_order
        for item in phase_items
        if phase_manager is manager
      ]
      manager.finalize(all_items_for_manager, self, state)

  def get_group_for_item(self, item: ConfigItem) -> ConfigItemGroup:
    for phase in self.execution_phases:
      for group in phase.merged_groups:
        if item in group.items:
          return group
    raise AssertionError(f"group not found for {item}")

  def prepare_execution_phases(self) -> list[ExecutionPhase]:
    original_groups: list[ConfigItemGroup] = self.get_all_provided_groups()
    merged_groups = self.merge_groups(original_groups)
    merged_groups_ordered_into_phases = self.reorder_into_phases(merged_groups)
    execution_phases: list[ExecutionPhase] = [
      self.create_execution_phase(groups_in_phase) for groups_in_phase in merged_groups_ordered_into_phases
    ]
    return execution_phases

  def reorder_into_phases(self, merged_groups: list[ConfigItemGroup]):
    result: list[list[ConfigItemGroup]] = [merged_groups]
    while True:
      violation = self.find_dependency_violation(result)
      if violation is None: break
      idx_phase, group = violation
      result[idx_phase].remove(group)
      if idx_phase > 0:
        result[idx_phase - 1].append(group)
      else:
        result = [[group]] + result
    return result

  def get_all_provided_groups(self):
    result: list[ConfigItemGroup] = []
    for module in self.modules:
      provides_raw = module.provides()
      provides_list = provides_raw if isinstance(provides_raw, list) else [provides_raw]
      result += [group for group in provides_list if group is not None]
    return result

  def create_execution_phase(self, merged_groups_in_phase: list[ConfigItemGroup]) -> ExecutionPhase:
    flattened_items = [item for group in merged_groups_in_phase for item in group.items if not isinstance(item, Requires)]
    execution_order: list[(ConfigManager, list[ConfigItem])] = []
    for manager in self.managers:
      managed_items = [item for item in flattened_items if item.__class__ in manager.managed_classes]
      if len(managed_items) > 0:
        execution_order.append((manager, managed_items))
    return ExecutionPhase(merged_groups_in_phase, execution_order)

  def merge_groups(self, groups: list[ConfigItemGroup]) -> list[ConfigItemGroup]:
    grouped_by_identifier: dict[str, list[ConfigItemGroup]] = defaultdict(list)
    unnamed_groups: list[ConfigItemGroup] = []
    for group in groups:
      if group.identifier is not None:
        grouped_by_identifier[group.identifier].append(group)
      else:
        unnamed_groups.append(group)
    result: list[ConfigItemGroup] = []
    for identifier, group_group in grouped_by_identifier.items():
      merged_items = [item for group in group_group for item in group.items]
      result.append(ConfigItemGroup(identifier, *merged_items))
    result += unnamed_groups
    return result

  def find_dependency_violation(self, phases: list[list[ConfigItemGroup]]):
    for phase_idx, phase in enumerate(phases):
      for group in phase:
        requires_items = [item for item in group.items if isinstance(item, Requires)]
        required_items = [item for req in requires_items for item in req.items]
        for required_item in required_items:
          required_phase_idx, required_group = self.find_required_group(required_item, phases)
          if required_phase_idx >= phase_idx:
            return required_phase_idx, required_group

  def find_required_group(self, required_item: ConfigItem | ConfigItemGroup, phases: list[list[ConfigItemGroup]]) -> [int, ConfigItemGroup]:
    for idx_phase, phase in enumerate(phases):
      for group in phase:
        if isinstance(required_item, ConfigItemGroup) and required_item.identifier == group.identifier:
          return idx_phase, group
        for group_item in group.items:
          if group_item.__class__ == required_item.__class__ and group_item.identifier == required_item.identifier:
            return idx_phase, group
    raise AssertionError("illegal state")

  def get_manager(self, name):
    for manager in self.managers:
      if manager.__class__.__name__ == name:
        return manager
    raise AssertionError(f"manager not found: '{name}'")


class ConfigModule:
  def provides(self) -> ConfigModuleGroups:
    return []


class ConfigItem:
  def __init__(self, identifier: str):
    self.identifier = identifier

  def check_configuration(self, state: ExecutionState):
    pass


class ConfigItemGroup:
  identifier: str | None
  items: list[ConfigItem]

  def __init__(self, first: str | ConfigItem | ConfigMetadata, *items: ConfigItem | ConfigMetadata):
    self.identifier = None if not isinstance(first, str) else first
    combined_items = ([] if isinstance(first, str) else [first]) + list(items)
    self.items = [item for item in combined_items if item is not None]


type ConfigModuleGroups = ConfigItemGroup | list[ConfigItemGroup]


class ConfigManager[T: ConfigItem]:
  managed_classes: list[Type] = []

  def check_configuration(self, item: T, core: ArchUpdate) -> bool:
    raise "method not implemented: check_configuration"

  def execute_phase(self, items: list[T], core: ArchUpdate, state: ExecutionState) -> list[T] | None:  # returns updated items
    raise "method not implemented: execute_phase"

  def finalize(self, items: list[T], core: ArchUpdate, state: ExecutionState) -> list[T]:  # returns updated items
    pass


class ConfigMetadata:
  pass


class Requires(ConfigMetadata):
  items: list[ConfigItem | ConfigItemGroup]

  def __init__(self, *items: ConfigItem | ConfigItemGroup):
    self.items = list(items)

  def __str__(self):
    return f"Require({", ".join([str(item) for item in self.items])})"


class ConfirmMode(ConfigMetadata):
  mode: ConfirmModeValues

  def __init__(self, mode: ConfirmModeValues):
    self.mode = mode

  def __str__(self):
    return f"ConfirmMode({self.mode})"


class ExecutionPhase:
  merged_groups: list[ConfigItemGroup]
  execution_order: list[tuple[ConfigManager, list[ConfigItem]]]

  def __init__(self, merged_groups: list[ConfigItemGroup], execution_order: list[tuple[ConfigManager, list[ConfigItem]]]):
    super().__init__()
    self.execution_order = execution_order
    self.merged_groups = merged_groups


class ExecutionState:
  processed_items: list[ConfigItem] = []
  updated_items: list[ConfigItem] = []


ConfirmModeValues = Literal["paranoid", "cautious", "yolo"]
