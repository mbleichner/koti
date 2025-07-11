from inspect import cleandoc
from typing import Generator

from koti import *
from koti.utils import shell_output

root_uuid = shell_output("findmnt -n -o UUID $(stat -c '%m' /)")

kernel_params = "console=tty1 loglevel=3 nowatchdog zswap.enabled=1"


def kernel_cachyos(sortkey: int) -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "CachyOS kernel + systemd-boot entry",
    confirm_mode = "paranoid",
    requires = [
      File("/etc/pacman.conf"),
    ],
    provides = [
      *Packages("linux-cachyos", "linux-cachyos-headers"),
      File("/boot/loader/entries/arch-cachyos.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by koti
        title    Arch Linux with CachyOS Kernel
        linux    /vmlinuz-linux-cachyos
        initrd   /initramfs-linux-cachyos.img
        options  root=UUID={root_uuid} rw {kernel_params}
        sort-key {sortkey}
      ''')),
      File("/boot/loader/entries/arch-cachyos-fallback.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by koti
        title    Arch Linux with CachyOS Kernel (Fallback)
        linux    /vmlinuz-linux-cachyos
        initrd   /initramfs-linux-cachyos-fallback.img
        options  root=UUID={root_uuid} rw
        sort-key {sortkey + 80}
      ''')),
    ]
  )


def kernel_stock(sortkey: int) -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "Arch kernel + systemd-boot entry",
    confirm_mode = "paranoid",
    provides = [
      *Packages("linux", "linux-headers"),
      File("/boot/loader/entries/arch-stock.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by koti
        title    Arch Linux with Stock Kernel
        linux    /vmlinuz-linux
        initrd   /initramfs-linux.img
        options  root=UUID={root_uuid} rw {kernel_params}
        sort-key {sortkey}
      ''')),
      File("/boot/loader/entries/arch-stock-fallback.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by koti
        title    Arch Linux with Stock Kernel (Fallback)
        linux    /vmlinuz-linux
        initrd   /initramfs-linux-fallback.img
        options  root=UUID={root_uuid} rw
        sort-key {sortkey + 80}
      ''')),
    ]
  )


def kernel_lts(sortkey: int) -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "Arch LTS kernel + systemd-boot entry",
    confirm_mode = "paranoid",
    provides = [
      *Packages("linux-lts", "linux-lts-headers"),
      File("/boot/loader/entries/arch-lts.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by koti
        title    Arch Linux with LTS Kernel
        linux    /vmlinuz-linux-lts
        initrd   /initramfs-linux-lts.img
        options  root=UUID={root_uuid} rw {kernel_params}
        sort-key {sortkey}
      ''')),
      File("/boot/loader/entries/arch-lts-fallback.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by koti
        title    Arch Linux with LTS Kernel (Fallback)
        linux    /vmlinuz-linux-lts
        initrd   /initramfs-linux-lts-fallback.img
        options  root=UUID={root_uuid} rw
        sort-key {sortkey + 80}
      ''')),
    ]
  )
