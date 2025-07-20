from __future__ import annotations

from typing import Literal

type ConfirmMode = Literal[
  "paranoid",  # confirm every change
  "cautious",  # confirm only destructive changes
  "yolo",  # apply everything without confirmation
]


def highest_confirm_mode(*modes: ConfirmMode | None) -> ConfirmMode | None:
  modes_in_order: list[ConfirmMode] = ["paranoid", "cautious", "yolo"]
  for mode in modes_in_order:
    if mode in modes:
      return mode
  return None
