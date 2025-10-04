from inspect import cleandoc
from typing import Generator

from koti import *


def nvidia_undervolting() -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "NVIDIA 3080 undervolting + clock tuning",
    provides = [
      Package("python-pynvml"),
      SystemdUnit("nvidia-undervolting.service"),

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
    ]
  )
