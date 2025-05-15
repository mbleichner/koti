from inspect import cleandoc

from lib import ConfigItemGroup, ConfigModule, ConfigModuleGroups
from managers.file import File
from managers.pacman import PacmanPackage
from managers.systemd import SystemdUnit


class RyzenUndervoltingModule(ConfigModule):

  def provides(self) -> ConfigModuleGroups:
    return ConfigItemGroup(

      PacmanPackage("ryzen_smu-dkms-git"),

      File(
        "/opt/undervolting/ryzen-undervolting.py",
        permissions = 0o444, path = "files/ryzen-undervolting.py"
        # Quelle: https://github.com/svenlange2/Ryzen-5800x3d-linux-undervolting
      ),

      File("/etc/systemd/system/ryzen-undervolting.service", permissions = 0o444, content = cleandoc('''
        # managed by arch-config
        [Unit]
        Description=Ryzen Undervolting
        
        [Service]
        Type=oneshot
        RemainAfterExit=true
        WorkingDirectory=/opt/undervolting
        ExecStart=/usr/bin/python3 ryzen-undervolting.py --corecount 8 --offset -30
        
        [Install]
        WantedBy=multi-user.target
      ''')),

      SystemdUnit("ryzen-undervolting.service")
    )
