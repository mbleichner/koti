from inspect import cleandoc

from koti import *


def cpufreq_defaults(min_freq: int, max_freq: int, governor: str) -> ConfigDict:
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


def cpufreq_auto_adjust(base_freq: int) -> ConfigDict:
  return {
    Section(f"automatic cpu frequency switching"): (
      Package("python-yaml"),
      Package("ryzen_smu-dkms-git"),
      Option[tuple[str, int]]("/etc/cpufreq/rules.yaml/ExtraEntries"),

      File("/etc/cpufreq/rules.yaml", permissions = "r--r--r--", content = lambda model: cleandoc(f'''
        "/usr/local/bin/koti": 3500
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


def cpufreq_systray(freq_options: list[int] = (1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500)) -> ConfigDict:
  return {
    Section("systray: CPU items"): (
      Package("yq"),  # needed to adjust target freq in /etc/cpufreq/state.yaml
      Package("moreutils"),  # sponge
      Package("kdialog"),
      Package("ryzen_smu-dkms-git"),

      Option[str]("/etc/sudoers/ExtraLines", value = [
        "manuel ALL=(ALL:ALL) NOPASSWD: /usr/bin/cpupower",
        "manuel ALL=(ALL:ALL) NOPASSWD: /usr/bin/tee /sys/devices/system/cpu/*",
        "manuel ALL=(ALL:ALL) NOPASSWD: /usr/bin/sponge /etc/cpufreq/state.yaml",
        "manuel ALL=(ALL:ALL) NOPASSWD: /usr/bin/systemctl restart cpufreq-adjuster.service",
      ]),

      File("/opt/systray/cpu/summary", permissions = "rwxr-xr-x", source = "files/cpu-summary"),
      systray_dialog("/opt/systray/cpu/dialog", "/opt/systray/cpu/actions"),

      File("/etc/systemd/system/cpufreq-adjuster.service"),  # dependency for the following items
      *(systray_cpufreq_target(f"/opt/systray/cpu/actions/max-freq-{freq}mhz", freq) for freq in freq_options),
      systray_cpufreq_mode("/opt/systray/cpu/actions/mode-auto", "auto"),
      systray_cpufreq_mode("/opt/systray/cpu/actions/mode-manual", "manual"),

      systray_cpu_governor("/opt/systray/cpu/actions/governor-performance", "performance"),
      systray_cpu_governor("/opt/systray/cpu/actions/governor-powersave", "powersave"),
      systray_hyperthreading("/opt/systray/cpu/actions/hyperthreading-on", "on"),
      systray_hyperthreading("/opt/systray/cpu/actions/hyperthreading-off", "off"),
    ),
  }


# ACHTUNG: Beim Aufruf des Skripts per Command Output Widget muss man aufgrund eines
# Bugs einen Parameter an das Skript übergeben, der überhaupt nicht benötigt wird
# z.B. /opt/systray/cpu/dialog moep
def systray_dialog(filename: str, actiondir: str) -> File:
  return File(filename, permissions = "rwxr-xr-x", content = cleandoc(r'''
    #!/bin/bash
    FILES=$(find ACTIONDIR/ -maxdepth 1 -perm -111 -type f -printf "%f\n" | sort)
    OPTIONS=$(echo "$FILES" | awk '{print $1 " " $1;}')
    HEIGHT=$(( 100 + 25 * $(echo "$FILES" | wc -l) ))
    SELECTION=$(kdialog --geometry "300x${HEIGHT}-400-0" --separate-output --menu "Skript auswählen:" $OPTIONS)
    if [[ -n "$SELECTION" ]]; then ACTIONDIR/$SELECTION; fi
  '''.replace("ACTIONDIR", actiondir)))


def systray_cpufreq_mode(filename: str, mode: Literal["manual", "auto"]) -> File:
  return File(filename, permissions = "rwxr-xr-x", content = cleandoc(f'''
    #!/bin/bash
    yq -y '.mode = "{mode}"' /etc/cpufreq/state.yaml | sudo sponge /etc/cpufreq/state.yaml
    sudo systemctl restart cpufreq-adjuster.service
  '''))


def systray_cpufreq_target(filename: str, freq: int) -> File:
  return File(filename, permissions = "rwxr-xr-x", content = cleandoc(f'''
    #!/bin/bash
    yq -y '.freq = {freq}' /etc/cpufreq/state.yaml | sudo sponge /etc/cpufreq/state.yaml
    sudo systemctl restart cpufreq-adjuster.service
  '''))


def systray_cpu_governor(filename: str, governor: str) -> File:
  return File(filename, permissions = "rwxr-xr-x", content = cleandoc(f'''
    #!/bin/bash
    sudo cpupower frequency-set -g {governor}
  '''))


def systray_hyperthreading(filename: str, state: str) -> File:
  return File(filename, permissions = "rwxr-xr-x", content = cleandoc(f'''
    #!/bin/bash
    echo {state} | sudo tee /sys/devices/system/cpu/smt/control
  '''))
