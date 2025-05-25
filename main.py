from __future__ import annotations

# Bytecode-Compilation deaktivieren, das macht mit sudo sonst immer Probleme
import sys

sys.dont_write_bytecode = True

from socket import gethostname
from utils import *
from managers import *
from modules import *

host = gethostname()
nvidia = host == "dan"
root_uuid = shell_output("findmnt -n -o UUID $(stat -c '%m' /)")

archupdate = Core(
  default_confirm_mode = "cautious",
  managers = [
    PreHookManager(),
    PacmanKeyManager(),
    PacmanPackageManager(PacmanAdapter("sudo -u manuel paru")),
    SwapfileManager(),
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
    FstabModule(),
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
print("all done.")
