from __future__ import annotations

from hashlib import sha256

from koti.core import Checksums, ConfigManager, Koti
from koti.items.hooks import PostHook
from koti.utils import JsonMapping, JsonStore
from koti.utils.confirm import confirm


class PostHookManager(ConfigManager[PostHook]):
  managed_classes = [PostHook]
  checksum_store: JsonMapping[str, str]

  def __init__(self):
    store = JsonStore("/var/cache/koti/PostHookManager.json")
    self.checksum_store = store.mapping("checksums")

  def check_configuration(self, item: PostHook, core: Koti):
    if item.execute is None:
      raise AssertionError("missing execute parameter")

  def checksums(self, core: Koti) -> PostHookChecksums:
    return PostHookChecksums(self, core, self.checksum_store)

  def apply_phase(self, items: list[PostHook], core: Koti):
    checksums = self.checksums(core)
    for hook in items:
      confirm(
        message = f"confirm executing {hook}",
        destructive = False,
        mode = core.get_confirm_mode_for_item(hook),
      )
      target_checksum = checksums.target(hook)
      hook.execute()
      self.checksum_store.put(hook.identifier, target_checksum)

  def cleanup(self, items: list[PostHook], core: Koti):
    pass


class PostHookChecksums(Checksums[PostHook]):
  manager: PostHookManager
  core: Koti
  checksum_store: JsonMapping[str, str]

  def __init__(self, manager: PostHookManager, core: Koti, checksum_store: JsonMapping[str, str]):
    self.manager = manager
    self.checksum_store = checksum_store
    self.core = core

  def current(self, hook: PostHook) -> str | None:
    return self.checksum_store.get(hook.identifier, None)

  def target(self, hook: PostHook) -> str | None:
    group_containing_hook = self.core.get_group_for_item(hook)
    sha256_hash = sha256()
    sha256_hash.update("\n".join(self.get_trigger_checksums(group_containing_hook)).encode())
    return sha256_hash.hexdigest()

  def get_trigger_checksums(self, group_containing_hook):
    result = []
    for manager in self.core.managers:
      managed_items = [item for item in group_containing_hook.items if item.__class__ in manager.managed_classes]
      if len(managed_items) == 0: continue
      manager_checksums = manager.checksums(self.core)
      for item in managed_items:
        if self.core.managers.index(manager) < self.core.managers.index(self.manager):
          result.append(str(manager_checksums.current(item)))
    return result
