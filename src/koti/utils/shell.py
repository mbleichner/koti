from __future__ import annotations

from inspect import cleandoc
from subprocess import CalledProcessError, Popen, run


def shell(command: str, check: bool = True, executable: str = "/bin/sh", sudo: str | None = None):
  with Popen(
    add_sudo(command, executable, sudo),
    shell = True,
    executable = executable,
  ) as process:
    if process.wait() != 0 and check:
      raise AssertionError(f"command failed: {command}")


def shell_output(command: str, check: bool = True, executable: str = "/bin/sh", sudo: str | None = None) -> str:
  return run(
    add_sudo(command, executable, sudo),
    check = check,
    shell = True,
    capture_output = True,
    universal_newlines = True,
    executable = executable,
  ).stdout.strip()


def shell_success(command: str, executable: str = "/bin/sh", sudo: str | None = None) -> bool:
  try:
    run(
      add_sudo(command, executable, sudo),
      check = True,
      shell = True,
      capture_output = True,
      universal_newlines = True,
      executable = executable,
    )
    return True
  except CalledProcessError:
    return False


def add_sudo(command: str, executable: str, sudo: str | None):
  if sudo is None:
    return command
  return cleandoc(f"""
    <<- 'EOF' sudo -u manuel {executable} -s
      {command}
    EOF
  """)
