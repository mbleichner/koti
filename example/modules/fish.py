from inspect import cleandoc

from koti import *


def fish() -> ConfigDict:
  return {
    Section("fish (+fastfetch)"): (
      Package("fish", tags = "bootstrap"),
      Package("pyenv"),
      Package("fastfetch"),
      Package("imagemagick"),  # notwendig für png-Anzeige in fastfetch

      File("/etc/fish/config.fish", content = cleandoc(r'''
        set fish_greeting ""
        pyenv init - fish | source
        if status is-interactive
        
          # Theme wählen und Hintergrundfarbe für interaktive Selektion fixen
          fish_config theme choose "Base16 Default Dark"
          set -x fish_pager_color_selected_background --background=333
          
          bind alt-u arch-update
          bind alt-m "history merge"
          bind alt-y y
          
          # Fastfetch ausführen, wenn aus Konsole gestartet (Dolphin unterstützt z.B. keine PNG Images)
          if test (pstree -s $fish_pid | string match -r "konsole")
            fastfetch
          end
        end
      ''')),

      File("/etc/fish/functions/fish_prompt.fish", content = cleandoc(r'''
        function fish_prompt --description 'Moep'
          set -l last_pipestatus $pipestatus
          set -l host (prompt_hostname)
          
          if [ "$USER" = "root" ]
            set_color red
          else
            set_color brblue
          end
          printf '\n%s' $USER
          
          set_color brwhite
          printf '@'
          
          if test -n "$SSH_CLIENT"
            set_color yellow
          else
            set_color brblue
          end
          printf '%s' (prompt_hostname)
        
          set_color 999
          printf ' %s' $PWD
        
          set -l git_info (fish_git_prompt " " | string trim)
          if test -n "$git_info"
            set_color white
            printf " @ %s" $git_info
          end
        
          if test $CMD_DURATION -gt 2000
            set_color 999
            printf ' %ss' (math $CMD_DURATION / 1000.0)
          end
        
          set -l status_color (set_color $fish_color_status)
          set -l statusb_color (set_color --bold $fish_color_status)
          set -l pipestatus_string (__fish_print_pipestatus "[" "]" "|" "$status_color" "$statusb_color" $last_pipestatus)
          printf ' %s' $pipestatus_string
        
          set_color red
          printf '\n❯ '
          set_color normal
        end
      ''')),

      File(
        filename = "/home/manuel/.config/fastfetch/fastfetch-logo.png",
        owner = "manuel",
        source = "files/fastfetch-logo.png"
      ),

      File("/home/manuel/.config/fastfetch/config.jsonc", owner = "manuel", content = cleandoc(r'''
        {
          "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
          "logo": { "source": "/home/manuel/.config/fastfetch/fastfetch-logo.png", "height": 13 },
          "display": { "color": "30" },
          "modules": [ "os", "host", "kernel", "uptime", "cpu", "gpu", "display", "memory", "disk", "swap", "localip", "packages", "de", "wm" ]
        }
      ''')),
    )
  }
