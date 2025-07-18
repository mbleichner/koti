from __future__ import annotations
from sys import exit

from koti import ConfirmModeValues


def confirm(message: str, destructive: bool = True, mode: ConfirmModeValues = "paranoid"):
  if not needs_confirmation(destructive, mode):
    print(f"{message}: skipping confirmation of {"destructive" if destructive else "non-destructive"} operation due to confirm_mode = {mode}")
    return None
  while True:
    answer = input(f'{message}: [Y/n] ').strip().lower()
    if answer in ('y', ''): return True
    if answer == 'n':
      print("execution cancelled")
      exit(1)


def needs_confirmation(destructive: bool, mode: ConfirmModeValues):
  if mode == "paranoid": return True
  if mode == "yolo": return False
  return destructive
