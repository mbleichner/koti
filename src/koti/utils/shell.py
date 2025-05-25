from __future__ import annotations

import subprocess


def shell_interactive(command: str, check: bool = True):
  with subprocess.Popen(command, shell = True) as process:
    if process.wait() != 0 and check:
      raise AssertionError(f"command failed: {command}")


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
