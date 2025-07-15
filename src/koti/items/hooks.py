from typing import Callable, Sequence

from koti.core import ConfigItem, ConfirmModeValues


class PostHook(ConfigItem):
  name: str
  execute: None | Callable
  trigger: list[ConfigItem]

  def __init__(self, name: str, execute: Callable | None = None, trigger: Sequence[ConfigItem] | None = None, confirm_mode: ConfirmModeValues | None = None):
    self.name = name
    self.execute = execute
    self.trigger = [item for item in (trigger or []) if item is not None]
    self.confirm_mode = confirm_mode

  def identifier(self):
    return f"PostHook('{self.name}')"


def PostHookTriggerScope(*items: ConfigItem) -> list[ConfigItem]:
  hooks = [item for item in items if isinstance(item, PostHook)]
  non_hooks = [item for item in items if not isinstance(item, PostHook)]
  for hook in hooks:
    hook.trigger += non_hooks
  return list(items)
