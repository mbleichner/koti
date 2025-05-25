from koti.core import ConfigItem


class Swapfile(ConfigItem):
  size_bytes: int | None

  def __init__(self, identifier: str, size_bytes: int | None = None):
    super().__init__(identifier)
    self.size_bytes = size_bytes

  def __str__(self):
    return f"Swapfile('{self.identifier}')"
