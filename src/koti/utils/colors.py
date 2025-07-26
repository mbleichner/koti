BLUE = '\033[94m'
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
ENDC = '\033[0m'


def printc(line: str, *styles: str | None):
  style = "".join((style for style in styles if style is not None))
  print(f"{style}{line.rstrip()}{ENDC}")
