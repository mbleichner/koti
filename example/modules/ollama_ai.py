from inspect import cleandoc

from koti import *
from koti.utils.shell import shell


def ollama_ai(cuda: bool) -> ConfigDict:
  ollama_package = "ollama-cuda" if cuda else "ollama"
  aichat_model = "glm-4.7-flash"
  opencode_context_size = 49152

  return {
    Section("ollama"): (
      Package(ollama_package),
      File("/etc/systemd/system/ollama.service.d/override.conf", content = cleandoc(f'''
        [Service]
        Environment="OLLAMA_KEEP_ALIVE=30m"
        Environment="OLLAMA_FLASH_ATTENTION=1"
        Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
        Environment="OLLAMA_CONTEXT_LENGTH=65536"
      ''')),
      SystemdUnit("ollama.service"),
    ),

    Section("aichat"): (
      Package("aichat"),
      File("/home/manuel/.config/aichat/config.yaml", owner = "manuel", content = cleandoc(f'''
        model: ollama:{aichat_model}
        serve_addr: 0.0.0.0:8000
        clients:
        - type: openai-compatible
          name: ollama
          api_base: http://localhost:11434/v1
          api_key: null
      ''')),
      PostHook(
        name = f"download aichat model ({aichat_model})",
        trigger = File("/home/manuel/.config/aichat/config.yaml"),
        execute = lambda: shell(f"ollama pull {aichat_model}"),
        requires = Package(ollama_package),
      ),
    ),

    Section("opencode"): (
      Package("opencode"),
      Option[tuple[str, int]]("/etc/cpufreq/rules.yaml/ExtraEntries", value = ("opencode", 3500)),
      Option[tuple[str, int]]("/etc/cpufreq/rules.yaml/ExtraEntries", value = ("main.py", 3500)),
      File("/home/manuel/.config/opencode/opencode.json", owner = "manuel", content = cleandoc('''
        {
          "$schema": "https://opencode.ai/config.json",
          "providers": {
            "ollama": {
              "settings": {
                "baseURL": "http://localhost:11434/v1"
              },
              "models": {
                "glm-4.7-flash-code:latest": {
                  "limit": { "context": %i },
                  "variants": [
                    { "id": "think",   "settings": { "reasoningEffort": "high" } },
                    { "id": "nothink", "settings": { "reasoningEffort": "none" } }
                  ]
                },
                "qwen3.8-9b-distill-code:latest": {
                  "limit": {
                    "context": 65536,
                    "output": 8192
                  }
                }
              }
            }
          },
          "policies": [
            { "action": "provider.use", "resource": "*", "effect": "deny" },
            { "action": "provider.use", "resource": "ollama", "effect": "allow" }
          ],
          "compaction": {
            "auto": true,
            "buffer": "10%%",
          }
        }
      ''' % opencode_context_size)),
      File("/home/manuel/.config/opencode/Modelfile.glm-4.7-flash-code", owner = "manuel", content = cleandoc(f'''
        FROM glm-4.7-flash
        PARAMETER num_ctx {opencode_context_size}
        PARAMETER stop "<|endoftext|>"
        PARAMETER stop "<|user|>"
        PARAMETER stop "<|assistant|>"
        TEMPLATE """{{- if .System }}{{ .System }}{{ end }}
        {{- range .Messages }}
        {{- if eq .Role "system" }}<|system|>
        {{ .Content }}{{ else if eq .Role "user" }}<|user|>
        {{ .Content }}{{ else if eq .Role "assistant" }}<|assistant|>
        {{ .Content }}{{ end }}
        {{- end }}
        <|assistant|>
        """
      ''')),
      File("/home/manuel/.config/opencode/Modelfile.qwen3.8-9b-distill-code", owner = "manuel", content = cleandoc(f'''
        FROM tobestyledintro/qwen3.8-9b-distill:latest
        PARAMETER num_ctx 65536
        PARAMETER num_predict 8192
      ''')),
      PostHook(
        name = f"compile glm-4.7-flash-code model",
        trigger = File("/home/manuel/.config/opencode/Modelfile.glm-4.7-flash-code"),
        execute = lambda: shell(f"ollama create glm-4.7-flash-code -f /home/manuel/.config/opencode/Modelfile.glm-4.7-flash-code"),
        requires = Package(ollama_package),
      ),
      PostHook(
        name = f"compile qwen3.8-9b-distill-code model",
        trigger = File("/home/manuel/.config/opencode/Modelfile.qwen3.8-9b-distill-code"),
        execute = lambda: shell(f"ollama create qwen3.8-9b-distill-code -f /home/manuel/.config/opencode/Modelfile.qwen3.8-9b-distill-code"),
        requires = Package(ollama_package),
      ),
    )
  }
