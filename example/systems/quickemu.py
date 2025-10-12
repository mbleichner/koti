from koti import *
from modules.base import base, swapfile
from modules.desktop import desktop
from modules.fish import fish
from modules.gaming import gaming
from modules.systray import systray

"""
wget https://geo.mirror.pkgbuild.com/images/latest/Arch-Linux-x86_64-basic.qcow2
create file: archlinux.conf:
  guest_os="linux"
  disk_img="Arch-Linux-x86_64-basic.qcow2"
quickemu --vm archlinux.conf
ssh arch@localhost -p 22220
  (can take a while until the ssh server is up; password is "arch")
sudo pacman -Syu git base-devel python python-urllib3 python-pyscipopt python-numpy
git clone https://github.com/mbleichner/koti.git && cd koti/example
git pull --rebase; sudo PYTHONPATH=/home/arch/koti/src ./koti-apply
"""


def quickemu() -> Generator[ConfigGroup | None]:
  yield from base()
  yield from swapfile(size_gb = 1)
  yield from fish()
  yield from desktop(nvidia = False, autologin = True, ms_fonts = False)
  yield from systray(ryzen = True, nvidia = False)
  yield from gaming()

  yield ConfigGroup(
    description = "firmware, drivers and filesystems for lenovo",
    provides = [
      Swapfile("/swapfile"),
      Package("linux-firmware-other"),
      Package("linux-firmware-intel"),
      Package("linux-firmware-nvidia"),
      Package("grub"),
      Package("linux"),
      Package("qemu-guest-agent"),
    ]
  )
