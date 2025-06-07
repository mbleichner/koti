from __future__ import annotations

# disable bytecode compilation (can cause issues with root-owned cache-files)
import sys
sys.dont_write_bytecode = True

# import koti stuff
from koti import *
from koti.utils import *
from koti.presets import KotiManagerPresets

# import user configs
from modules.ananicy import ananicy
from modules.cpufreq import cpufreq
from modules.fish import fish
from modules.fstab import fstab
from modules.gaming import gaming
from modules.kernel import kernel
from modules.nvidia_undervolting import nvidia_undervolting
from modules.nvme_thermal_throttling import nvme_thermal_throttling
from modules.ollama_aichat import ollama_aichat
from modules.ryzen_undervolting import ryzen_undervolting
from modules.systray import systray
from modules.base import base
from modules.desktop import desktop
from modules.pacman import pacman

from socket import gethostname
host = gethostname()
nvidia = host == "dan"

koti = Koti(
  managers = KotiManagerPresets.arch(PacmanAdapter("sudo -u manuel paru")),
  configs = [
    kernel(root_uuid = shell_output("findmnt -n -o UUID $(stat -c '%m' /)"), cachyos = True),
    pacman(cachyos = True),
    fish(),
    base(swapfile_gb = 12 if host == "dan" else 4),
    fstab(host),
    ananicy(),
    desktop(nvidia = nvidia, autologin = True),
    gaming(),
    systray(ryzen = True, nvidia = nvidia),
    nvidia_undervolting(enabled = nvidia),
    ryzen_undervolting(),
    nvme_thermal_throttling(),
    ollama_aichat(nvidia = nvidia),
    cpufreq(
      min_freq = 2000 if host == "dan" else 1500,
      max_freq = 4500,
      governor = "performance" if host == "dan" else "powersave",
    ),
  ],
)

koti.plan()
confirm("confirm execution")
koti.apply()
print("execution finished.")
