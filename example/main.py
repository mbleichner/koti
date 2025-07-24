import sys
sys.dont_write_bytecode = True  # disable bytecode compilation (can cause issues with root-owned cache-files)

from koti import *
from koti.utils import confirm
from systems import *  # my system configs
from socket import gethostname

my_arch_systems = {
  "dan": dan(),  # DAN A4-SFX desktop PC
  "lenovo": lenovo(),  # Lenovo X13 laptop
  "mserver": mserver(),  # homelab server
}

koti = Koti(
  configs = my_arch_systems[gethostname()],  # choose system config based on the current hostname
  managers = KotiManagerPresets.arch(PacmanAdapter("sudo -u manuel paru")),  # predefined managers for Arch Linux, but use paru instead of pacman
)

if koti.plan():
  confirm("confirm execution")
  koti.apply()
  print("execution finished.")
