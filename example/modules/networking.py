from koti import *


def network_manager() -> ConfigDict:
  return {
    Section("network-manager and wifi"): (
      Package("networkmanager"),
      SystemdUnit("NetworkManager.service"),
      SystemdUnit("wpa_supplicant.service"),
    )
  }
