from inspect import cleandoc

from koti import *
from modules.base import base
from modules.cpufreq import cpufreq_auto_adjust, cpufreq_defaults
from modules.desktop import desktop
from modules.gaming import gaming
from modules.kernel import kernel
from modules.systray import cpufreq_systray


# Configuration for my Lenovo X13 laptop
def lenovo() -> ConfigDict:
  return {
    **base(),
    **desktop(nvidia = False, autologin = True, ms_fonts = True),
    **gaming(),
    **cpufreq_defaults(min_freq = 1500, max_freq = 4000, governor = "powersave"),
    **cpufreq_auto_adjust(base_freq = 1500),
    **cpufreq_systray(),
    **kernel("linux-cachyos", sortkey = 1, powersave = True),
    **kernel("linux-cachyos-lts", sortkey = 2, powersave = True),

    Section("swapfile (4GB) and fstab"): (
      Swapfile("/swapfile", 4 * (1024 ** 3)),
      File("/etc/fstab", requires = Swapfile("/swapfile"), content = cleandoc('''
        UUID=79969cb9-9b6e-48e2-a672-4aee50f04c56  /      ext4  rw 0 1
        UUID=1CA6-490D                             /boot  vfat  rw 0 2
        /swapfile                                  swap   swap  defaults 0 0
      '''))
    ),

    Section("firmware and drivers for lenovo"): (
      Package("linux-firmware-other"),
      Package("linux-firmware-amdgpu"),
      Package("linux-firmware-realtek"),
      Package("ryzen_smu-dkms-git"), # AUR
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
