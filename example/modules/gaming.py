from inspect import cleandoc
from typing import Generator

from koti import *
from koti.items.hooks import PostHookTriggerScope
from koti.utils import shell


def gaming() -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "gaming-packages",
    provides = [
      Package("discord"),
      Package("gamescope"),
      Package("gpu-screen-recorder-ui"),
      Package("proton-ge-custom-bin"),
      Package("protontricks"),
      Package("protonplus"),
      Package("ryujinx"),
      Package("steam"),
      Package("nexusmods-app-bin"),
      Package("r2modman-bin"),
      Package("mangohud"),
    ]
  )

  yield ConfigGroup(
    description = "gaming-settings",
    provides = [
      *PostHookTriggerScope(
        # https://wiki.cachyos.org/configuration/general_system_tweaks
        File("/etc/sysctl.d/99-splitlock.conf", permissions = 0o444, content = cleandoc('''
          # managed by koti
          kernel.split_lock_mitigate=0
        ''')),
        PostHook("apply-splitlock-sysctl", execute = lambda: shell("sysctl --system")),
      )
    ]
  )

  yield ConfigGroup(
    description = "proton + ntsync configs",
    provides = [
      File("/etc/modules-load.d/ntsync.conf", permissions = 0o444, content = cleandoc(f'''
        # managed by koti
        ntsync
      ''')),
      File("/etc/environment.d/proton.conf", permissions = 0o444, content = cleandoc(f'''
        # managed by koti
        PROTON_ENABLE_WAYLAND = 1
        PROTON_USE_NTSYNC = 1
        PROTON_USE_WOW64 = 1
      ''')),
    ]
  )


