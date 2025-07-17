from __future__ import annotations

from typing import Callable, Sequence

from koti import ManagedConfigItem
from koti.core import ConfigItem


class PostHook(ManagedConfigItem):
  name: str
  execute: None | Callable
  trigger: list[ManagedConfigItem]

  def __init__(self, name: str, execute: Callable | None = None, trigger: Sequence[ManagedConfigItem] | None = None):
    self.name = name
    self.execute = execute
    self.trigger = [item for item in (trigger or []) if item is not None]

  def identifier(self):
    return f"PostHook('{self.name}')"

  def merge(self, other: ConfigItem) -> PostHook:
    assert isinstance(other, PostHook)
    assert other.identifier() == self.identifier()
    raise AssertionError(f"PostHook('{self.name}') cannot be declared twice")


def PostHookTriggerScope(*items: ConfigItem) -> list[ConfigItem]:
  hooks = [item for item in items if isinstance(item, PostHook)]
  non_hooks = [item for item in items if not isinstance(item, PostHook) and isinstance(item, ManagedConfigItem)]
  for hook in hooks:
    hook.trigger += non_hooks
  return list(items)
