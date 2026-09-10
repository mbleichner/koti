from inspect import cleandoc

from koti import *
from koti.utils.shell import shell


def ollama_aichat(cuda: bool) -> ConfigDict:
  ollama_model = "Godmoded/llama3-lexi-uncensored"
  return {
    Section("ollama + aichat"): (
      Package("aichat"),
      Package("ollama-cuda" if cuda else "ollama"),
      File("/home/manuel/.config/aichat/config.yaml", owner = "manuel", content = cleandoc(f'''
        model: ollama:{ollama_model}
        serve_addr: 0.0.0.0:8000
        clients:
        - type: openai-compatible
          name: ollama
          api_base: http://localhost:11434/v1
          api_key: null
      ''')),
      SystemdUnit("ollama.service"),
      PostHook(
        name = f"download {ollama_model}",
        trigger = File("/home/manuel/.config/aichat/config.yaml"),
        execute = lambda: shell(f"ollama pull {ollama_model}"),
      ),
    )
  }
