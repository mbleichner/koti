from inspect import cleandoc
from typing import Generator

from koti import *
from koti.items.hooks import PostHookTriggerScope
from koti.utils import shell
from modules.base import base, swapfile
from modules.cpufreq import cpufreq
from modules.fish import fish
from modules.kernel import kernel_lts, kernel_stock


def DockerComposeService(composefile: File, *other: ConfigItem) -> list[ConfigItem]:
  return PostHookTriggerScope(
    composefile,
    *other,
    PostHook(
      name = f"docker compose {composefile.filename}",
      execute = lambda: shell(f"docker compose -f {composefile.filename} up -d --force-recreate --remove-orphans")
    ),
  )


# Configuration for my 7700K homelab server
def mserver() -> Generator[ConfigGroup | None]:
  yield from base()
  yield from cpufreq(min_freq = 800, max_freq = 4200, governor = "powersave")
  yield from swapfile(8)
  yield from kernel_lts(1)
  yield from kernel_stock(2)
  yield from fish()

  yield ConfigGroup(
    description = "firmware",
    provides = [
      Package("linux-firmware-other"),
      Package("linux-firmware-intel"),
      Package("linux-firmware-realtek"),
    ]
  )

  yield ConfigGroup(
    description = "fstab (mserver)",
    tags = ["CRITICAL"],
    requires = [
      Swapfile("/swapfile"),
    ],
    provides = [
      File("/etc/fstab", permissions = "r--", content = cleandoc('''
        UUID=77abf8d1-814f-4b0f-b3be-0b5f128f2e34  /      ext4  rw,noatime 0 1
        UUID=b964a65f-8230-4281-8401-d525b48c2a66  /opt   ext4  rw,noatime 0 1
        UUID=41E5-985A                             /boot  vfat  rw,defaults 0 2
        /swapfile                                  swap   swap  defaults 0 0
      ''')),
    ]
  )

  yield ConfigGroup(
    description = "networking via systemd-networkd",
    tags = ["CRITICAL"],
    provides = [
      SystemdUnit("systemd-networkd.service"),

      File("/etc/systemd/network/20-wired.network", permissions = "r--", content = cleandoc('''
        [Match]
        Name=enp0s31f6
        
        [Network]
        Address=192.168.1.100/24
        Address=8.8.8.8/24
        Address=8.8.4.4/24
        Gateway=192.168.1.1
        DNS=192.168.1.1
      ''')),

      File("/etc/resolv.conf", permissions = "r--", content = cleandoc('''
        nameserver 192.168.1.100
        nameserver 192.168.1.1
        search fritz.box
        options timeout:3
      ''')),
    ]
  )

  yield ConfigGroup(
    description = "docker-update script",
    provides = [
      File("/usr/local/bin/docker-update", permissions = "r-x", content = cleandoc('''
        #!/bin/bash -e
        for DIR in homeassistant nextcloud pihole pyanodon-mapshot pacoloco traefik; do
          cd /opt/$DIR && sudo docker compose pull && sudo docker compose up -d
        done
      ''')),
    ]
  )

  yield ConfigGroup(
    description = "docker and services",
    tags = ["CRITICAL"],
    provides = [
      Package("docker"),
      Package("docker-compose"),
      Package("containerd"),
      SystemdUnit("docker.service"),

      *DockerComposeService(
        File("/opt/traefik/docker-compose.yml", permissions = "r--", source = "files/traefik/docker-compose.yml"),
      ),

      *DockerComposeService(
        File("/opt/nextcloud/docker-compose.yml", permissions = "r--", source = "files/nextcloud/docker-compose.yml"),
      ),

      *DockerComposeService(
        File("/opt/homeassistant/docker-compose.yml", permissions = "r--", source = "files/homeassistant/docker-compose.yml"),
      ),

      *DockerComposeService(
        File("/opt/pihole/docker-compose.yml", permissions = "r--", source = "files/pihole/docker-compose.yml"),
      ),

      *DockerComposeService(
        File("/opt/pyanodon-mapshot/docker-compose.yml", permissions = "r--", source = "files/pyanodon-mapshot/docker-compose.yml"),
      ),

      *DockerComposeService(
        File("/opt/pacoloco/docker-compose.yml", permissions = "r--", source = "files/pacoloco/docker-compose.yml"),
        File("/opt/pacoloco/pacoloco.yaml", permissions = "r--", source = "files/pacoloco/pacoloco.yaml"),
      ),
    ]
  )
