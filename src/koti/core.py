from __future__ import annotations

import os
from typing import Literal, Type

type ConfirmModeValues = Literal["paranoid", "cautious", "yolo"]
type ConfigGroups = list[ConfigGroup | None] | ConfigGroup | None


class Koti:
  managers: list[ConfigManager]
  configs: list[ConfigGroups]
  execution_phases: list[ExecutionPhase]
  default_confirm_mode: ConfirmModeValues

  def __init__(self, managers: list[ConfigManager], configs: list[ConfigGroups], default_confirm_mode: ConfirmModeValues = "cautious"):
    Koti.check_manager_consistency(managers, configs)
    self.default_confirm_mode = default_confirm_mode
    self.configs = configs
    self.managers = managers
    self.execution_phases = Koti.build_execution_phases(managers, configs)
    Koti.check_config_item_consistency(managers, configs, self)

  def plan(self, summary: bool = True) -> int:
    items_total: list[ConfigItem] = []
    items_to_update: list[ConfigItem] = []
    for phase_idx, phase in enumerate(self.execution_phases):
      print(f"Phase {phase_idx + 1}:")
      for manager, items in phase.execution_order:
        checksums = manager.checksums(self)
        for item in items:
          items_total.append(item)
          needs_update = checksums.current(item) != checksums.target(item)
          if needs_update: items_to_update.append(item)
          print(f"{"*" if needs_update else "-"} {item}")
      print()

    if summary:
      if len(items_to_update) > 0:
        print(f"{len(items_total)} items total, {len(items_to_update)} items to update:")
        for item in items_to_update: print(f"- {item}")
        print()
      else:
        print(f"{len(items_total)} items total, everything up to date")
        print()

    return len(items_to_update)

  def apply(self):
    if os.getuid() != 0:
      raise AssertionError("this program must be run as root (or through sudo)")

    for phase_idx, phase in enumerate(self.execution_phases):
      for manager, items in phase.execution_order:
        checksums = manager.checksums(self)
        items_to_update = [item for item in items if checksums.current(item) != checksums.target(item)]
        self.print_phase_log(phase_idx, manager, items, items_to_update)
        manager.apply_phase(items_to_update, self) or []

    for manager in reversed(self.managers):
      all_items_for_manager = [
        item for phase in self.execution_phases
        for phase_manager, phase_items in phase.execution_order
        for item in phase_items
        if phase_manager is manager
      ]
      if len(all_items_for_manager):
        self.print_phase_log(None, manager, all_items_for_manager, [])
        manager.cleanup(all_items_for_manager, self)

  def print_phase_log(self, phase_idx: int | None, manager: ConfigManager, items: list[ConfigItem], items_to_update: list[ConfigItem]):
    phase = f"Phase {phase_idx + 1}" if phase_idx is not None else "Cleanup"
    max_manager_name_len = max([len(m.__class__.__name__) for m in self.managers])

    if len(items_to_update) == 0:
      details = "all items up to date"
    else:
      details = f"items to update: {", ".join([str(item) for item in items_to_update])}"

    print(f"{phase}  {manager.__class__.__name__.ljust(max_manager_name_len)}  {details}")

  def get_group_for_item(self, item: ConfigItem) -> ConfigGroup:
    for phase in self.execution_phases:
      for group in phase.groups_in_phase:
        if item in group.items:
          return group
    raise AssertionError(f"group not found for {item}")

  def get_confirm_mode_for_item(self, items: ConfigItem | list[ConfigItem]) -> ConfirmModeValues:
    item_list = items if isinstance(items, list) else [items]
    groups = [self.get_group_for_item(item) for item in item_list]
    confirm_modes = [item.mode for group in groups for item in group.items if isinstance(item, ConfirmMode)]
    return self.get_effective_confirm_mode(confirm_modes)

  def get_effective_confirm_mode(self, modes: list[ConfirmModeValues]) -> ConfirmModeValues:
    modes_in_order: list[ConfirmModeValues] = ["paranoid", "cautious", "yolo"]
    for mode in modes_in_order:
      if mode in modes: return mode
    return self.default_confirm_mode

  def get_manager_for_item(self, item: ConfigItem):
    for manager in self.managers:
      if item.__class__ in manager.managed_classes:
        return manager
    raise AssertionError(f"manager not found for item: {str(item)}")

  @staticmethod
  def build_execution_phases(managers: list[ConfigManager], configs: list[ConfigGroups]) -> list[ExecutionPhase]:
    groups = Koti.get_all_provided_groups(configs)
    groups_ordered_into_phases = Koti.reorder_into_phases(groups)
    execution_phases: list[ExecutionPhase] = [
      Koti.create_execution_phase(managers, groups_in_phase) for groups_in_phase in groups_ordered_into_phases
    ]
    return execution_phases

  @staticmethod
  def check_manager_consistency(managers: list[ConfigManager], configs: list[ConfigGroups]):
    for group in Koti.get_all_provided_groups(configs):
      for item in group.items:
        if isinstance(item, ConfigMetadata): continue
        matching_managers = [manager for manager in managers if item.__class__ in manager.managed_classes]
        if len(matching_managers) == 0:
          raise AssertionError(f"no manager found for class {item.__class__.__name__}")
        if len(matching_managers) > 1:
          raise AssertionError(f"multiple managers found for class {item.__class__.__name__}")

  @staticmethod
  def check_config_item_consistency(managers: list[ConfigManager], configs: list[ConfigGroups], koti: Koti):
    for group in Koti.get_all_provided_groups(configs):
      for item in group.items:
        if isinstance(item, ConfigMetadata): continue
        matching_managers = [manager for manager in managers if item.__class__ in manager.managed_classes]
        manager = matching_managers[0]
        try:
          manager.check_configuration(item, koti)
        except Exception as e:
          raise AssertionError(f"{manager.__class__.__name__}: {e}")

  @staticmethod
  def reorder_into_phases(groups: list[ConfigGroup]):
    result: list[list[ConfigGroup]] = [groups]
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
  def get_all_provided_groups(configs: list[ConfigGroups]) -> list[ConfigGroup]:
    result: list[ConfigGroup] = []
    for config_group in configs:
      config_group_list = config_group if isinstance(config_group, list) else [config_group]
      result += [group for group in config_group_list if group is not None]
    return result

  @staticmethod
  def create_execution_phase(managers: list[ConfigManager], groups_in_phase: list[ConfigGroup]) -> ExecutionPhase:
    flattened_items = [item for group in groups_in_phase for item in group.items]
    execution_order: list[tuple[ConfigManager, list[ConfigItem]]] = []
    for manager in managers:
      managed_items = [item for item in flattened_items if item.__class__ in manager.managed_classes]
      if len(managed_items) > 0:
        execution_order.append((manager, managed_items))
    return ExecutionPhase(groups_in_phase, execution_order)

  @staticmethod
  def find_dependency_violation(phases: list[list[ConfigGroup]]) -> tuple[int, ConfigGroup] | None:
    for phase_idx, phase in enumerate(phases):
      for group in phase:
        for requires_item in [item for item in group.items if isinstance(item, Requires)]:
          for required_item in requires_item.items:
            required_phase_and_group = Koti.find_required_group(required_item, phases)
            if required_phase_and_group is None:
              raise AssertionError(f"required item not found: {required_item}")
            required_phase_idx, required_group = required_phase_and_group
            if required_phase_idx >= phase_idx:
              if group == required_group: raise AssertionError(f"group with dependency to itself")
              return required_phase_idx, required_group
    return None

  @staticmethod
  def find_required_group(required_item: ConfigItem | ConfigGroup, phases: list[list[ConfigGroup]]) -> tuple[int, ConfigGroup] | None:
    for idx_phase, phase in enumerate(phases):
      for group in phase:
        for group_item in group.items:
          if group_item.__class__ == required_item.__class__ and group_item.identifier == required_item.identifier:
            return idx_phase, group
    return None


