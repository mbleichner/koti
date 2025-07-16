from koti.core import ConfigItem


class Checkpoint(ConfigItem):
  name: str
  managed = False

  def __init__(self, name: str):
    self.name = name

  def identifier(self):
    return f"Checkpoint('{self.name}')"
