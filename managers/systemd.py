from definitions import ConfigItem, ConfigManager, ExecutionState
from managers.pacman import interactive
from utils import JsonStore, confirm


class SystemdUnit(ConfigItem):
  def __init__(self, identifier: str, ):
    super().__init__(identifier)

  def __str__(self):
    return f"SystemdUnit('{self.identifier}')"


class SystemdUnitManager(ConfigManager[SystemdUnit]):
  managed_classes = [SystemdUnit]
  store: JsonStore

  def __init__(self):
    self.store = JsonStore("/var/cache/arch-config/FileManager.json")

  def execute_phase(self, items: list[SystemdUnit], state: ExecutionState):
    if len(items) > 0:
      interactive(f"systemctl daemon-reload")
      interactive(f"systemctl enable --now {" ".join([item.identifier for item in items])}")
      managed_units_set = set(self.store.get("managed_units", []))
      self.store.put("managed_units", list(managed_units_set.union({item.identifier for item in items})))

  def finalize(self, items: list[SystemdUnit], state: ExecutionState):
    interactive(f"systemctl daemon-reload")
    currently_managed_units = [item.identifier for item in items]
    previously_managed_units = self.store.get("managed_units", [])
    units_to_deactivate = [file for file in previously_managed_units if file not in currently_managed_units]
    if len(units_to_deactivate) > 0:
      confirm(f"confirm to deactivate units: {", ".join(units_to_deactivate)}")
      interactive(f"systemctl disable --now {" ".join(units_to_deactivate)}")
      self.store.put("managed_units", currently_managed_units)
