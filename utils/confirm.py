from __future__ import annotations

from core import Core, ConfigItem, ConfirmMode, ConfirmModeValues


def confirm(message: str, destructive: bool, mode: ConfirmModeValues):
  if not needs_confirmation(destructive, mode):
    print(f"{message}: skipping confirmation of {"destructive" if destructive else "non-destructive"} operation due to confirm_mode = {mode}")
    return
  while True:
    answer = input(f'{message}: [Y/n] ').strip().lower()
    if answer in ('y', ''): return True
    if answer == 'n': raise AssertionError("execution cancelled")


def needs_confirmation(destructive: bool, mode: ConfirmModeValues):
  if mode == "paranoid": return True
  if mode == "yolo": return False
  return destructive
