import subprocess

from definitions import ConfigModule, ConfigModuleGroups


class SwapfileModule(ConfigModule):
  def __init__(self, size_gb: int):
    self.size_gb = size_gb

  # FIXME

  def after_version_change(self):
    subprocess.run(["swapoff", "/swapfile"], check = False)
    subprocess.run(["rm", "-f", "/swapfile"], check = True)
    subprocess.run(["fallocate", "/swapfile", "-l", f"{self.size_gb}G"], check = True)
    subprocess.run(["chmod", "0600", "/swapfile"], check = True)
    subprocess.run(["mkswap", "/swapfile"], check = True)
    subprocess.run(["swapon", "/swapfile"], check = True)
