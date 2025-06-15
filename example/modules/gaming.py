from koti import *
from koti.utils import shell_interactive


def gaming() -> ConfigGroups: return [

  ConfigGroup(
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
  ),

  ConfigGroup(
    # https://wiki.cachyos.org/configuration/general_system_tweaks
    File("/etc/sysctl.d/99-splitlock.conf", permissions = 0o444, content = "kernel.split_lock_mitigate=0"),
    PostHook("apply-splitlock-sysctl", execute = lambda: shell_interactive("sysctl --system")),
  ),
]
