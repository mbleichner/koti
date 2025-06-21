from __future__ import annotations

# disable bytecode compilation (can cause issues with root-owned cache-files)
import sys
from typing import Generator

sys.dont_write_bytecode = True

# import koti stuff
from koti import *
from koti.utils import *
from koti.presets import KotiManagerPresets

# import user configs
from systems.dan import dan
from systems.lenovo import lenovo
from systems.mserver import mserver

from socket import gethostname

configs: dict[str, Generator[ConfigGroup | None]] = {
  "dan": dan(),
  "lenovo": lenovo(),
  "mserver": mserver(),
}

koti = Koti(
  managers = KotiManagerPresets.arch(PacmanAdapter("sudo -u manuel paru")),
  configs = list(filter(None, configs[gethostname()])),
)

koti.plan(groups = True, items = False, summary = True)
confirm("confirm execution")
koti.apply()
print("execution finished.")
