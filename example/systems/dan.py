from inspect import cleandoc

from koti import *
from modules.base import base
from modules.cpu import cpufreq_auto_adjust, cpufreq_defaults, cpufreq_systray
from modules.desktop import desktop
from modules.development import development
from modules.fish import fish
from modules.gaming import gaming
from modules.kernel import kernel_cachyos, kernel_stock
from modules.nvidia import nvidia_systray, nvidia_undervolting
from modules.ryzen import ryzen_undervolting


# Configuration for my DAN A4-SFX desktop machine (Ryzen 5800X3D, RTX3080)
def dan() -> ConfigDict:
  return {
    **base(),
    **fish(),
    **desktop(nvidia = True, autologin = True, ms_fonts = True),
    **cpufreq_defaults(min_freq = 2000, max_freq = 4000, governor = "performance"),
    **cpufreq_auto_adjust(base_freq = 2000),
    **cpufreq_systray(),
    **kernel_cachyos(sortkey = 1),
    **kernel_stock(sortkey = 2),
    **nvidia_systray(),
    **nvidia_undervolting(),
    **ryzen_undervolting(),
    **gaming(),
    **development(),

    Section("swapfile (12GB) and fstab"): (
      Swapfile("/swapfile", 12 * (1024 ** 3)),
      File("/etc/fstab", content = cleandoc('''
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

    Section("network-manager and wifi"): (
      Package("networkmanager"),
      SystemdUnit("NetworkManager.service"),
      SystemdUnit("wpa_supplicant.service"),
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

      # nvidia 580.105.08:
      # Added a new environment variable, CUDA_DISABLE_PERF_BOOST, to allow for disabling the default behavior of boosting the GPU to a higher
      # power state when running CUDA applications. Setting this environment variable to '1' will disable the boost.
      File("/etc/environment.d/cuda-boost.conf", content = cleandoc(f'''
        CUDA_DISABLE_PERF_BOOST=1
      ''')),

      # Nicht das vorkompilierte NVIDIA Modul von CachyOS nehmen, sonst kommt es gelegentlich zu Dependency-Fehlern, wenn das
      # CachyOS-Modul von einer zu neuen nvidia-utils Version abhängt, die in den Arch-Repos noch nicht verfügbar ist
      Package("nvidia-open-dkms"),
      Package("nvidia-settings"),
    ),

    Section("NVMe thermal throttling (Kingston KC3000)"): (
      Package("nvme-cli"),
      File("/etc/systemd/system/nvme-thermal-throttling.service", content = cleandoc('''
      [Unit]
      Description=NVMe Thermal Throttling

      [Service]
      Type=oneshot
      RemainAfterExit=true
      ExecStart=/sbin/nvme set-feature /dev/nvme0 --feature-id=0x10 --value=0x01520160

      [Install]
      WantedBy=multi-user.target
   ''')),
      SystemdUnit("nvme-thermal-throttling.service"),
    ),

    Section("quickemu for koti testing"): (
      Package("quickemu-git"),
    ),

    Section("dan specific gaming stuff"): (
      Package("beyondallreason-appimage"),
      Package("headsetcontrol-git"),
      Package("teamspeak"),
      Package("teamspeak3"),
      Package("mumble"),
    ),

    Section("homeoffice stuff"): (
      Package("xwaylandvideobridge"),
      Package("linphone-desktop-appimage"),
      Package("microsoft-edge-stable-bin"),
      # FlatpakPackage("us.zoom.Zoom"),
    ),
  }
