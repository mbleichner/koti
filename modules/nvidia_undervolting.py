from inspect import cleandoc

from definitions import ConfigItemGroup, ConfigModule, ConfigModuleGroups
from managers.file import File
from managers.package import Package
from managers.systemd import SystemdUnit


class NvidiaUndervoltingModule(ConfigModule):

  def provides(self) -> ConfigModuleGroups:
    return ConfigItemGroup(
      Package("python-pynvml"),

      File("/opt/undervolting/nvidia-undervolting.py", permissions = 0o444, content = cleandoc('''
        # Managed by decman
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

      File("/etc/systemd/system/nvidia-undervolting.service", permissions = 0o444, content = cleandoc('''
        # Managed by decman
        [Unit]
        Description=NVIDIA Undervolting
        
        [Service]
        Type=oneshot
        RemainAfterExit=true
        WorkingDirectory=/opt/undervolting
        ExecStart=/usr/bin/python3 nvidia-undervolting.py --corecount 8 --offset -30
        
        [Install]
        WantedBy=multi-user.target
     ''')),
      SystemdUnit("nvidia-undervolting.service")
    )
