from inspect import cleandoc
from typing import Generator

from koti import *


def ryzen_undervolting() -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "Ryzen 5800X3D undervolting",
    provides = [
      Package("ryzen_smu-dkms-git"),
      SystemdUnit("ryzen-undervolting.service"),

      # Quelle: https://github.com/svenlange2/Ryzen-5800x3d-linux-undervolting
      File("/opt/undervolting/ryzen-undervolting.py", source = "files/ryzen-undervolting.py"),

      File("/etc/systemd/system/ryzen-undervolting.service", permissions = "r--", content = cleandoc('''
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
    ]
  )
