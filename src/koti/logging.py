from __future__ import annotations

from typing import Any, Literal


class LogMessage:
  text: str
  level: Literal["info", "warn", "debug", "error"]

  def __init__(self, level: Literal["info", "warn", "debug", "error"], text: str):
    self.level = level
    self.text = text


class WarnMessage(LogMessage):
  def __init__(self, text: str):
    super().__init__("warn", text)


class InfoMessage(LogMessage):
  def __init__(self, text: str):
    super().__init__("info", text)


class DebugMessage(LogMessage):
  def __init__(self, text: str):
    super().__init__("debug", text)


class ErrorMessage(LogMessage):
  def __init__(self, text: str):
    super().__init__("error", text)


# class Logger:
#   source: Any
#   messages: list[LogMessage] = []
#
#   def __init__(self, source: Any):
#     self.source = source
#
#   def info(self, msg: str):
#     self.messages.append(LogMessage(msg, self.source, "info"))
#
#   def warn(self, msg: str):
#     self.messages.append(LogMessage(msg, self.source, "warn"))
#
#   def debug(self, msg: str):
#     self.messages.append(LogMessage(msg, self.source, "debug"))
