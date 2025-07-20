from __future__ import annotations

from subprocess import CalledProcessError, Popen, run


def shell(command: str, check: bool = True, executable: str | None = "/bin/sh"):
  with Popen(command, shell = True, executable = executable) as process:
    if process.wait() != 0 and check:
      raise AssertionError(f"command failed: {command}")


def shell_output(command: str, check: bool = True, executable: str | None = "/bin/sh") -> str:
  return run(
    command,
    check = check,
    shell = True,
    capture_output = True,
    universal_newlines = True,
    executable = executable,
  ).stdout.strip()


def shell_success(command: str, executable: str | None = "/bin/sh") -> bool:
  try:
    run(
      command,
      check = True,
      shell = True,
      capture_output = True,
      universal_newlines = True,
      executable = executable,
    )
    return True
  except CalledProcessError:
    return False
