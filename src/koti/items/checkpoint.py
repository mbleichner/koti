from koti.core import ConfigItem


class Checkpoint(ConfigItem):
  identifier: str | None

  def __init__(self, identifier: str | None):
    super().__init__(identifier)
    self.identifier = identifier

  def __str__(self):
    return f"Checkpoint('{self.identifier}')"
