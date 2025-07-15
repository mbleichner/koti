from __future__ import annotations

import os
from typing import Iterable, Iterator, Literal, Sequence, Type

type ConfirmModeValues = Literal["paranoid", "cautious", "yolo"]


class Koti:
  managers: Sequence[ConfigManager]
  configs: Sequence[ConfigGroup]
  execution_phases: Sequence[ExecutionPhase]
  default_confirm_mode: ConfirmModeValues

  def __init__(
    self,
    managers: Iterator[ConfigManager | None] | Iterable[ConfigManager | None],
    configs: Iterator[ConfigGroup | None] | Iterable[ConfigGroup | None],
    default_confirm_mode: ConfirmModeValues = "cautious"
  ):
    self.configs = [c for c in configs if c is not None]
    self.managers = [m for m in managers if m is not None]
    Koti.check_manager_consistency(self.managers, self.configs)
    self.default_confirm_mode = default_confirm_mode
    self.execution_phases = Koti.build_execution_phases(self.managers, self.configs)
    Koti.check_config_item_consistency(self.managers, self.configs, self)

  def plan(self, groups: bool = True, items: bool = True, summary: bool = True) -> int:
    items_total: list[ConfigItem] = []
    items_to_update: list[ConfigItem] = []
    for phase_idx, phase in enumerate(self.execution_phases):

      for manager, items_in_phase in phase.execution_order:
        checksums = manager.checksums(self)
        for item in items_in_phase:
          items_total.append(item)
          needs_update = checksums.current(item) != checksums.target(item)
          if needs_update:
            items_to_update.append(item)

      print(f"Phase {phase_idx + 1}:")
      if groups:
        for group in phase.groups_in_phase:
          needs_update = len([item for item in group.provides if item in items_to_update]) > 0
          print(f"{"*" if needs_update else "-"} {group.description}")
      if items:
        for manager, items_in_phase in phase.execution_order:
          for item in items_in_phase:
            needs_update = item in items_to_update
            print(f"{"*" if needs_update else "-"} {item.description()}")
      print()

    if summary:
      if len(items_to_update) > 0:
        print(f"{len(items_total)} items total, {len(items_to_update)} items to update:")
        for item in items_to_update: print(f"- {item.description()}")
        print()
      else:
        print(f"{len(items_total)} items total, no outdated items found - only cleanup will be performed")
        print()

    return len(items_to_update)

  def apply(self):
    if os.getuid() != 0:
      raise AssertionError("this program must be run as root (or through sudo)")
    for phase_idx, phase in enumerate(self.execution_phases):
      for manager, items in phase.execution_order:
        checksums = manager.checksums(self)
        items_to_update = [item for item in items if checksums.current(item) != checksums.target(item)]
        self.print_phase_log(phase_idx, manager, items_to_update)
        manager.install(items_to_update, self) or []

    for manager in self.get_cleanup_phase_manager_order():
      all_items_for_manager = [
        item for phase in self.execution_phases
        for phase_manager, phase_items in phase.execution_order
        for item in phase_items
        if phase_manager is manager
      ]
      if len(all_items_for_manager):
        self.print_phase_log(None, manager, [])
        manager.cleanup(all_items_for_manager, self)

  def print_phase_log(self, phase_idx: int | None, manager: ConfigManager, items_to_update: list[ConfigItem]):
    phase = f"Phase {phase_idx + 1}" if phase_idx is not None else "Cleanup"
    max_manager_name_len = max([len(m.__class__.__name__) for m in self.managers])

    if phase_idx is None:
      details = "cleaning up leftover items"
    elif len(items_to_update) == 0:
      details = "no outdated items found"
    else:
      details = f"items to update: {", ".join([item.description() for item in items_to_update])}"

    print(f"{phase}  {manager.__class__.__name__.ljust(max_manager_name_len)}  {details}")

  def get_cleanup_phase_manager_order(self):
    return [
      *[manager for manager in self.managers if manager.order_in_cleanup_phase == "first"],
      *reversed([manager for manager in self.managers if manager.order_in_cleanup_phase == "reverse_install_order"]),
      *[manager for manager in self.managers if manager.order_in_cleanup_phase == "last"],
    ]

  def get_group_for_item(self, item: ConfigItem) -> ConfigGroup:
    for phase in self.execution_phases:
      for group in phase.groups_in_phase:
        if item in group.provides:
          return group
    raise AssertionError(f"group not found for {item.identifier()}")

  def _get_confirm_mode_single(self, item: ConfigItem) -> ConfirmModeValues:
    if item.confirm_mode is not None:
      return item.confirm_mode
    group = self.get_group_for_item(item)
    if group.confirm_mode is not None:
      return group.confirm_mode
    return self.default_confirm_mode

  def _merge_confirm_modes(self, modes: Sequence[ConfirmModeValues]) -> ConfirmModeValues:
    modes_in_order: list[ConfirmModeValues] = ["paranoid", "cautious", "yolo"]
    for mode in modes_in_order:
      if mode in modes: return mode
    return self.default_confirm_mode

  def get_confirm_mode(self, *items: ConfigItem | ConfirmModeValues) -> ConfirmModeValues:
    confirm_modes_from_items = [self._get_confirm_mode_single(item) for item in items if isinstance(item, ConfigItem)]
    confirm_modes_from_strings = [item for item in items if isinstance(item, str)]
    return self._merge_confirm_modes(confirm_modes_from_items + confirm_modes_from_strings)

  def get_manager_for_item(self, item: ConfigItem):
    for manager in self.managers:
      if item.__class__ in manager.managed_classes:
        return manager
    raise AssertionError(f"manager not found for item: {str(item)}")

  @staticmethod
  def build_execution_phases(managers: Sequence[ConfigManager], configs: Sequence[ConfigGroup]) -> list[ExecutionPhase]:
    groups = Koti.get_all_provided_groups(configs)
    groups_ordered_into_phases = Koti.reorder_into_phases(groups)
    execution_phases: list[ExecutionPhase] = [
      Koti.create_execution_phase(managers, groups_in_phase) for groups_in_phase in groups_ordered_into_phases
    ]
    return execution_phases

  @staticmethod
  def check_manager_consistency(managers: Sequence[ConfigManager], configs: Sequence[ConfigGroup]):
    for group in Koti.get_all_provided_groups(configs):
      for item in filter(lambda x: x is not None, group.provides):
        matching_managers = [manager for manager in managers if item.__class__ in manager.managed_classes]
        if len(matching_managers) == 0:
          raise AssertionError(f"no manager found for class {item.__class__.__name__}")
        if len(matching_managers) > 1:
          raise AssertionError(f"multiple managers found for class {item.__class__.__name__}")

  @staticmethod
  def check_config_item_consistency(managers: Sequence[ConfigManager], configs: Sequence[ConfigGroup], koti: Koti):
    for group in Koti.get_all_provided_groups(configs):
      for item in filter(lambda x: x is not None, group.provides):
        if not isinstance(item, ConfigItem): continue
        matching_managers = [manager for manager in managers if item.__class__ in manager.managed_classes]
        manager = matching_managers[0]
        try:
          manager.check_configuration(item, koti)
        except Exception as e:
          raise AssertionError(f"{manager.__class__.__name__}: {e}")

  @staticmethod
  def reorder_into_phases(groups: Sequence[ConfigGroup]) -> list[list[ConfigGroup]]:
    result: list[list[ConfigGroup]] = [list(groups)]
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
  def get_all_provided_groups(configs: Sequence[ConfigGroup]) -> Sequence[ConfigGroup]:
    result: list[ConfigGroup] = []
    for config_group in configs:
      config_group_list = config_group if isinstance(config_group, list) else [config_group]
      result += [group for group in config_group_list if group is not None]
    return result

  @staticmethod
  def create_execution_phase(managers: Sequence[ConfigManager], groups_in_phase: Sequence[ConfigGroup]) -> ExecutionPhase:
    flattened_items = [item for group in groups_in_phase for item in group.provides if item is not None]
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
        for required_item in group.requires:
          required_phase_and_group = Koti.find_required_group(required_item, phases)
          if required_phase_and_group is None:
            raise AssertionError(f"required item not found: {required_item.identifier()}")
          required_phase_idx, required_group = required_phase_and_group
          if required_phase_idx >= phase_idx:
            if group == required_group: raise AssertionError(f"group with dependency to itself")
            return required_phase_idx, required_group
    return None

  @staticmethod
  def find_required_group(required_item: ConfigItem, phases: list[list[ConfigGroup]]) -> tuple[int, ConfigGroup] | None:
    for idx_phase, phase in enumerate(phases):
      for group in phase:
        for group_item in group.provides:
          if group_item.identifier() == required_item.identifier():
            return idx_phase, group
    return None


