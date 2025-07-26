from inspect import cleandoc
from typing import Generator

from koti import *
from koti.items import *
from koti.items.hooks import PostHookTriggerScope
from koti.utils import shell


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

      *PostHookTriggerScope(
        # https://wiki.cachyos.org/configuration/general_system_tweaks
        File("/etc/sysctl.d/99-splitlock.conf", permissions = "r--", content = cleandoc('''
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

      File("/etc/modules-load.d/proton-ntsync.conf", permissions = "r--", content = cleandoc(f'''
        # ntsync module has to be loaded manually in order for proton to be able to use it
        ntsync
      ''')),

      File("/etc/environment.d/proton-wayland.conf", permissions = "r--", content = cleandoc(f'''
        PROTON_ENABLE_WAYLAND=1
      ''')),

      File("/usr/bin/steam", permissions = "r-x", content = cleandoc(f'''
        #!/bin/sh
        
        # Workaround für Wine/Wayland Keyboard Layout Bug
        # https://bugs.winehq.org/show_bug.cgi?id=57097#c7
        export LC_ALL=de_DE.UTF-8
        
        exec /usr/lib/steam/steam "$@"
      ''')),

      Option("/etc/pacman.conf/NoUpgrade", "usr/bin/steam"),
    ]
  )
