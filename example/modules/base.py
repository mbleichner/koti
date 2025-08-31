from koti import *
from koti.utils import *


def base() -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "base packages needed on every system",
    provides = [
      Package("efibootmgr"),
      Package("base"),
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
      Package("nload"),

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
      Package("ethtool"),
      Package("tcpdump"),

      # Hardware Utilities
      Package("cpupower"),
      Package("bluez-utils"),
      Package("fwupd"),

      # Dateisysteme
      Package("gparted"),
      Package("ntfs-3g"),
      Package("dosfstools"),

      # Alternatives
      Package("zlib-ng"),
      Package("zlib-ng-compat"),

      SystemdUnit("systemd-timesyncd.service"),
      SystemdUnit("systemd-boot-update.service"),
      SystemdUnit("fstrim.timer"),
      SystemdUnit("fwupd.service"),
    ]
  )

  yield ConfigGroup(
    description = "bootstrap keyrings, pacman, paru",
    tags = ["bootstrap"],
    before = lambda item: isinstance(item, Package) and not "bootstrap" in item.tags,
    provides = [
      PacmanKey("F3B607488DB35A47", comment = "cachyos"),
      Package("cachyos-keyring", url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-keyring-20240331-1-any.pkg.tar.zst"),
      Package("cachyos-mirrorlist", url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-mirrorlist-22-1-any.pkg.tar.zst"),
      Package("cachyos-v3-mirrorlist", url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-v3-mirrorlist-22-1-any.pkg.tar.zst"),

      User(
        username = "manuel",
        home = "/home/manuel",
        shell = "/usr/bin/fish",
        groups = ["games", "wheel"], # FIXME: Gruppen anlegen, falls noch nicht vorhanden
      ),

      Package("paru", script = lambda model: shell("""
        builddir=$(mktemp -d -t paru.XXXXXX)
        echo $?
        echo $builddir
        git clone https://aur.archlinux.org/paru.git $builddir
        makepkg -si -D $builddir
      """, sudo = "manuel")),

      # Declare options for pacman.conf (so I don't have to null-check later)
      Option[str]("/etc/pacman.conf/NoExtract"),
      Option[str]("/etc/pacman.conf/NoUpgrade"),

      File("/etc/pacman.conf", permissions = "r--", content = lambda model: cleandoc(f'''
        [options]
        HoldPkg = pacman glibc
        Architecture = auto x86_64_v3
        NoExtract = {" ".join(model.item(Option[str]("/etc/pacman.conf/NoExtract")).distinct())}
        NoUpgrade = {" ".join(model.item(Option[str]("/etc/pacman.conf/NoUpgrade")).distinct())}
        Color
        CheckSpace
        VerbosePkgLists
        ParallelDownloads = 8
        DownloadUser = alpm
        SigLevel = Required DatabaseOptional
        LocalFileSigLevel = Optional
    
        [core]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
    
        [extra]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
    
        [multilib]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
    
        [core-testing]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
    
        [extra-testing]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
    
        [multilib-testing]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
    
        [cachyos-v3]
        CacheServer = http://pacoloco.fritz.box/repo/cachyos-v3/$arch_v3/$repo
        Include = /etc/pacman.d/cachyos-v3-mirrorlist
    
        [cachyos]
        CacheServer = http://pacoloco.fritz.box/repo/cachyos/$arch/$repo
        Include = /etc/pacman.d/cachyos-mirrorlist
      ''')),

      File("/etc/paru.conf", permissions = "r--", content = cleandoc('''
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
    ]
  )

  yield ConfigGroup(
    description = "pacman related utilities",
    tags = ["CRITICAL"],
    provides = [
      Package("pacman-contrib"),
      Package("pacutils"),
      Package("base-devel"),
      Package("reflector"),
      Package("lostfiles"),

      File("/etc/pacman.d/hooks/nvidia.hook", permissions = "r--", content = cleandoc('''
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

      File("/etc/xdg/reflector/reflector.conf", permissions = "r--", content = cleandoc('''
        --save /etc/pacman.d/mirrorlist
        --protocol https
        --country France,Germany,Switzerland
        --latest 5
        --sort delay
      ''')),

      PostHook(
        name = "reflector: update mirrorlist",
        trigger = File("/etc/xdg/reflector/reflector.conf"),
        execute = lambda: shell("systemctl start reflector"),
      ),
    ]
  )

  yield ConfigGroup(
    description = "tools for koti development",
    provides = [
      Package("python"),
      Package("pyenv"),
      Package("mypy"),
      Package("python-urllib3"),
      Package("distrobox"),
      Package("docker"),
      Package("containerd"),
      SystemdUnit("docker.socket"),
    ]
  )

  yield ConfigGroup(
    description = "sudo + /etc/sudoers",
    provides = [
      Package("sudo"),
      File("/etc/sudoers", permissions = "r--", content = cleandoc('''
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
    ],
  )

  yield ConfigGroup(
    description = "arch-update (for user manuel)",
    provides = [
      Package("arch-update"),
      File("/home/manuel/.config/arch-update/arch-update.conf", owner = "manuel", permissions = "r--", content = cleandoc('''
        NoNotification
        KeepOldPackages=2
        KeepUninstalledPackages=0
        DiffProg=diff
        TrayIconStyle=light
      ''')),
      SystemdUnit("arch-update-tray.service", user = "manuel"),
      SystemdUnit("arch-update.timer", user = "manuel"),
      PostHook("restart-arch-update-tray", execute = lambda: "systemctl --user -M manuel@ restart arch-update-tray.service", trigger = [
        File("/home/manuel/.config/arch-update/arch-update.conf"),
      ]),
    ]
  )

  yield ConfigGroup(
    description = "various system config files",
    provides = [
      File("/etc/environment.d/editor.conf", permissions = "r--", content = cleandoc(f'''
        EDITOR=nano
      ''')),

      File("/boot/loader/loader.conf", permissions = "r-x", content = cleandoc(f'''
        timeout 3
        console-mode 2
      ''')),

      File("/etc/vconsole.conf", permissions = "r--", content = cleandoc('''
        KEYMAP=de-latin1
        FONT=ter-124b
      ''')),

      File("/etc/modprobe.d/disable-watchdog-modules.conf", permissions = "r--", content = cleandoc('''
        blacklist sp5100_tco
      ''')),

      File("/home/manuel/.gitconfig", owner = "manuel", permissions = "r--", content = cleandoc('''
        [user]
        email = mbleichner@gmail.com
        name = Manuel Bleichner
        [pull]
        rebase = true
      ''')),

      File("/home/manuel/.config/tealdeer/config.toml", owner = "manuel", permissions = "r--", content = cleandoc('''
        [updates]
        auto_update = true
      ''')),

      File("/etc/locale.conf", permissions = "r--", content = cleandoc('''
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

      File("/etc/locale.gen", permissions = "r--", content = cleandoc('''
        en_US.UTF-8 UTF-8
        de_DE.UTF-8 UTF-8
        # Zeilenumbruch hinter den Locales ist wichtig, sonst werden sie ignoriert
      ''')),

      PostHook("regenerate-locales", execute = lambda: shell("locale-gen"), trigger = [
        File("/etc/locale.gen"),
      ]),
    ]
  )

  yield ConfigGroup(
    description = "ssh daemon + config",
    provides = [
      Package("openssh"),
      SystemdUnit("sshd.service"),
      File("/etc/ssh/sshd_config", owner = "root", permissions = "r--", content = cleandoc('''
        Include /etc/ssh/sshd_config.d/*.conf
        PermitRootLogin yes
        AuthorizedKeysFile .ssh/authorized_keys
        Subsystem sftp /usr/lib/ssh/sftp-server
      ''')),
    ],
  )


def swapfile(swapfile_gb: int) -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = f"swapfile ({swapfile_gb} GByte)",
    provides = [
      Swapfile("/swapfile", swapfile_gb * 1024 ** 3),  # 8GB
    ]
  )
