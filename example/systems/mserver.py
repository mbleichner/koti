from inspect import cleandoc

from koti import *
from systems.common import common

# Configuration for my 7700K homelab server
mserver: list[ConfigGroups] = [
  *common(cachyos_kernel = False, swapfile_gb = 8, min_freq = 1000, max_freq = 4200, governor = "powersave"),

  File("/etc/network/interfaces", permissions = 0o444, content = cleandoc('''
    # managed by koti

    auto lo
    iface lo inet loopback

    auto enp0s31f6
    iface enp0s31f6 inet static
      address 192.168.1.100/24
      gateway 192.168.1.1

    # Chromecast verwendet hardcoded die Google-Server, also hijacken wir die hier die IP-Adressen.
    # In der Fritzbox ist eingetragen, dass 8.8.8.8 und 8.8.4.4 hierher umgeleitet werden. (Netzwerk -> statische Routen)
    iface enp0s31f6 inet static
      address 8.8.8.8/32
    iface enp0s31f6 inet static
      address 8.8.4.4/32
  '''))
]
