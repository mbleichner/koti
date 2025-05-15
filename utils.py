from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from definitions import ConfirmMode, Executable


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
