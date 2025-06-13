from typing import Callable

from koti.core import ConfigItem


class PostHook(ConfigItem):
  identifier: str | None
  execute: None | Callable

  def __init__(self, identifier: str | None, execute: Callable = None):
    super().__init__(identifier)
    self.identifier = identifier
    self.execute = execute

  def __str__(self):
    return f"PostHook('{self.identifier}')"
