from __future__ import annotations

from subprocess import CalledProcessError, Popen, run


def shell(command: str, check: bool = True):
  with Popen(command, shell = True) as process:
    if process.wait() != 0 and check:
      raise AssertionError(f"command failed: {command}")


def shell_output(command: str, check: bool = True) -> str:
  return run(
    command,
    check = check,
    shell = True,
    capture_output = True,
    universal_newlines = True,
  ).stdout.strip()


def shell_success(command: str) -> bool:
  try:
    run(command, check = True, shell = True, capture_output = True, universal_newlines = True)
    return True
  except CalledProcessError:
    return False
