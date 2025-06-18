from inspect import cleandoc

from koti import *
from modules.base import base, swapfile
from modules.cpufreq import cpufreq, throttle_after_boot
from modules.desktop import desktop
from modules.fish import fish
from modules.gaming import gaming
from modules.kernel import kernel_cachyos, kernel_stock
from modules.ollama_aichat import ollama_aichat
from modules.ryzen_undervolting import ryzen_undervolting
from modules.systray import systray

# Configuration for my Lenovo X13 laptop
lenovo: list[ConfigGroups] = [
  base(),
  cpufreq(min_freq = 1000, max_freq = 4500, governor = "powersave"),
  throttle_after_boot(1500),
  swapfile(4),
  kernel_cachyos(1),
  kernel_stock(2),
  fish(),
  desktop(nvidia = False, autologin = True),
  systray(ryzen = True, nvidia = False),
  gaming(),
  ryzen_undervolting(),
  ollama_aichat(cuda = False),

  ConfigGroup(
    Package("networkmanager"),
    SystemdUnit("wpa_supplicant.service"),
    SystemdUnit("NetworkManager.service"),
  ),

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
