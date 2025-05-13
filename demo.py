from __future__ import annotations

from main import ArchUpdate
from modules.ananicy import AnanicyModule
from modules.base import BaseModule
from modules.cpu_freq_policy import CpuFreqPolicyModule
from modules.desktop import DesktopModule
from modules.fish import FishModule
from modules.gaming import GamingModule
from modules.kernel import KernelModule
from modules.nvidia_undervolting import NvidiaUndervoltingModule
from modules.nvme_thermal_throttling import NvmeThermalThrottlingModule
from modules.ollama_aichat import OllamaAichatModule
from modules.pacman import PacmanModule
from modules.ryzen_undervolting import RyzenUndervoltingModule
from modules.systray import SystrayModule

arch_update = ArchUpdate()
arch_update.managers += [

]
arch_update.modules += [
  KernelModule(root_uuid = "moep", cachyos = True),
  PacmanModule(cachyos = True),
  FishModule(),
  BaseModule(),
  AnanicyModule(),
  DesktopModule(nvidia = True, autologin = True),
  GamingModule(),
  SystrayModule(ryzen = True, nvidia = True),
  NvidiaUndervoltingModule(),
  RyzenUndervoltingModule(),
  NvmeThermalThrottlingModule(),
  CpuFreqPolicyModule(min_freq = 2000, max_freq = 4500, governor = "performance"),
  OllamaAichatModule(nvidia = True),
]

for phase_idx, phase_managers in enumerate(arch_update.build_execution_order()):
  print(f"Phase {phase_idx + 1}")
  for manager, items in phase_managers:
    print(f"- {manager}:")
    for item in items:
      print(f"  - {item}")

arch_update.execute()

# paru -D --asexplicit ryzen_monitor-git wireguard-tools coolercontrol unrar pyenv noto-fonts-emoji fish efibootmgr gparted dosfstools pacman-contrib man-db nvidia-utils sudo decman btop wine gwenview pycharm-community-edition kolourpaint linux-cachyos-headers git-lfs ntfs-3g openbsd-netcat cachyos-v3-mirrorlist kate gpu-screen-recorder-ui nexusmods-app-bin kdiff3 noto-fonts libreoffice-fresh nvidia-open-dkms bluez-utils python cachyos-keyring spectacle gamescope zoxide gimp linux konsole qt6-multimedia-ffmpeg obsidian google-chrome nextcloud-client kcalc protontricks wget traceroute kdialog samba jdk17-openjdk man-pages bind cachyos-mirrorlist mangohud nvme-cli openssh linux-firmware fastfetch ttf-ms-win10-auto ark greetd-tuigreet linux-cachyos okular base-devel proton-ge-custom-bin firefox moreutils ryujinx networkmanager linphone-desktop-appimage dolphin paru-bin discord plasma-meta iotop cpupower steam ryzen_smu-dkms-git jq pipewire-jack ncdu htop tealdeer yazi sddm lib32-nvidia-utils less reflector linux-headers nano lostfiles ananicy-cpp terminus-font archlinux-wallpaper unzip r2modman-bin pavucontrol zip git tig kleopatra ksnip base arch-update python-pynvml code ollama-cuda pacutils phonon-qt6-vlc
