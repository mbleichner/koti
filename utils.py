import json
import os
import subprocess
from pathlib import Path


def shell_interactive(command: str):
  with subprocess.Popen(command, shell = True) as process:
    if process.wait() != 0:
      raise AssertionError("command failed")


def shell_output(command: str, check: bool = True) -> str:
  return subprocess.run(
    command,
    check = check,
    shell = True,
    capture_output = True,
    universal_newlines = True,
  ).stdout.strip()


def confirm(message: str):
  while True:
    answer = input(f'{message}: [Y/n] ').strip().lower()
    if answer in ('y', ''): return True
    if answer == 'n': raise AssertionError("execution cancelled")


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

  def get(self, key, default = None):
    return self.store.get(key, default)

  def put(self, key, value):
    self.store[key] = value
    Path(os.path.dirname(self.store_file)).mkdir(parents = True, exist_ok = True)
    with open(self.store_file, 'w+', encoding = 'utf-8') as fh:
      json.dump(self.store, fh)
