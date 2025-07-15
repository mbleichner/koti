from pathlib import Path

from koti.core import ConfigItem, ConfirmModeValues


class File(ConfigItem):
  content: bytes | None
  permissions: int = 0o755
  owner: str = "root"
  filename: str

  def __init__(
    self,
    filename: str,
    content: str | None = None,
    content_from_file: str | None = None,
    permissions: int = 0o444,
    owner: str = "root",
    confirm_mode: ConfirmModeValues | None = None
  ):
    self.filename = filename
    if content is not None:
      self.content = content.encode("utf-8")
    elif content_from_file is not None:
      self.content = Path(content_from_file).read_bytes()
    else:
      self.content = None
    self.permissions = permissions
    self.owner = owner
    self.confirm_mode = confirm_mode

  def identifier(self):
    return f"File('{self.filename}')"
