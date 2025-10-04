BLUE = '\033[0;33m'
CYAN = '\033[0;36m'
GREEN = '\033[0;32m'
YELLOW = '\033[0;33m'
RED = '\033[0;31m'
BOLD = '\033[1m'
ENDC = '\033[0m'


def printc(line: str):
  print(f"{ENDC}{line}{ENDC}")


def strip_colors(line: str) -> str:
  result = line
  for x in [BLUE, CYAN, GREEN, YELLOW, RED, BOLD, UNDERLINE, ENDC]:
    result = result.replace(x, "")
  return result


def ljust(line: str, width: int) -> str:
  return line + (width - max(0, len(strip_colors(line)))) * " "
