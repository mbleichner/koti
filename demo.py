from __future__ import annotations

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

arch_update = ArchUpdate()
arch_update.managers += [

]
arch_update.modules += [
  KernelModule(root_uuid = "moep", cachyos = True),
  PacmanModule(cachyos = True),
  FishModule(),
  BaseModule(),
  AnanicyModule(),
  DesktopModule(nvidia = True, autologin = True),
  GamingModule(),
  SystrayModule(ryzen = True, nvidia = True),
  NvidiaUndervoltingModule(),
  RyzenUndervoltingModule(),
  NvmeThermalThrottlingModule(),
  CpuFreqPolicyModule(min_freq = 2000, max_freq = 4500, governor = "performance"),
  OllamaAichatModule(nvidia = True),
]

for phase_idx, phase_managers in enumerate(arch_update.build_execution_order()):
  print(f"Phase {phase_idx + 1}")
  for manager, items in phase_managers:
    print(f"- {manager}:")
    for item in items:
      print(f"  - {item}")

arch_update.execute()
