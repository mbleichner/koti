from __future__ import annotations

from os import getuid
from typing import Iterable, Iterator

from koti.types import *
from koti.utils import JsonMapping, JsonStore


class Koti:
  store: JsonStore
  model: ExecutionModel
  confirm_mode_store: JsonMapping[str, ConfirmMode]

  def __init__(
    self,
    managers: Iterator[ConfigManager | None] | Iterable[ConfigManager | None],
    configs: Iterator[ConfigGroup | None] | Iterable[ConfigGroup | None],
    default_confirm_mode: ConfirmMode = "cautious"
  ):
    assert getuid() == 0, "this program must be run as root (or through sudo)"
    self.store = JsonStore("/var/cache/koti/Koti.json")
    configs_cleaned = [c for c in configs if c is not None]
    managers_cleaned = [m for m in managers if m is not None]
    Koti.check_manager_consistency(managers_cleaned, configs_cleaned)
    self.model = Koti.build_execution_model(managers_cleaned, configs_cleaned, default_confirm_mode, self.store)
    Koti.check_config_item_consistency(self.model)

  def plan(self, groups: bool = True, items: bool = True) -> int:
    items_total: list[ManagedConfigItem] = []
    items_changed: list[ManagedConfigItem] = []
    for phase_idx, phase in enumerate(self.model.install_phases):
      for manager, items_in_phase in phase.order:
        checksums = manager.checksums(self.model)
        for item in items_in_phase:
          items_total.append(item)
          needs_update = checksums.current(item) != checksums.target(item)
          if needs_update:
            items_changed.append(item)

    for phase_idx, phase in enumerate(self.model.install_phases):
      print(f"Phase {phase_idx + 1}:")
      if groups:
        for group in phase.groups:
          needs_update = len([item for item in group.provides if item in items_changed]) > 0
          print(f"{"*" if needs_update else "-"} {group.description}")
      if items:
        for manager, items_in_phase in phase.order:
          for item in items_in_phase:
            needs_update = item in items_changed or item in items_changed
            print(f"{"*" if needs_update else "-"} {item.description()}")
      print()

    installed = [item.identifier() for manager in self.model.managers for item in manager.list_installed_items()]
    items_to_install = [item for item in items_changed if item.identifier() not in installed]
    items_to_update = [item for item in items_changed if item.identifier() in installed]
    items_to_uninstall = self.model.cleanup_phase.items

    count = len(items_to_install) + len(items_to_update) + len(items_to_uninstall)
    if count > 0:
      print(f"{len(items_total)} items total, {count} items to update:")
      for item in items_to_install:
        print(f"- install: {item.description()}")
      for item in items_to_update:
        print(f"- update:  {item.description()}")
      for item in items_to_uninstall:
        print(f"- remove:  {item.description()}")
      print()
      print("// additional updates may be triggered by PostHooks")
    else:
      print(f"{len(items_total)} items total, everything up to date")
    print()

    return len(items_to_update)

  def apply(self):
    for phase_idx, phase in enumerate(self.model.install_phases):
      for manager, items in phase.order:
        checksums = manager.checksums(self.model)
        items_to_update = [item for item in items if checksums.current(item) != checksums.target(item)]
        Koti.print_phase_log(self.model, phase_idx, manager, items_to_update)
        manager.install(items_to_update, self.model) or []
    for manager, items_to_uninstall in self.model.cleanup_phase.order:
      if len(items_to_uninstall):
        Koti.print_phase_log(self.model, None, manager, items_to_uninstall)
        manager.uninstall(items_to_uninstall, self.model)
    Koti.save_confirm_modes(self.store, self.model)

  @staticmethod
  def print_phase_log(model: ExecutionModel, phase_idx: int | None, manager: ConfigManager, items: list[ConfigItem]):
    phase = f"Phase {phase_idx + 1}" if phase_idx is not None else "Cleanup"
    max_manager_name_len = max([
      len(manager.__class__.__name__)
      for phase in model.install_phases for manager, items in phase.order
    ])

    if phase_idx is None:
      details = f"{len(items)} items to uninstall"
    elif len(items) == 0:
      details = "no outdated items found"
    elif len(items) < 5:
      details = f"items to install/update: {", ".join([item.description() for item in items])}"
    else:
      details = f"{len(items)} items to update"

    print(f"{phase}  {manager.__class__.__name__.ljust(max_manager_name_len)}  {details}")

  @staticmethod
  def get_cleanup_phase_manager_order(managers: Sequence[ConfigManager]) -> Sequence[ConfigManager]:
    return [
      *[manager for manager in managers if manager.order_in_cleanup_phase == "first"],
      *reversed([manager for manager in managers if manager.order_in_cleanup_phase == "reverse_install_order"]),
      *[manager for manager in managers if manager.order_in_cleanup_phase == "last"],
    ]

  @staticmethod
  def build_execution_model(
    managers: Sequence[ConfigManager],
    configs: Sequence[ConfigGroup],
    default_confirm_mode: ConfirmMode,
    store: JsonStore,
  ) -> ExecutionModel:
    groups = Koti.get_all_provided_groups(configs)
    groups_separated_into_phases = Koti.separate_into_phases(groups)
    merged_items_grouped_by_phase: list[list[ConfigItem]] = Koti.merge_items([
      [item for group in phase for item in group.provides]
      for phase in groups_separated_into_phases
    ])

    return ExecutionModel(
      managers = managers,
      install_phases = [
        Koti.create_install_phase(managers, groups_in_phase, items_in_phase)
        for groups_in_phase, items_in_phase in zip(groups_separated_into_phases, merged_items_grouped_by_phase)
      ],
      cleanup_phase = (Koti.create_cleanup_phase(managers, merged_items_grouped_by_phase)),
      confirm_mode_fallback = default_confirm_mode,
      confirm_mode_archive = Koti.load_confirm_modes(store),
    )

  @staticmethod
  def load_confirm_modes(store: JsonStore) -> dict[str, ConfirmMode]:
    result = store.get("confirm_modes")
    return result if isinstance(result, dict) else {}

  @staticmethod
  def save_confirm_modes(store: JsonStore, model: ExecutionModel):
    result: dict[str, ConfirmMode] = {}
    for phase in model.install_phases:
      for manager, items in phase.order:
        for item in items:
          result[item.identifier()] = model.confirm_mode(item)
    store.put("confirm_modes", result)

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
  def check_config_item_consistency(model: ExecutionModel):
    for phase in model.install_phases:
      for manager, items_for_manager in phase.order:
        for item in items_for_manager:
          try:
            manager.check_configuration(item, model)
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
  def create_install_phase(managers: Sequence[ConfigManager], groups_in_phase: list[ConfigGroup], merged_items_in_phase: list[ConfigItem]) -> InstallPhase:
    order: list[tuple[ConfigManager, list[ManagedConfigItem]]] = []
    for manager in managers:
      managed_items = [
        item for item in merged_items_in_phase
        if isinstance(item, ManagedConfigItem) and item.__class__ in manager.managed_classes
      ]
      if len(managed_items) > 0:
        order.append((manager, managed_items))
    return InstallPhase(
      groups = groups_in_phase,
      order = order,
      items = merged_items_in_phase
    )

  @staticmethod
  def create_cleanup_phase(managers, merged_items_grouped_by_phase) -> CleanupPhase:
    all_item_identifieres = [item.identifier() for phase in merged_items_grouped_by_phase for item in phase]
    return CleanupPhase(
      order = [
        (manager, [item for item in manager.list_installed_items() if item.identifier() not in all_item_identifieres])
        for manager in Koti.get_cleanup_phase_manager_order(managers)
      ]
    )

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
