from __future__ import annotations

import hashlib

from koti.core import Checksums, ConfigManager, ExecutionState, Koti
from koti.items.hooks import PostHook
from koti.utils import JsonMapping, JsonStore
from koti.utils.confirm import confirm


class PostHookManager(ConfigManager[PostHook]):
  managed_classes = [PostHook]
  checksum_store: JsonMapping[str, str]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/PostHookManager.json")
    self.checksum_store = store.mapping("checksums")

  def check_configuration(self, item: PostHook, core: Koti):
    if item.execute is None:
      raise AssertionError("missing execute parameter")

  def checksums(self, core: Koti, state: ExecutionState) -> PostHookChecksums:
    return PostHookChecksums(core, state, self.checksum_store)

  def apply_phase(self, items: list[PostHook], core: Koti, state: ExecutionState):
    checksums = self.checksums(core, state)
    for hook in items:
      confirm(
        message = f"confirm executing {hook}",
        destructive = False,
        mode = core.get_confirm_mode_for_item(hook),
      )
      target_checksum = checksums.target(hook)
      hook.execute()
      self.checksum_store.put(hook.identifier, target_checksum)

  def cleanup(self, items: list[PostHook], core: Koti, state: ExecutionState):
    pass


class PostHookChecksums(Checksums[PostHook]):
  core: Koti
  state: ExecutionState
  checksum_store: JsonMapping[str, str]

  def __init__(self, core: Koti, state: ExecutionState, checksum_store: JsonMapping[str, str]):
    self.checksum_store = checksum_store
    self.state = state
    self.core = core

  def current(self, hook: PostHook) -> str | int | None:
    return self.checksum_store.get(hook.identifier, None)

  def target(self, hook: PostHook) -> str | int | None:
    group_containing_hook = self.core.get_group_for_item(hook)
    processed_items_in_group = sorted(
      list(set(group_containing_hook.items).intersection(self.state.processed_items)),
      key = lambda x: f"{x.__class__.__name__}:{x.identifier}"
    )
    sub_checksums = [
      str(self.core.get_manager_for_item(item).checksums(self.core, self.state).current(item))
      for item in processed_items_in_group
    ]
    sha256_hash = hashlib.sha256()
    sha256_hash.update("\n".join(sub_checksums).encode())
    return sha256_hash.hexdigest()
