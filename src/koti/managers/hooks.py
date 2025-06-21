from __future__ import annotations

from hashlib import sha256

from koti import ConfigItem
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

  def check_configuration(self, hook: PostHook, core: Koti):
    if hook.execute is None:
      raise AssertionError("missing execute parameter")
    if len(hook.trigger) == 0:
      raise AssertionError(f"{hook} has no trigger(s)")
    for item in hook.trigger:
      exec_order_item = PostHookManager.index_in_execution_order(core, item)  # can be None in case the item isn't set up by koti (i.e. files created by pacman hooks or such)
      exec_order_hook = PostHookManager.index_in_execution_order(core, hook)
      if exec_order_hook is None: raise AssertionError("illegal state")
      if exec_order_item is not None and not exec_order_item < exec_order_hook:
        raise AssertionError(f"{hook} has trigger that is evaluated too late: {item}")

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
      if hook.execute is None:
        raise AssertionError(f"{hook} has no execute method")
      hook.execute()
      self.checksum_store.put(hook.identifier, str(target_checksum))

  def cleanup(self, items: list[PostHook], core: Koti):
    currently_managed_hooks = [item.identifier for item in items]
    previously_managed_hooks = self.checksum_store.keys()
    hooks_to_delete = [identifier for identifier in previously_managed_hooks if identifier not in currently_managed_hooks]
    for hook_identifier in hooks_to_delete:
      self.checksum_store.remove(hook_identifier)

  @staticmethod
  def index_in_execution_order(core: Koti, needle: ConfigItem) -> int | None:
    result = 0
    for phase in core.execution_phases:
      for manager, items_for_manager in phase.execution_order:
        for item in items_for_manager:
          if item.__class__ == needle.__class__ and item.identifier == needle.identifier:
            return result
          result += 1
    return None


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
    checksums = self.get_current_checksums_for_items(hook.trigger)
    # print(hook)
    sha256_hash = sha256()
    for idx, trigger in enumerate(hook.trigger):
      checksum = checksums[idx]
      # print(f"- {trigger} {checksum}")
      sha256_hash.update(str(trigger).encode())
      sha256_hash.update(str(checksum).encode())
    return sha256_hash.hexdigest()

  def get_current_checksums_for_items(self, dependent_items: list[ConfigItem]) -> list[str | None]:
    result = []
    for manager in self.core.managers:
      managed_items = [item for item in dependent_items if item.__class__ in manager.managed_classes]
      if len(managed_items) == 0: continue
      manager_checksums = manager.checksums(self.core)
      for item in managed_items:
        result.append(manager_checksums.current(item))
    return result
