from __future__ import annotations

# Bytecode-Compilation deaktivieren, das macht mit sudo sonst immer Probleme
import sys
sys.dont_write_bytecode = True

from socket import gethostname
from confirm import confirm
from modules.fstab import FstabModule
from shell import shell_output
from core import ArchUpdate
from managers.checkpoint import CheckpointManager
from managers.file import FileManager
from managers.hook import PostHookManager, PreHookManager
from managers.pacman import PacmanAdapter, PacmanPackageManager
from managers.pacman_key import PacmanKeyManager
from managers.swapfile import SwapfileManager
from managers.systemd import SystemdUnitManager
from modules.ananicy import AnanicyModule
from modules.base import BaseModule
from modules.cpufreq import CpuFreqPolicyModule
from modules.desktop import DesktopModule
from modules.fish import FishModule
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
root_uuid = shell_output("findmnt -n -o UUID $(stat -c '%m' /)")

archupdate = ArchUpdate(
  default_confirm_mode = "cautious",
  managers = [
    PreHookManager(),
    SwapfileManager(),
    PacmanKeyManager(),
    PacmanPackageManager(PacmanAdapter("sudo -u manuel paru")),
    FileManager(),
    SystemdUnitManager(),
    PostHookManager(),
    CheckpointManager(),
  ],
  modules = [
    KernelModule(root_uuid = root_uuid, cachyos = True),
    PacmanModule(cachyos = True),
    FishModule(),
    BaseModule(),
    FstabModule(host = host),
    AnanicyModule(),
    DesktopModule(nvidia = nvidia, autologin = True),
    GamingModule(),
    SystrayModule(ryzen = True, nvidia = nvidia),
    NvidiaUndervoltingModule(enabled = nvidia),
    RyzenUndervoltingModule(),
    NvmeThermalThrottlingModule(),
    CpuFreqPolicyModule(
      min_freq = 2000 if host == "dan" else 1500,
      max_freq = 4500,
      governor = "performance" if host == "dan" else "powersave",
    ),
    OllamaAichatModule(nvidia = nvidia),
  ],
)

archupdate.plan()
confirm("execute now?", destructive = True, mode = "paranoid")
archupdate.apply()

print("execution finished successfully")
