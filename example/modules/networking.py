from typing import Generator

from koti import *


def network_manager() -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "network-manager and wifi",
    provides = [
      Package("networkmanager"),
      SystemdUnit("NetworkManager.service"),
      SystemdUnit("wpa_supplicant.service"),
    ]
  )
