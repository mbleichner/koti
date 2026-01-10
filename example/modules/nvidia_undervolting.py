from inspect import cleandoc

from koti import *


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
