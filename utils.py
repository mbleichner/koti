import hashlib
import json
import os
import subprocess
from pathlib import Path


def interactive(command: str, stderr = None):
  print(f"running shell command: {command}")
  with subprocess.Popen(command, shell = True, stderr = stderr) as process:
    if process.wait() != 0:
      raise AssertionError("command failed")


def get_output(command: str, check: bool = True) -> str:
  print(f"running shell command: {command}")
  return subprocess.run(
    command,
    check = check,
    shell = True,
    capture_output = True
  ).stdout.decode().strip()


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


def file_hash(filename):
  if not os.path.isfile(filename):
    return "-"
  stat = os.stat(filename)
  sha256_hash = hashlib.sha256()
  sha256_hash.update(str(stat.st_uid).encode())
  sha256_hash.update(str(stat.st_gid).encode())
  sha256_hash.update(str(stat.st_mode & 0o777).encode())
  with open(filename, "rb") as f:
    for byte_block in iter(lambda: f.read(4096), b""):
      sha256_hash.update(byte_block)
  return sha256_hash.hexdigest()


def virtual_file_hash(uid, gid, mode, content):
  sha256_hash = hashlib.sha256()
  sha256_hash.update(str(uid).encode())
  sha256_hash.update(str(gid).encode())
  sha256_hash.update(str(mode & 0o777).encode())
  sha256_hash.update(content)
  return sha256_hash.hexdigest()
