from __future__ import annotations

import socket

from main import ArchUpdate
from modules.ananicy import AnanicyModule
from modules.base import BaseModule
from modules.cpu_freq_policy import CpuFreqPolicyModule
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
from utils import get_output

host = socket.gethostname()
nvidia = host == "dan"
root_uuid = get_output("findmnt -n -o UUID $(stat -c '%m' /)")

arch_update = ArchUpdate()

arch_update.modules += [
  KernelModule(root_uuid = root_uuid, cachyos = True),
  PacmanModule(cachyos = True),
  FishModule(),
  BaseModule(),
  AnanicyModule(),
  DesktopModule(nvidia = nvidia, autologin = True),
  GamingModule(),
  SystrayModule(ryzen = True, nvidia = nvidia),
  NvidiaUndervoltingModule(),
  RyzenUndervoltingModule(),
  NvmeThermalThrottlingModule(),
  CpuFreqPolicyModule(
    min_freq = 2000 if host == "dan" else 1500,
    max_freq = 4500,
    governor = "performance" if host == "dan" else "powersave",
  ),
  OllamaAichatModule(nvidia = nvidia),
]

for phase_idx, phase_managers in enumerate(arch_update.build_execution_order()):
  print(f"Phase {phase_idx + 1}")
  for manager, items in phase_managers:
    print(f"- {manager}:")
    for item in items:
      print(f"  - {item}")

arch_update.execute()
