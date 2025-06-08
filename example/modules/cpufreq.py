from inspect import cleandoc

from koti import *


def cpufreq(min_freq: int, max_freq: int, governor: str, throttle_after_boot: bool) -> ConfigGroups:
  return ConfigGroup(
    Package("cpupower"),

    File("/etc/default/cpupower", permissions = 0o444, content = cleandoc(f'''
      governor="{governor}"
      min_freq="{min_freq}MHz"
      max_freq="{max_freq}MHz"
   ''')),

    File("/etc/systemd/system/cpu-freq-after-boot.service", permissions = 0o444, content = cleandoc(f'''
      # managed by koti
      [Unit]
      Description=Throttle CPU after boot
      
      [Service]
      Type=simple
      ExecStart=/bin/sh -c "sleep 8 && cpupower frequency-set -u {min_freq}MHz"
      
      [Install]
      WantedBy=graphical.target
   ''')) if throttle_after_boot else None,

    SystemdUnit("cpu-freq-after-boot.service") if throttle_after_boot else None,
  )
