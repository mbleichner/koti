from __future__ import annotations

from abc import ABCMeta, abstractmethod
from os import getuid
from typing import Callable, Iterable, Iterator, Literal, Sequence, Type, cast

from koti.utils import highest_confirm_mode

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
    Koti.check_config_item_consistency(self.managers, self.configs, self)  # needs to be executed last when koti is fully initialized

  def plan(self, groups: bool = True, items: bool = True, summary: bool = True) -> int:
    items_total: list[ConfigItem] = []
    items_to_update: list[ManagedConfigItem] = []
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
    if getuid() != 0:
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
        if item.identifier() in [p.identifier() for p in group.provides]:
          return group
    raise AssertionError(f"group not found for {item.identifier()}")

  def get_confirm_mode(self, *args: ManagedConfigItem | ConfirmModeValues) -> ConfirmModeValues:
    items = [item for item in args if isinstance(item, ConfigItem)]

    confirm_modes_from_strings = [item for item in args if isinstance(item, str)]
    confirm_modes_from_items = [
      group.confirm_mode
      for phase in self.execution_phases
      for group in phase.groups_in_phase
      for item in items
      if item.identifier() in [p.identifier() for p in group.provides]
    ]

    highest = highest_confirm_mode(*confirm_modes_from_items, *confirm_modes_from_strings)
    if highest: return highest
    return self.default_confirm_mode

  def get_manager_for_item(self, item: ConfigItem):
    for manager in self.managers:
      if item.__class__ in manager.managed_classes:
        return manager
    raise AssertionError(f"manager not found for item: {str(item)}")

  def get_item[T: ConfigItem](self, reference: T) -> T | None:
    return next((
      cast(T, item)
      for phase in self.execution_phases
      for item in phase.merged_items_in_phase
      if item.identifier() == reference.identifier()
    ), None)

  def map_item[T: ConfigItem, R](self, reference: T, map: Callable[[T], R], fallback: R) -> R:
    item = next((cast(T, item) for phase in self.execution_phases for item in phase.merged_items_in_phase if item.identifier() == reference.identifier()), None)
    return map(item) if item is not None else fallback

  @staticmethod
  def build_execution_phases(managers: Sequence[ConfigManager], configs: Sequence[ConfigGroup]) -> list[ExecutionPhase]:
    groups = Koti.get_all_provided_groups(configs)
    groups_separated_into_phases = Koti.separate_into_phases(groups)

    merged_items_grouped_by_phase: list[list[ConfigItem]] = Koti.merge_items([
      [item for group in phase for item in group.provides]
      for phase in groups_separated_into_phases
    ])

    return [
      Koti.create_execution_phase(managers, groups_in_phase, items_in_phase)
      for groups_in_phase, items_in_phase in zip(groups_separated_into_phases, merged_items_grouped_by_phase)
    ]

  @staticmethod
  def merge_items(items_grouped_by_phase: list[list[ConfigItem]]) -> list[list[ConfigItem]]:
    flattened = [item for phase in items_grouped_by_phase for item in phase]
    processed_identifiers: set[str] = set()
    result: list[list[ConfigItem]] = []
    for phase in items_grouped_by_phase:
      phase_new: list[ConfigItem] = []
      result.append(phase_new)
      for item in phase:
        if item.identifier() in processed_identifiers: continue
        others = [other for other in flattened if other.identifier() == item.identifier()]
        merged = Koti.reduce_items(others)
        phase_new.append(merged)
        processed_identifiers.add(item.identifier())
    return result

  @staticmethod
  def reduce_items(items: list[ConfigItem]) -> ConfigItem:
    if len(items) == 1:
      return items[0]
    merged_item = items[0].merge(items[1])
    return Koti.reduce_items([merged_item, *items[2:]])

  @staticmethod
  def check_manager_consistency(managers: Sequence[ConfigManager], configs: Sequence[ConfigGroup]):
    for group in Koti.get_all_provided_groups(configs):
      for item in (x for x in group.provides if x is not None and isinstance(x, ManagedConfigItem)):
        matching_managers = [manager for manager in managers if item.__class__ in manager.managed_classes]
        if len(matching_managers) == 0:
          raise AssertionError(f"no manager found for class {item.__class__.__name__}")
        if len(matching_managers) > 1:
          raise AssertionError(f"multiple managers found for class {item.__class__.__name__}")

  @staticmethod
  def check_config_item_consistency(managers: Sequence[ConfigManager], configs: Sequence[ConfigGroup], koti: Koti):
    for group in Koti.get_all_provided_groups(configs):
      for item in (x for x in group.provides if x is not None and isinstance(x, ManagedConfigItem)):
        matching_managers = [manager for manager in managers if item.__class__ in manager.managed_classes]
        manager = matching_managers[0]
        try:
          manager.check_configuration(item, koti)
        except Exception as e:
          raise AssertionError(f"{manager.__class__.__name__}: {e}")

  @staticmethod
  def separate_into_phases(groups: Sequence[ConfigGroup]) -> list[list[ConfigGroup]]:
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
  def create_execution_phase(managers: Sequence[ConfigManager], groups_in_phase: list[ConfigGroup], merged_items_in_phase: list[ConfigItem]) -> ExecutionPhase:
    install_order: list[tuple[ConfigManager, list[ManagedConfigItem]]] = []
    for manager in managers:
      managed_items = [item for item in merged_items_in_phase if isinstance(item, ManagedConfigItem) and item.__class__ in manager.managed_classes]
      if len(managed_items) > 0:
        install_order.append((manager, managed_items))
    return ExecutionPhase(merged_items_in_phase = merged_items_in_phase, install_order = install_order, groups_in_phase = groups_in_phase)

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


