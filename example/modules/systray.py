from inspect import cleandoc

from koti import *


def nvidia_systray() -> ConfigDict:
  return {
    Section("systray: GPU items"): (
      Package("kdialog"),
      Package("python-nvidia-ml-py"),
      Option[str]("/etc/sudoers/ExtraLines", value = "manuel ALL=(ALL:ALL) NOPASSWD: /usr/bin/nvidia-smi *"),
      File("/opt/systray/gpu/summary", permissions = "rwxr-xr-x", source = "files/gpu-summary"),
      systray_dialog("/opt/systray/gpu/dialog", "/opt/systray/gpu/actions"),
      systray_gpu_power_limit("/opt/systray/gpu/actions/power-limit-160w", 160),
      systray_gpu_power_limit("/opt/systray/gpu/actions/power-limit-180w", 180),
      systray_gpu_power_limit("/opt/systray/gpu/actions/power-limit-200w", 200),
      systray_gpu_power_limit("/opt/systray/gpu/actions/power-limit-220w", 220),
    ),
  }


def cpufreq_systray(freq_options: Sequence[int] = (1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500)) -> ConfigDict:
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
      *(systray_cpufreq_target(f"/opt/systray/cpu/actions/cpu-freq-{freq}mhz", freq) for freq in freq_options),
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


def systray_gpu_power_limit(filename: str, watt: int) -> File:
  return File(filename, permissions = "rwxr-xr-x", content = cleandoc(f'''
    #!/bin/bash
    sudo nvidia-smi -i 0 -pl {watt}
  '''))