class ConfigItem:
  def __init__(self, identifier: str):
    self.identifier = identifier

  def check_configuration(self):
    pass

  def state_hash(self) -> str:
    pass


class ConfigGroup:
  items: list[ConfigItem | ConfigMetadata | None]

  def __init__(self, *items: ConfigItem | ConfigMetadata | None):
    self.items = list(items)


class ConfigManager[T: ConfigItem]:
  managed_classes: list[Type] = []

  def check_configuration(self, item: T, core: Koti):
    raise AssertionError(f"method not implemented: {self.__class__.__name__}.check_configuration()")

  def checksums(self, core: Koti) -> Checksums[T]:
    raise AssertionError(f"method not implemented: {self.__class__.__name__}.checksums()")

  def checksum_current(self, items: list[T], core: Koti) -> str | None:
    raise AssertionError(f"method not implemented: {self.__class__.__name__}.checksum_current()")

  def checksum_target(self, items: list[T], core: Koti) -> str | None:
    raise AssertionError(f"method not implemented: {self.__class__.__name__}.checksum_target()")

  def apply_phase(self, items: list[T], core: Koti):
    raise AssertionError(f"method not implemented: {self.__class__.__name__}.apply_phase()")

  def cleanup(self, items: list[T], core: Koti):
    raise AssertionError(f"method not implemented: {self.__class__.__name__}.cleanup()")


class Checksums[T:ConfigItem]:

  def current(self, item: T) -> str | None:
    pass

  def target(self, item: T) -> str | None:
    pass


class ConfigMetadata:
  pass


class Requires(ConfigMetadata):
  items: list[ConfigItem]

  def __init__(self, *items: ConfigItem):
    self.items = list(items)

  def __str__(self):
    return f"Requires({", ".join([str(item) for item in self.items])})"


class ConfirmMode(ConfigMetadata):
  mode: ConfirmModeValues

  def __init__(self, mode: ConfirmModeValues):
    self.mode = mode

  def __str__(self):
    return f"ConfirmMode({self.mode})"


class ExecutionPhase:
  groups_in_phase: list[ConfigGroup]
  execution_order: list[tuple[ConfigManager, list[ConfigItem]]]

  def __init__(self, groups_in_phase: list[ConfigGroup], execution_order: list[tuple[ConfigManager, list[ConfigItem]]]):
    self.groups_in_phase = groups_in_phase
    self.execution_order = execution_order
