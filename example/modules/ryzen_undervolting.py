from inspect import cleandoc
from typing import Generator

from koti import *


def ryzen_undervolting() -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "Ryzen 5800X3D undervolting",
    provides = [
      Package("ryzen_smu-dkms-git"),
      SystemdUnit("ryzen-undervolting.service"),

      File(
        "/opt/undervolting/ryzen-undervolting.py",
        source = "https://raw.githubusercontent.com/svenlange2/Ryzen-5800x3d-linux-undervolting/4c06f511b7132bd2a44bac82fd33c73f9398ea0d/ruv.py",
        permissions = "r--",
      ),

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
