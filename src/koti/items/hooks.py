from typing import Callable, Literal

from koti.core import ConfigItem, ExecutionState


class PreHook(ConfigItem):
  identifier: str | None
  execute: None | Callable

  def __init__(self, identifier: str | None, execute: Callable = None):
    super().__init__(identifier)
    self.identifier = identifier
    self.execute = execute

  def check_configuration(self, state: ExecutionState):
    pass

  def __str__(self):
    return f"PreHook('{self.identifier}')"


class PostHook(ConfigItem):
  identifier: str | None
  execute: None | Callable
  trigger: Literal["always"] | Literal["on_change"]

  def __init__(self, identifier: str | None, execute: Callable = None, trigger: Literal["always"] | Literal["on_change"] = "on_change"):
    super().__init__(identifier)
    self.trigger = trigger
    self.identifier = identifier
    self.execute = execute

  def check_configuration(self, state: ExecutionState):
    pass

  def __str__(self):
    return f"PostHook('{self.identifier}')"
