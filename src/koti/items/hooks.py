from __future__ import annotations

from typing import Callable, Sequence, Unpack

from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs

type PostHookTriggerType = ManagedConfigItem | Callable[[ManagedConfigItem], bool]


class PostHook(ManagedConfigItem):
  """An item that will run an executable whenever its dependencies change state.
  For example, this can be used to call some rebuild script whenever a config file changes."""
  name: str
  execute: None | Callable
  trigger: Sequence[PostHookTriggerType]

  def __init__(
    self,
    name: str,
    execute: Callable | None = None,
    trigger: PostHookTriggerType | Sequence[PostHookTriggerType] | None = None,
    add_trigger_as_dependency = True,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.name = name
    self.execute = execute

    if isinstance(trigger, ManagedConfigItem) or callable(trigger):
      self.trigger = [trigger]
    else:
      self.trigger = (trigger or [])

    if add_trigger_as_dependency:
      self.after = [*self.after, *self.trigger]

  def __str__(self) -> str:
    return f"PostHook('{self.name}')"

  def merge(self, other: ConfigItem) -> PostHook:
    raise AssertionError(f"{self} cannot be declared twice")


# noinspection PyPep8Naming
def PostHookScope(*items: ConfigItem) -> list[ConfigItem]:
  """Convenience wrapper to connect PostHooks with their triggers."""
  hooks = [item for item in items if isinstance(item, PostHook)]
  non_hooks = [item for item in items if not isinstance(item, PostHook) and isinstance(item, ManagedConfigItem)]
  for hook in hooks:
    hook.trigger = [*hook.trigger, *non_hooks]
  return list(items)
