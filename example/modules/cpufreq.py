from inspect import cleandoc

from koti import *


class CpuFreqPolicyModule(ConfigModule):
  def __init__(self, min_freq: int, max_freq: int, governor: str):
    self.governor = governor
    self.max_freq = max_freq
    self.min_freq = min_freq

  def provides(self) -> ConfigModuleGroups:
    return ConfigItemGroup(
      Package("cpupower"),
      File("/etc/default/cpupower", permissions = 0o444, content = cleandoc(f'''
        governor="{self.governor}"
        min_freq="{self.min_freq}MHz"
        max_freq="{self.max_freq}MHz"
     ''')),

      File("/etc/systemd/system/cpu-freq-after-boot.service", permissions = 0o444, content = cleandoc(f'''
        # managed by koti
        [Unit]
        Description=Throttle CPU after boot
        
        [Service]
        Type=simple
        ExecStart=/bin/sh -c "sleep 8 && cpupower frequency-set -u {self.min_freq}MHz"
        
        [Install]
        WantedBy=graphical.target
     ''')),

      SystemdUnit("cpu-freq-after-boot.service")
    )
