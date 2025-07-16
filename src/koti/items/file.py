from pathlib import Path
from typing import Callable

from koti.core import ConfigItem, ConfirmModeValues, Koti


class FileOption(ConfigItem):
  value: str
  option: str
  filename: str

  def __init__(self, filename: str, option: str, value: str):
    self.filename = filename
    self.option = option
    self.value = value

  def identifier(self):
    return f"FileOption('{self.filename}', '{self.option}')"


class File(ConfigItem):
  content: Callable[[Koti], bytes] | None
  permissions: int = 0o755
  owner: str = "root"
  filename: str

  def __init__(
    self,
    filename: str,
    content: str | None = None,
    content_from_file: str | None = None,
    content_from_function: Callable[[list[FileOption]], str] | None = None,
    permissions: int = 0o444,
    owner: str = "root",
    confirm_mode: ConfirmModeValues | None = None
  ):
    self.filename = filename
    if content is not None:
      self.content = lambda core: content.encode("utf-8")
    elif content_from_function is not None:
      def gen_content(core: Koti):
        options = [
            item
            for phase in core.execution_phases
            for group in phase.groups_in_phase
            for item in group.provides
            if isinstance(item, FileOption) and item.filename == self.filename
        ]
        return content_from_function(options).encode("utf-8")
      self.content = lambda core: gen_content(core)
    elif content_from_file is not None:
      self.content = lambda core: Path(content_from_file).read_bytes()
    else:
      self.content = None
    self.permissions = permissions
    self.owner = owner
    self.confirm_mode = confirm_mode

  def identifier(self):
    return f"File('{self.filename}')"
