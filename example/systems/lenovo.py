from inspect import cleandoc

from koti import *
from modules.desktop import desktop
from modules.gaming import gaming
from modules.ollama_aichat import ollama_aichat
from modules.ryzen_undervolting import ryzen_undervolting
from modules.systray import systray
from systems.common import common

# Configuration for my Lenovo X13 laptop
lenovo: list[ConfigGroups] = [
  *common(cachyos_kernel = True, swapfile_gb = 4, min_freq = 1500, max_freq = 4500, governor = "powersave"),
  desktop(nvidia = False, autologin = True),
  systray(ryzen = True, nvidia = False),
  gaming(),
  ryzen_undervolting(),
  ollama_aichat(cuda = False),

  ConfigGroup(
    ConfirmMode("paranoid"),
    Requires(Swapfile("/swapfile")),
    File("/etc/fstab", permissions = 0o444, content = cleandoc('''
      # managed by koti
      UUID=79969cb9-9b6e-48e2-a672-4aee50f04c56  /      ext4  rw,noatime 0 1
      UUID=1CA6-490D                             /boot  vfat  rw,defaults 0 2
      /swapfile                                  swap   swap  defaults 0 0
    ''')),
  )
]
