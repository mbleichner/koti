from __future__ import annotations

from typing import Any, Sequence

from koti.model import ConfigItem, UnmanagedConfigItem


class Option[T](UnmanagedConfigItem):
  """Helper item to specify options that may be used by other ConfigItems; for example
  being rendered into a config file. Options can contain one or multiple values.
  """

  name: str
  _values: list[T]

  def __init__(self, name: str, value: Sequence[T] | T | None = None):
    self.name = name
    if isinstance(value, list):
      self._values = [*value]
    elif isinstance(value, str):
      self._values = [value]
    else:
      self._values = []

  def values(self) -> list[T]:
    """Returns all values that have been provided for this option, possibly containing duplicates."""
    return self._values

  def distinct(self) -> list[T]:
    """Returns all distinct values that have been provided for this option (duplicates will get removed by __eq__)."""
    result: list[T] = []
    for value in self._values:
      if not value in result:
        result.append(value)
    return result

  def optional(self) -> T | None:
    """Returns the value that has been provided for this option if it is unique. Throws an error otherwise."""
    if len(self._values) == 0: return None
    first = self._values[0]
    assert all((first == value for value in self._values[1:])), f"{self} contains non-unique values"
    return first

  def single(self) -> T:
    """Returns the value that has been provided for this option if it is unique. Throws an error otherwise."""
    result = self.optional()
    assert result is not None, f"No value provided for {self}"
    return result

  def __eq__(self, other: Any) -> bool:
    return isinstance(other, Option) and self.name == other.name

  def __hash__(self):
    return hash(self.name)

  def __str__(self):
    return f"Option('{self.name}')"

  def merge(self, other: ConfigItem) -> Option:
    assert isinstance(other, Option) and self == other
    return Option(
      name = self.name,
      value = list([*self._values, *other._values]),
    )
