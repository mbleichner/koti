from inspect import cleandoc

from koti import *


def ryzen_undervolting() -> ConfigGroups:
  return ConfigGroup(
    Package("ryzen_smu-dkms-git"),

    # Quelle: https://github.com/svenlange2/Ryzen-5800x3d-linux-undervolting
    File("/opt/undervolting/ryzen-undervolting.py", permissions = 0o444, content_from_file = "files/ryzen-undervolting.py"),

    File("/etc/systemd/system/ryzen-undervolting.service", permissions = 0o444, content = cleandoc('''
      # managed by koti
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
