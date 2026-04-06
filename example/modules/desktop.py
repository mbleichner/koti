from inspect import cleandoc

from koti import *
from koti.utils.shell import shell


def desktop(nvidia: bool, autologin: bool, ms_fonts: bool) -> ConfigDict:
  return {
    Section("plasma desktop"): (
      Package("plasma-meta"),
      Package("archlinux-wallpaper"),
      Directory("/opt/gamma-icc-profiles", source = "files/gamma-icc-profiles.zip", mask = "r--"),
      Option("/etc/pacman.conf/NoExtract", "etc/xdg/autostart/org.kde.discover.notifier.desktop"),  # prevent startup of discover (KDE package manager)
    ),

    Section("optimizations for responsiveness"): (
      Package("cachyos-settings"),
      Package("cachyos-ananicy-rules"),  # (also a dependency of cachyos-settings)
      Package("ananicy-cpp"),
      File("/etc/ananicy.d/compilers.rules", content = cleandoc('''
        {"name": "cc",    "nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"}
        {"name": "gcc",   "nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"}
        {"name": "make",  "nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"}
        {"name": "clang", "nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"}
        {"name": "rustc", "nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"}
      ''')),
      SystemdUnit("ananicy-cpp.service"),
    ),

    Section("applications"): (
      Package("code"),  # vscode
      Package("coolercontrol"),
      Package("dolphin"),
      Package("firefox"),
      Package("gimp"),
      Package("chromium"),
      Package("google-chrome"),
      Package("obsidian"),
      Package("okular"),
      Package("spectacle"),
      Package("gwenview"),
      Package("kate"),
      Package("kcalc"),
      Package("kleopatra"),
      Package("kolourpaint"),
      Package("ksnip"),
      Package("libreoffice-fresh"),
      Package("nextcloud-client"),
      Package("pavucontrol"),
      Package("wiremix"),
      Package("konsole"),
      Package("ark"),
      Package("wine"),
      SystemdUnit("coolercontrold.service"),
    ),

    Section("network-manager and wifi"): (
      Package("networkmanager"),
      File("/etc/NetworkManager/NetworkManager.conf", content = cleandoc(f'''
        # Disable connectivity checks, so networks stay connected even without internet access
        [connectivity]
        uri=
        interval=0
      ''')),
      SystemdUnit("NetworkManager.service"),
      SystemdUnit("wpa_supplicant.service"),
    ),

    Section("bluetooth"): (
      Package("bluez"),
      Package("bluez-utils"),
      SystemdUnit("bluetooth.service"),
    ),

    Section("fonts"): (
      Package("ttf-ms-win11-auto") if ms_fonts else None,
      Package("noto-fonts"),
      Package("noto-fonts-emoji"),
    ),

    Section("video players, codecs, hardware decoding"): (
      Package("vlc"),
      Package("vlc-plugins-all"),
      Package("libva-utils"),
      Package("vdpauinfo") if nvidia else None,
      Package("libva-nvidia-driver") if nvidia else None,
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

    Section("wireplumber config"): (
      Package("wireplumber"),
      *PostHookScope(
        File("/home/manuel/.config/wireplumber/wireplumber.conf.d/prevent-messing-with-mic-volume.conf", owner = "manuel", content = cleandoc('''
          access.rules = [ {
            matches = [
              { application.process.binary = "chromium" }
              { application.process.binary = "chrome" }
              { application.process.binary = "firefox" }
              { application.process.binary = "msedge" }
            ]
            actions = { update-props = { default_permissions = "rx" } }
          } ]
        ''')),
        File("/home/manuel/.config/wireplumber/wireplumber.conf.d/priorities.conf", owner = "manuel", content = cleandoc('''
          monitor.alsa.rules = [
            # Alle Bluetooth Devices bekommen immer Prio 1010 zugewiesen und diese kann hier
            # aus bislang unerfindlichen Gründen nicht geändert werden
            { # Steelseries Game Channel
              matches = [ { node.name = "alsa_output.usb-SteelSeries_SteelSeries_Arctis_7-00.stereo-game" } ]
              actions = { update-props = { priority.driver = 1000, priority.session = 1000 } }
            }
            { # Steelseries Chat Channel
              matches = [ { node.name = "alsa_output.usb-SteelSeries_SteelSeries_Arctis_7-00.mono-chat" } ]
              actions = { update-props = { priority.driver = 900, priority.session = 900 } }
            }
          ]
        ''')),
        PostHook("restart wireplumber", execute = lambda: shell("systemctl --user -M manuel@ restart wireplumber"))
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
