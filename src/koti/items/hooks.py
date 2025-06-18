from typing import Callable, Literal

from koti.core import ConfigItem


class PostHook(ConfigItem):
  identifier: str | None
  execute: None | Callable
  trigger: Literal["group"] | list[ConfigItem] | ConfigItem

  def __init__(self, identifier: str | None, execute: Callable = None, trigger: Literal["group"] | list[ConfigItem] | ConfigItem = "group"):
    super().__init__(identifier)
    self.identifier = identifier
    self.execute = execute
    self.trigger = trigger

  def __str__(self):
    return f"PostHook('{self.identifier}')"
