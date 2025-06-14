from inspect import cleandoc
from typing import TypedDict

from koti import *


def desktop(nvidia: bool, autologin: bool) -> ConfigGroups: return [
  ConfigGroup(
    "plasma-optional-dependencies",
    Package("qt6-multimedia-ffmpeg"),  # qt6-multimedia-backend
    Package("phonon-qt6-vlc"),  # phonon-qt6-backend
    Package("pipewire-jack"),  # jack
    Package("jdk17-openjdk"),  # java-runtime=17
    Package("nvidia-utils" if nvidia else "vulkan-radeon"),  # vulkan-driver
    Package("lib32-nvidia-utils" if nvidia else "lib32-vulkan-radeon"),  # lib32-vulkan-driver
  ),

  ConfigGroup(
    "desktop-packages",
    Requires(
      ConfigGroup("plasma-optional-dependencies"),  # avoid pacman asking for possible alternatives
      File("/etc/pacman.conf"),  # wg. NoExtract = etc/xdg/autostart/org.kde.discover.notifier.desktop
    ),
    Package("archlinux-wallpaper"),
    Package("ark"),
    Package("code"),
    Package("coolercontrol"),
    Package("dolphin"),
    Package("firefox"),
    Package("gimp"),
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
    Package("nvidia-open-dkms") if nvidia else None,
    Package("obsidian"),
    Package("okular"),
    Package("pavucontrol"),
    Package("plasma-meta"),
    Package("samba"),
    Package("spectacle"),
    Package("wine"),
    Package("google-chrome"),
    Package("microsoft-edge-stable-bin"),
    Package("linphone-desktop-appimage"),
    Package("ttf-ms-win10-auto"),  # Das win11 Package war zuletzt broken
    Package("noto-fonts"),
    Package("noto-fonts-emoji"),
    Package("pycharm-community-edition"),
    SystemdUnit("coolercontrold.service"),
    SystemdUnit("bluetooth.service"),
  ),

  ConfigGroup(
    "display-manager",

    Package("greetd-tuigreet"),
    SystemdUnit("greetd.service"),

    File("/etc/greetd/config.toml", permissions = 0o444, owner = "manuel", content = cleandoc(f'''
      # managed by koti
      [terminal]
      vt = 2

      [default_session]
      user = "{tuigreet_session(autologin)["user"]}"
      command = "{tuigreet_session(autologin)["command"]}"
    ''')),
  ),

  ConfigGroup(
    File("/home/manuel/.config/wireplumber/wireplumber.conf.d/priorities.conf", permissions = 0o444, owner = "manuel", content = cleandoc('''
      # managed by koti
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

  ConfigGroup(
    "ananicy-cpp",

    Requires(Package("cachyos-mirrorlist")),  # Das Package ist in den CachyOS Repos vorkompiliert vorhanden

    Package("ananicy-cpp"),
    SystemdUnit("ananicy-cpp.service"),

    File("/etc/ananicy.d/ananicy.conf", permissions = 0o444, content = cleandoc('''
      # managed by koti
      # Generated by ananicy-cpp at 2024-11-29 20:02:04.668520254
      check_freq = 20
      loglevel = info
      cgroup_realtime_workaround = true
      rule_load = true
      type_load = true
      log_applied_rule = false
      apply_latnice = false
      apply_oom_score_adj = true
      apply_ionice = true
      cgroup_load = true
      apply_sched = true
      apply_nice = true
    ''')),

    File("/etc/ananicy.d/arch-update.rules", permissions = 0o444, content = cleandoc('''
      # managed by koti
      {"name": "arch-update", "nice": 10}
    ''')),

    File("/etc/ananicy.d/audio-system.rules", permissions = 0o444, content = cleandoc('''
      # managed by koti
      {"name": "pipewire", "nice": -10, "latency_nice": -10}
      {"name": "wireplumber", "nice": -10, "latency_nice": -10}
      {"name": "pipewire-pulse", "nice": -10, "latency_nice": -10}
    ''')),

    File("/etc/ananicy.d/kwin.rules", permissions = 0o444, content = cleandoc('''
      # managed by koti
      {"name": "kwin_wayland", "nice": -10, "latency_nice": -10}
    ''')),

    File("/etc/ananicy.d/compilers.rules", permissions = 0o444, content = cleandoc('''
      # managed by koti
      {"name": "gcc",   "nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"}
      {"name": "make",  "nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"}
      {"name": "clang", "nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"}
    ''')),

    File("/etc/ananicy.d/games.rules", permissions = 0o444, content = cleandoc('''
      # managed by koti
      {"name": "steam",   "nice": -5, "latency_nice": -5}
      {"name": "ryujinx", "nice": -5, "latency_nice": -5}
      {"name": "lutris",  "nice": -5, "latency_nice": -5}
      {"name": "heroic",  "nice": -5, "latency_nice": -5}
    ''')),

    File("/etc/ananicy.d/nextcloud.rules", permissions = 0o444, content = cleandoc('''
      # managed by koti
      {"name": "nextcloud", "nice": 10}
    ''')),
  )
]


class TuiGreetSession(TypedDict):
  user: str
  command: str


def tuigreet_session(autologin: bool) -> TuiGreetSession:
  if autologin:
    return {"user": "manuel", "command": "startplasma-wayland"}
  else:
    return {"user": "greeter", "command": "tuigreet -trc startplasma-wayland"}
