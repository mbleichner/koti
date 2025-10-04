from inspect import cleandoc
from typing import TypedDict

from koti import *
from koti.utils.shell import shell


def desktop(nvidia: bool, autologin: bool, ms_fonts: bool) -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "desktop packages",
    requires = [File("/etc/pacman.conf")],  # Damit NoExtract bei der ersten Ausführung angewendet wird
    provides = [
      Option("/etc/pacman.conf/NoExtract", "etc/xdg/autostart/org.kde.discover.notifier.desktop"),
      Directory("/opt/gamma-icc-profiles", source = "files/gamma-icc-profiles.zip", mask = "r--"),

      # Dependencies that have multiple alternatives (pacman will ask during installation)
      Package("qt6-multimedia-ffmpeg"),  # ... qt6-multimedia-backend
      Package("phonon-qt6-vlc"),  # .......... phonon-qt6-backend
      Package("pipewire-jack"),  # ........... jack
      Package("jdk17-openjdk"),  # ........... java-runtime=17
      Package("noto-fonts"),  # .............. ttf-fonts

      Package("archlinux-wallpaper"),
      Package("ark"),
      Package("code"),
      Package("coolercontrol"),
      Package("dolphin"),
      Package("firefox"),
      Package("gimp"),
      Package("vlc"),
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
      Package("obsidian"),
      Package("okular"),
      Package("pavucontrol"),
      Package("plasma-meta"),
      Package("samba"),
      Package("spectacle"),
      Package("wine"),
      Package("chromium"),
      Package("google-chrome"),
      Package("ttf-ms-win10-auto") if ms_fonts else None,  # Das win11 Package war zuletzt broken
      Package("noto-fonts-emoji"),
      Package("pycharm-community-edition"),
      Package("libva-utils"),
      Package("vdpauinfo") if nvidia else None,
      Package("libva-nvidia-driver") if nvidia else None,
      Package("xwaylandvideobridge"),
      SystemdUnit("coolercontrold.service"),
      SystemdUnit("bluetooth.service"),
    ]
  )

  yield ConfigGroup(
    description = "display manager and auto-login",
    provides = [
      Checkpoint("display-manager"),
      Package("greetd-tuigreet"),
      SystemdUnit("greetd.service"),
      File("/etc/greetd/config.toml", content = cleandoc(f'''
        [terminal]
        vt = 2
  
        [default_session]
        user = "{tuigreet_session(autologin)["user"]}"
        command = "{tuigreet_session(autologin)["command"]}"
      ''')),
    ]
  )

  yield ConfigGroup(
    description = "wireplumber priorities",
    provides = [
      File("/home/manuel/.config/wireplumber/wireplumber.conf.d/priorities.conf", owner = "manuel", content = cleandoc('''
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
    ]
  )

  yield ConfigGroup(
    description = "ananicy-cpp and configuration",
    provides = [
      Package("ananicy-cpp"),
      SystemdUnit("ananicy-cpp.service"),

      *PostHookScope(
        File("/etc/ananicy.d/ananicy.conf", content = cleandoc('''
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

        File("/etc/ananicy.d/arch-update.rules", content = cleandoc('''
          {"name": "arch-update", "nice": 10}
        ''')),

        File("/etc/ananicy.d/audio-system.rules", content = cleandoc('''
          {"name": "pipewire", "nice": -10, "latency_nice": -10}
          {"name": "wireplumber", "nice": -10, "latency_nice": -10}
          {"name": "pipewire-pulse", "nice": -10, "latency_nice": -10}
        ''')),

        File("/etc/ananicy.d/kwin.rules", content = cleandoc('''
          {"name": "kwin_wayland", "nice": -10, "latency_nice": -10}
        ''')),

        File("/etc/ananicy.d/compilers.rules", content = cleandoc('''
          {"name": "gcc",   "nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"}
          {"name": "make",  "nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"}
          {"name": "clang", "nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"}
        ''')),

        File("/etc/ananicy.d/games.rules", content = cleandoc('''
          {"name": "steam",   "nice": -5, "latency_nice": -5}
          {"name": "ryujinx", "nice": -5, "latency_nice": -5}
          {"name": "lutris",  "nice": -5, "latency_nice": -5}
          {"name": "heroic",  "nice": -5, "latency_nice": -5}
        ''')),

        File("/etc/ananicy.d/nextcloud.rules", content = cleandoc('''
          {"name": "nextcloud", "nice": 10}
        ''')),

        PostHook("restart-ananicy-cpp", execute = lambda: shell("systemctl restart ananicy-cpp.service"))
      )
    ]
  )


class TuiGreetSession(TypedDict):
  user: str
  command: str


def tuigreet_session(autologin: bool) -> TuiGreetSession:
  if autologin:
    return {"user": "manuel", "command": "startplasma-wayland"}
  else:
    return {"user": "greeter", "command": "tuigreet -trc startplasma-wayland"}