class ConfigItem:
  confirm_mode: ConfirmModeValues | None

  def identifier(self) -> str:
    raise AssertionError(f"method not implemented: {self.__class__.__name__}.identifier()")

  def description(self) -> str:
    return self.identifier()


class ConfigGroup:
  description: str
  confirm_mode: ConfirmModeValues | None
  requires: Sequence[ConfigItem]
  provides: Sequence[ConfigItem]

  def __init__(self, description: str, provides: Sequence[ConfigItem | None], requires: Sequence[ConfigItem | None] | None = None, confirm_mode: ConfirmModeValues | None = None):
    self.description = description
    self.confirm_mode = confirm_mode
    self.requires = [item for item in (requires or []) if item is not None]
    self.provides = [item for item in (provides or []) if item is not None]

  def __str__(self):
    return f"ConfigGroup('{self.description}')"


class ConfigManager[T: ConfigItem]:
  managed_classes: list[Type] = []
  order_in_cleanup_phase: Literal["reverse_install_order", "first", "last"] = "reverse_install_order"

  def check_configuration(self, item: T, core: Koti):
    raise AssertionError(f"method not implemented: {self.__class__.__name__}.check_configuration()")

  def checksums(self, core: Koti) -> Checksums[T]:
    raise AssertionError(f"method not implemented: {self.__class__.__name__}.checksums()")

  def install(self, items: list[T], core: Koti):
    raise AssertionError(f"method not implemented: {self.__class__.__name__}.install()")

  def cleanup(self, items_to_keep: list[T], core: Koti):
    raise AssertionError(f"method not implemented: {self.__class__.__name__}.cleanup()")


class Checksums[T:ConfigItem]:

  def current(self, item: T) -> str | None:
    pass

  def target(self, item: T) -> str | None:
    pass


class ConfigMetadata:
  pass


class ExecutionPhase:
  groups_in_phase: Sequence[ConfigGroup]
  execution_order: Sequence[tuple[ConfigManager, list[ConfigItem]]]

  def __init__(self, groups_in_phase: Sequence[ConfigGroup], execution_order: Sequence[tuple[ConfigManager, list[ConfigItem]]]):
    self.groups_in_phase = groups_in_phase
    self.execution_order = execution_order
