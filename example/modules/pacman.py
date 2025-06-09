from inspect import cleandoc

from koti import *


def pacman(cachyos_repo: bool) -> ConfigGroups: return [
  ConfigGroup(
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
  ),

  ConfigGroup(

    Requires(
      Package("cachyos-keyring"),
      Package("cachyos-mirrorlist"),
      Package("cachyos-v3-mirrorlist")
    ),

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
]
