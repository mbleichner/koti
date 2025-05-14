from definitions import ConfigItem, ConfigManager, ExecutionState
from managers.package import interactive
from utils import JsonStore


# class IdempotentCommand(ConfigItem):
#   def __init__(self, identifier: str, command: str):
#     super().__init__(identifier)
#     self.command = command
#
#   def __str__(self):
#     return f"IdempotentCommand('{self.identifier}')"
#
#
# class IdempotentCommandManager(ConfigManager[IdempotentCommand]):
#   managed_classes = [IdempotentCommand]
#   store: JsonStore
#
#   def __init__(self):
#     self.store = JsonStore("/var/cache/arch-config/FileManager.json")
#
#   def execute_phase(self, items: list[IdempotentCommand], state: ExecutionState):
#     for item in items:
#       interactive(item.command)
