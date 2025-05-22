from inspect import cleandoc
from typing import TypedDict

from core import ConfigItemGroup, ConfigModule, ConfigModuleGroups, Requires
from managers.file import File
from managers.pacman import PacmanPackage
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
        PacmanPackage("qt6-multimedia-ffmpeg"),  # qt6-multimedia-backend
        PacmanPackage("phonon-qt6-vlc"),  # phonon-qt6-backend
        PacmanPackage("pipewire-jack"),  # jack
        PacmanPackage("jdk17-openjdk"),  # java-runtime=17
        PacmanPackage("nvidia-utils" if self.nvidia else "vulkan-radeon"),  # vulkan-driver
        PacmanPackage("lib32-nvidia-utils" if self.nvidia else "lib32-vulkan-radeon"),  # lib32-vulkan-driver
      ),

      ConfigItemGroup(
        Requires(
          ConfigItemGroup("plasma-optional-dependencies"),
          File("/etc/pacman.conf"), # wg. NoExtract = etc/xdg/autostart/org.kde.discover.notifier.desktop
        ),
        PacmanPackage("archlinux-wallpaper"),
        PacmanPackage("ark"),
        PacmanPackage("code"),
        PacmanPackage("coolercontrol"),
        PacmanPackage("dolphin"),
        PacmanPackage("firefox"),
        PacmanPackage("gimp"),
        PacmanPackage("greetd-tuigreet"),
        PacmanPackage("gwenview"),
        PacmanPackage("kate"),
        PacmanPackage("kcalc"),
        PacmanPackage("kdiff3"),
        PacmanPackage("kleopatra"),
        PacmanPackage("kolourpaint"),
        PacmanPackage("konsole"),
        PacmanPackage("ksnip"),
        PacmanPackage("libreoffice-fresh"),
        PacmanPackage("nextcloud-client"),
        PacmanPackage("nvidia-open-dkms") if self.nvidia else None,
        PacmanPackage("obsidian"),
        PacmanPackage("okular"),
        PacmanPackage("pavucontrol"),
        PacmanPackage("plasma-meta"),
        PacmanPackage("samba"),
        PacmanPackage("sddm"),
        PacmanPackage("spectacle"),
        PacmanPackage("wine"),
        PacmanPackage("google-chrome"),
        PacmanPackage("linphone-desktop-appimage"),
        PacmanPackage("ttf-ms-win10-auto"),  # Das win11 Package war zuletzt broken
        PacmanPackage("noto-fonts"),
        PacmanPackage("noto-fonts-emoji"),
        PacmanPackage("pycharm-community-edition"),

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

        File("/home/manuel/.config/wireplumber/wireplumber.conf.d/priorities.conf", permissions = 0o444, owner = "manuel", content = cleandoc('''
          # managed by arch-config
          monitor.alsa.rules = [
          
            # Alle Bluetooth Devices bekommen immer Prio 1010 zugewiesen und diese kann hier
            # aus bislang unerfindlichen Gründen nicht geändert werden
          
            { # Steelseries Game Channel
              matches = [{node.name = "alsa_output.usb-SteelSeries_SteelSeries_Arctis_7-00.stereo-game"}]
              actions = {
                update-props = {
                  priority.driver = 1000
                  priority.session = 1000
                }
              }
            }
          
            { # Steelseries Chat Channel
              matches = [{node.name = "alsa_output.usb-SteelSeries_SteelSeries_Arctis_7-00.mono-chat"}]
              actions = {
                update-props = {
                  priority.driver = 900
                  priority.session = 900
                }
              }
            }
          ]
        ''')),
      ),
    ]
