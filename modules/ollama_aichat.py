from inspect import cleandoc

from lib import ConfigItemGroup, ConfigModule, ConfigModuleGroups
from managers.file import File
from managers.pacman import PacmanPackage
from managers.systemd import SystemdUnit


class OllamaAichatModule(ConfigModule):
  def __init__(self, nvidia: bool):
    self.nvidia = nvidia

  def provides(self) -> ConfigModuleGroups:
    return ConfigItemGroup(
      PacmanPackage("aichat"),
      PacmanPackage("ollama-cuda" if self.nvidia else "ollama"),
      File("/home/manuel/.config/aichat/config.yaml", permissions = 0o444, owner = "manuel", content = cleandoc('''
        # managed by arch-config
        model: ollama:Godmoded/llama3-lexi-uncensored
        serve_addr: 0.0.0.0:8000
        clients:
        - type: openai-compatible
          name: ollama
          api_base: http://localhost:11434/v1
          api_key: null
      ''')),
      SystemdUnit("ollama.service")
    )
