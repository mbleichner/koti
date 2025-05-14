from inspect import cleandoc

from definitions import ConfigItemGroup, ConfigModule, ConfigModuleGroups, ShellCommand
from managers.file import File
from managers.hook import Hook
from managers.package import Package
from managers.systemd import SystemdUnit


class BaseModule(ConfigModule):

  def provides(self) -> ConfigModuleGroups:
    return ConfigItemGroup(

      Package("base"),
      Package("sudo"),
      Package("terminus-font"),
      Package("ca-certificates"),
      Package("ca-certificates-mozilla"),

      # Command Line Utilities
      Package("nano"),
      Package("less"),
      Package("bat"),
      Package("moreutils"),  # enthält sponge
      Package("jq"),
      Package("man-db"),
      Package("man-pages"),
      Package("tealdeer"),
      Package("unrar"),
      Package("zip"),
      Package("unzip"),
      Package("7zip"),
      Package("yazi"),
      Package("zoxide"),

      # Monitoring + Analyse
      Package("btop"),
      Package("htop"),
      Package("iotop"),
      Package("ncdu"),
      Package("ryzen_monitor-git"),
      Package("bandwhich"),

      # Development und Libraries
      Package("git"),
      Package("git-lfs"),
      Package("tig"),
      Package("python"),
      Package("pyenv"),

      # Networking
      Package("bind"),
      Package("networkmanager"),
      Package("openbsd-netcat"),
      Package("traceroute"),
      Package("wireguard-tools"),
      Package("wget"),
      Package("openssh"),

      # Hardware Utilities
      Package("cpupower"),
      Package("bluez-utils"),

      # Dateisysteme
      Package("gparted"),
      Package("ntfs-3g"),
      Package("dosfstools"),

      SystemdUnit("NetworkManager.service"),
      SystemdUnit("wpa_supplicant.service"),
      SystemdUnit("sshd.service"),
      SystemdUnit("systemd-timesyncd.service"),

      Hook(
        "regenerate-locales",
        execute = ShellCommand("locale-gen"),
        triggered_by = [
          File("/etc/locale.gen"),
          File("/etc/locale.conf"),
        ],
      ),

      File("/etc/vconsole.conf", permissions = 0o444, content = cleandoc('''
        # managed by arch-config
        KEYMAP=de-latin1
        FONT=ter-124b
      ''')),

      File(
        "/etc/locale.conf",
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
        "/etc/locale.gen",
        on_file_change = ShellCommand("locale-gen"),
        permissions = 0o444,
        content = cleandoc('''
        en_US.UTF-8 UTF-8
        de_DE.UTF-8 UTF-8
        # Zeilenumbruch hinter den Locales ist wichtig, sonst werden sie ignoriert
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
    )
