import hashlib

from koti.core import ConfigManager, ExecutionState, Koti
from koti.items.hooks import PostHook
from koti.utils import JsonMapping, JsonStore
from koti.utils.confirm import confirm


class PostHookManager(ConfigManager[PostHook]):
  managed_classes = [PostHook]
  checksums: JsonMapping[str, str]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/PostHookManager.json")
    self.checksums = store.mapping("checksums")

  def check_configuration(self, item: PostHook, core: Koti):
    if item.execute is None:
      raise AssertionError("missing execute parameter")

  def checksum_current(self, items: list[PostHook], core: Koti, state: ExecutionState) -> list[str | int | None]:
    return [self.checksum_current_single(item, core, state) for item in items]

  def checksum_target(self, items: list[PostHook], core: Koti, state: ExecutionState) -> list[str | int | None]:
    return [self.checksum_target_single(item, core, state) for item in items]

  def checksum_current_single(self, hook: PostHook, core: Koti, state: ExecutionState) -> str | None:
    return self.checksums.get(hook.identifier, None)

  def checksum_target_single(self, hook: PostHook, core: Koti, state: ExecutionState) -> str | int | None:
    group_containing_hook = core.get_group_for_item(hook)
    processed_items_in_group = sorted(
      list(set(group_containing_hook.items).intersection(state.processed_items)),
      key = lambda x: f"{x.__class__.__name__}:{x.identifier}"
    )
    sub_checksums = [str(core.get_manager_for_item(item).checksum_current([item], core, state)[0]) for item in processed_items_in_group]
    sha256_hash = hashlib.sha256()
    sha256_hash.update("\n".join(sub_checksums).encode())
    return sha256_hash.hexdigest()

  def apply_phase(self, items: list[PostHook], core: Koti, state: ExecutionState):
    for hook in items:
      if self.has_triggered(hook, core, state):
        confirm(
          message = f"confirm executing {hook}",
          destructive = False,
          mode = core.get_confirm_mode_for_item(hook),
        )
        hook.execute()
      checksum = self.checksum_target_single(hook, core, state)
      self.checksums.put(hook.identifier, checksum)

  def has_triggered(self, hook: PostHook, core: Koti, state: ExecutionState) -> bool:
    group_containing_hook = core.get_group_for_item(hook)
    triggered_items_in_group = set(group_containing_hook.items).intersection(state.updated_items)
    return len(triggered_items_in_group) > 0

  def cleanup(self, items: list[PostHook], core: Koti, state: ExecutionState):
    pass
