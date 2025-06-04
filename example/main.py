from __future__ import annotations

# Bytecode-Compilation deaktivieren, das macht mit sudo sonst immer Probleme
import sys
sys.dont_write_bytecode = True

from koti import *
from koti.utils import *
from socket import gethostname
from koti.presets import KotiManagerPresets
from modules.ananicy import AnanicyModule
from modules.base import BaseModule
from modules.cpufreq import CpuFreqPolicyModule
from modules.desktop import DesktopModule
from modules.fish import FishModule
from modules.fstab import FstabModule
from modules.gaming import GamingModule
from modules.kernel import KernelModule
from modules.nvidia_undervolting import NvidiaUndervoltingModule
from modules.nvme_thermal_throttling import NvmeThermalThrottlingModule
from modules.ollama_aichat import OllamaAichatModule
from modules.pacman import PacmanModule
from modules.ryzen_undervolting import RyzenUndervoltingModule
from modules.systray import SystrayModule

host = gethostname()
nvidia = host == "dan"

koti = Koti(
  managers = KotiManagerPresets.arch(PacmanAdapter("sudo -u manuel paru")),
  modules = [
    KernelModule(root_uuid = shell_output("findmnt -n -o UUID $(stat -c '%m' /)"), cachyos = True),
    PacmanModule(cachyos = True),
    FishModule(),
    BaseModule(swapfile_gb = 12 if host == "dan" else 4),
    FstabModule(),
    AnanicyModule(),
    DesktopModule(nvidia = nvidia, autologin = True, evsieve = host == "dan"),
    GamingModule(),
    SystrayModule(ryzen = True, nvidia = nvidia),
    NvidiaUndervoltingModule(enabled = nvidia),
    RyzenUndervoltingModule(),
    NvmeThermalThrottlingModule(),
    OllamaAichatModule(nvidia = nvidia),
    CpuFreqPolicyModule(
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
