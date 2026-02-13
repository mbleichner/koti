from inspect import cleandoc

from koti import *
from koti.utils.shell import shell


def cpufreq(min_freq: int, max_freq: int, governor: str) -> ConfigDict:
  return {
    Section("set default cpu frequency range and governor"): (
      Package("cpupower"),
      File("/etc/default/cpupower-service.conf", content = cleandoc(f'''
        GOVERNOR="{governor}"
        MIN_FREQ="{min_freq}MHz"
        MAX_FREQ="{max_freq}MHz"
      '''))
    )
  }


def throttle_after_boot(freq: int) -> ConfigDict:
  return {
    Section(f"throttle CPU to {freq}MHz after boot"): (
      Package("cpupower"),
      File("/etc/systemd/system/cpu-freq-after-boot.service", content = cleandoc(f'''
        [Unit]
        Description=Throttle CPU after boot
  
        [Service]
        Type=simple
        ExecStart=/bin/sh -c "sleep 8 && cpupower frequency-set -u {freq}MHz"
  
        [Install]
        WantedBy=graphical.target
      ''')),
      SystemdUnit("cpu-freq-after-boot.service"),
    )
  }


def auto_cpufreq(base_freq: int) -> ConfigDict:
  return {
    Section(f"automatic cpu frequency switching"): (
      File(f"/opt/systray/cpu/actions/max-freq-{base_freq}mhz", permissions = "rwxr-xr-x"),  # dependency
      *PostHookScope(
        File("/opt/auto-cpu-freq/auto-cpu-freq.py", source = "files/auto-cpu-freq.py", permissions = "r-x"),
        File("/etc/systemd/system/auto-cpu-freq.service", content = cleandoc(f'''
          [Unit]
          Description=Auto adjust CPU frequency
    
          [Service]
          Type=simple
          ExecStart=/bin/sh -c "sleep 8 && /opt/auto-cpu-freq/auto-cpu-freq.py {base_freq}"
    
          [Install]
          WantedBy=graphical.target
        ''')),
        SystemdUnit("auto-cpu-freq.service"),
        PostHook(
          name = "restart auto-cpu-freq.service on script updates",
          execute = lambda: shell("systemctl restart auto-cpu-freq.service"),
        ),
      )
    )
  }
