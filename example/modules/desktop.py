from inspect import cleandoc

from koti import *
from koti.utils.shell import shell


def desktop(nvidia: bool, autologin: bool, ms_fonts: bool) -> ConfigDict:
  return {
    Section("desktop packages"): (
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
      Package("noto-fonts"),
      Package("noto-fonts-emoji"),
      Package("pycharm-community-edition"),
      Package("libva-utils"),
      Package("vdpauinfo") if nvidia else None,
      Package("libva-nvidia-driver") if nvidia else None,

      # pacman will ask for these during installation:
      # - qt6-multimedia-ffmpeg  (qt6-multimedia-backend)
      # - phonon-qt6-vlc         (phonon-qt6-backend)
      # - pipewire-jack          (jack)

      Directory("/opt/gamma-icc-profiles", source = "files/gamma-icc-profiles.zip", mask = "r--"),

      SystemdUnit("coolercontrold.service"),
      SystemdUnit("bluetooth.service"),

      # prevent startup of discover (KDE package manager)
      Option("/etc/pacman.conf/NoExtract", "etc/xdg/autostart/org.kde.discover.notifier.desktop"),
    ),

    Section("flatpak and flathub"): (
      # flatpak currently required by plasma-meta
      Package("flatpak", before = lambda item: isinstance(item, FlatpakRepo) or isinstance(item, FlatpakPackage)),
      FlatpakRepo("flathub", spec_url = "https://dl.flathub.org/repo/flathub.flatpakrepo"),
    ),

    Section("display manager and auto-login"): (
      Package("greetd-tuigreet"),
      File("/etc/greetd/config.toml", content = cleandoc(f'''
        [terminal]
        vt = 2
  
        [default_session]
        user = "{tuigreet_session(autologin)["user"]}"
        command = "{tuigreet_session(autologin)["command"]}"
      ''')),
      SystemdUnit("greetd.service"),
    ),

    Section("wireplumber priorities"): (
      Package("wireplumber"),
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

    ),

    Section("ananicy-cpp and configuration"): (
      Package("ananicy-cpp"),

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

        SystemdUnit("ananicy-cpp.service"),

        PostHook("restart-ananicy-cpp", execute = lambda: shell("systemctl restart ananicy-cpp.service"))
      ),
    ),
  }


class TuiGreetSession(TypedDict):
  user: str
  command: str


def tuigreet_session(autologin: bool) -> TuiGreetSession:
  if autologin:
    return {"user": "manuel", "command": "startplasma-wayland"}
  else:
    return {"user": "greeter", "command": "tuigreet -trc startplasma-wayland"}
