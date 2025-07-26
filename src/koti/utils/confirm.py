from __future__ import annotations

from sys import exit


def confirm(message: str):
  while True:
    answer = input(f'{message}: [Y/n] ').strip().lower()
    if answer in ('y', ''): return True
    if answer == 'n':
      print("execution cancelled")
      exit(1)
