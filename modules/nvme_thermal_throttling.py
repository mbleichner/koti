from inspect import cleandoc

from lib import ConfigItemGroup, ConfigModule, ConfigModuleGroups
from managers.file import File
from managers.pacman import PacmanPackage
from managers.systemd import SystemdUnit


class NvmeThermalThrottlingModule(ConfigModule):

  def provides(self) -> ConfigModuleGroups:
    return ConfigItemGroup(
      PacmanPackage("nvme-cli"),
      File("/etc/systemd/system/nvme-thermal-throttling.service", permissions = 0o444, content = cleandoc('''
        # managed by arch-config
        [Unit]
        Description=NVMe Thermal Throttling
  
        [Service]
        Type=oneshot
        RemainAfterExit=true
        ExecStart=/sbin/nvme set-feature /dev/nvme0 --feature-id=0x10 --value=0x01520160
        
        [Install]
        WantedBy=multi-user.target
     ''')),

      SystemdUnit("nvme-thermal-throttling.service")
    )
