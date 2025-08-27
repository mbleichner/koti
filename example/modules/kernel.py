from inspect import cleandoc

from koti import *
from koti.utils import shell_output

root_uuid = shell_output("findmnt -n -o UUID $(stat -c '%m' /)")

kernel_params = "console=tty1 loglevel=3 nowatchdog zswap.enabled=1"


def kernel_cachyos(sortkey: int) -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "CachyOS kernel + systemd-boot entry",
    tags = ["CRITICAL"],
    requires = [File("/etc/pacman.conf")],
    provides = [
      *Packages("linux-cachyos", "linux-cachyos-headers"),
      *SystemdBootLoader(
        filename = "/boot/loader/entries/arch-cachyos.conf",
        description = "Arch Linux with CachyOS Kernel",
        kernel = "linux-cachyos",
        sortkey = sortkey
      ),
    ]
  )


def kernel_stock(sortkey: int) -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "Arch kernel + systemd-boot entry",
    tags = ["CRITICAL"],
    provides = [
      *Packages("linux", "linux-headers"),
      *SystemdBootLoader(
        filename = "/boot/loader/entries/arch-stock.conf",
        description = "Arch Linux with Stock Kernel",
        kernel = "linux",
        sortkey = sortkey
      ),
    ]
  )


def kernel_lts(sortkey: int) -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "Arch LTS kernel + systemd-boot entry",
    tags = ["CRITICAL"],
    provides = [
      *Packages("linux-lts", "linux-lts-headers"),
      *SystemdBootLoader(
        filename = "/boot/loader/entries/arch-lts.conf",
        description = "Arch Linux with LTS Kernel",
        kernel = "linux-lts",
        sortkey = sortkey
      ),
    ]
  )


# noinspection PyPep8Naming
def SystemdBootLoader(filename: str, description: str, kernel: str, sortkey: int) -> Generator[File]:
  yield File(filename, permissions = "r-x", content = cleandoc(f'''
    title    {description}
    linux    /vmlinuz-{kernel}
    initrd   /initramfs-{kernel}.img
    options  root=UUID={root_uuid} rw {kernel_params}
    sort-key {sortkey}
  '''))
  yield File(filename.replace(".conf", "-fallback.conf"), permissions = "r-x", content = cleandoc(f'''
    title    {description} (Fallback)
    linux    /vmlinuz-{kernel}
    initrd   /initramfs-{kernel}-fallback.img
    options  root=UUID={root_uuid} rw
    sort-key {sortkey + 80}
  '''))
