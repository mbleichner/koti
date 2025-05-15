from __future__ import annotations

from typing import Literal, Type

ConfirmMode = Literal["paranoid", "careful", "yolo"]


class ExecutionPhase:
  merged_groups: list[ConfigItemGroup]
  execution_order: list[tuple[ConfigManager, list[ConfigItem]]]

  def __init__(self, merged_groups: list[ConfigItemGroup], execution_order: list[tuple[ConfigManager, list[ConfigItem]]]):
    super().__init__()
    self.execution_order = execution_order
    self.merged_groups = merged_groups


class ExecutionState:
  execution_phases: list[ExecutionPhase]
  default_confirm_mode: ConfirmMode = "destructive_changes"
  processed_items: list[ConfigItem] = []
  updated_items: list[ConfigItem] = []

  def __init__(self, execution_phases: list[ExecutionPhase]):
    super().__init__()
    self.execution_phases = execution_phases

  def find_merged_group(self, item: ConfigItem) -> ConfigItemGroup:
    for phase in self.execution_phases:
      for group in phase.merged_groups:
        if item in group.items:
          return group
    raise AssertionError(f"group not found for hook {item}")

  def get_confirm_mode(self, item: ConfigItem) -> ConfirmMode:
    group = self.find_merged_group(item)
    confirm_modes = [item.confirm_mode for item in group.items if isinstance(item, Options)]
    return self.effective_confirm_mode(confirm_modes)

  def effective_confirm_mode(self, modes: list[ConfirmMode]) -> ConfirmMode:
    modes_in_order: list[ConfirmMode] = ["paranoid", "careful", "yolo"]
    for mode in modes_in_order:
      if mode in modes: return mode
    return self.default_confirm_mode


class Executable:
  def execute(self):
    pass


type ConfigModuleGroups = ConfigItemGroup | list[ConfigItemGroup]


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


class ConfigManager[T: ConfigItem]:
  managed_classes: list[Type] = []

  def check_configuration(self, item: T) -> bool:
    raise "method not implemented: check_configuration"

  def execute_phase(self, items: list[T], state: ExecutionState) -> list[T] | None:  # returns updated items
    raise "method not implemented: execute_phase"

  def finalize(self, items: list[T], state: ExecutionState) -> list[T]:  # returns updated items
    pass


class ConfigMetadata:
  pass


class Requires(ConfigMetadata):
  items: list[ConfigItem | ConfigItemGroup]

  def __init__(self, *items: ConfigItem | ConfigItemGroup):
    self.items = list(items)

  def __str__(self):
    return f"Require({", ".join([str(item) for item in self.items])})"


class Options(ConfigMetadata):
  confirm_mode: ConfirmMode

  def __init__(self, confirm_mode: ConfirmMode):
    self.confirm_mode = confirm_mode

  def __str__(self):
    return f"Protection({self.confirm_mode})"
