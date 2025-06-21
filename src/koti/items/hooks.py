from typing import Callable, Sequence

from koti.core import ConfigItem


class PostHook(ConfigItem):
  identifier: str
  execute: None | Callable
  trigger: list[ConfigItem]

  def __init__(self, identifier: str, execute: Callable | None = None, trigger: Sequence[ConfigItem] | None = None):
    super().__init__(identifier)
    self.identifier = identifier
    self.execute = execute
    self.trigger = [item for item in (trigger or []) if item is not None]

  def __str__(self):
    return f"PostHook('{self.identifier}')"


def PostHookTriggerScope(*items: ConfigItem) -> list[ConfigItem]:
  hooks = [item for item in items if isinstance(item, PostHook)]
  non_hooks = [item for item in items if not isinstance(item, PostHook)]
  for hook in hooks:
    hook.trigger += non_hooks
  return list(items)
