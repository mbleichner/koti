from inspect import cleandoc

from definitions import ConfigItemGroup, ConfigModule, ConfigModuleGroups, Requires
from managers.file import File
from managers.package import Package


class PacmanModule(ConfigModule):
  def __init__(self, cachyos: bool):
    self.cachyos = cachyos

  def provides(self) -> ConfigModuleGroups:
    return ConfigItemGroup(

      Requires(
        Package("cachyos-keyring"),
        Package("cachyos-mirrorlist"),
        Package("cachyos-v3-mirrorlist")
      ),

      File("/etc/pacman.conf", permissions = 0o444, content = cleandoc('''
        # managed by arch-config
        [options]
        HoldPkg     = pacman glibc
        Architecture = auto x86_64_v3
        NoExtract   = etc/xdg/autostart/org.kde.discover.notifier.desktop
        Color
        CheckSpace
        VerbosePkgLists
        ParallelDownloads = 5
        DownloadUser = alpm
        SigLevel    = Required DatabaseOptional
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
      ''' + '''
        # CachyOS für den Kernel
        [cachyos-v3]
        Include = /etc/pacman.d/cachyos-v3-mirrorlist
        [cachyos]
        Include = /etc/pacman.d/cachyos-mirrorlist
      ''' if self.cachyos else "")),

      File("/etc/paru.conf", permissions = 0o444, content = cleandoc('''
        # managed by arch-config
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
        # managed by arch-config
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
        # managed by arch-config
        --save /etc/pacman.d/mirrorlist
        --protocol https
        --country France,Germany,Switzerland
        --latest 5
        --sort delay
     ''')),

      Package("pacman-contrib"),
      Package("pacutils"),
      Package("paru"),
      Package("decman"),
      Package("arch-update"),
      Package("base-devel"),
      Package("reflector"),
      Package("lostfiles"),
    )
