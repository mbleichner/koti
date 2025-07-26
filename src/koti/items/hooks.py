from __future__ import annotations

from typing import Callable, Iterable, Sequence

from koti.model import ConfigItem, ManagedConfigItem


class PostHook(ManagedConfigItem):
  """An item that will run an executable whenever its dependencies change state.
  For example, this can be used to call some rebuild script whenever a config file changes."""
  name: str
  execute: None | Callable
  trigger: list[ManagedConfigItem]

  def __init__(
    self,
    name: str,
    execute: Callable | None = None,
    trigger: Sequence[ManagedConfigItem] | ManagedConfigItem | None = None,
    tags: Iterable[str] | None = None,
  ):
    self.name = name
    self.execute = execute
    if isinstance(trigger, ManagedConfigItem):
      self.trigger = [trigger]
    else:
      self.trigger = [item for item in (trigger or []) if item is not None]
    self.tags = set(tags or [])

  def identifier(self):
    return f"PostHook('{self.name}')"

  def merge(self, other: ConfigItem) -> PostHook:
    assert isinstance(other, PostHook)
    assert other.identifier() == self.identifier()
    raise AssertionError(f"PostHook('{self.name}') cannot be declared twice")


# noinspection PyPep8Naming
def PostHookTriggerScope(*items: ConfigItem) -> list[ConfigItem]:
  """Convenience wrapper to connect PostHooks with their triggers."""
  hooks = [item for item in items if isinstance(item, PostHook)]
  non_hooks = [item for item in items if not isinstance(item, PostHook) and isinstance(item, ManagedConfigItem)]
  for hook in hooks:
    hook.trigger += non_hooks
  return list(items)
