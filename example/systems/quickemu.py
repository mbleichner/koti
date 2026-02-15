from koti import *
from modules.base import base
from modules.cpu import cpufreq_systray
from modules.desktop import desktop
from modules.fish import fish
from modules.gaming import gaming

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


def quickemu() -> ConfigDict:
  return {
    **base(),
    **fish(),
    **desktop(nvidia = False, autologin = True, ms_fonts = False),
    **cpufreq_systray(),
    **gaming(),
    Section("firmware, drivers and filesystems for quickemu"): (
      Package("linux-firmware-other"),
      Package("linux-firmware-intel"),
      Package("linux-firmware-nvidia"),
      Package("grub"),
      Package("linux"),
      Package("qemu-guest-agent"),
    )
  }
