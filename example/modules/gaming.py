from inspect import cleandoc

from koti import *
from koti.items import *


def gaming() -> ConfigDict:
  return {
    Section("game launchers and utilities"): (
      Package("eden-bin"),
      Package("steam"),
      Package("heroic-games-launcher-bin"),
      Package("lutris"),
      Package("discord"),
      Package("gamescope"),
      Package("gpu-screen-recorder-ui"),
      Package("r2modman-bin"),
      # *Packages("vortex", "dotnet-runtime-9.0"), # derzeit zu verbuggt
      Package("amethyst-mod-manager"),
      Package("mangohud"),
      UserGroupAssignment("manuel", "games"),

      File("/home/manuel/.steam/steam/steam_dev.cfg", owner = "manuel", content = cleandoc(f'''
        # number of fossilize_replay processes to run
        unShaderBackgroundProcessingThreads 16
      ''')),

      File("/usr/bin/steam", permissions = "rwxr-xr-x", content = cleandoc(f'''
        #!/bin/sh
    
        # Workaround für Wine/Wayland Keyboard Layout Bug
        # https://bugs.winehq.org/show_bug.cgi?id=57097#c7
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

    Section("proton"): (
      Package("proton-cachyos"),
      Package("proton-cachyos-slr"),
      Package("proton-ge-custom-bin"),
      Package("protontricks"),
      Package("protonplus"),

      File("/etc/environment.d/proton-wayland.conf", content = cleandoc(f'''
        # Force use of wayland in proton if available
        PROTON_USE_WAYLAND=1
        PROTON_ENABLE_WAYLAND=1
      ''')),
    ),

    Section("gaming optimizations"): (
      # Increase shader cache size on disk to avoid recompilation due to eviction
      File("/etc/environment.d/shader-cache-size.conf", content = cleandoc(f'''
        # NVIDIA:
        __GL_SHADER_DISK_CACHE_SIZE=20000000000
        # AMD:
        MESA_SHADER_CACHE_MAX_SIZE=20G
      ''')),
      File("/etc/sysctl.d/splitlock-mitigation.conf", content = cleandoc(f'''
        kernel.split_lock_mitigate=0
      ''')),
    ),

    Section("lossless scaling + frame generation", disabled = True): (
      Package("lsfg-vk"),
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
    )
  }
