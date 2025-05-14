from __future__ import annotations

from collections import defaultdict

from definitions import ConfigItem, ConfigItemGroup, ConfigManager, ConfigModule, ExecutionPhase, ExecutionState, Requires
from managers.checkpoint import CheckpointManager
from managers.file import FileManager
from managers.hook import HookManager
from managers.pacman import PacmanAdapter, PacmanPackageManager
from managers.pacman_key import PacmanKeyManager
from managers.symlink import SymlinkManager
from managers.systemd import SystemdUnitManager


class ArchUpdate:
  managers: list[ConfigManager] = [
    PacmanKeyManager(),
    PacmanPackageManager(PacmanAdapter("sudo -u manuel paru")),
    SymlinkManager(),
    FileManager(),
    SystemdUnitManager(),
    HookManager(),
    CheckpointManager(),
  ]
  modules: list[ConfigModule] = []
  cautious: bool = False
  paranoid: bool = False

  def plan(self):
    order = self.build_execution_order()
    for phase_idx, phase_managers in enumerate(order):
      print(f"Phase {phase_idx + 1}:")
      for manager, items in phase_managers:
        for item in items:
          print(f" - {item}")

  def apply(self):
    order = self.build_execution_order()
    state: ExecutionState = {"processed_items": [], "updated_items": []}
    for phase in order:
      for manager, items in phase:
        state["updated_items"] += manager.execute_phase(items, state) or []
        state["processed_items"] += items
    for manager in self.managers:
      all_items_for_manager = [item for phase in order for phase_manager, phase_items in phase for item in phase_items if phase_manager is manager]
      manager.finalize(all_items_for_manager, state)

  def build_execution_order(self) -> list[ExecutionPhase]:
    order: list[ExecutionPhase] = []
    for groups in self.separate_groups_into_phases():
      order.append(self.merge_into_phase(groups))

    # sanity checks
    flattened_items = [item for phase in order for manager, items in phase for item in items]
    for item in flattened_items:
      item.check_configuration(order)

    return order

  def separate_groups_into_phases(self):
    groups: list[ConfigItemGroup] = []
    for module in self.modules:
      provides = module.provides()
      groups += provides if isinstance(provides, list) else [provides]
    merged_groups = self.merge_groups(groups)

    phases: list[list[ConfigItemGroup]] = [merged_groups]
    while True:
      violation = self.find_order_violation(phases)
      if violation is None: break
      idx_phase, group = violation
      phases[idx_phase].remove(group)
      if idx_phase > 0:
        phases[idx_phase - 1].append(group)
      else:
        phases = [[group]] + phases
    return phases

  def merge_into_phase(self, groups: list[ConfigItemGroup]) -> ExecutionPhase:
    flattened_items = [item for group in groups for item in group.items if not isinstance(item, Requires)]
    result: list[(ConfigManager, list[ConfigItem])] = []
    for manager in self.managers:
      managed_items = [item for item in flattened_items if item.__class__ in manager.managed_classes]
      if len(managed_items) > 0:
        result.append((manager, managed_items))
    return result

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

  def find_order_violation(self, phases: list[list[ConfigItemGroup]]):
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
