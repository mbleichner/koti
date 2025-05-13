from definitions import ConfigItem, ConfigManager


class Symlink(ConfigItem):
  def __init__(self, identifier: str, target: str = None):
    super().__init__(identifier)
    self.target = target

  def __str__(self):
    return f"Symlink('{self.identifier}', target = '{self.target}')"


# FIXME
class SymlinkManager(ConfigManager[Symlink]):
  managed_classes = [Symlink]

  def check_configuration(self, item: Symlink) -> str | None:
    if item.target is None:
      return "Symlink() needs to define a target"

  def execute_phase(self, items: list[Symlink]):
    for item in items:
      print(f"creating symlink {item.identifier} -> {item.target}")
