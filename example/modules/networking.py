from koti import *


def network_manager() -> ConfigGroups:
  return ConfigGroup(
    description = "network-manager and wifi",
    provides = [
      Package("networkmanager"),
      SystemdUnit("NetworkManager.service"),
      SystemdUnit("wpa_supplicant.service"),
    ]
  )
