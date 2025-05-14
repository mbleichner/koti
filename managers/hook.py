from definitions import ConfigItem, ConfigManager, Executable, ExecutionState


class Hook(ConfigItem):
  identifier: str | None
  execute: None | Executable
  triggered_by: None | ConfigItem | list[ConfigItem]

  def __init__(self, identifier: str | None, execute: Executable = None, triggered_by: ConfigItem | list[ConfigItem] = None):
    super().__init__(identifier)
    self.identifier = identifier
    self.triggered_by = triggered_by
    self.execute = execute

  def __str__(self):
    return f"Hook('{self.identifier}')"


class HookManager(ConfigManager[Hook]):
  managed_classes = [Hook]

  def execute_phase(self, items: list[Hook], state: ExecutionState):
    for hook in items:
      if hook.triggered_by is None:
        print(f"executing hook '{hook.identifier}'")
        hook.execute.execute()
      else:
        all_triggers = hook.triggered_by if isinstance(hook.triggered_by, list) else [hook.triggered_by]
        active_triggers = [trigger for trigger in all_triggers if self.is_triggered(trigger, state)]
        if len(active_triggers) > 0:
          print(f"executing hook '{hook.identifier}', caused by update in {", ".join([str(a) for a in active_triggers])}")
          hook.execute.execute()

  def is_triggered(self, item: ConfigItem, state: ExecutionState) -> bool:
    for other in state["updated_items"]:
      if other.__class__ == item.__class__ and other.identifier == item.identifier:
        return True
    return False
