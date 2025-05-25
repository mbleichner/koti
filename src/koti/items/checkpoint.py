from koti.core import ConfigItem


class Checkpoint(ConfigItem):
  def __init__(self, identifier: str):
    super().__init__(identifier)

  def __str__(self):
    return f"Checkpoint('{self.identifier}')"
