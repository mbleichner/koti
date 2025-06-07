from inspect import cleandoc

from koti import *


def ollama_aichat(nvidia: bool) -> ConfigGroups:
  return ConfigGroup(
    Package("aichat"),
    Package("ollama-cuda" if nvidia else "ollama"),
    File("/home/manuel/.config/aichat/config.yaml", permissions = 0o444, owner = "manuel", content = cleandoc('''
      # managed by koti
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
