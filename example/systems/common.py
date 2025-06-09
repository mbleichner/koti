from koti import *
from modules.ananicy import ananicy
from modules.base import base
from modules.cpufreq import cpufreq
from modules.fish import fish
from modules.pacman import pacman


# Configuration that is shared between all of my systems
def common(cachyos_repo: bool, swapfile_gb: int, min_freq: int, max_freq: int, governor: str, throttle_after_boot: bool) -> ConfigGroups: return [
  pacman(cachyos_repo = cachyos_repo),
  base(swapfile_gb = swapfile_gb),
  fish(),
  ananicy(),
  cpufreq(
    min_freq = min_freq,
    max_freq = max_freq,
    governor = governor,
    throttle_after_boot = throttle_after_boot,
  ),
]
