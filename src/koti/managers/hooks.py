from __future__ import annotations

from hashlib import sha256

from koti import ConfigItem, ConfigMetadata
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
    for item in PostHookManager.get_trigger_items(core, hook):

      try:
        PostHookManager.assert_valid_trigger(core, hook, item)
      except AssertionError as e:
        raise AssertionError(f"{str(hook)} depends on invalid trigger {item}: {str(e)}")

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
    currently_managed_hooks = [item.identifier for item in items]
    previously_managed_hooks = self.checksum_store.keys()
    hooks_to_delete = [identifier for identifier in previously_managed_hooks if identifier not in currently_managed_hooks]
    for hook_identifier in hooks_to_delete:
      self.checksum_store.remove(hook_identifier)

  @staticmethod
  def get_trigger_items(core: Koti, hook: PostHook) -> list[ConfigItem]:
    if hook.trigger == "group":
      return [item for item in core.get_group_for_item(hook).items if PostHookManager.is_valid_trigger(core, hook, item)]
    elif isinstance(hook.trigger, ConfigItem):
      return [hook.trigger]
    elif isinstance(hook.trigger, list):
      return hook.trigger
    raise AssertionError(f"illegal PostHook trigger argument: {hook.trigger}")

  @staticmethod
  def assert_valid_trigger(core: Koti, hook: PostHook, item: ConfigItem | ConfigMetadata):
    if isinstance(item, PostHook):
      raise AssertionError("cannot be a PostHook")
    if not isinstance(item, ConfigItem):
      raise AssertionError("needs to be a ConfigItem")
    if not PostHookManager.index_in_execution_order(core, item) < PostHookManager.index_in_execution_order(core, hook):
      raise AssertionError("needs to be executed before hook")

  @staticmethod
  def is_valid_trigger(core: Koti, hook: PostHook, item: ConfigItem | ConfigMetadata) -> bool:
    try:
      PostHookManager.assert_valid_trigger(core, hook, item)
      return True
    except AssertionError as e:
      return False

  @staticmethod
  def index_in_execution_order(core: Koti, needle: ConfigItem) -> int:
    result = 0
    for phase in core.execution_phases:
      for group in phase.groups:
        for item in group.items:
          if isinstance(item, ConfigItem):
            if item.__class__ == needle.__class__ and item.identifier == needle.identifier:
              return result
            result += 1
    raise AssertionError(f"item not found in execution order: {needle}")


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
    trigger_items = PostHookManager.get_trigger_items(self.core, hook)
    checksums = self.get_current_checksums_for_items(trigger_items)
    sha256_hash = sha256()
    for idx, trigger in enumerate(trigger_items):
      checksum = checksums[idx]
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
