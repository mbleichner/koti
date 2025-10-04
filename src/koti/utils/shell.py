from __future__ import annotations

from inspect import cleandoc
from subprocess import CalledProcessError, Popen, run
from os import environ

verbose_mode: bool = False


def shell(command: str, check: bool = True, executable: str = "/bin/sh", user: str | None = None):
  if verbose_mode:
    lines = cleandoc(command).split("\n")
    for idx, line in enumerate(lines):
      prefix = "$" if idx == 0 else " "
      print(f"{prefix} {line}")
  with Popen(
    command,
    shell = True,
    executable = executable,
    user = user,
    env = env_for_user(user) if user else None,
  ) as process:
    exitcode = process.wait()
    assert exitcode == 0 or not check, f"command failed: {command}"


def shell_output(command: str, check: bool = True, executable: str = "/bin/sh", user: str | None = None) -> str:
  return run(
    command,
    executable = executable,
    check = check,
    shell = True,
    capture_output = True,
    universal_newlines = True,
    user = user,
    env = env_for_user(user) if user else None,
  ).stdout.strip()


def shell_success(command: str, executable: str = "/bin/sh", user: str | None = None) -> bool:
  try:
    run(
      command,
      executable = executable,
      check = True,
      shell = True,
      capture_output = True,
      universal_newlines = True,
      user = user,
      env = env_for_user(user) if user else None,
    )
    return True
  except CalledProcessError:
    return False


# class ShellAction:
#   def __init__(self, command: str, user: str | None = None):
#     self.command = command
#     self.user = user
#
#   def __call__(self, *args, **kwargs):
#     shell(self.command, user = self.user)


def env_for_user(user: str) -> dict[str, str]:
  user_homes: dict[str, str] = dict([line.split(":") for line in shell_output("getent passwd | cut -d: -f1,6").splitlines()])
  home = user_homes.get(user, None)
  result = {**environ, "USER": user}
  if home:
    result["HOME"] = home
  return result
