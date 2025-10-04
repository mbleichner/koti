from __future__ import annotations

from hashlib import sha256
from typing import Generator, Sequence

from koti import Action
from koti.model import ConfigItem, ConfigItemState, ConfigManager, ConfigModel, ManagedConfigItem
from koti.items.hooks import PostHook
from koti.utils.json_store import JsonMapping, JsonStore


class PostHookState(ConfigItemState):
  trigger_hashes: dict[str, str]  # trigger.identifier() => trigger_state.hash()

  def __init__(self, trigger_hashes: dict[str, str]):
    self.trigger_hashes = trigger_hashes

  def sha256(self) -> str:
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

  def assert_installable(self, hook: PostHook, model: ConfigModel):
    assert hook.execute is not None, "missing execute parameter"
    for item in hook.trigger:
      exec_order_item = PostHookManager.index_in_execution_order(model, item)  # can be None in case the item isn't set up by koti (i.e. files created by pacman hooks or such)
      exec_order_hook = PostHookManager.index_in_execution_order(model, hook)
      assert exec_order_hook is not None, f"{hook} not found in execution order"
      assert exec_order_item is None or exec_order_item < exec_order_hook, f"{hook} has trigger that is evaluated too late: {item}"

  @staticmethod
  def index_in_execution_order(model: ConfigModel, needle: ConfigItem) -> int | None:
    result = 0
    for phase in model.phases:
      for step in phase.steps:
        for item in step.items_to_install:
          if item == needle:
            return result
          result += 1
    return None

  def state_current(self, hook: PostHook) -> PostHookState | None:
    stored_value = self.trigger_hash_store.get(hook.name, None)
    if stored_value is None or not isinstance(stored_value, dict):
      return None
    trigger_hashes: dict[str, str] = stored_value
    return PostHookState(trigger_hashes)

  def state_target(self, hook: PostHook, model: ConfigModel, dryrun: bool) -> PostHookState:
    trigger_hashes: dict[str, str] = {}
    for trigger_ref in hook.trigger:
      trigger_state = self.state_for_trigger(trigger_ref, model, dryrun)
      if trigger_state is not None:
        trigger_hashes[str(trigger_ref)] = trigger_state.sha256()
    return PostHookState(trigger_hashes)

  def state_for_trigger(self, reference: ManagedConfigItem, model: ConfigModel, dryrun: bool) -> ConfigItemState | None:
    manager: ConfigManager = model.manager(reference)

    # during dryrun, assume that the trigger item will already have been
    # updated to its target state (if managed by koti)
    if dryrun:
      trigger_item = model.item(reference, optional = True)
      if trigger_item is not None:
        return manager.state_target(trigger_item, model, dryrun)

    return manager.state_current(reference)

  def plan_install(self, items_to_check: Sequence[PostHook], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    for hook in items_to_check:
      current, target = self.states(hook, model, dryrun)
      if current == target:
        continue
      assert target is not None
      if current is None:
        yield Action(
          installs = [hook],
          description = f"execute hook '{hook.name}' for the first time",
          execute = lambda: self.execute_hook(hook, target),
        )
      else:
        yield Action(
          updates = [hook],
          description = f"execute hook '{hook.name}' because of updated dependencies",
          execute = lambda: self.execute_hook(hook, target),
        )

  def plan_cleanup(self, items_to_keep: Sequence[PostHook], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    currently_tracked_hooks = [PostHook(name) for name in self.trigger_hash_store.keys()]
    for hook in currently_tracked_hooks:
      if hook in items_to_keep:
        continue
      yield Action(
        removes = [hook],
        description = f"hook will no longer be tracked: {hook.name}",
        execute = lambda: self.unregister_hook(hook)
      )

  def execute_hook(self, hook: PostHook, target: PostHookState):
    assert hook.execute is not None
    hook.execute()
    self.trigger_hash_store.put(hook.name, target.trigger_hashes)

  def unregister_hook(self, hook: PostHook):
    self.trigger_hash_store.remove(hook.name),

  def finalize(self, model: ConfigModel, dryrun: bool):
    if not dryrun:
      currently_installed = [item.name for phase in model.phases for item in phase.items if isinstance(item, PostHook)]
      previously_installed = self.trigger_hash_store.keys()
      for name in previously_installed:
        if name not in currently_installed:
          self.trigger_hash_store.remove(name)
