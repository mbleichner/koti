from __future__ import annotations

from random import random
from hashlib import sha256

from koti import ConfigItem
from koti.core import ConfigManager, ConfigModel, SystemState
from koti.items.hooks import PostHook
from koti.utils import JsonMapping, JsonStore


class PostHookManager(ConfigManager[PostHook]):
  managed_classes = [PostHook]
  checksum_store: JsonMapping[str, str]
  order_in_cleanup_phase = "last"

  def __init__(self):
    store = JsonStore("/var/cache/koti/PostHookManager.json")
    self.checksum_store = store.mapping("checksums")

  def check_configuration(self, hook: PostHook, model: ConfigModel):
    assert hook.execute is not None, "missing execute parameter"
    for item in hook.trigger:
      exec_order_item = PostHookManager.index_in_execution_order(model, item)  # can be None in case the item isn't set up by koti (i.e. files created by pacman hooks or such)
      exec_order_hook = PostHookManager.index_in_execution_order(model, hook)
      assert exec_order_hook is not None, f"{hook} not found in execution order"
      assert exec_order_item is None or exec_order_item < exec_order_hook
      if exec_order_item is not None and not exec_order_item < exec_order_hook: f"{hook} has trigger that is evaluated too late: {item}"

  def install(self, items: list[PostHook], model: ConfigModel, state: SystemState):
    for hook in items:
      assert hook.execute is not None
      target_checksum = self.checksum_target(hook, model, state)
      hook.execute()
      self.checksum_store.put(hook.name, str(target_checksum))

  @staticmethod
  def index_in_execution_order(model: ConfigModel, needle: ConfigItem) -> int | None:
    result = 0
    for phase in model.phases:
      for step in phase.steps:
        for item in step.items_to_install:
          if item.identifier() == needle.identifier():
            return result
          result += 1
    return None

  def installed(self, model: ConfigModel) -> list[PostHook]:
    return [PostHook(name) for name in self.checksum_store.keys()]

  def uninstall(self, items: list[PostHook], model: ConfigModel):
    pass

  def checksum_current(self, hook: PostHook) -> str:
    return self.checksum_store.get(hook.name, "n/a")

  def checksum_target(self, hook: PostHook, model: ConfigModel, state: SystemState) -> str:
    if not hook.trigger:
      return str(random())
    checksums = [state.checksum(trigger_item) for trigger_item in hook.trigger]
    sha256_hash = sha256()
    for idx, trigger in enumerate(hook.trigger):
      checksum = checksums[idx]
      sha256_hash.update(trigger.identifier().encode())
      sha256_hash.update(str(checksum).encode())
    return sha256_hash.hexdigest()
