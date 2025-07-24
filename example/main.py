from __future__ import annotations

# disable bytecode compilation (can cause issues with root-owned cache-files)
import sys
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

my_arch_systems = {
  "dan": dan(),  # DAN A4-SFX desktop PC
  "lenovo": lenovo(),  # Lenovo X13 laptop
  "mserver": mserver(),  # homelab server
}

koti = Koti(
  managers = KotiManagerPresets.arch(PacmanAdapter("sudo -u manuel paru")),  # predefined managers for Arch Linux, but use paru instead of pacman
  configs = my_arch_systems[gethostname()],  # choose system config based on the current hostname
)

if koti.plan():
  confirm("confirm execution")
  koti.apply()
  print("execution finished.")
