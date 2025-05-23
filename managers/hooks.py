from core import ArchUpdate, ConfigManager, ExecutionState
from items.hooks import PostHook, PreHook


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
