from __future__ import annotations

from collections import defaultdict

from lib import ConfigItem, ConfigItemGroup, ConfigManager, ConfigModule, ExecutionPhase, ExecutionState, Requires
from managers.checkpoint import CheckpointManager
from managers.file import FileManager
from managers.hook import PostHookManager, PreHookManager
from managers.pacman import PacmanAdapter, PacmanPackageManager
from managers.pacman_key import PacmanKeyManager
from managers.swapfile import SwapfileManager
from managers.systemd import SystemdUnitManager




class ArchUpdate:
  managers: list[ConfigManager] = [
    PreHookManager(),
    SwapfileManager(),
    PacmanKeyManager(),
    PacmanPackageManager(PacmanAdapter("sudo -u manuel paru")),
    FileManager(),
    SystemdUnitManager(),
    PostHookManager(),
    CheckpointManager(),
  ]
  modules: list[ConfigModule] = []
  cautious: bool = False
  paranoid: bool = False

  def plan(self):
    state = self.init_state()
    for phase_idx, phase in enumerate(state.execution_phases):
      print(f"Phase {phase_idx + 1}:")
      for manager, items in phase.execution_order:
        for item in items:
          print(f" - {item}")

  def apply(self):
    state = self.init_state()
    for phase in state.execution_phases:
      for manager, items in phase.execution_order:
        state.updated_items += manager.execute_phase(items, state) or []
        state.processed_items += items
    for manager in self.managers:
      all_items_for_manager = [
        item for phase in state.execution_phases
        for phase_manager, phase_items in phase.execution_order
        for item in phase_items
        if phase_manager is manager
      ]
      manager.finalize(all_items_for_manager, state)

  def init_state(self):
    original_groups: list[ConfigItemGroup] = self.get_all_provided_groups()
    merged_groups = self.merge_groups(original_groups)
    merged_groups_ordered_into_phases = self.reorder_into_phases(merged_groups)
    execution_phases: list[ExecutionPhase] = [
      self.create_execution_phase(groups_in_phase) for groups_in_phase in merged_groups_ordered_into_phases
    ]
    return ExecutionState(execution_phases)

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
      provides = module.provides()
      result += provides if isinstance(provides, list) else [provides]
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
