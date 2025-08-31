from inspect import cleandoc

from koti import *
from modules.base import base, swapfile
from modules.cpufreq import cpufreq, throttle_after_boot
from modules.desktop import desktop
from modules.fish import fish
from modules.gaming import gaming
from modules.kernel import kernel_cachyos, kernel_stock
from modules.networking import network_manager
from modules.systray import systray


# Configuration for my Lenovo X13 laptop
def distrobox() -> Generator[ConfigGroup | None]:
  yield from base()
  yield from swapfile(1)
  yield from fish()
  yield from desktop(nvidia = False, autologin = True)
  yield from systray(ryzen = True, nvidia = False)
  yield from gaming()

  yield ConfigGroup(
    description = "firmware, drivers and filesystems for lenovo",
    tags = ["CRITICAL"],
    requires = [Swapfile("/swapfile")],
    provides = [
      Package("linux-firmware-other"),
      Package("linux-firmware-intel"),
      Package("linux-firmware-nvidia"),
      Package("nvidia-open"),
      Package("linux-cachyos-nvidia-open"),
      Package("nvidia-settings"),
    ]
  )
