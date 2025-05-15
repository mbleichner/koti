from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
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


def needs_confirmation(destructive: bool, mode: ConfirmMode):
  if mode == "paranoid": return True
  if mode == "yolo": return False
  return destructive


def confirm(message: str, destructive: bool, mode: ConfirmMode):
  if not needs_confirmation(destructive, mode):
    print(f"{message}: skipped {"destructive" if destructive else "non-destructive"} operation due to confirm_mode = {mode}")
    return
  while True:
    answer = input(f'{message}: [Y/n] ').strip().lower()
    if answer in ('y', ''): return True
    if answer == 'n': raise AssertionError("execution cancelled")


def shell_interactive(command: str, check: bool = True):
  with subprocess.Popen(command, shell = True) as process:
    if process.wait() != 0 and check:
      raise AssertionError("command failed")


def shell_output(command: str, check: bool = True) -> str:
  return subprocess.run(
    command,
    check = check,
    shell = True,
    capture_output = True,
    universal_newlines = True,
  ).stdout.strip()


def shell_success(command: str) -> bool:
  try:
    subprocess.run(command, check = True, shell = True, capture_output = True, universal_newlines = True)
    return True
  except:
    return False


class ShellCommand(Executable):
  command: str

  def __init__(self, command: str):
    self.command = command

  def execute(self):
    shell_interactive(self.command)

  def __eq__(self, other):
    return type(other) is type(self) and self.command == other.command


class JsonStore:
  store_file: str
  store: dict

  def __init__(self, store_file: str):
    self.store_file = store_file
    try:
      with open(self.store_file, encoding = 'utf-8') as fh:
        self.store = json.load(fh)
    except:
      self.store = {}

  def mapping[K, V](self, name) -> JsonMapping[K, V]:
    return JsonMapping[K, V](self, name)

  def collection[T](self, name) -> JsonCollection[T]:
    return JsonCollection[T](self, name)

  def get(self, key, default = None):
    return self.store.get(key, default)

  def put(self, key, value):
    self.store[key] = value
    Path(os.path.dirname(self.store_file)).mkdir(parents = True, exist_ok = True)
    with open(self.store_file, 'w+', encoding = 'utf-8') as fh:
      # noinspection PyTypeChecker
      json.dump(self.store, fh)


class JsonMapping[K, V]:
  store: JsonStore
  name: str

  def __init__(self, store: JsonStore, name: str):
    super().__init__()
    self.name = name
    self.store = store

  def get[F](self, key: K, default: F) -> V | F:
    mapping: dict[K, V] = self.store.get(self.name, {})
    return mapping.get(key, default)

  def put(self, key: K, value: V):
    mapping: dict[K, V] = self.store.get(self.name, {})
    mapping[key] = value
    self.store.put(self.name, mapping)

  def remove(self, key: K):
    mapping: dict[K, V] = self.store.get(self.name, {})
    mapping.pop(key, None)
    self.store.put(self.name, mapping)

  def keys(self) -> list[K]:
    mapping: dict[K, V] = self.store.get(self.name, {})
    return list(mapping.keys())


class JsonCollection[T]:
  store: JsonStore
  name: str

  def __init__(self, store: JsonStore, name: str):
    super().__init__()
    self.name = name
    self.store = store

  def elements(self) -> list[T]:
    collection = self.store.get(self.name, [])
    return collection

  def add(self, value: T):
    collection = self.store.get(self.name, [])
    new_collection = set(collection).union({value})
    self.store.put(self.name, new_collection)

  def remove(self, value: T):
    collection = self.store.get(self.name, [])
    new_collection = set(collection).difference({value})
    self.store.put(self.name, new_collection)
