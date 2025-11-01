from inspect import cleandoc

from koti import *
from modules.base import base
from modules.cpufreq import cpufreq, throttle_after_boot
from modules.desktop import desktop
from modules.fish import fish
from modules.gaming import gaming
from modules.kernel import kernel_cachyos, kernel_lts, kernel_stock
from modules.networking import network_manager
from modules.systray import systray


# Configuration for my Lenovo X13 laptop
def lenovo() -> ConfigDict:
  return {
    **base(),
    **cpufreq(min_freq = 1000, max_freq = 4500, governor = "powersave"),
    **throttle_after_boot(1500),
    **kernel_cachyos(sortkey = 1),
    **kernel_stock(sortkey = 2),
    **fish(),
    **desktop(nvidia = False, autologin = True, ms_fonts = True),
    **systray(ryzen = True, nvidia = False),
    **gaming(),
    **network_manager(),

    Section("swapfile (4GB) and fstab"): (
      Swapfile("/swapfile", 4 * (1024 ** 3)),
      File("/etc/fstab", requires = Swapfile("/swapfile"), content = cleandoc('''
        UUID=79969cb9-9b6e-48e2-a672-4aee50f04c56  /      ext4  rw,noatime 0 1
        UUID=1CA6-490D                             /boot  vfat  rw,defaults 0 2
        /swapfile                                  swap   swap  defaults 0 0
      '''))
    ),

    Section("firmware for lenovo"): (
      Package("linux-firmware-other"),
      Package("linux-firmware-amdgpu"),
      Package("linux-firmware-realtek"),
    ),

    Section("graphics drivers for lenovo"): (
      Package('vulkan-radeon'),
      Package('lib32-vulkan-radeon'),
    ),

    Section("disable wakeup from touchpad"): (
      File("/etc/udev/rules.d/50-disable-touchpad-wakeup.rules", content = cleandoc('''
        ACTION=="add|change", SUBSYSTEM=="i2c", DRIVER=="i2c_hid_acpi", ATTR{name}=="ELAN0678:00", ATTR{power/wakeup}="disabled"
        # Einstellung testen per udevadm info -q all -a /sys/devices/platform/AMDI0010:02/i2c-2/i2c-ELAN0678:00
      '''))
    )
  }
