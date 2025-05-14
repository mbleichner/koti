from inspect import cleandoc

from definitions import ConfigItemGroup, ConfigModule, ConfigModuleGroups, ShellCommand
from managers.file import File
from managers.hook import Hook
from managers.pacman import PacmanPackage


class FishModule(ConfigModule):

  def provides(self) -> ConfigModuleGroups:
    return ConfigItemGroup(
      PacmanPackage("fish"),
      PacmanPackage("pyenv"),
      PacmanPackage("fastfetch"),

      Hook(
        "set-fish-as-default-shell",
        execute = ShellCommand("chsh -s /usr/bin/fish manuel"),
        triggered_by = PacmanPackage("fish"),
      ),

      File("/etc/fish/config.fish", permissions = 0o444, content = cleandoc(r'''
        # managed by arch-config
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

      File("/etc/fish/functions/fish_prompt.fish", permissions = 0o444, content = cleandoc(r'''
        # managed by arch-config
        function fish_prompt --description 'Moep'
          set -l last_pipestatus $pipestatus
        
          set_color brblue
          printf '\n%s@%s' $USER (prompt_hostname)
        
          set_color 999999
          printf ' %s' $PWD
        
          set -l git_info (fish_git_prompt " " | string trim)
          if test -n "$git_info" 
            set_color white
            printf " @ %s" $git_info
          end
        
          if test $CMD_DURATION -gt 2000
            set_color 999999
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

      File("/home/manuel/.config/fastfetch/config.jsonc", permissions = 0o444, owner = "manuel", content = cleandoc(r'''
        // managed by arch-config
        {
          "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
          "logo": { "source": "/home/manuel/.config/fastfetch/fastfetch-logo.png", "height": 13 },
          "display": { "color": "30" },
          "modules": [ "os", "host", "kernel", "uptime", "cpu", "gpu", "display", "memory", "disk", "swap", "localip", "packages", "de", "wm" ]
        }
      ''')),

      File("/home/manuel/.config/fastfetch/fastfetch-logo.png", permissions = 0o444, owner = "manuel", path = "files/fastfetch-logo.png"),
    )
