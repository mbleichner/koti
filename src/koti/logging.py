from __future__ import annotations

from typing import Any, Literal


class LogMessage:
  text: str
  source: Any
  level: Literal["info", "warn", "debug"]

  def __init__(self, text: str, source: Any, level: Literal["info", "warn", "debug"], ):
    self.level = level
    self.source = source
    self.text = text


class Logger:
  source: Any
  messages: list[LogMessage] = []

  def __init__(self, source: Any):
    self.source = source

  def info(self, msg: str):
    self.messages.append(LogMessage(msg, self.source, "info"))

  def warn(self, msg: str):
    self.messages.append(LogMessage(msg, self.source, "warn"))

  def debug(self, msg: str):
    self.messages.append(LogMessage(msg, self.source, "debug"))
