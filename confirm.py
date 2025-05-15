from __future__ import annotations

from core import ArchUpdate, ConfigItem, ConfirmMode, ConfirmModeValues


def confirm(message: str, destructive: bool, mode: ConfirmModeValues):
  if not needs_confirmation(destructive, mode):
    print(f"{message}: skipped {"destructive" if destructive else "non-destructive"} operation due to confirm_mode = {mode}")
    return
  while True:
    answer = input(f'{message}: [Y/n] ').strip().lower()
    if answer in ('y', ''): return True
    if answer == 'n': raise AssertionError("execution cancelled")


def needs_confirmation(destructive: bool, mode: ConfirmModeValues):
  if mode == "paranoid": return True
  if mode == "yolo": return False
  return destructive


def get_confirm_mode(item: ConfigItem, core: ArchUpdate) -> ConfirmModeValues:
  group = core.get_group_for_item(item)
  confirm_modes = [item.mode for item in group.items if isinstance(item, ConfirmMode)]
  return effective_confirm_mode(confirm_modes, core)


def effective_confirm_mode(modes: list[ConfirmModeValues], core: ArchUpdate) -> ConfirmModeValues:
  modes_in_order: list[ConfirmModeValues] = ["paranoid", "cautious", "yolo"]
  for mode in modes_in_order:
    if mode in modes: return mode
  return core.default_confirm_mode
