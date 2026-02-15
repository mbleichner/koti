from inspect import cleandoc

from koti import *
from modules.cpu import systray_dialog


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


def systray_gpu_power_limit(filename: str, watt: int) -> File:
  return File(filename, permissions = "rwxr-xr-x", content = cleandoc(f'''
    #!/bin/bash
    sudo nvidia-smi -i 0 -pl {watt}
  '''))


def nvidia_undervolting() -> ConfigDict:
  return {
    Section("NVIDIA 3080 undervolting + clock tuning"): (
      Package("python-nvidia-ml-py"),

      File("/opt/undervolting/nvidia-undervolting.py", content = cleandoc('''
        from pynvml import *

        nvmlInit()
        myGPU = nvmlDeviceGetHandleByIndex(0)

        # Power Limit in Milliwatt
        nvmlDeviceSetPowerManagementLimit(myGPU, 220000)

        # Memory und Core Offsets
        nvmlDeviceSetGpcClkVfOffset(myGPU, 200)
        nvmlDeviceSetMemClkVfOffset(myGPU, 500)

        # Core Taktrate begrenzen, sonst reicht die verringerte Spannung nicht mehr aus
        nvmlDeviceSetGpuLockedClocks(myGPU, 210, 1710)
      ''')),

      File("/etc/systemd/system/nvidia-undervolting.service", content = cleandoc('''
        [Unit]
        Description=NVIDIA Undervolting

        [Service]
        Type=oneshot
        RemainAfterExit=true
        WorkingDirectory=/opt/undervolting
        ExecStart=/usr/bin/python3 nvidia-undervolting.py

        [Install]
        WantedBy=multi-user.target
     ''')),

      SystemdUnit("nvidia-undervolting.service"),
    )
  }
