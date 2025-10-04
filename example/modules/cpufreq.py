from inspect import cleandoc
from typing import Generator

from koti import *


def cpufreq(min_freq: int, max_freq: int, governor: str) -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "set default cpu frequency range and governor",
    provides = [
      Package("cpupower"),
      File("/etc/default/cpupower", content = cleandoc(f'''
        governor="{governor}"
        min_freq="{min_freq}MHz"
        max_freq="{max_freq}MHz"
     ''')),
    ]
  )


def throttle_after_boot(freq: int) -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = f"throttle CPU to {freq}MHz after boot",
    provides = [
      Package("cpupower"),

      File("/etc/systemd/system/cpu-freq-after-boot.service", content = cleandoc(f'''
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
