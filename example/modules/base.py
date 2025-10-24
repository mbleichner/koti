from inspect import cleandoc

from koti import *
from koti.utils.shell import shell


def base() -> ConfigDict:
  return {
    Section("bootstrap sudo, pacman and paru"): (

      # setup sudo and sudo user
      Package("sudo", tags = "bootstrap"),
      User("manuel"),
      UserHome("manuel", homedir = "/home/manuel"),
      UserGroupAssignment("manuel", "wheel"),

      File("/etc/sudoers", permissions = 0o440, content = cleandoc('''
        Defaults!/usr/bin/visudo env_keep += "SUDO_EDITOR EDITOR VISUAL"
        Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/bin"
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

      # install CachyOS keyrings and mirrorlist, and set up pacman
      PacmanKey("F3B607488DB35A47"),
      Package("cachyos-keyring", url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-keyring-20240331-1-any.pkg.tar.zst", tags = "bootstrap"),
      Package("cachyos-mirrorlist", url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-mirrorlist-22-1-any.pkg.tar.zst", tags = "bootstrap"),
      Package("cachyos-v3-mirrorlist", url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-v3-mirrorlist-22-1-any.pkg.tar.zst", tags = "bootstrap"),
      Option[str]("/etc/pacman.conf/NoExtract"),  # Declare options for pacman.conf (so I don't have to null-check later)
      Option[str]("/etc/pacman.conf/NoUpgrade"),  # Declare options for pacman.conf (so I don't have to null-check later)
      File("/etc/pacman.conf", content = lambda model: cleandoc(f'''
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
      PostHook(
        name = "update pacman databases after config change",
        trigger = File("/etc/pacman.conf"),
        execute = lambda: shell("pacman -Syyu"),
      ),

      # install and configure paru
      Package("paru", script = lambda: shell("""
        builddir=$(mktemp -d -t paru.XXXXXX)
        git clone https://aur.archlinux.org/paru.git $builddir
        makepkg -si -D $builddir
      """, user = "manuel"), tags = "bootstrap"),
      File(
        filename = "/etc/paru.conf",
        before = lambda item: isinstance(item, Package) and "bootstrap" not in item.tags,
        content = cleandoc('''
          [options]
          PgpFetch
          Devel
          Provides
          DevelSuffixes = -git -cvs -svn -bzr -darcs -always -hg -fossil
          RemoveMake
          SudoLoop
          CombinedUpgrade
          CleanAfter
        '''),
      ),
    ),

    Section("base packages and configs needed on every system"): (

      # basic arch dependencies
      Package("base"),
      Package("base-devel"),
      Package("efibootmgr"),
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

      # Arch + Pacman Utilities
      Package("pacman-contrib"),
      Package("pacutils"),
      Package("lostfiles"),

      # Monitoring + Analyse
      Package("btop"),
      # Package("htop", before = User("manuel")),
      Package("htop"),
      Package("iotop"),
      Checkpoint("moep"),
      Package("ncdu"),
      Package("bandwhich"),
      Package("nload"),

      # Development und Libraries
      Package("git"),
      Package("git-lfs"),
      Package("tig"),

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

      File("/etc/environment.d/editor.conf", content = cleandoc(f'''
        EDITOR=nano
      ''')),

      File("/boot/loader/loader.conf", permissions = "rwxr-xr-x", content = cleandoc(f'''
        timeout 3
        console-mode 2
      ''')),

      File("/etc/vconsole.conf", content = cleandoc('''
        KEYMAP=de-latin1
        FONT=ter-124b
      ''')),

      File("/etc/modprobe.d/disable-watchdog-modules.conf", content = cleandoc('''
        blacklist sp5100_tco
      ''')),

      File("/home/manuel/.gitconfig", owner = "manuel", content = cleandoc('''
        [user]
        email = mbleichner@gmail.com
        name = Manuel Bleichner
        [pull]
        rebase = true
      ''')),

      File("/home/manuel/.config/tealdeer/config.toml", owner = "manuel", content = cleandoc('''
        [updates]
        auto_update = true
      ''')),

      File("/etc/pacman.d/hooks/paccache.hook", requires = Package("pacman-contrib"), content = cleandoc('''
        [Trigger]
        Operation = Upgrade
        Operation = Install
        Operation = Remove
        Type = Package
        Target = *
  
        [Action]
        When = PostTransaction
        Description = Cleaning package cache...
        Exec = /usr/bin/paccache -rk2 --quiet
        Exec = /usr/bin/paccache -ruk0 --quiet
      '''
      )),

      SystemdUnit("systemd-timesyncd.service"),
      SystemdUnit("systemd-boot-update.service"),
      SystemdUnit("fstrim.timer"),
      SystemdUnit("fwupd.service"),
      SystemdUnit("docker.socket"),
    ),

    Section("python development and koti dependencies"): (
      Package("python"),
      Package("pyenv"),
      Package("mypy"),
      Package("python-urllib3"),
      Package("python-pyscipopt"),
      Package("python-numpy"),
    ),

    Section("docker and containers"): (
      Package("docker"),
      Package("docker-compose"),
      Package("containerd"),
      UserGroupAssignment("manuel", "docker", requires = User("manuel")),
    ),

    Section("locales"): (
      File("/etc/locale.conf", content = cleandoc('''
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
      File("/etc/locale.gen", content = cleandoc('''
        en_US.UTF-8 UTF-8
        de_DE.UTF-8 UTF-8
        # without this linebreak, the last locale will be ignored
      ''')),
      PostHook("regenerate-locales", execute = lambda: shell("locale-gen"), trigger = File("/etc/locale.gen")),
    ),

    Section("reflector"): (
      Package("reflector"),
      *PostHookScope(
        File("/etc/xdg/reflector/reflector.conf", content = cleandoc('''
          --save /etc/pacman.d/mirrorlist
          --protocol https
          --country France,Germany,Switzerland
          --latest 5
          --sort delay
        ''')),
        PostHook(
          name = "reflector: update mirrorlist",
          execute = lambda: shell("systemctl start reflector"),
        ),
      )
    ),

    Section("arch-update"): (
      Package("arch-update"),
      File("/home/manuel/.config/arch-update/arch-update.conf", owner = "manuel", content = cleandoc('''
        NoNotification
        KeepOldPackages=2
        KeepUninstalledPackages=0
        DiffProg=diff
        TrayIconStyle=light
      ''')),
      SystemdUnit("arch-update-tray.service", user = "manuel"),
      SystemdUnit("arch-update.timer", user = "manuel"),
      PostHook(
        "restart-arch-update-tray",
        execute = lambda: shell("systemctl --user -M manuel@ restart arch-update-tray.service"),
        trigger = File("/home/manuel/.config/arch-update/arch-update.conf"),
      )
    ),

    Section("ssh daemon + config"): (
      Package("openssh"),
      File("/etc/ssh/sshd_config", owner = "root", content = cleandoc('''
        Include /etc/ssh/sshd_config.d/*.conf
        PermitRootLogin yes
        AuthorizedKeysFile .ssh/authorized_keys
        Subsystem sftp /usr/lib/ssh/sftp-server
      ''')),
      SystemdUnit("sshd.service"),
    )
  }


def swapfile(size_gb: int) -> ConfigDict:
  return {
    Section(f"swapfile ({size_gb} GByte)"): (
      Swapfile("/swapfile", size_gb * 1024 ** 3),  # 8GB
    )
  }
