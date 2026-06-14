from inspect import cleandoc

from koti import *


def cpufreq_defaults(min_freq: int, max_freq: int, governor: str) -> ConfigDict:
  return {
    Section("set default cpu frequency range and governor"): (
      Package("cpupower"),
      File("/etc/default/cpupower-service.conf", content = cleandoc(f'''
        GOVERNOR={governor}
        MAX_FREQ={max_freq}MHz
        MIN_FREQ={min_freq}MHz
      ''')),
      SystemdUnit("cpupower.service"),
    )
  }


def cpufreq_auto_adjust(base_freq: int) -> ConfigDict:
  return {
    Section(f"automatic cpu frequency switching"): (
      Package("python-yaml"),
      Option[tuple[str, int]]("/etc/cpufreq/rules.yaml/ExtraEntries"),

      File("/etc/cpufreq/rules.yaml", permissions = "r--r--r--", content = lambda model: cleandoc(f'''
        "koti": 3500
        "borg": 3500
        "/usr/bin/pacman": 3500
        "/usr/bin/makepkg": 3500
      ''') + "\n\n" + format_processes_extra_entries(model)),

      File("/opt/cpufreq-adjuster/cpufreq-adjuster.py", source = "files/cpufreq-adjuster.py", permissions = "r-x"),

      File("/etc/systemd/system/cpufreq-adjuster.service", content = cleandoc(f'''
        [Unit]
        Description=Auto adjust CPU frequency
  
        [Service]
        Type=simple
        ExecStart=/opt/cpufreq-adjuster/cpufreq-adjuster.py auto {base_freq}
        RemainAfterExit=true
      ''')),

      File("/etc/systemd/system/cpufreq-adjuster.timer", content = cleandoc(f'''
        [Unit]
        Description=Start cpufreq-adjuster a few seconds after boot
        
        [Timer]
        OnBootSec=15sec
        
        [Install]
        WantedBy=graphical.target
      ''')),

      SystemdUnit("cpufreq-adjuster.timer"),
    )
  }


def format_processes_extra_entries(model: ConfigModel) -> str:
  entries = model.item(Option[tuple[str, int]]("/etc/cpufreq/rules.yaml/ExtraEntries")).distinct()
  return "\n".join(f'"{name}": {freq}' for name, freq in entries)
