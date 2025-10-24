from inspect import cleandoc

from koti import *
from modules.base import base, swapfile
from modules.cpufreq import cpufreq, throttle_after_boot
from modules.desktop import desktop
from modules.fish import fish
from modules.gaming import gaming
from modules.kernel import kernel_cachyos, kernel_stock
from modules.networking import network_manager
from modules.nvidia_undervolting import nvidia_undervolting
from modules.nvme_thermal_throttling import nvme_thermal_throttling
from modules.ryzen_undervolting import ryzen_undervolting
from modules.systray import systray


# Configuration for my DAN A4-SFX desktop machine (Ryzen 5800X3D, RTX3080)
def dan() -> ConfigDict:
  return {
    **base(),
    **cpufreq(min_freq = 2000, max_freq = 4500, governor = "performance"),
    **throttle_after_boot(2000),
    **swapfile(size_gb = 12),
    **kernel_cachyos(sortkey = 1),
    **kernel_stock(sortkey = 2),
    **fish(),
    **desktop(nvidia = True, autologin = True, ms_fonts = True),
    **systray(ryzen = True, nvidia = True),
    **gaming(),
    **nvme_thermal_throttling(),
    **nvidia_undervolting(),
    **ryzen_undervolting(),
    **network_manager(),

    Section("filesystems for dan"): (
      File("/etc/fstab", requires = Swapfile("/swapfile"), content = cleandoc('''
        UUID=3409a847-0bd6-43e4-96fd-6e8be4e3c58d  /             ext4  rw,noatime 0 1
        UUID=AF4E-18BD                             /boot         vfat  rw,defaults 0 2
        UUID=CCA2A808A2A7F55C                      /mnt/windows  ntfs  rw,x-systemd.automount 0 0
        UUID=c0b79d2c-5a0a-4f82-8fab-9554344159a5  /home/shared  ext4  rw,noatime 0 1
        /swapfile                                  swap          swap  defaults 0 0
      ''')),
    ),

    Section("firmware for dan"): (
      Package("linux-firmware-other"),
      Package("linux-firmware-intel"),
      Package("linux-firmware-nvidia"),
    ),

    Section("nvidia drivers for dan"): (
      File("/etc/pacman.d/hooks/nvidia.hook", content = cleandoc('''
        [Trigger]
        Operation=Install
        Operation=Upgrade
        Operation=Remove
        Type=Package
        Target=nvidia-open
  
        [Action]
        Description=Updating NVIDIA module in initcpio
        Depends=mkinitcpio
        When=PostTransaction
        NeedsTargets
        Exec=/usr/bin/mkinitcpio -P
      ''')),

      # Nicht das vorkompilierte NVIDIA Modul von CachyOS nehmen, sonst kommt es gelegentlich zu Dependency-Fehlern, wenn das
      # CachyOS-Modul von einer zu neuen nvidia-utils Version abhängt, die in den Arch-Repos noch nicht verfügbar ist
      Package("nvidia-open-dkms"),
      Package("nvidia-settings"),
    ),

    Section("stuff for koti testing"): (
      Package("quickemu-git"),
      # Package("python-flask"),
      # Package("python-bottle"),
      # File("/tmp/test", content = "moep moep moep"),
      # PostHook("moep hook 1", execute = lambda: shell("echo moep 1"), trigger = File("/tmp/test")),
      # PostHook("moep hook 2", execute = lambda: shell("echo moep 2"), trigger = PostHook("moep hook 1")),
    ),

    Section("homeoffice stuff"): (
      Package("xwaylandvideobridge"),
      Package("linphone-desktop-appimage"),
      Package("microsoft-edge-stable-bin"),
      FlatpakPackage("us.zoom.Zoom"),
    ),
  }