class ConfigItem(metaclass = ABCMeta):

  # ConfigItems with the same identifier are considered to be the same thing (with possibly
  # differing attributes) that will be merged together before running the installation process.
  @abstractmethod
  def identifier(self) -> str:
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.identifier()")

  # Usually, the identifier will be printed in all outputs by koti. Sometimes it may be necessary to
  # add some human-readable information. This can be done by overriding this function.
  def description(self) -> str:
    return self.identifier()

  # This function is called whenever there are multiple items with the same identifier. It can
  # attempt to merge those definitions together (or throw an error if they're incompatible).
  @abstractmethod
  def merge(self, other: ConfigItem) -> ConfigItem:
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.merge()")


# ConfigItems that can be installed to the system. ManagedConfigItem require a corresponding
# ConfigManager being registered in koti.
class ManagedConfigItem(ConfigItem, metaclass = ABCMeta):
  pass


# ConfigItems that only provide some kind of meta information (e.g. for declaring dependencies)
# or values that are being used by other ConfigItems (e.g. options that get merged into some file).
class UnmanagedConfigItem(ConfigItem, metaclass = ABCMeta):
  pass


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


class ConfigManager[T: ManagedConfigItem](metaclass = ABCMeta):
  managed_classes: list[Type] = []
  order_in_cleanup_phase: Literal["reverse_install_order", "first", "last"] = "reverse_install_order"

  @abstractmethod
  def check_configuration(self, item: T, core: Koti):
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.check_configuration()")

  @abstractmethod
  def checksums(self, core: Koti) -> Checksums[T]:
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.checksums()")

  @abstractmethod
  def install(self, items: list[T], core: Koti):
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.install()")

  @abstractmethod
  def cleanup(self, items_to_keep: list[T], core: Koti):
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.cleanup()")


class Checksums[T:ConfigItem]:

  def current(self, item: T) -> str | None:
    pass

  def target(self, item: T) -> str | None:
    pass


class ConfigMetadata:
  pass


class ExecutionPhase:
  groups_in_phase: list[ConfigGroup]
  merged_items_in_phase: Sequence[ConfigItem]
  execution_order: Sequence[tuple[ConfigManager, list[ManagedConfigItem]]]

  def __init__(self, merged_items_in_phase: Sequence[ConfigItem], install_order: Sequence[tuple[ConfigManager, list[ManagedConfigItem]]], groups_in_phase: list[ConfigGroup]):
    self.execution_order = install_order
    self.merged_items_in_phase = merged_items_in_phase
    self.groups_in_phase = groups_in_phase
