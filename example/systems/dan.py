from inspect import cleandoc

from koti import *
from modules.desktop import desktop
from modules.gaming import gaming
from modules.nvidia_undervolting import nvidia_undervolting
from modules.nvme_thermal_throttling import nvme_thermal_throttling
from modules.ollama_aichat import ollama_aichat
from modules.ryzen_undervolting import ryzen_undervolting
from modules.systray import systray
from systems.common import common

# Configuration for my DAN A4-SFX gaming machine (Ryzen 5800X3D, RTX3080)
dan: list[ConfigGroups] = [
  *common(cachyos_kernel = True, swapfile_gb = 12, min_freq = 2000, max_freq = 4500, governor = "performance"),
  desktop(nvidia = True, autologin = True),
  systray(ryzen = True, nvidia = True),
  gaming(),
  nvme_thermal_throttling(),
  nvidia_undervolting(),
  ryzen_undervolting(),
  ollama_aichat(cuda = True),

  ConfigGroup(
    ConfirmMode("paranoid"),
    Requires(Swapfile("/swapfile")),
    File("/etc/fstab", permissions = 0o444, content = cleandoc('''
      # managed by koti
      UUID=3409a847-0bd6-43e4-96fd-6e8be4e3c58d  /             ext4  rw,noatime 0 1
      UUID=AF4E-18BD                             /boot         vfat  rw,defaults 0 2
      UUID=CCA2A808A2A7F55C                      /mnt/windows  ntfs  rw,x-systemd.automount 0 0
      UUID=c0b79d2c-5a0a-4f82-8fab-9554344159a5  /home/shared  ext4  rw,noatime 0 1
      /swapfile                                  swap          swap  defaults 0 0
    ''')),
  )
]
