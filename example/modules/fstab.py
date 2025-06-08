from inspect import cleandoc
from socket import gethostname

from koti import *


def fstab() -> ConfigGroups:
  host = gethostname()
  return ConfigGroup(
    ConfirmMode("paranoid"),
    Requires(Swapfile("/swapfile")),

    File("/etc/fstab", permissions = 0o444, content = cleandoc('''
      # managed by koti
      UUID=3409a847-0bd6-43e4-96fd-6e8be4e3c58d  /             ext4  rw,noatime 0 1
      UUID=AF4E-18BD                             /boot         vfat  rw,defaults 0 2
      UUID=CCA2A808A2A7F55C                      /mnt/windows  ntfs  rw,x-systemd.automount 0 0
      UUID=c0b79d2c-5a0a-4f82-8fab-9554344159a5  /home/shared  ext4  rw,noatime 0 1
      /swapfile                                  swap          swap  defaults 0 0
    ''')) if host == "dan" else None,

    File("/etc/fstab", permissions = 0o444, content = cleandoc('''
      # managed by koti
      UUID=79969cb9-9b6e-48e2-a672-4aee50f04c56  /      ext4  rw,noatime 0 1
      UUID=1CA6-490D                             /boot  vfat  rw,defaults 0 2
      /swapfile                                  swap   swap  defaults 0 0
    ''')) if host == "lenovo" else None,
  )
