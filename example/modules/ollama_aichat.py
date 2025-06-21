from inspect import cleandoc
from typing import Generator

from koti import *


def ollama_aichat(cuda: bool) -> Generator[ConfigGroup]:
  yield ConfigGroup(
    description = "ollama + aichat",
    provides = [
      Package("aichat"),
      Package("ollama-cuda" if cuda else "ollama"),
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
    ]
  )
