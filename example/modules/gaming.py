from inspect import cleandoc

from koti import *
from koti.items import *


def gaming(nvidia: bool) -> ConfigDict:
  return {
    Section("game launchers, proton, emulators, mod managers"): (
      # Package("amethyst-mod-manager"), # AUR
      Package("discord"),
      # Package("eden-git"), # Chaotic-AUR # macht aktuell Probleme wegen unerfüllbaren Dependencies
      Package("gamescope"),
      Package("gpu-screen-recorder-ui"),
      Package("faugus-launcher"), # CachyOS
      Package("mangohud"),
      Package("libxnvctrl") if nvidia else None, # optional dependency of mangohud to display GPU sensors
      Package("proton-cachyos-slr"),
      Package("proton-ge-custom-bin"), # AUR
      Package("protonplus"),
      Package("protontricks"),
      Package("r2modman-bin"), # AUR
      Package("steam"),
      Package("teamspeak3"),
      # Package("teamspeak"), # AUR
      UserGroupAssignment("manuel", "games"),

      # increase number of fossilize_replay processes
      File("/home/manuel/.steam/steam/steam_dev.cfg", owner = "manuel", content = cleandoc(f'''
        unShaderBackgroundProcessingThreads 16
      ''')),

      # Workaround für Wine/Wayland Keyboard Layout Bug (https://bugs.winehq.org/show_bug.cgi?id=57097#c7)
      File("/usr/bin/steam", permissions = "rwxr-xr-x", content = cleandoc(f'''
        #!/bin/sh
        export LC_ALL=de_DE.UTF-8
        exec /usr/lib/steam/steam "$@"
      ''')),

      Option[tuple[str, int]]("/etc/cpufreq/rules.yaml/ExtraEntries", value = [
        ("SteamLinuxRuntime", 4000),
        ("beyond-all-reason", 4000),
        ("/usr/bin/eden", 4000),
        ("wineserver", 4000),
        ("fossilize_replay", 3000),
      ]),

      Option("/etc/pacman.conf/NoExtract", "usr/bin/steam"),
      Option("/etc/pacman.conf/NoUpgrade", "usr/bin/steam"),
    ),

    Section("gaming optimizations"): (

      # Load ntsync module on boot
      File("/etc/modules-load.d/ntsync.conf", content = 'ntsync'),

      # Force use of wayland in proton if available
      File("/etc/environment.d/proton-wayland.conf", content = cleandoc(f'''
        PROTON_USE_WAYLAND=1
        PROTON_ENABLE_WAYLAND=1
      ''')),

      # enable vkd3d-proton descriptor heap (currently opt-in in proton-cachyos)
      File("/etc/environment.d/proton-descriptor-heap.conf", content = cleandoc(f'''
        VKD3D_CONFIG=descriptor_heap
      ''')),

      # Increase shader cache size on disk to avoid recompilation due to eviction (1st NVIDIA; 2nd AMD)
      File("/etc/environment.d/shader-cache-size.conf", content = cleandoc(f'''
        __GL_SHADER_DISK_CACHE_SIZE=20000000000
        MESA_SHADER_CACHE_MAX_SIZE=20G
      ''')),

      # disable splitlock mitigation
      File("/etc/sysctl.d/70-splitlock-mitigation.conf", content = cleandoc(f'''
        kernel.split_lock_mitigate=0
      ''')),
    ),

    Section("lossless scaling + frame generation"): (
      Package("lsfg-vk"),

      # Docs at https://lsfg-vk.dev/docs/configuration/configuration-options/
      # NOTE: only proton versions by Valve seem to be working correctly with lsfg-vk
      # NOTE: at the moment, the "lsfg-vk" branch must be selected in steam for the dll to be available
      # Apply to process:   LSFGVK_PROFILE=2x %command%
      # Testing/debugging:  LSFGVK_PROFILE=2x vkcube
      File("/home/manuel/.config/lsfg-vk/conf.toml", permissions = "rw-", owner = "manuel", content = cleandoc(f'''
        version = 2
        
        [global]
        log_level = "info"
        
        [[profile]]
        name = "2x"
        multiplier = 2
        flow_scale = 1.0
        pacing_mode = "vsync"
        performance_mode = true
      ''')),
    )
  }
