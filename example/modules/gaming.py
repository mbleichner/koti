from inspect import cleandoc

from koti import *
from koti.items.hooks import PostHookTriggerScope
from koti.utils import shell


def gaming() -> ConfigGroups: return [
  ConfigGroup(
    name = "gaming-packages",
    provides = [
      Package("discord"),
      Package("gamescope"),
      Package("gpu-screen-recorder-ui"),
      Package("proton-ge-custom-bin"),
      Package("protontricks"),
      Package("ryujinx"),
      Package("steam"),
      Package("nexusmods-app-bin"),
      Package("r2modman-bin"),
      Package("mangohud"),
    ]),

  ConfigGroup(
    name = "gaming-settings",
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
  ),
]
