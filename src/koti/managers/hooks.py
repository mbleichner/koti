from __future__ import annotations

from hashlib import sha256

from koti import ConfigItem
from koti.core import Checksums, ConfigManager, ExecutionModel, ManagedConfigItem
from koti.items.hooks import PostHook
from koti.utils import JsonMapping, JsonStore
from koti.utils.confirm import confirm


class PostHookManager(ConfigManager[PostHook]):
  managed_classes = [PostHook]
  checksum_store: JsonMapping[str, str]
  order_in_cleanup_phase = "last"

  def __init__(self):
    store = JsonStore("/var/cache/koti/PostHookManager.json")
    self.checksum_store = store.mapping("checksums")

  def check_configuration(self, hook: PostHook, model: ExecutionModel):
    assert hook.execute is not None, "missing execute parameter"
    assert len(hook.trigger) > 0, f"{hook} has no trigger(s)"
    for item in hook.trigger:
      exec_order_item = PostHookManager.index_in_execution_order(model, item)  # can be None in case the item isn't set up by koti (i.e. files created by pacman hooks or such)
      exec_order_hook = PostHookManager.index_in_execution_order(model, hook)
      assert exec_order_hook is not None, f"{hook} not found in execution order"
      assert exec_order_item is None or exec_order_item < exec_order_hook
      if exec_order_item is not None and not exec_order_item < exec_order_hook: f"{hook} has trigger that is evaluated too late: {item}"

  def checksums(self, model: ExecutionModel) -> PostHookChecksums:
    return PostHookChecksums(self, model, self.checksum_store)

  def install(self, items: list[PostHook], model: ExecutionModel):
    checksums = self.checksums(model)
    for hook in items:
      confirm(
        message = f"confirm executing {hook.description()}",
        destructive = False,
        mode = model.get_confirm_mode(hook),
      )
      assert hook.execute is not None
      target_checksum = checksums.target(hook)
      hook.execute()
      self.checksum_store.put(hook.name, str(target_checksum))

  def cleanup(self, items_to_keep: list[PostHook], model: ExecutionModel):
    currently_managed_hooks = [item.name for item in items_to_keep]
    previously_managed_hooks = self.checksum_store.keys()
    hooks_to_delete = [name for name in previously_managed_hooks if name not in currently_managed_hooks]
    for hook_name in hooks_to_delete:
      self.checksum_store.remove(hook_name)

  def finalize(self, all_items: list[PostHook], model: ExecutionModel):
    self.install(all_items, model)

  @staticmethod
  def index_in_execution_order(model: ExecutionModel, needle: ConfigItem) -> int | None:
    result = 0
    for phase in model.install_phases:
      for manager, items_for_manager in phase.order:
        for item in items_for_manager:
          if item.identifier() == needle.identifier():
            return result
          result += 1
    return None


class PostHookChecksums(Checksums[PostHook]):
  manager: PostHookManager
  model: ExecutionModel
  checksum_store: JsonMapping[str, str]

  def __init__(self, manager: PostHookManager, model: ExecutionModel, checksum_store: JsonMapping[str, str]):
    self.manager = manager
    self.checksum_store = checksum_store
    self.model = model

  def current(self, hook: PostHook) -> str | None:
    return self.checksum_store.get(hook.name, None)

  def target(self, hook: PostHook) -> str | None:
    checksums = self.get_current_checksums_for_items(hook.trigger)
    sha256_hash = sha256()
    for idx, trigger in enumerate(hook.trigger):
      checksum = checksums[idx]
      sha256_hash.update(trigger.identifier().encode())
      sha256_hash.update(str(checksum).encode())
    return sha256_hash.hexdigest()

  def get_current_checksums_for_items(self, dependent_items: list[ManagedConfigItem]) -> list[str | None]:
    result = []
    for manager in self.model.managers:
      managed_items = [item for item in dependent_items if item.__class__ in manager.managed_classes]
      if len(managed_items) == 0: continue
      manager_checksums = manager.checksums(self.model)
      for item in managed_items:
        result.append(manager_checksums.current(item))
    return result
