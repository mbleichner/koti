from typing import TypedDict

from confirm import confirm, effective_confirm_mode, get_confirm_mode
from core import ArchUpdate, ConfigItem, ConfigManager, ConfirmModeValues, ExecutionState
from json_store import JsonMapping, JsonStore
from managers.pacman import shell_interactive


class SystemdUnit(ConfigItem):
  def __init__(self, identifier: str, ):
    super().__init__(identifier)

  def __str__(self):
    return f"SystemdUnit('{self.identifier}')"


def SystemdUnits(*identifiers: str) -> list[SystemdUnit]:
  return [SystemdUnit(identifier) for identifier in identifiers]


class SystemdUnitStoreEntry(TypedDict):
  confirm_mode: ConfirmModeValues


class SystemdUnitManager(ConfigManager[SystemdUnit]):
  managed_classes = [SystemdUnit]
  managed_units_store: JsonMapping[str, SystemdUnitStoreEntry]

  def __init__(self):
    super().__init__()
    store = JsonStore("/var/cache/arch-config/SystemdUnitManager.json")
    self.managed_units_store = store.mapping("managed_units")

  def execute_phase(self, items: list[SystemdUnit], core: ArchUpdate, state: ExecutionState):
    if len(items) > 0:
      shell_interactive(f"systemctl daemon-reload")
      shell_interactive(f"systemctl enable --now {" ".join([item.identifier for item in items])}")
      for item in items:
        mode = get_confirm_mode(item, core)
        self.managed_units_store.put(item.identifier, {"confirm_mode": mode})

  def finalize(self, items: list[SystemdUnit], core: ArchUpdate, state: ExecutionState):
    shell_interactive(f"systemctl daemon-reload")
    currently_managed_units = [item.identifier for item in items]
    previously_managed_units = self.managed_units_store.keys()
    units_to_deactivate = [file for file in previously_managed_units if file not in currently_managed_units]
    if len(units_to_deactivate) > 0:
      confirm(
        message = f"confirm to deactivate units: {", ".join(units_to_deactivate)}",
        destructive = True,
        mode = effective_confirm_mode([
          self.managed_units_store.get(unit, {}).get("confirm_mode", core.default_confirm_mode) for unit in units_to_deactivate
        ], core),
      )
      shell_interactive(f"systemctl disable --now {" ".join(units_to_deactivate)}")
      for identifier in units_to_deactivate:
        self.managed_units_store.remove(identifier)
