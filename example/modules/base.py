from inspect import cleandoc

from koti import *
from koti.utils import *


def base(cachyos_repo: bool) -> ConfigGroups: return [
  ConfigGroup(
    "base-packages",

    Package("linux-firmware"),
    Package("efibootmgr"),
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
    Package("bandwhich"),

    # Development und Libraries
    Package("git"),
    Package("git-lfs"),
    Package("tig"),
    Package("python"),
    Package("pyenv"),

    # Networking
    Package("bind"),
    Package("openbsd-netcat"),
    Package("traceroute"),
    Package("wireguard-tools"),
    Package("wget"),

    # Hardware Utilities
    Package("cpupower"),
    Package("bluez-utils"),

    # Dateisysteme
    Package("gparted"),
    Package("ntfs-3g"),
    Package("dosfstools"),

    SystemdUnit("systemd-timesyncd.service"),
    SystemdUnit("systemd-boot-update.service"),
  ),

  ConfigGroup(
    "cachyos-repo",
    ConfirmMode("paranoid"),
    PacmanKey("cachyos", key_id = "F3B607488DB35A47"),
    Package(
      "cachyos-keyring",
      url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-keyring-20240331-1-any.pkg.tar.zst"
    ),
    Package(
      "cachyos-mirrorlist",
      url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-mirrorlist-22-1-any.pkg.tar.zst"
    ),
    Package(
      "cachyos-v3-mirrorlist",
      url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-v3-mirrorlist-22-1-any.pkg.tar.zst"
    ),
  ) if cachyos_repo else None,

  ConfigGroup(
    "pacman-config",

    ConfirmMode("paranoid"),
    Requires(
      Package("cachyos-keyring"),
      Package("cachyos-mirrorlist"),
      Package("cachyos-v3-mirrorlist")
    ) if cachyos_repo else None,

    File("/etc/pacman.conf", permissions = 0o444, content = cleandoc('''
        # managed by koti
        [options]
        HoldPkg = pacman glibc
        Architecture = auto x86_64_v3
        NoExtract = etc/xdg/autostart/org.kde.discover.notifier.desktop
        Color
        CheckSpace
        VerbosePkgLists
        ParallelDownloads = 5
        DownloadUser = alpm
        SigLevel = Required DatabaseOptional
        LocalFileSigLevel = Optional

        [core]
        Include = /etc/pacman.d/mirrorlist
        [extra]
        Include = /etc/pacman.d/mirrorlist
        [multilib]
        Include = /etc/pacman.d/mirrorlist

        # Arch Testing (nur für explizit installierte Pakete, z.B. Nvidia-Treiber)
        [core-testing]
        Include = /etc/pacman.d/mirrorlist
        [extra-testing]
        Include = /etc/pacman.d/mirrorlist
        [multilib-testing]
        Include = /etc/pacman.d/mirrorlist
      ''' + ('''
        # CachyOS für den Kernel
        [cachyos-v3]
        Include = /etc/pacman.d/cachyos-v3-mirrorlist
        [cachyos]
        Include = /etc/pacman.d/cachyos-mirrorlist
      ''' if cachyos_repo else ""))),

    File("/etc/paru.conf", permissions = 0o444, content = cleandoc('''
        # managed by koti
        [options]
        PgpFetch
        Devel
        Provides
        DevelSuffixes = -git -cvs -svn -bzr -darcs -always -hg -fossil
        RemoveMake
        SudoLoop
        CombinedUpgrade
        CleanAfter
     ''')),

    File("/etc/pacman.d/hooks/nvidia.hook", permissions = 0o444, content = cleandoc('''
        # managed by koti
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

    File("/etc/xdg/reflector/reflector.conf", permissions = 0o444, content = cleandoc('''
        # managed by koti
        --save /etc/pacman.d/mirrorlist
        --protocol https
        --country France,Germany,Switzerland
        --latest 5
        --sort delay
     ''')),

    Package("pacman-contrib"),
    Package("pacutils"),
    Package("paru"),
    Package("base-devel"),
    Package("reflector"),
    Package("lostfiles"),
  ),

  ConfigGroup(
    "arch-update",

    Package("arch-update"),

    File("/home/manuel/.config/arch-update/arch-update.conf", owner = "manuel", permissions = 0o444, content = cleandoc('''
        # managed by koti
        NoNotification
        KeepOldPackages=2
        KeepUninstalledPackages=0
        DiffProg=diff
        TrayIconStyle=light
      ''')),

    SystemdUnit("arch-update-tray.service", user = "manuel"),
    SystemdUnit("arch-update.timer", user = "manuel"),

    PostHook(
      "restart arch-update-tray",
      execute = lambda: "systemctl --user -M manuel@ restart arch-update-tray.service"
    ),
  ),

  ConfigGroup(

    File("/boot/loader/loader.conf", permissions = 0o555, content = cleandoc(f'''
      # managed by koti
      timeout 3
      console-mode 2
    ''')),

    File("/etc/modprobe.d/disable-watchdog-modules.conf", permissions = 0o444, content = cleandoc('''
      # managed by koti
      blacklist sp5100_tco
    ''')),

    File("/etc/vconsole.conf", permissions = 0o444, content = cleandoc('''
      # managed by koti
      KEYMAP=de-latin1
      FONT=ter-124b
    ''')),

    File("/etc/sudoers", permissions = 0o444, content = cleandoc('''
      # managed by koti
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
      # managed by koti
      ACTION=="add", SUBSYSTEM=="usb", DRIVERS=="usb", ATTR{power/wakeup}="disabled"
    ''')),

    File("/home/manuel/.gitconfig", owner = "manuel", permissions = 0o444, content = cleandoc('''
      # managed by koti
      [user]
      email = mbleichner@gmail.com
      name = Manuel Bleichner
      [pull]
      rebase = true
    ''')),

    File("/home/manuel/.config/tealdeer/config.toml", owner = "manuel", permissions = 0o444, content = cleandoc('''
      # managed by koti
      [updates]
      auto_update = true
    ''')),
  ),

  ConfigGroup(
    "ssh-server",

    Package("openssh"),
    SystemdUnit("sshd.service"),

    File("/etc/ssh/sshd_config", owner = "root", permissions = 0o444, content = cleandoc('''
      # managed by koti
      Include /etc/ssh/sshd_config.d/*.conf
      PermitRootLogin yes
      AuthorizedKeysFile .ssh/authorized_keys
      Subsystem sftp /usr/lib/ssh/sftp-server
    ''')),
  ),

  ConfigGroup(
    "locale-setup",

    File("/etc/locale.conf", permissions = 0o444, content = cleandoc('''
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

    File("/etc/locale.gen", permissions = 0o444, content = cleandoc('''
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


def swapfile(swapfile_gb: int) -> ConfigGroups: return [
  ConfigGroup(
    "swapfile",
    Swapfile("/swapfile", swapfile_gb * 1024 ** 3),  # 8GB
  )
]
