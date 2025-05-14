from __future__ import annotations

import argparse
# Bytecode-Compilation deaktivieren, das macht mit sudo sonst immer Probleme
import sys
sys.dont_write_bytecode = True

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

parser = argparse.ArgumentParser(
  prog = 'ArchConfig',
)

parser.add_argument(
  'action', default = "plan", choices = ["plan", "apply"],
  help = "plan (show all steps that will be executed, in order)\napply (run all system updates)"
)
parser.add_argument(
  '--cautious', default = False, action = "store_true",
  help = "confirm every possibly destructive operation"
)
parser.add_argument(
  '--paranoid', default = False, action = "store_true",
  help = "confirm every single operation, even non-destructive ones"
)

try:
  args = parser.parse_args()
except:
  parser.print_help()
  sys.exit(1)

host = socket.gethostname()
nvidia = host == "dan"
root_uuid = get_output("findmnt -n -o UUID $(stat -c '%m' /)")

arch_update = ArchUpdate()

arch_update.action = args.action
arch_update.cautious = args.cautious
arch_update.paranoid = args.paranoid

arch_update.modules += [
  KernelModule(root_uuid = root_uuid, cachyos = True),
  PacmanModule(cachyos = True),
  FishModule(),
  BaseModule(),
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
]

if args.action == "plan":
  arch_update.plan()
if args.action == "apply":
  arch_update.apply()
