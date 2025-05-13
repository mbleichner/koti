from __future__ import annotations

from collections import defaultdict

from definitions import ConfigItem, ConfigItemGroup, ConfigManager, ConfigModule, Requires
from managers.checkpoint import CheckpointManager
from managers.file import FileManager
from managers.command import IdempotentCommandManager
from managers.package import PackageManager, PacmanLikeSyntax
from managers.pacman_key import PacmanKeyManager
from managers.symlink import SymlinkManager
from managers.systemd import SystemdUnitManager

type ExecutionPhase = list[tuple[ConfigManager, list[ConfigItem]]]


class ArchUpdate:
  managers: list[ConfigManager] = [
    PacmanKeyManager(),
    PackageManager(PacmanLikeSyntax("sudo -u manuel paru")),
    SymlinkManager(),
    FileManager(),
    SystemdUnitManager(),
    IdempotentCommandManager(),
    CheckpointManager(),
  ]
  modules: list[ConfigModule] = []
  dry_run = True

  def execute(self):
    all_items_per_manager = [[] for manager in self.managers]
    for phase in self.build_execution_order():
      execute_phase_results_per_manager = [[] for manager in self.managers]
      for manager, items in phase:
        all_items_per_manager[self.managers.index(manager)] += items
        execute_phase_results = manager.execute_phase(items)
        execute_phase_results_per_manager[self.managers.index(manager)] = execute_phase_results
      for manager, _ in phase:
        execute_phase_results = execute_phase_results_per_manager[self.managers.index(manager)]
        manager.finalize_phase(execute_phase_results)
    for manager in self.managers:
      all_items = all_items_per_manager[self.managers.index(manager)]
      manager.finalize(all_items)

  def build_execution_order(self) -> list[ExecutionPhase]:
    result: list[ExecutionPhase] = []
    for groups in self.separate_groups_into_phases():
      result.append(self.merge_into_phase(groups))
    return result

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
