from __future__ import annotations

from typing import Generator, Optional


def filter_present[T](*values: Optional[T]) -> Generator[T]:
  for value in values:
    if value is not None:
      yield value
