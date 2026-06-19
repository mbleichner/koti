from inspect import cleandoc

from koti import *
from koti.utils.shell import shell
from modules.base import base
from modules.cpufreq import cpufreq_defaults
from modules.kernel import kernel


# Configuration for my 7700K homelab server
def mserver() -> ConfigDict:
  return {
    **base(aurcache = False),  # avoid self dependency
    **cpufreq_defaults(min_freq = 800, max_freq = 4200, governor = "powersave"),
    **kernel("linux-cachyos-server", sortkey = 1, powersave = True),
    **kernel("linux-cachyos-lts", sortkey = 2, powersave = True),

    Section("swapfile (8GB) and fstab"): (
      Swapfile("/swapfile", 8 * 1024 ** 3),
      File("/etc/fstab", requires = Swapfile("/swapfile"), content = cleandoc('''
        UUID=77abf8d1-814f-4b0f-b3be-0b5f128f2e34  /      ext4  rw,noatime 0 1
        UUID=41E5-985A                             /boot  vfat  rw,defaults 0 2
        /swapfile                                  swap   swap  defaults 0 0
      ''')),
    ),

    Section("firmware and drivers for mserver"): (
      Package("linux-firmware-other"),
      Package("linux-firmware-intel"),
      Package("linux-firmware-realtek"),
    ),

    Section("firewall rules"): PostHookScope(
      File("/usr/local/bin/update-iptables", permissions = "r-x", content = cleandoc(f'''
        #!/bin/bash -ex
        iptables -N FIREWALL || iptables -F FIREWALL                                 # create FIREWALL chain (or flush if already exists)
        iptables -F INPUT       && iptables -I INPUT       -i enp0s31f6 -j FIREWALL  # link FIREWALL chain into INPUT chain
        iptables -F DOCKER-USER && iptables -I DOCKER-USER -i enp0s31f6 -j FIREWALL  # link FIREWALL chain into DOCKER-USER chain
        
        iptables -A FIREWALL -s 192.168.0.0/16    -j RETURN -m comment --comment "local traffic"
        iptables -A FIREWALL -p tcp --dport 22    -j RETURN -m comment --comment "ssh server"
        iptables -A FIREWALL -p tcp --dport 80    -j RETURN -m comment --comment "traefik http"
        iptables -A FIREWALL -p tcp --dport 443   -j RETURN -m comment --comment "traefik https"
        iptables -A FIREWALL -p udp --dport 2456  -j RETURN -m comment --comment "valheim"
        iptables -A FIREWALL -p udp --dport 2457  -j RETURN -m comment --comment "valheim"
        iptables -A FIREWALL -p udp --dport 2458  -j RETURN -m comment --comment "valheim"
        iptables -A FIREWALL -p tcp --dport 7777  -j RETURN -m comment --comment "abiotic"
        iptables -A FIREWALL -p udp --dport 7777  -j RETURN -m comment --comment "abiotic"
        iptables -A FIREWALL -p tcp --dport 7777  -j RETURN -m comment --comment "satisfactory"
        iptables -A FIREWALL -p udp --dport 7777  -j RETURN -m comment --comment "satisfactory"
        iptables -A FIREWALL -p tcp --dport 8888  -j RETURN -m comment --comment "satisfactory"
        iptables -A FIREWALL -p udp --dport 8888  -j RETURN -m comment --comment "satisfactory"
        iptables -A FIREWALL -p udp --dport 21027 -j RETURN -m comment --comment "syncthing"
        iptables -A FIREWALL -p tcp --dport 22000 -j RETURN -m comment --comment "syncthing"
        iptables -A FIREWALL -p udp --dport 22000 -j RETURN -m comment --comment "syncthing"
        
        iptables -A FIREWALL -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
        iptables -A FIREWALL -j DROP
      ''')),

      File("/etc/systemd/system/firewall.service", requires = SystemdUnit("docker.service"), content = cleandoc(f'''
        [Unit]
        Description=custom firewall rules
        Requires=docker.service
        After=docker.service
    
        [Service]
        Type=oneshot
        ExecStart=/usr/local/bin/update-iptables

        [Install]
        WantedBy=multi-user.target
      ''')),

      SystemdUnit("firewall.service"),

      PostHook(
        name = "update-iptables",
        execute = lambda: shell("systemctl daemon-reload && systemctl restart firewall.service"),
      ),
    ),

    Section("borg server"): PostHookScope(
      User("borg", password = False),
      Package("borg"),
      UserHome(username = "borg", homedir = "/home/borg"),
      File("/home/borg/.ssh/authorized_keys", owner = "borg", content = cleandoc(f'''
        ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILHYYC3eJGcl/X9eM8f6BnUtBvekI2ZUzkfLY5ltjPTw manuel@dan
        ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINL1K4/a2LLS6qrB5cNMIyVk6skyhRAVE++tIj6UTL0s manuel@lenovo
        ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKa8TBfPVjdfsMkhki/j3PjOLcNJMV5OMb7sDu6ld6ek manuel@mserver
      ''')),
      PostHook(  # create single shared repo for more efficient deduplication
        name = "create-repo",
        execute = lambda: shell("borg init --encryption=none /home/borg/repo || true", user = "borg")
      )
    ),

    Section("glances monitoring", disabled = True): PostHookScope(
      Package("glances"),
      # optional dependencies (missing ones will get listed in /home/manuel/.local/share/glances/glances.log)
      *Packages("uvicorn", "python-fastapi", "python-docker", "python-netifaces2", "python-dateutil", "python-pylxd"),
      File("/etc/glances/glances.conf", content = cleandoc('''
        [global]
        refresh=5
        check_update=False
        [network]
        show=enp0s31f6,wlp2s0
      ''')),
      SystemdUnit("glances-web.service"),
      PostHook("restart-glances", execute = lambda: shell("systemctl daemon-reload && systemctl restart glances-web.service")),
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

    Section("docker services"): (
      *Packages("docker", "docker-buildx", "docker-compose"),

      SystemdUnit("docker.service"),  # always enable the docker daemon

      Directory("/opt/services", source = "files/services"),

      File("/usr/local/bin/update-docker", permissions = "rwxr-xr-x", content = cleandoc('''
        #!/bin/bash -ex
        docker compose --project-directory /opt/services build
        docker compose --project-directory /opt/services pull
        docker compose --project-directory /opt/services up --quiet-build --quiet-pull --remove-orphans --detach
        docker system prune -f > /dev/null
      ''')),

      PostHook(
        name = "update docker images and services",
        execute = lambda: shell("/usr/local/bin/update-docker"),
      ),

      PostHook(
        name = "download pacoloco .db files",
        # Pacoloco prefetch only works if .db files have been added to the cache, which will not happen if we use
        # the CacheServer setting. As a workaround, we trigger a download of the .db files manually.
        trigger = File("/opt/services/pacoloco.yaml"),
        execute = lambda: shell('''
          curl -s http://pacoloco.fritz.box/repo/archlinux/core/os/x86_64/core.db > /dev/null
          curl -s http://pacoloco.fritz.box/repo/archlinux/extra/os/x86_64/extra.db > /dev/null
          curl -s http://pacoloco.fritz.box/repo/archlinux/multilib/os/x86_64/multilib.db > /dev/null
          curl -s http://pacoloco.fritz.box/repo/cachyos-extra-v3/x86_64_v3/cachyos-extra-v3/cachyos-v3.db > /dev/null
          curl -s http://pacoloco.fritz.box/repo/cachyos-core-v3/x86_64_v3/cachyos-core-v3/cachyos-v3.db > /dev/null
          curl -s http://pacoloco.fritz.box/repo/cachyos-v3/x86_64_v3/cachyos-v3/cachyos-v3.db > /dev/null
          curl -s http://pacoloco.fritz.box/repo/cachyos/x86_64/cachyos/cachyos.db > /dev/null
        '''),
      ),

      Option[str]("/etc/borgmatic/config.yaml/Patterns", value = [
        "R /var/opt/services",
        "! /var/opt/services/pacoloco/cache",
      ]),
    ),
  }
