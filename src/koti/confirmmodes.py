from __future__ import annotations

from typing import Literal

type ConfirmModeValues = Literal["paranoid", "cautious", "yolo"]


def highest_confirm_mode(*modes: ConfirmModeValues | None) -> ConfirmModeValues | None:
  modes_in_order: list[ConfirmModeValues] = ["paranoid", "cautious", "yolo"]
  for mode in modes_in_order:
    if mode in modes: return mode
  return None
