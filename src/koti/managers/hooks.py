from koti.core import Koti, ConfigManager, ExecutionState
from koti.items.hooks import PostHook, PreHook
from koti.utils.confirm import confirm


class PreHookManager(ConfigManager[PreHook]):
  managed_classes = [PreHook]

  def execute_phase(self, items: list[PreHook], core: Koti, state: ExecutionState):
    for hook in items:
      confirm(
        message = f"confirm executing {hook}",
        destructive = False,
        mode = core.get_confirm_mode(hook),
      )
      hook.execute()


class PostHookManager(ConfigManager[PostHook]):
  managed_classes = [PostHook]

  def execute_phase(self, items: list[PostHook], core: Koti, state: ExecutionState):
    for hook in items:
      if hook.trigger == "always" or self.has_triggered(hook, core, state):
        confirm(
          message = f"confirm executing {hook}",
          destructive = False,
          mode = core.get_confirm_mode(hook),
        )
        hook.execute()

  def has_triggered(self, hook: PostHook, core: Koti, state: ExecutionState) -> bool:
    group_containing_hook = core.get_group_for_item(hook)
    triggered_items_in_group = set(group_containing_hook.items).intersection(state.updated_items)
    return len(triggered_items_in_group) > 0
