BLUE = '\033[0;33m'
PURPLE = '\033[0;35m'
GREEN = '\033[0;32m'
YELLOW = '\033[0;33m'
RED = '\033[0;31m'
BOLD = '\033[1m'
ENDC = '\033[0m'


def printc(line: str):
  print(f"{ENDC}{line}{ENDC}")


def strip_colors(line: str) -> str:
  result = line
  for x in [BLUE, PURPLE, GREEN, YELLOW, RED, BOLD, ENDC]:
    result = result.replace(x, "")
  return result


def ljust(line: str, width: int) -> str:
  return line + (width - max(0, len(strip_colors(line)))) * " "
