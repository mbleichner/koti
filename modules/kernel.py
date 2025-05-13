from inspect import cleandoc

from definitions import ConfigItemGroup, ConfigModule, ConfigModuleGroups, Requires
from managers.file import File
from managers.package import Package
from managers.pacman_key import PacmanKey


class KernelModule(ConfigModule):
  def __init__(self, root_uuid: str, cachyos: bool):
    self.root_uuid = root_uuid
    self.cachyos = cachyos

  def provides(self) -> ConfigModuleGroups: return [
    ConfigItemGroup(
      PacmanKey("cachyos", key_id = "F3B607488DB35A47"),
      Package(
        "cachyos-keyring",
        url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-keyring-20240331-1-any.pkg.tar.zst"
      ),
      Package(
        "cachyos-mirrorlist",
        url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-mirrorlist-22-1-any.pkg.tar.zst"
      ),
      Package(
        "cachyos-v3-mirrorlist",
        url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-v3-mirrorlist-22-1-any.pkg.tar.zst"
      ),
    ),

    ConfigItemGroup(
      Requires(
        Package("cachyos-keyring"),
        Package("cachyos-mirrorlist"),
        Package("cachyos-v3-mirrorlist")
      ),

      Package("linux"),
      Package("linux-firmware"),
      Package("linux-headers"),
      Package("efibootmgr"),
      Package("linux-cachyos") if self.cachyos else None,
      Package("linux-cachyos-headers") if self.cachyos else None,

      File("/boot/loader/entries/arch-cachyos.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by arch-config
        title    Arch Linux with CachyOS Kernel
        linux    /vmlinuz-linux-cachyos
        initrd   /initramfs-linux-cachyos.img
        options  root=UUID={self.root_uuid} rw console=tty1 loglevel=3 nowatchdog zswap.enabled=1
        sort-key 0
      ''')) if self.cachyos else None,

      File("/boot/loader/entries/arch-stock.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by arch-config
        title    Arch Linux with Stock Kernel
        linux    /vmlinuz-linux
        initrd   /initramfs-linux.img
        options  root=UUID={self.root_uuid} rw console=tty1 loglevel=3 nowatchdog zswap.enabled=1
        sort-key 10
      ''')),

      File("/boot/loader/entries/arch-fallback.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by arch-config
        title    Arch Linux Fallback Configuration
        linux    /vmlinuz-linux
        initrd   /initramfs-linux-fallback.img
        options  root=UUID={self.root_uuid} rw
        sort-key 99
      ''')),

      File("/boot/loader/loader.conf", permissions = 0o555, content = cleandoc(f'''
        # managed by arch-config
        default {"arch-cachyos.conf" if self.cachyos else "arch-stock.conf"}
        timeout 3
        console-mode 2
      ''')),

      File("/etc/modprobe.d/disable-watchdog-modules.conf", permissions = 0o444, content = cleandoc('''
        # managed by arch-config
        blacklist sp5100_tco
      ''')),
    )
  ]
