BLUE = '\033[94m'
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
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
