from __future__ import annotations

from koti.utils.text import RED, YELLOW


class Logger:
  messages: list[str]

  def __init__(self):
    self.messages = []

  def clear(self):
    self.messages = []

  def info(self, message: str):
    self.messages.append(message)

  def warn(self, message: str):
    self.messages.append(f"{YELLOW}{message}")

  def error(self, message: str):
    self.messages.append(f"{RED}{message}")


logger = Logger()
