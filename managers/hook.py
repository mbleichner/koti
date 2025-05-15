from typing import Literal

from lib import ConfigItem, ConfigItemGroup, ConfigManager, Executable, ExecutionState


class PreHook(ConfigItem):
  identifier: str | None
  execute: None | Executable

  def __init__(self, identifier: str | None, execute: Executable = None):
    super().__init__(identifier)
    self.identifier = identifier
    self.execute = execute

  def check_configuration(self, state: ExecutionState):
    pass

  def __str__(self):
    return f"PreHook('{self.identifier}')"


class PostHook(ConfigItem):
  identifier: str | None
  execute: None | Executable
  trigger: Literal["always"] | Literal["on_change"]

  def __init__(self, identifier: str | None, execute: Executable = None, trigger: Literal["always"] | Literal["on_change"] = "on_change"):
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

  def execute_phase(self, items: list[PreHook], state: ExecutionState):
    for hook in items:
      print(f"executing pre-hook '{hook.identifier}'")
      hook.execute.execute()


class PostHookManager(ConfigManager[PostHook]):
  managed_classes = [PostHook]

  def execute_phase(self, items: list[PostHook], state: ExecutionState):
    for hook in items:
      if hook.trigger == "always" or self.has_triggered(hook, state):
        print(f"executing post-hook '{hook.identifier}'")
        hook.execute.execute()

  def has_triggered(self, hook: PostHook, state: ExecutionState) -> bool:
    group_containing_hook = state.find_merged_group(hook)
    triggered_items_in_group = set(group_containing_hook.items).intersection(state.updated_items)
    return len(triggered_items_in_group) > 0
