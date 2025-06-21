from typing import Callable

from koti.core import ConfigItem


class PostHook(ConfigItem):
  identifier: str | None
  execute: None | Callable
  trigger: list[ConfigItem]

  def __init__(self, identifier: str | None, execute: Callable = None, trigger: ConfigItem | list[ConfigItem] = None):
    super().__init__(identifier)
    self.identifier = identifier
    self.execute = execute
    self.trigger = trigger if isinstance(trigger, list) else [trigger]
    self.trigger = list(filter(lambda x: x is not None, self.trigger))

  def __str__(self):
    return f"PostHook('{self.identifier}')"


def PostHookTriggerScope(*items: ConfigItem) -> list[ConfigItem]:
  hooks = [item for item in items if isinstance(item, PostHook)]
  non_hooks = [item for item in items if not isinstance(item, PostHook)]
  for hook in hooks:
    hook.trigger += non_hooks
  return list(items)
