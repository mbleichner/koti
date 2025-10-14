from inspect import cleandoc

from koti import *


def ryzen_undervolting() -> ConfigDict:
  return {
    Section("Ryzen 5800X3D undervolting"): (
      Package("ryzen_smu-dkms-git"),

      File(
        "/opt/undervolting/ryzen-undervolting.py",
        source = "https://raw.githubusercontent.com/svenlange2/Ryzen-5800x3d-linux-undervolting/4c06f511b7132bd2a44bac82fd33c73f9398ea0d/ruv.py",
      ),

      File("/etc/systemd/system/ryzen-undervolting.service", content = cleandoc('''
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

      SystemdUnit("ryzen-undervolting.service"),
    )
  }
