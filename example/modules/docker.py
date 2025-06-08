from koti import *


def docker() -> ConfigGroups:
  return ConfigGroup(
    Package("docker"),
    Package("docker-compose"),
    Package("containerd"),
  )
