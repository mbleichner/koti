from pathlib import Path

from koti.core import ConfigItem


class File(ConfigItem):
  content: bytes | None
  permissions: int = 0o755
  owner: str = "root"

  def __init__(
    self,
    identifier: str,
    content: str = None,
    path = None,
    permissions: int = 0o444,
    owner: str = "root",
  ):
    super().__init__(identifier)
    if content is not None: self.content = content.encode("utf-8")
    if path is not None: self.content = Path(path).read_bytes()
    self.permissions = permissions
    self.owner = owner

  def __str__(self):
    return f"File('{self.identifier}')"
