from __future__ import annotations

import pwd, grp, os
from inspect import cleandoc
from subprocess import CalledProcessError, Popen, run

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
    group = group_for_user(user) if user else None,
    extra_groups = extra_groups_for_user(user) if user else None,
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
    group = group_for_user(user) if user else None,
    extra_groups = extra_groups_for_user(user) if user else None,
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
      group = group_for_user(user) if user else None,
      extra_groups = extra_groups_for_user(user) if user else None,
      env = env_for_user(user) if user else None,
    )
    return True
  except CalledProcessError:
    return False



def group_for_user(user: str) -> str:
  gid = pwd.getpwnam(user).pw_gid
  return grp.getgrgid(gid).gr_name


def extra_groups_for_user(user: str) -> list[str]:
  return [g.gr_name for g in grp.getgrall() if user in g.gr_mem]


def env_for_user(user: str) -> dict[str, str]:
  user_env_lines = run(
    f"echo printenv | su - {user}",
    check=True,
    shell=True,
    capture_output=True,
    universal_newlines=True,
  ).stdout.splitlines()
  return {**os.environ, **dict([line.split('=', 1) for line in user_env_lines])}