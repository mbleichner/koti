from __future__ import annotations

from typing import Any, Type

from utils import interactive


class Triggerable:
  def execute(self):
    pass


type ConfigModuleGroups = ConfigItemGroup | list[ConfigItemGroup]


class ConfigModule:
  def provides(self) -> ConfigModuleGroups:
    return []


class ConfigItem:
  # manager: str
  # depends: list[ConfigItem | ConfigModule] = []
  # triggers: list[Triggerable] = []
  def __init__(
    self,
    identifier: str,
    # manager: str,
    # depends: list[ConfigItem] = None,
    # triggers: list[Triggerable] = None
  ):
    self.identifier = identifier
    # self.manager = manager
    # self.triggers = triggers if triggers is not None else []
    # self.depends = depends if depends is not None else []

  def check_configuration(self) -> str:
    pass


class ConfigItemGroup:
  identifier: str | None
  items: list[ConfigItem]

  def __init__(self, first: str | ConfigItem | Requires, *items: ConfigItem | Requires):
    self.identifier = None if not isinstance(first, str) else first
    combined_items = ([] if isinstance(first, str) else [first]) + list(items)
    self.items = [item for item in combined_items if item is not None]


class ConfigManager[T: ConfigItem]:
  managed_classes: list[Type] = []

  def check_configuration(self, item: T) -> bool:
    raise "method not implemented: check_configuration"

  def execute_phase(self, items: list[T]) -> Any:  # returns updated items
    raise "method not implemented: execute_phase"

  def finalize_phase(self, result_from_execute_phase: Any):
    pass

  def finalize(self, all_items: list[T]) -> list[T]:  # returns updated items
    pass


class ShellCommand(Triggerable):
  command: str

  def __init__(self, command: str):
    self.command = command

  def execute(self):
    interactive(self.command)

  def __eq__(self, other):
    return type(other) is type(self) and self.command == other.command


class Requires:
  items: list[ConfigItem | ConfigItemGroup]

  # manager = "RequireManager"
  def __init__(self, *items: ConfigItem | ConfigItemGroup):
    self.items = list(items)

  def __str__(self):
    return f"Require({", ".join([str(item) for item in self.items])})"
