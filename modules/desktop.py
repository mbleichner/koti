from inspect import cleandoc
from typing import TypedDict

from definitions import ConfigItem, ConfigItemGroup, ConfigModule, ConfigModuleGroups, Requires
from managers.file import File
from managers.package import Package
from managers.pacman_key import PacmanKey
from managers.systemd import SystemdUnit


class TuiGreetSession(TypedDict):
  user: str
  command: str


class DesktopModule(ConfigModule):
  def __init__(self, nvidia: bool, autologin: bool):
    self.autologin = autologin
    self.nvidia = nvidia

  def tuigreet_session(self) -> TuiGreetSession:
    if self.autologin:
      return {"user": "manuel", "command": "startplasma-wayland"}
    else:
      return {"user": "greeter", "command": "tuigreet -trc startplasma-wayland"}

  def provides(self) -> ConfigModuleGroups:
    return [
      ConfigItemGroup(
        "plasma-optional-dependencies",
        Package("qt6-multimedia-ffmpeg"),  # qt6-multimedia-backend
        Package("phonon-qt6-vlc"),  # phonon-qt6-backend
        Package("pipewire-jack"),  # jack
        Package("jdk17-openjdk"),  # java-runtime=17
        Package("nvidia-utils" if self.nvidia else "vulkan-radeon"),  # vulkan-driver
        Package("lib32-nvidia-utils" if self.nvidia else "lib32-vulkan-radeon"),  # lib32-vulkan-driver
      ),

      ConfigItemGroup(
        Requires(ConfigItemGroup("plasma-optional-dependencies")),
        Package("archlinux-wallpaper"),
        Package("ark"),
        Package("code"),
        Package("coolercontrol"),
        Package("dolphin"),
        Package("firefox"),
        Package("gimp"),
        Package("greetd-tuigreet"),
        Package("gwenview"),
        Package("kate"),
        Package("kcalc"),
        Package("kdiff3"),
        Package("kleopatra"),
        Package("kolourpaint"),
        Package("konsole"),
        Package("ksnip"),
        Package("libreoffice-fresh"),
        Package("nextcloud-client"),
        Package("nvidia-open-dkms") if self.nvidia else None,
        Package("obsidian"),
        Package("okular"),
        Package("pavucontrol"),
        Package("plasma-meta"),
        Package("samba"),
        Package("sddm"),
        Package("spectacle"),
        Package("wine"),
        Package("google-chrome"),
        Package("linphone-desktop-appimage"),
        Package("ttf-ms-win10-auto"),  # Das win11 Package war zuletzt broken
        Package("noto-fonts"),
        Package("noto-fonts-emoji"),
        Package("pycharm-community-edition"),

        File("/etc/greetd/config.toml", permissions = 0o444, owner = "manuel", content = cleandoc(f'''
          # managed by arch-config
          [terminal]
          vt = 2
    
          [default_session]
          user = "{self.tuigreet_session()["user"]}"
          command = "{self.tuigreet_session()["command"]}"
        ''')),

        SystemdUnit("greetd.service"),
        SystemdUnit("coolercontrold.service"),
        SystemdUnit("bluetooth.service"),
      )
    ]
