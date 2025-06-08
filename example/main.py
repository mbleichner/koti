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
from modules.docker import docker
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


def common(cachyos_kernel: bool, swapfile_gb: int, min_freq: int, max_freq: int, governor: str) -> ConfigGroups: return [
  kernel(cachyos_kernel = cachyos_kernel),
  pacman(cachyos_kernel = cachyos_kernel),
  base(swapfile_gb = swapfile_gb),
  fish(),
  fstab(),
  ananicy(),
  cpufreq(
    min_freq = min_freq,
    max_freq = max_freq,
    governor = governor,
  ),
]


koti = Koti(
  managers = KotiManagerPresets.arch(PacmanAdapter("sudo -u manuel paru")),
  configs = {
    "dan": [
      *common(cachyos_kernel = True, swapfile_gb = 12, min_freq = 2000, max_freq = 4500, governor = "performance"),
      desktop(nvidia = True, autologin = True),
      gaming(),
      systray(ryzen = True, nvidia = True),
      nvme_thermal_throttling(),
      nvidia_undervolting(),
      ryzen_undervolting(),
      ollama_aichat(cuda = True),
    ],
    "lenovo": [
      *common(cachyos_kernel = True, swapfile_gb = 4, min_freq = 1500, max_freq = 4500, governor = "powersave"),
      desktop(nvidia = False, autologin = True),
      gaming(),
      systray(ryzen = True, nvidia = False),
      ryzen_undervolting(),
      ollama_aichat(cuda = False),
    ],
    "mserver": [
      *common(cachyos_kernel = False, swapfile_gb = 8, min_freq = 1000, max_freq = 4200, governor = "powersave"),
      docker(),
    ]
  }[gethostname()],
)

koti.plan()
confirm("confirm execution")
koti.apply()
print("execution finished.")
