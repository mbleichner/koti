from inspect import cleandoc
from typing import Generator

from koti import *
from koti.items import *
from koti.utils.shell import shell


def gaming() -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "game launchers and utilities",
    provides = [
      Package("discord"),
      Package("gamescope"),
      Package("gpu-screen-recorder-ui"),
      Package("ryujinx"),
      Package("steam"),
      Package("nexusmods-app-bin"),
      Package("r2modman-bin"),
      Package("mangohud"),
      GroupAssignment("manuel", "games"),

      *PostHookScope(
        # https://wiki.cachyos.org/configuration/general_system_tweaks
        File("/etc/sysctl.d/99-splitlock.conf", content = cleandoc('''
          kernel.split_lock_mitigate=0
        ''')),
        PostHook("apply-splitlock-sysctl", execute = lambda: shell("sysctl --system")),
      )
    ]
  )

  yield ConfigGroup(
    description = "proton/wine + configs",
    provides = [
      Package("proton-ge-custom-bin"),
      Package("protontricks"),
      Package("protonplus"),

      File("/etc/modules-load.d/proton-ntsync.conf", content = cleandoc(f'''
        # ntsync module has to be loaded manually in order for proton to be able to use it
        # (not all proton version will actually use ntsync - e.g. proton-cachyos is built
        # without ntsync support atm due to technical issues)
        ntsync
      ''')),

      File("/etc/environment.d/proton-wayland.conf", content = cleandoc(f'''
        # Force use of wayland in proton if available
        PROTON_USE_WAYLAND=1
        PROTON_ENABLE_WAYLAND=1
      ''')),

      File("/usr/bin/steam", permissions = "rwxr-xr-x", content = cleandoc(f'''
        #!/bin/sh
        
        # Workaround für Wine/Wayland Keyboard Layout Bug
        # https://bugs.winehq.org/show_bug.cgi?id=57097#c7
        export LC_ALL=de_DE.UTF-8
        
        exec /usr/lib/steam/steam "$@"
      ''')),

      Option("/etc/pacman.conf/NoUpgrade", "usr/bin/steam"),
    ]
  )

  yield ConfigGroup(
    description = "lossless scaling + frame generation",
    provides = [
      # Package("lsfg-vk"),

      File("/home/manuel/.config/lsfg-vk/conf.toml", permissions = "rw-", owner = "manuel", content = cleandoc(f'''
        version = 1

        # See the docs at: https://github.com/PancakeTAS/lsfg-vk/wiki/
        # Since games get identified by their process name instead of their actual exe filename, we sometimes have to
        # override the process name, in order to be able to distinguish them properly:
        #   LSFG_PROCESS=helldivers2 %command%
        #
        # Almost every flag can be hot-reloaded, meaning you can edit the file while the game is running and it will apply instantly.
        # As long as you have an entry in the configuration at the time of launching the game, it will work just fine.
        
        [[game]]
        exe = "helldivers2" 
        multiplier = 2
        performance_mode = true
        
        [[game]]
        exe = "vkcube"
        multiplier = 2
        performance_mode = true
      ''')),
    ]
  )
