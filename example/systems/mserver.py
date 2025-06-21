from inspect import cleandoc

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
      identifier = f"docker compose {composefile.identifier}",
      execute = lambda: shell(f"docker compose -f {composefile} up -d --force-recreate --remove-orphans")
    ),
  )


# Configuration for my 7700K homelab server
mserver: list[ConfigGroups] = [
  base(),
  cpufreq(min_freq = 800, max_freq = 4200, governor = "powersave"),
  swapfile(8),
  kernel_lts(1),
  kernel_stock(2),
  fish(),

  ConfigGroup(
    description = "fstab",
    confirm_mode = "paranoid",
    requires = [
      Swapfile("/swapfile"),
    ],
    provides = [
      File("/etc/fstab", permissions = 0o444, content = cleandoc('''
        # managed by koti
        UUID=77abf8d1-814f-4b0f-b3be-0b5f128f2e34  /      ext4  rw,noatime 0 1
        UUID=b964a65f-8230-4281-8401-d525b48c2a66  /opt   ext4  rw,noatime 0 1
        UUID=41E5-985A                             /boot  vfat  rw,defaults 0 2
        /swapfile                                  swap   swap  defaults 0 0
      ''')),
    ]
  ),

  ConfigGroup(
    description = "networking via systemd-networkd",
    confirm_mode = "paranoid",
    provides = [
      SystemdUnit("systemd-networkd.service"),

      File("/etc/systemd/network/20-wired.network", permissions = 0o444, content = cleandoc('''
        [Match]
        Name=enp0s31f6
        
        [Network]
        Address=192.168.1.100/24
        Address=8.8.8.8/24
        Address=8.8.4.4/24
        Gateway=192.168.1.1
        DNS=192.168.1.1
      ''')),

      File("/etc/resolv.conf", permissions = 0o444, content = cleandoc('''
        nameserver 192.168.1.100
        nameserver 192.168.1.1
        search fritz.box
        options timeout:3
      ''')),
    ]
  ),

  ConfigGroup(
    description = "system update script",
    confirm_mode = "yolo",
    provides = [
      File("/home/manuel/system-update", permissions = 0o555, content = cleandoc('''
        #!/bin/bash -e
        arch-update
        echo
        for DIR in homeassistant nextcloud pihole pyanodon-mapshot pacoloco traefik; do
          cd /opt/$DIR && sudo docker compose pull && sudo docker compose up -d
        done
      ''')),
    ]
  ),

  ConfigGroup(
    description = "docker and services",
    confirm_mode = "paranoid",
    provides = [
      Package("docker"),
      Package("docker-compose"),
      Package("containerd"),
      SystemdUnit("docker.service"),

      *DockerComposeService(
        File("/opt/traefik/docker-compose.yml", permissions = 0o444, content_from_file = "docker/traefik/docker-compose.yml"),
      ),

      *DockerComposeService(
        File("/opt/nextcloud/docker-compose.yml", permissions = 0o444, content_from_file = "docker/nextcloud/docker-compose.yml"),
      ),

      *DockerComposeService(
        File("/opt/homeassistant/docker-compose.yml", permissions = 0o444, content_from_file = "docker/homeassistant/docker-compose.yml"),
      ),

      *DockerComposeService(
        File("/opt/pihole/docker-compose.yml", permissions = 0o444, content_from_file = "docker/pihole/docker-compose.yml"),
      ),

      *DockerComposeService(
        File("/opt/pyanodon-mapshot/docker-compose.yml", permissions = 0o444, content_from_file = "docker/pyanodon-mapshot/docker-compose.yml"),
      ),

      *DockerComposeService(
        File("/opt/pacoloco/docker-compose.yml", permissions = 0o444, content_from_file = "docker/pacoloco/docker-compose.yml"),
        File("/opt/pacoloco/pacoloco.yaml", permissions = 0o444, content_from_file = "docker/pacoloco/pacoloco.yaml"),
      ),
    ]
  ),
]
