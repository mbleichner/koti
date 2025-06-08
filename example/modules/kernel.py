from inspect import cleandoc

from koti import *
from koti.utils import shell_output


def kernel(cachyos_kernel: bool) -> ConfigGroups:
  root_uuid = shell_output("findmnt -n -o UUID $(stat -c '%m' /)")
  return [
    ConfigGroup(
      ConfirmMode("paranoid"),
      Requires(
        Package("cachyos-keyring"),
        Package("cachyos-mirrorlist"),
        Package("cachyos-v3-mirrorlist")
      ),

      Package("linux"),
      Package("linux-firmware"),
      Package("linux-headers"),
      Package("efibootmgr"),
      Package("linux-cachyos") if cachyos_kernel else None,
      Package("linux-cachyos-headers") if cachyos_kernel else None,

      File("/boot/loader/entries/arch-cachyos.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by koti
        title    Arch Linux with CachyOS Kernel
        linux    /vmlinuz-linux-cachyos
        initrd   /initramfs-linux-cachyos.img
        options  root=UUID={root_uuid} rw console=tty1 loglevel=3 nowatchdog zswap.enabled=1
        sort-key 0
      ''')) if cachyos_kernel else None,

      File("/boot/loader/entries/arch-stock.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by koti
        title    Arch Linux with Stock Kernel
        linux    /vmlinuz-linux
        initrd   /initramfs-linux.img
        options  root=UUID={root_uuid} rw console=tty1 loglevel=3 nowatchdog zswap.enabled=1
        sort-key 10
      ''')),

      File("/boot/loader/entries/arch-fallback.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by koti
        title    Arch Linux Fallback Configuration
        linux    /vmlinuz-linux
        initrd   /initramfs-linux-fallback.img
        options  root=UUID={root_uuid} rw
        sort-key 99
      ''')),

      File("/boot/loader/loader.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by koti
        default {"arch-cachyos.conf" if cachyos_kernel else "arch-stock.conf"}
        timeout 3
        console-mode 2
      ''')),

      File("/etc/modprobe.d/disable-watchdog-modules.conf", permissions = 0o444, content = cleandoc('''
        # managed by koti
        blacklist sp5100_tco
      ''')),
    )
  ]
