from __future__ import annotations

from typing import Any, Callable

from koti.model import ExecutionPlan, ManagedConfigItem
from koti.utils.shell import shell
from koti.utils.colors import *


class GenericExecutionPlan[T: ManagedConfigItem](ExecutionPlan[T]):
  executable: Callable[[], Any]
  _description: str
  _details: list[str]
  after_execute: list[Callable[[], Any]]

  def __init__(
    self,
    items: list[T],
    executable: Callable[[], Any],
    description: str,
    details: list[str] | str | None = None,
    after_execute: list[Callable[[], Any]] | Callable[[], Any] | None = None
  ):
    super().__init__(items)
    self.executable = executable
    self._description = description
    self._details = [details] if isinstance(details, str) else (details or [])
    self.after_execute = [after_execute] if callable(after_execute) else (after_execute or [])

  def execute(self):
    self.executable()
    for hook in self.after_execute: hook()

  def description(self):
    return self._description

  def details(self) -> list[str]:
    return self._details


class ShellExecutionPlan[T: ManagedConfigItem](GenericExecutionPlan[T]):
  def __init__(
    self,
    items: list[T],
    command: str,
    description: str,
    user: str | None = None,
    details: list[str] | str | None = None,
    after_execute: list[Callable[[], Any]] | Callable[[], Any] | None = None
  ):
    super().__init__(
      items = items,
      executable = lambda: shell(command, user = user),
      description = description,
      details = [
        f"{CYAN}{command}{ENDC}" + (f" (run as {user})" if user else ""),
        *([details] if isinstance(details, str) else (details or []))
      ],
      after_execute = after_execute,
    )
