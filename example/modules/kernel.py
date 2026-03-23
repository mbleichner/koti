from inspect import cleandoc

from koti import *
from koti.utils.shell import shell_output

root_uuid = shell_output("findmnt -n -o UUID $(stat -c '%m' /)")


def kernel(packagename: str, sortkey: int, powersave = False) -> ConfigDict:
  kernel_params = [
    "console=tty1",
    "loglevel=3",
    "nowatchdog",
    "zswap.enabled=1",
    "rcutree.enable_rcu_lazy=1" if powersave else None,
  ]
  return {
    Section(f"{packagename} + systemd-boot entry"): (
      Package(packagename),
      Package(packagename + "-headers"),
      File(f"/boot/loader/entries/{packagename}.conf", permissions = "rwxr-xr-x", content = cleandoc(f'''
        title    Arch/CachyOS ({packagename})
        linux    /vmlinuz-{packagename}
        initrd   /initramfs-{packagename}.img
        options  root=UUID={root_uuid} rw {" ".join(param for param in kernel_params if param is not None)}
        sort-key {sortkey}
      ''')),
      File(f"/boot/loader/entries/{packagename}-fallback.conf", permissions = "rwxr-xr-x", content = cleandoc(f'''
        title    Arch/CachyOS ({packagename}, Fallback)
        linux    /vmlinuz-{packagename}
        initrd   /initramfs-{packagename}.img
        options  root=UUID={root_uuid} rw
        sort-key {sortkey + 80}
      ''')),
    )
  }
