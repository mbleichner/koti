from typing import Callable, Literal

from core import ArchUpdate, ConfigItem, ConfigManager, ExecutionState


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


class PreHookManager(ConfigManager[PreHook]):
  managed_classes = [PreHook]

  def execute_phase(self, items: list[PreHook], core: ArchUpdate, state: ExecutionState):
    for hook in items:
      print(f"executing pre-hook '{hook.identifier}'")
      hook.execute()


class PostHookManager(ConfigManager[PostHook]):
  managed_classes = [PostHook]

  def execute_phase(self, items: list[PostHook], core: ArchUpdate, state: ExecutionState):
    for hook in items:
      if hook.trigger == "always" or self.has_triggered(hook, core, state):
        print(f"executing post-hook '{hook.identifier}'")
        hook.execute()

  def has_triggered(self, hook: PostHook, core: ArchUpdate, state: ExecutionState) -> bool:
    group_containing_hook = core.get_group_for_item(hook)
    triggered_items_in_group = set(group_containing_hook.items).intersection(state.updated_items)
    return len(triggered_items_in_group) > 0
