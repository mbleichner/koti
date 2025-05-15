from inspect import cleandoc

from core import ConfigItemGroup, ConfigModule, ConfigModuleGroups, Options
from shell import shell_interactive
from managers.file import File
from managers.hook import PostHook
from managers.pacman import PacmanPackage
from managers.swapfile import Swapfile
from managers.systemd import SystemdUnit


class BaseModule(ConfigModule):

  def provides(self) -> ConfigModuleGroups: return [
    ConfigItemGroup(
      Options(confirm_mode = "paranoid"),

      PacmanPackage("base"),
      PacmanPackage("sudo"),
      PacmanPackage("terminus-font"),
      PacmanPackage("ca-certificates"),
      PacmanPackage("ca-certificates-mozilla"),

      # Command Line Utilities
      PacmanPackage("nano"),
      PacmanPackage("less"),
      PacmanPackage("bat"),
      PacmanPackage("moreutils"),  # enthält sponge
      PacmanPackage("jq"),
      PacmanPackage("man-db"),
      PacmanPackage("man-pages"),
      PacmanPackage("tealdeer"),
      PacmanPackage("unrar"),
      PacmanPackage("zip"),
      PacmanPackage("unzip"),
      PacmanPackage("7zip"),
      PacmanPackage("yazi"),
      PacmanPackage("zoxide"),

      # Monitoring + Analyse
      PacmanPackage("btop"),
      PacmanPackage("htop"),
      PacmanPackage("iotop"),
      PacmanPackage("ncdu"),
      PacmanPackage("ryzen_monitor-git"),
      PacmanPackage("bandwhich"),

      # Development und Libraries
      PacmanPackage("git"),
      PacmanPackage("git-lfs"),
      PacmanPackage("tig"),
      PacmanPackage("python"),
      PacmanPackage("pyenv"),

      # Networking
      PacmanPackage("bind"),
      PacmanPackage("networkmanager"),
      PacmanPackage("openbsd-netcat"),
      PacmanPackage("traceroute"),
      PacmanPackage("wireguard-tools"),
      PacmanPackage("wget"),
      PacmanPackage("openssh"),

      # Hardware Utilities
      PacmanPackage("cpupower"),
      PacmanPackage("bluez-utils"),

      # Dateisysteme
      PacmanPackage("gparted"),
      PacmanPackage("ntfs-3g"),
      PacmanPackage("dosfstools"),

      SystemdUnit("NetworkManager.service"),
      SystemdUnit("wpa_supplicant.service"),
      SystemdUnit("sshd.service"),
      SystemdUnit("systemd-timesyncd.service"),

      Swapfile("/swapfile", 4 * 1024 ** 3),  # 4GB

      File("/etc/vconsole.conf", permissions = 0o444, content = cleandoc('''
        # managed by arch-config
        KEYMAP=de-latin1
        FONT=ter-124b
      ''')),

      File("/etc/sudoers", permissions = 0o444, content = cleandoc('''
        # managed by arch-config
        ## Defaults specification
        ##
        ## Preserve editor environment variables for visudo.
        ## To preserve these for all commands, remove the "!visudo" qualifier.
        Defaults!/usr/bin/visudo env_keep += "SUDO_EDITOR EDITOR VISUAL"
        ##
        ## Use a hard-coded PATH instead of the user's to find commands.
        ## This also helps prevent poorly written scripts from running
        ## artbitrary commands under sudo.
        Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/bin"
        
        # https://www.reddit.com/r/archlinux/comments/dnxjbx/annoyance_with_sudo_password_expired/
        Defaults passwd_tries=3, passwd_timeout=180
        
        # Notwendig für paru SudoLoop ohne initiale Passworteingabe  
        Defaults verifypw = any
        
        root ALL=(ALL:ALL) ALL
        %wheel ALL=(ALL:ALL) ALL
        
        @includedir /etc/sudoers.d
        
        # Für die Systray Tools
        manuel ALL=(ALL:ALL) NOPASSWD: /usr/bin/cpupower
        manuel ALL=(ALL:ALL) NOPASSWD: /usr/bin/tee /sys/devices/system/cpu/*
        manuel ALL=(ALL:ALL) NOPASSWD: /usr/bin/nvidia-smi *
        
        # Erlaubt von arch-update aufgerufene Kommandos ohne Passwort
        manuel ALL=(ALL:ALL) NOPASSWD: /usr/bin/pacman *
        manuel ALL=(ALL:ALL) NOPASSWD: /usr/bin/paccache *
        manuel ALL=(ALL:ALL) NOPASSWD: /usr/bin/checkservices *
      ''')),

      File("/etc/udev/rules.d/50-disable-usb-wakeup.rules", permissions = 0o444, content = cleandoc('''
        # managed by arch-config
        ACTION=="add", SUBSYSTEM=="usb", DRIVERS=="usb", ATTR{power/wakeup}="disabled"
      ''')),
    ),

    ConfigItemGroup(
      "locale-setup",

      File(
        identifier = "/etc/locale.conf",
        permissions = 0o444,
        content = cleandoc('''
        LANG=en_US.UTF-8
        LC_ADDRESS=de_DE.UTF-8
        LC_IDENTIFICATION=de_DE.UTF-8
        LC_MEASUREMENT=de_DE.UTF-8
        LC_MONETARY=de_DE.UTF-8
        LC_NAME=de_DE.UTF-8
        LC_NUMERIC=de_DE.UTF-8
        LC_PAPER=de_DE.UTF-8
        LC_TELEPHONE=de_DE.UTF-8
        LC_TIME=de_DE.UTF-8
      ''')),

      File(
        identifier = "/etc/locale.gen",
        permissions = 0o444,
        content = cleandoc('''
        en_US.UTF-8 UTF-8
        de_DE.UTF-8 UTF-8
        # Zeilenumbruch hinter den Locales ist wichtig, sonst werden sie ignoriert
      ''')),

      PostHook(
        identifier = "regenerate-locales",
        execute = lambda: shell_interactive("locale-gen")
      ),
    )
  ]
