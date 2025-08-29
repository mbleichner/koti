from __future__ import annotations

from hashlib import sha256
from typing import cast

from koti.model import ConfigItem, ConfigItemState, ConfigManager, ConfigModel, ManagedConfigItem
from koti.items.hooks import PostHook
from koti.utils import JsonMapping, JsonStore


class PostHookState(ConfigItemState):
  trigger_hashes: dict[str, str]  # trigger.identifier() => trigger_state.hash()

  def __init__(self, trigger_hashes: dict[str, str]):
    self.trigger_hashes = trigger_hashes

  def hash(self) -> str:
    sha256_hash = sha256()
    for identifier, trigger_hash in self.trigger_hashes.items():
      sha256_hash.update(identifier.encode())
      sha256_hash.update(trigger_hash.encode())
    return sha256_hash.hexdigest()


class PostHookManager(ConfigManager[PostHook, PostHookState]):
  managed_classes = [PostHook]
  trigger_hash_store: JsonMapping[str, dict[str, str]]
  order_in_cleanup_phase = "last"

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/koti/PostHookManager.json")
    self.trigger_hash_store = store.mapping("checksums")

  def check_configuration(self, hook: PostHook, model: ConfigModel):
    assert hook.execute is not None, "missing execute parameter"
    for item in hook.trigger:
      exec_order_item = PostHookManager.index_in_execution_order(model, item)  # can be None in case the item isn't set up by koti (i.e. files created by pacman hooks or such)
      exec_order_hook = PostHookManager.index_in_execution_order(model, hook)
      assert exec_order_hook is not None, f"{hook} not found in execution order"
      assert exec_order_item is None or exec_order_item < exec_order_hook
      if exec_order_item is not None and not exec_order_item < exec_order_hook: f"{hook} has trigger that is evaluated too late: {item}"

  def install(self, items: list[PostHook], model: ConfigModel):
    for hook in items:
      assert hook.execute is not None
      new_state = self.state_target(hook, model, planning = False)
      hook.execute()
      self.trigger_hash_store.put(hook.name, new_state.trigger_hashes)

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
    return [PostHook(name) for name in self.trigger_hash_store.keys()]

  def uninstall(self, items: list[PostHook], model: ConfigModel):
    pass

  def state_current(self, hook: PostHook) -> PostHookState | None:
    stored_value = self.trigger_hash_store.get(hook.name, None)
    if stored_value is None or not isinstance(stored_value, dict):
      return None
    trigger_hashes: dict[str, str] = stored_value
    return PostHookState(trigger_hashes)

  def state_target(self, hook: PostHook, model: ConfigModel, planning: bool) -> PostHookState:
    return PostHookState(
      trigger_hashes = dict(
        (ref.identifier(), self.state_for_trigger(ref, model, planning).hash())
        for ref in hook.trigger
      )
    )

  @staticmethod
  def state_for_trigger(reference: ManagedConfigItem, model: ConfigModel, planning: bool) -> ConfigItemState | None:
    manager: ConfigManager = model.manager(reference)

    # during planning, assume that the trigger item will already have been
    # updated to its target state (if managed by koti)
    if planning:
      trigger_item = model.item(reference, optional = True)
      if trigger_item is not None:
        return manager.state_target(trigger_item, model, planning)

    return manager.state_current(reference)

  def describe_change(self, item: PostHook, state_current: ConfigItemState | None, state_target: ConfigItemState) -> list[str]:
    state_current = cast(PostHookState | None, state_current)
    state_target = cast(PostHookState, state_target)
    if state_current is None:
      return ["initial trigger"]
    all_triggers = set(state_current.trigger_hashes.keys()).union(state_target.trigger_hashes.keys())
    changed_triggers = [
      trigger for trigger in all_triggers
      if state_current.trigger_hashes.get(trigger, None) != state_target.trigger_hashes.get(trigger, None)
    ]
    return [f"changed triggers: {", ".join(changed_triggers)}"] if changed_triggers else []
