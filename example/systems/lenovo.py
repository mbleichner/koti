from inspect import cleandoc
from typing import Generator

from koti import *
from modules.base import base, swapfile
from modules.cpufreq import cpufreq, throttle_after_boot
from modules.desktop import desktop
from modules.fish import fish
from modules.gaming import gaming
from modules.kernel import kernel_cachyos, kernel_stock
from modules.networking import network_manager
from modules.ollama_aichat import ollama_aichat
from modules.systray import systray


# Configuration for my Lenovo X13 laptop
def lenovo() -> Generator[ConfigGroup | None]:
  yield from base()
  yield from cpufreq(min_freq = 1000, max_freq = 4500, governor = "powersave")
  yield from throttle_after_boot(1500)
  yield from swapfile(4)
  yield from kernel_cachyos(1)
  yield from kernel_stock(2)
  yield from fish()
  yield from desktop(nvidia = False, autologin = True)
  yield from systray(ryzen = True, nvidia = False)
  yield from gaming()
  yield from ollama_aichat(cuda = False)
  yield from network_manager()

  yield ConfigGroup(
    description = "firmware (lenovo)",
    provides = [
      Package("linux-firmware-other"),
      Package("linux-firmware-amdgpu"),
      Package("linux-firmware-realtek"),
    ]
  )

  yield ConfigGroup(
    description = "fstab (lenovo)",
    confirm_mode = "paranoid",
    requires = [
      Swapfile("/swapfile"),
    ],
    provides = [
      File("/etc/fstab", permissions = 0o444, content = cleandoc('''
        # managed by koti
        UUID=79969cb9-9b6e-48e2-a672-4aee50f04c56  /      ext4  rw,noatime 0 1
        UUID=1CA6-490D                             /boot  vfat  rw,defaults 0 2
        /swapfile                                  swap   swap  defaults 0 0
      '''))
    ]
  )

  yield ConfigGroup(
    description = "disable wakeup from touchpad",
    provides = [
      File("/etc/udev/rules.d/50-disable-touchpad-wakeup.rules", permissions=0o444, content=cleandoc('''
        # managed by koti
        ACTION=="add|change", SUBSYSTEM=="i2c", DRIVER=="i2c_hid_acpi", ATTR{name}=="ELAN0678:00", ATTR{power/wakeup}="disabled"
        # Einstellung testen per udevadm info -q all -a /sys/devices/platform/AMDI0010:02/i2c-2/i2c-ELAN0678:00
      '''))
    ]
  )
