from pathlib import Path

from koti.core import ConfigItem


class File(ConfigItem):
  content: bytes | None
  permissions: int = 0o755
  owner: str = "root"

  def __init__(
    self,
    identifier: str,
    content: str | None = None,
    content_from_file: str | None = None,
    permissions: int = 0o444,
    owner: str = "root",
  ):
    super().__init__(identifier)
    if content is not None:
      self.content = content.encode("utf-8")
    elif content_from_file is not None:
      self.content = Path(content_from_file).read_bytes()
    else:
      self.content = None
    self.permissions = permissions
    self.owner = owner

  def __str__(self):
    return f"File('{self.identifier}')"
