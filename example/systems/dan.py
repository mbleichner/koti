from inspect import cleandoc

from koti import *
from koti.utils.shell import shell
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
def dan() -> Generator[ConfigGroup | None]:
  yield from base()
  yield from cpufreq(min_freq = 2000, max_freq = 4500, governor = "performance")
  yield from throttle_after_boot(2000)
  yield from swapfile(size_gb = 12)
  yield from kernel_cachyos(sortkey = 1)
  yield from kernel_stock(sortkey = 2)
  yield from fish()
  yield from desktop(nvidia = True, autologin = True, ms_fonts = True)
  yield from systray(ryzen = True, nvidia = True)
  yield from gaming()
  yield from nvme_thermal_throttling()
  yield from nvidia_undervolting()
  yield from ryzen_undervolting()
  # yield from ollama_aichat(cuda = True)
  yield from network_manager()

  yield ConfigGroup(
    description = "firmware, drivers and filesystems for dan",
    requires = [Swapfile("/swapfile")],
    provides = [
      Package("linux-firmware-other"),
      Package("linux-firmware-intel"),
      Package("linux-firmware-nvidia"),

      # Nicht das vorkompilierte NVIDIA Modul von CachyOS nehmen, sonst kommt es gelegentlich zu Dependency-Fehlern, wenn das
      # CachyOS-Modul von einer zu neuen nvidia-utils Version abhängt, die in den Arch-Repos noch nicht verfügbar ist
      Package("nvidia-open-dkms"),
      Package("nvidia-settings"),

      # Package("python-flask"),
      # Package("python-bottle"),
      # Package("python-numpy"),
      # Package("python-steam"),
      # Package("python-tests"),
      # Package("python-mock"),
      # Package("python-mock"),

      GroupAssignment("manuel", "docker"),
      File("/tmp/test", content = cleandoc('''
        moep moep moep
      ''')),

      PostHook("moep hook 1", execute = lambda: shell("echo moep 1"), trigger = File("/tmp/test")),
      PostHook("moep hook 2", execute = lambda: shell("echo moep 2"), trigger = PostHook("moep hook 1")),

      File("/etc/fstab", content = cleandoc('''
        UUID=3409a847-0bd6-43e4-96fd-6e8be4e3c58d  /             ext4  rw,noatime 0 1
        UUID=AF4E-18BD                             /boot         vfat  rw,defaults 0 2
        UUID=CCA2A808A2A7F55C                      /mnt/windows  ntfs  rw,x-systemd.automount 0 0
        UUID=c0b79d2c-5a0a-4f82-8fab-9554344159a5  /home/shared  ext4  rw,noatime 0 1
        /swapfile                                  swap          swap  defaults 0 0
      ''')),
    ]
  )

  yield ConfigGroup(
    description = "homeoffice stuff",
    provides = [
      Package("linphone-desktop-appimage"),
      Package("microsoft-edge-stable-bin"),
      # Package("flatpak"),
      # FlatpakRepo("flathub", spec_url = "https://dl.flathub.org/repo/flathub.flatpakrepo"),
      # FlatpakPackage("com.discordapp.Discord"),
      # FlatpakPackage("us.zoom.Zoom"),
    ]
  )
