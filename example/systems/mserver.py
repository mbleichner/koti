from inspect import cleandoc

from koti import *
from modules.docker import docker
from systems.common import common

# Configuration for my 7700K homelab server
mserver: list[ConfigGroups] = [
  *common(cachyos_kernel = False, swapfile_gb = 8, min_freq = 1000, max_freq = 4200, governor = "powersave"),
  docker(),

  ConfigGroup(
    ConfirmMode("paranoid"),
    Requires(Swapfile("/swapfile")),
    File("/etc/fstab", permissions = 0o444, content = cleandoc('''
    # managed by koti
    UUID=77abf8d1-814f-4b0f-b3be-0b5f128f2e34  /      ext4  rw,noatime 0 1
    UUID=41E5-985A                             /boot  vfat  rw,defaults 0 2
    /swapfile                                  swap   swap  defaults 0 0
  ''')),
  ),

  ConfigGroup(
    "networking",

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
    ''')),

    File("/etc/resolv.conf", permissions = 0o444, content = cleandoc('''
      # managed by koti
      domain fritz.box
      search fritz.box
      
      # Lokal ist ein DNS-Server installiert, aber den nutzen wir hier lieber nicht, sonst gibts Probleme, wenn PiHole down ist.
      # Google darf hier auch nicht benutzt werden, weil wir die Adressen 8.8.8.8 und 8.8.4.4 hijacken (siehe /etc/network/interfaces)
      nameserver 192.168.1.1
    ''')),
  )
]
