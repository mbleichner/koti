from inspect import cleandoc

from koti import *


def cpufreq(min_freq: int, max_freq: int, governor: str) -> ConfigGroups:
  return ConfigGroup(
    description = "set default cpu frequency range and governor",
    provides = [
      Package("cpupower"),
      File("/etc/default/cpupower", permissions = 0o444, content = cleandoc(f'''
        governor="{governor}"
        min_freq="{min_freq}MHz"
        max_freq="{max_freq}MHz"
     ''')),
    ]
  )


def throttle_after_boot(freq: int) -> ConfigGroups:
  return ConfigGroup(
    description = f"set up cpu throttling to {freq}MHz after boot",
    provides = [
      Package("cpupower"),

      File("/etc/systemd/system/cpu-freq-after-boot.service", permissions = 0o444, content = cleandoc(f'''
        # managed by koti
        [Unit]
        Description=Throttle CPU after boot
  
        [Service]
        Type=simple
        ExecStart=/bin/sh -c "sleep 8 && cpupower frequency-set -u {freq}MHz"
  
        [Install]
        WantedBy=graphical.target
     ''')),

      SystemdUnit("cpu-freq-after-boot.service"),
    ]
  )
