from inspect import cleandoc

from koti import *
from modules.docker import docker
from systems.common import common

# Configuration for my 7700K homelab server
mserver: list[ConfigGroups] = [
  *common(cachyos_kernel = False, swapfile_gb = 8, min_freq = 800, max_freq = 4000, governor = "powersave", throttle_after_boot = False),
  docker(),

  ConfigGroup(
    ConfirmMode("paranoid"),
    Requires(Swapfile("/swapfile")),
    File("/etc/fstab", permissions = 0o444, content = cleandoc('''
    # managed by koti
    UUID=77abf8d1-814f-4b0f-b3be-0b5f128f2e34  /      ext4  rw,noatime 0 1
    UUID=b964a65f-8230-4281-8401-d525b48c2a66  /opt   ext4  rw,noatime 0 1
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

    File("/etc/NetworkManager/system-connections/LAN.nmconnection", permissions = 0o444, content = cleandoc('''
      # managed by koti
      [connection]
      id=LAN
      uuid=e9c1c826-bc30-355d-86ae-2a3d3ff40aec
      type=ethernet
      autoconnect-priority=-999
      interface-name=enp0s31f6
      timestamp=1749381574
      
      [ethernet]
      
      [ipv4]
      address1=192.168.1.100/24
      address2=8.8.8.8/32
      address3=8.8.4.4/32
      dns=192.168.1.1;
      dns-search=fritz.box;
      gateway=192.168.1.1
      method=manual
      
      [ipv6]
      addr-gen-mode=default
      method=auto
      
      [proxy]
    ''')),
  )
]
