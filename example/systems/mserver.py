from inspect import cleandoc

from koti import *
from koti.utils.shell import shell
from modules.base import base
from modules.cpu import cpufreq_defaults
from modules.fish import fish
from modules.kernel import kernel


# Configuration for my 7700K homelab server
def mserver() -> ConfigDict:
  return {
    **base(),
    **cpufreq_defaults(min_freq = 800, max_freq = 4200, governor = "powersave"),
    **kernel("linux-cachyos-server", sortkey = 1, powersave = True),
    **kernel("linux-cachyos-lts", sortkey = 2, powersave = True),
    **fish(),

    Section("swapfile (8GB) and fstab"): (
      Swapfile("/swapfile", 8 * 1024 ** 3),
      File("/etc/fstab", requires = Swapfile("/swapfile"), content = cleandoc('''
        UUID=77abf8d1-814f-4b0f-b3be-0b5f128f2e34  /      ext4  rw,noatime 0 1
        UUID=b964a65f-8230-4281-8401-d525b48c2a66  /opt   ext4  rw,noatime 0 1
        UUID=41E5-985A                             /boot  vfat  rw,defaults 0 2
        /swapfile                                  swap   swap  defaults 0 0
      ''')),
    ),

    Section("firmware for mserver"): (
      Package("linux-firmware-other"),
      Package("linux-firmware-intel"),
      Package("linux-firmware-realtek"),
    ),

    Section("networking via systemd-networkd"): (
      SystemdUnit("systemd-networkd.service"),

      File("/etc/systemd/network/20-wired.network", content = cleandoc('''
        [Match]
        Name=enp0s31f6
        
        [Network]
        Address=192.168.1.100/24
        Address=8.8.8.8/24
        Address=8.8.4.4/24
        Gateway=192.168.1.1
        DNS=192.168.1.1
      ''')),

      File("/etc/resolv.conf", content = cleandoc('''
        nameserver 192.168.1.100
        nameserver 192.168.1.1
        search fritz.box
        options timeout:3
      ''')),
    ),

    Section("docker and services"): (
      User("manuel"),
      SystemdUnit("docker.service"),
      Directory("/opt/services", source = "files/services"),
      File("/usr/local/bin/update-docker", permissions = "rwxr-xr-x", content = cleandoc('''
        #!/bin/bash -e
        docker compose --project-directory /opt/services pull
        docker compose --project-directory /opt/services up -d
      ''')),
      PostHook(
        name = f"docker compose up",
        trigger = Directory("/opt/services"),
        execute = lambda: shell(f"docker compose --project-directory /opt/services up -d --remove-orphans")
      ),
      PostHook(
        'download pacoloco .db files',
        # Pacoloco prefetch only works if .db files have been added to the cache, which will not happen if we use
        # the CacheServer setting. As a workaround, we trigger a download of the .db files manually.
        trigger = Directory("/opt/services"),
        execute = lambda: shell('''
          curl http://pacoloco.fritz.box/repo/archlinux/core/os/x86_64/core.db > /dev/null
          curl http://pacoloco.fritz.box/repo/archlinux/extra/os/x86_64/extra.db > /dev/null
          curl http://pacoloco.fritz.box/repo/archlinux/multilib/os/x86_64/multilib.db > /dev/null
          curl http://pacoloco.fritz.box/repo/cachyos-extra-v3/x86_64_v3/cachyos-extra-v3/cachyos-v3.db > /dev/null
          curl http://pacoloco.fritz.box/repo/cachyos-core-v3/x86_64_v3/cachyos-core-v3/cachyos-v3.db > /dev/null
          curl http://pacoloco.fritz.box/repo/cachyos-v3/x86_64_v3/cachyos-v3/cachyos-v3.db > /dev/null
          curl http://pacoloco.fritz.box/repo/cachyos/x86_64/cachyos/cachyos.db > /dev/null
        '''),
      ),
    ),
  }
