from inspect import cleandoc

from koti import *


def fstab(host: str) -> ConfigGroups:
  return ConfigGroup(

    ConfirmMode("paranoid"),
    Requires(Swapfile("/swapfile")),

    File("/etc/fstab", permissions = 0o444, content = cleandoc('''
      # managed by koti
      # <file system> <dir> <type> <options> <dump> <pass>
      UUID=3409a847-0bd6-43e4-96fd-6e8be4e3c58d  /             ext4  rw,noatime 0 1
      UUID=AF4E-18BD                             /boot         vfat  rw,noatime,fmask=0022,dmask=0022,codepage=437,iocharset=ascii,shortname=mixed,utf8,errors=remount-ro 0 2
      UUID=CCA2A808A2A7F55C                      /mnt/windows  ntfs  rw,x-systemd.automount 0 0
      UUID=c0b79d2c-5a0a-4f82-8fab-9554344159a5  /home/shared  ext4  rw,noatime 0 1
      /swapfile                                  swap          swap  defaults 0 0
    ''')) if host == "dan" else None,
  )
