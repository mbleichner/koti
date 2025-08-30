from koti import *
from koti.utils import *


def koti_dev() -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "tools for koti development",
    provides = [
      Package("python"),
      Package("pyenv"),
      Package("mypy"),
      Package("python-urllib3"),
      Package("distrobox"),
      Package("docker"),
      Package("containerd"),
      SystemdUnit("docker.socket"),
    ]
  )
