from __future__ import annotations

from typing import Literal
type ConfirmModeValues = Literal["paranoid", "cautious", "yolo"]
import sys


def confirm(message: str, destructive: bool = True, mode: ConfirmModeValues = "paranoid"):
  if not needs_confirmation(destructive, mode):
    print(f"{message}: skipping confirmation of {"destructive" if destructive else "non-destructive"} operation due to confirm_mode = {mode}")
    return None
  while True:
    answer = input(f'{message}: [Y/n] ').strip().lower()
    if answer in ('y', ''): return True
    if answer == 'n':
      print("execution cancelled")
      sys.exit(1)


def needs_confirmation(destructive: bool, mode: ConfirmModeValues):
  if mode == "paranoid": return True
  if mode == "yolo": return False
  return destructive


def highest_confirm_mode(*modes: ConfirmModeValues | None) -> ConfirmModeValues | None:
  modes_in_order: list[ConfirmModeValues] = ["paranoid", "cautious", "yolo"]
  for mode in modes_in_order:
    if mode in modes: return mode
  return None
