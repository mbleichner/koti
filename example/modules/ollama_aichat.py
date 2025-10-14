from inspect import cleandoc

from koti import *


def ollama_aichat(cuda: bool) -> ConfigDict:
  return {
    Section("ollama + aichat"): (
      Package("aichat"),
      Package("ollama-cuda" if cuda else "ollama"),
      File("/home/manuel/.config/aichat/config.yaml", owner = "manuel", content = cleandoc('''
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
  }
