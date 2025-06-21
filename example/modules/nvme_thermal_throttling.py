from inspect import cleandoc

from koti import *


def nvme_thermal_throttling() -> ConfigGroups:
  return ConfigGroup(
    name = "nvme_thermal_throttling",
    provides = [
      Package("nvme-cli"),
      SystemdUnit("nvme-thermal-throttling.service"),

      File("/etc/systemd/system/nvme-thermal-throttling.service", permissions = 0o444, content = cleandoc('''
        # managed by koti
        [Unit]
        Description=NVMe Thermal Throttling
  
        [Service]
        Type=oneshot
        RemainAfterExit=true
        ExecStart=/sbin/nvme set-feature /dev/nvme0 --feature-id=0x10 --value=0x01520160
        
        [Install]
        WantedBy=multi-user.target
     ''')),
    ]
  )
