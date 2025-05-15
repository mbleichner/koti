from inspect import cleandoc

from core import ConfigItemGroup, ConfigModule, ConfigModuleGroups, Options
from managers.file import File
from managers.pacman import PacmanPackage


class SystrayModule(ConfigModule):
  def __init__(self, ryzen: bool, nvidia: bool):
    self.nvidia = nvidia
    self.ryzen = ryzen

  def provides(self) -> ConfigModuleGroups: return ConfigItemGroup(

    Options(confirm_mode = "yolo"),
    PacmanPackage("kdialog"),

    *[  # NVIDIA Skripte
      PacmanPackage("python-pynvml"),
      File("/opt/systray/cpu/summary", permissions = 0o555, content = cleandoc(r'''
          #!/bin/bash
          # managed by arch-config
          CPU_MAX=$(( $(cat /sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq) / 1000 ))
          SMT="$(cat /sys/devices/system/cpu/smt/control)"
          if [[ "$SMT" == "0" || "$SMT" == "off" ]]; then
            CPU_HT=" (HT:off)"
          fi
          echo "CPU: ${CPU_MAX}MHz${CPU_HT}"
          CPU_GOV="$(cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor)"
          echo "gov:${CPU_GOV}"
        ''')),
      systray_dialog("/opt/systray/cpu/dialog", "/opt/systray/cpu/actions"),
      systray_cpu_governor("/opt/systray/cpu/actions/governor-performance", "performance"),
      systray_cpu_governor("/opt/systray/cpu/actions/governor-powersave", "powersave"),
      systray_cpu_freq("/opt/systray/cpu/actions/max-freq-1500mhz", "1500MHz"),
      systray_cpu_freq("/opt/systray/cpu/actions/max-freq-2000mhz", "2000MHz"),
      systray_cpu_freq("/opt/systray/cpu/actions/max-freq-2500mhz", "2500MHz"),
      systray_cpu_freq("/opt/systray/cpu/actions/max-freq-3000mhz", "3000MHz"),
      systray_cpu_freq("/opt/systray/cpu/actions/max-freq-3500mhz", "3500MHz"),
      systray_cpu_freq("/opt/systray/cpu/actions/max-freq-4000mhz", "4000MHz"),
      systray_cpu_freq("/opt/systray/cpu/actions/max-freq-4500mhz", "4500MHz"),
      systray_hyperthreading("/opt/systray/cpu/actions/hyperthreading-on", "on"),
      systray_hyperthreading("/opt/systray/cpu/actions/hyperthreading-off", "off"),
    ] if self.ryzen else None,

    *[  # Ryzen CPU Skripte
      File("/opt/systray/gpu/summary", permissions = 0o555, content = cleandoc(r'''
         #!/usr/bin/python3
         # managed by arch-config
         from pynvml import *
         nvmlInit()
         myGPU = nvmlDeviceGetHandleByIndex(0)
         print("GPU: %iW" % (nvmlDeviceGetPowerManagementLimit(myGPU) / 1000))
         print("+%i/+%i" % (nvmlDeviceGetGpcClkVfOffset(myGPU), nvmlDeviceGetMemClkVfOffset(myGPU)))
      ''')),
      systray_dialog("/opt/systray/gpu/dialog", "/opt/systray/gpu/actions"),
      systray_gpu_power_limit("/opt/systray/gpu/actions/power-limit-160w", 160),
      systray_gpu_power_limit("/opt/systray/gpu/actions/power-limit-180w", 180),
      systray_gpu_power_limit("/opt/systray/gpu/actions/power-limit-200w", 200),
      systray_gpu_power_limit("/opt/systray/gpu/actions/power-limit-220w", 220),
    ] if self.nvidia else None
  )


# ACHTUNG: Beim Aufruf des Skripts per Command Output Widget muss man aufgrund eines
# Bugs einen Parameter an das Skript übergeben, der überhaupt nicht benötigt wird
# z.B. /opt/systray/cpu/dialog moep
def systray_dialog(filename: str, actiondir: str) -> File:
  return File(filename, permissions = 0o555, content = cleandoc(r'''
    #!/bin/bash
    FILES=$(find ACTIONDIR/ -maxdepth 1 -perm -111 -type f -printf "%f\n" | sort)
    OPTIONS=$(echo "$FILES" | awk '{print $1 " " $1;}')
    HEIGHT=$(( 100 + 25 * $(echo "$FILES" | wc -l) ))
    SELECTION=$(kdialog --geometry "300x${HEIGHT}-400-0" --separate-output --menu "Skript auswählen:" $OPTIONS)
    if [[ -n "$SELECTION" ]]; then ACTIONDIR/$SELECTION; fi
  '''.replace("ACTIONDIR", actiondir)))


def systray_cpu_freq(filename: str, freq: str) -> File:
  return File(filename, permissions = 0o555, content = cleandoc(f'''
    #!/bin/bash
    sudo cpupower frequency-set -u {freq}
  '''))


def systray_cpu_governor(filename: str, governor: str) -> File:
  return File(filename, permissions = 0o555, content = cleandoc(f'''
    #!/bin/bash
    sudo cpupower frequency-set -g {governor}
  '''))


def systray_hyperthreading(filename: str, state: str) -> File:
  return File(filename, permissions = 0o555, content = cleandoc(f'''
    #!/bin/bash
    echo {state} | sudo tee /sys/devices/system/cpu/smt/control
  '''))


def systray_gpu_power_limit(filename: str, watt: int) -> File:
  return File(filename, permissions = 0o555, content = cleandoc(f'''
    #!/bin/bash
    sudo nvidia-smi -i 0 -pl {watt}
  '''))
