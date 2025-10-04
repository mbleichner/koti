from koti import *
from modules.base import base, swapfile
from modules.desktop import desktop
from modules.fish import fish
from modules.gaming import gaming
from modules.systray import systray


# wget https://geo.mirror.pkgbuild.com/images/latest/Arch-Linux-x86_64-basic.qcow2
# quickemu --vm archlinux-latest.conf --display spice
# ssh arch@localhost -p 22220
#   Password "arch"
# sudo pacman -Syu git base-devel
# git clone https://github.com/mbleichner/koti.git
# cd /home/arch/koti/example
# sudo PYTHONPATH=/home/arch/koti/src ./koti-apply

# Configuration for my Lenovo X13 laptop
def quickemu() -> Generator[ConfigGroup | None]:
  yield from base()
  yield from swapfile(size_gb = 1)
  yield from fish()
  yield from desktop(nvidia = False, autologin = True)
  yield from systray(ryzen = True, nvidia = False)
  yield from gaming()

  yield ConfigGroup(
    description = "firmware, drivers and filesystems for lenovo",
    requires = [Swapfile("/swapfile")],
    provides = [
      Package("linux-firmware-other"),
      Package("linux-firmware-intel"),
      Package("linux-firmware-nvidia"),
      Package("grub"),
    ]
  )
