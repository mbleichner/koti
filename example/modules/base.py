from socket import gethostname
from inspect import cleandoc

from koti import *
from koti.utils.shell import shell

hostname = gethostname()


def base() -> ConfigDict:
  return {
    Section("bootstrap sudo, pacman and paru"): (

      # setup sudo and sudo user
      # (sudo is assumed to be already installed here)
      Package("sudo", tags = "bootstrap"),
      User("manuel"),
      UserHome("manuel", homedir = "/home/manuel"),
      UserGroupAssignment("manuel", "wheel"),
      Option[str]("/etc/sudoers/ExtraLines"),
      File("/etc/sudoers", permissions = 0o440, content = lambda model: cleandoc(f'''
        Defaults!/usr/bin/visudo env_keep += "SUDO_EDITOR EDITOR VISUAL"
        Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/bin"
        Defaults passwd_tries=3, passwd_timeout=180
        
        # Workaround for repeated sudo prompts caused by paru internally spawning
        # a new pty, causing sudo to "forget" about its current session
        Defaults timestamp_type=global
  
        # Notwendig für paru SudoLoop ohne initiale Passworteingabe  
        Defaults verifypw = any
  
        root ALL=(ALL:ALL) ALL
        %wheel ALL=(ALL:ALL) ALL
        %wheel ALL=(ALL:ALL) NOPASSWD: /usr/bin/poweroff
        %wheel ALL=(ALL:ALL) NOPASSWD: /usr/bin/reboot
        @includedir /etc/sudoers.d
      ''') + "\n\n" + "\n".join(model.item(Option[str]("/etc/sudoers/ExtraLines")).distinct())),

      # install CachyOS keyrings and mirrorlist, and set up pacman
      PacmanKey("F3B607488DB35A47"),  # CachyOS
      PacmanKey("3056513887B78AEB"),  # Chaotic AUR
      Package("cachyos-keyring", url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-keyring-20240331-1-any.pkg.tar.zst", tags = "bootstrap"),
      Package("cachyos-mirrorlist", url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-mirrorlist-22-1-any.pkg.tar.zst", tags = "bootstrap"),
      Package("cachyos-v3-mirrorlist", url = "https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-v3-mirrorlist-22-1-any.pkg.tar.zst", tags = "bootstrap"),
      Package("chaotic-keyring", url = "https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst", tags = "bootstrap"),
      Package("chaotic-mirrorlist", url = "https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst", tags = "bootstrap"),
      Option[str]("/etc/pacman.conf/NoExtract"),  # Declare options for pacman.conf (so I don't have to null-check later)
      Option[str]("/etc/pacman.conf/NoUpgrade"),  # Declare options for pacman.conf (so I don't have to null-check later)
      Option[str]("/etc/pacman.conf/IgnorePkg"),  # Declare options for pacman.conf (so I don't have to null-check later)
      File("/etc/pacman.conf", content = lambda model: cleandoc(f'''
        [options]
        HoldPkg = pacman glibc
        Architecture = auto x86_64_v3
        NoExtract = {" ".join(model.item(Option[str]("/etc/pacman.conf/NoExtract")).distinct())}
        NoUpgrade = {" ".join(model.item(Option[str]("/etc/pacman.conf/NoUpgrade")).distinct())}
        IgnorePkg = {" ".join(model.item(Option[str]("/etc/pacman.conf/IgnorePkg")).distinct())}
        Color
        CheckSpace
        VerbosePkgLists
        ParallelDownloads = 8
        DownloadUser = alpm
        SigLevel = Required DatabaseOptional
        LocalFileSigLevel = Optional
    
        [core]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
    
        [extra]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
    
        [multilib]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
    
        [cachyos-v3]
        CacheServer = http://pacoloco.fritz.box/repo/cachyos-v3/$arch_v3/$repo
        Include = /etc/pacman.d/cachyos-v3-mirrorlist
        
        [cachyos]
        CacheServer = http://pacoloco.fritz.box/repo/cachyos/$arch/$repo
        Include = /etc/pacman.d/cachyos-mirrorlist
    
        [chaotic-aur]
        CacheServer = http://pacoloco.fritz.box/repo/chaotic/$repo/$arch
        Include = /etc/pacman.d/chaotic-mirrorlist
        
        [core-testing]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
    
        [extra-testing]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
    
        [multilib-testing]
        CacheServer = http://pacoloco.fritz.box/repo/archlinux/$repo/os/$arch
        Include = /etc/pacman.d/mirrorlist
      ''')),
      PostHook(
        name = "update pacman databases after config change",
        trigger = File("/etc/pacman.conf"),
        execute = lambda: shell("pacman -Syyu"),
      ),

      # install and configure paru
      Package("paru", script = lambda: shell("""
        builddir=$(mktemp -d -t paru.XXXXXX)
        git clone https://aur.archlinux.org/paru.git $builddir
        makepkg -si -D $builddir
      """, user = "manuel"), tags = "bootstrap"),
      File(
        filename = "/etc/paru.conf",
        before = lambda item: isinstance(item, Package) and "bootstrap" not in item.tags,
        content = cleandoc('''
          [options]
          PgpFetch
          Devel
          DevelSuffixes = -git -cvs -svn -bzr -darcs -always -hg -fossil
          SudoLoop
          CombinedUpgrade
          NewsOnUpgrade
          RemoveMake
          CleanAfter
        '''),
      ),

      File("/etc/makepkg.conf", content = cleandoc(r'''
        #!/hint/bash
        DLAGENTS=('file::/usr/bin/curl -qgC - -o %o %u'
                  'ftp::/usr/bin/curl -qgfC - --ftp-pasv --retry 3 --retry-delay 3 -o %o %u'
                  'http::/usr/bin/curl -qgb "" -fLC - --retry 3 --retry-delay 3 -o %o %u'
                  'https::/usr/bin/curl -qgb "" -fLC - --retry 3 --retry-delay 3 -o %o %u'
                  'rsync::/usr/bin/rsync --no-motd -z %u %o'
                  'scp::/usr/bin/scp -C %u %o')
        VCSCLIENTS=('bzr::breezy' 'fossil::fossil' 'git::git' 'hg::mercurial' 'svn::subversion')
        CARCH="x86_64"
        CHOST="x86_64-pc-linux-gnu"
        CFLAGS="-march=x86-64 -mtune=generic -O2 -pipe -fno-plt -fexceptions -Wp,-D_FORTIFY_SOURCE=3 -Wformat -Werror=format-security \
                -fstack-clash-protection -fcf-protection -fno-omit-frame-pointer -mno-omit-leaf-frame-pointer"
        CXXFLAGS="$CFLAGS -Wp,-D_GLIBCXX_ASSERTIONS"
        LDFLAGS="-Wl,-O1 -Wl,--sort-common -Wl,--as-needed -Wl,-z,relro -Wl,-z,now -Wl,-z,pack-relative-relocs"
        LTOFLAGS="-flto=auto"
        MAKEFLAGS="-j16"
        DEBUG_CFLAGS="-g"
        DEBUG_CXXFLAGS="$DEBUG_CFLAGS"
        OPTIONS=(strip docs !libtool !staticlibs emptydirs zipman purge debug lto)
        INTEGRITY_CHECK=(sha256)
        STRIP_BINARIES="--strip-all"
        STRIP_SHARED="--strip-unneeded"
        STRIP_STATIC="--strip-debug"
        MAN_DIRS=(usr{,/local}{,/share}/{man,info})
        DOC_DIRS=(usr/{,local/}{,share/}{doc,gtk-doc})
        PURGE_TARGETS=(usr/{,share}/info/dir .packlist *.pod)
        DBGSRCDIR="/usr/src/debug"
        LIB_DIRS=('lib:usr/lib' 'lib32:usr/lib32')
        PKGDEST=~/.cache/makepkg
        COMPRESSGZ=(gzip -c -f -n)
        COMPRESSBZ2=(bzip2 -c -f)
        COMPRESSXZ=(xz -c -z -)
        COMPRESSZST=(zstd -c -T0 -)
        COMPRESSLRZ=(lrzip -q)
        COMPRESSLZO=(lzop -q)
        COMPRESSZ=(compress -c -f)
        COMPRESSLZ4=(lz4 -q)
        COMPRESSLZ=(lzip -c -f)
        PKGEXT='.pkg.tar.zst'
        SRCEXT='.src.tar.gz'
      ''')),

      Package("pacman-contrib"),
      Package("pacutils"),
      Package("lostfiles"),
      File("/etc/pacman.d/hooks/paccache.hook", requires = Package("pacman-contrib"), content = cleandoc('''
        [Trigger]
        Operation = Upgrade
        Operation = Install
        Operation = Remove
        Type = Package
        Target = *
    
        [Action]
        When = PostTransaction
        Description = Cleaning package cache...
        Exec = /bin/sh -c "/usr/bin/paccache -qrk2; /usr/bin/paccache -qruk0"
      ''')),
    ),

    Section("basic system packages and configs"): (
      Package("base"),
      Package("base-devel"),
      Package("efibootmgr"),
      Package("terminus-font"),
      Package("ca-certificates"),
      Package("ca-certificates-mozilla"),
      Package("fwupd"),

      File("/etc/vconsole.conf", content = cleandoc('''
        KEYMAP=de-latin1
        FONT=ter-124b
      ''')),

      File("/boot/loader/loader.conf", permissions = 0o755, content = cleandoc(f'''
        timeout 2
        console-mode max
      ''')),

      File("/etc/locale.conf", content = cleandoc('''
        LANG=en_US.UTF-8
        LC_ADDRESS=de_DE.UTF-8
        LC_IDENTIFICATION=de_DE.UTF-8
        LC_MEASUREMENT=de_DE.UTF-8
        LC_MONETARY=de_DE.UTF-8
        LC_NAME=de_DE.UTF-8
        LC_NUMERIC=de_DE.UTF-8
        LC_PAPER=de_DE.UTF-8
        LC_TELEPHONE=de_DE.UTF-8
        LC_TIME=de_DE.UTF-8
      ''')),

      File("/etc/locale.gen", content = cleandoc('''
        en_US.UTF-8 UTF-8
        de_DE.UTF-8 UTF-8
        # without this linebreak, the last locale will be ignored
      ''')),

      File("/etc/systemd/timesyncd.conf", content = cleandoc('''
        [Time]
        NTP=time.cloudflare.com
        FallbackNTP=time.google.com 0.arch.pool.ntp.org 1.arch.pool.ntp.org 2.arch.pool.ntp.org 3.arch.pool.ntp.org
      ''')),

      SystemdUnit("fstrim.timer"),
      SystemdUnit("fwupd.service"),
      SystemdUnit("systemd-boot-update.service"),
      SystemdUnit("systemd-timesyncd.service"),
      PostHook("regenerate-locales", execute = lambda: shell("locale-gen"), trigger = File("/etc/locale.gen")),
    ),

    Section("command line tools"): (
      Package("nano"),
      Package("less"),
      Package("bat"),
      Package("moreutils"),  # enthält sponge
      Package("jq"),
      Package("man-db"),
      Package("man-pages"),
      Package("tealdeer"),
      Package("unrar"),
      Package("zip"),
      Package("unzip"),
      Package("7zip"),
      Package("yazi"),
      Package("zoxide"),
      Package("btop"),
      Package("htop"),
      Package("iotop"),
      Package("ncdu"),
      Package("perl-image-exiftool"),
      Package("fdupes"),

      File("/etc/environment.d/editor.conf", content = cleandoc(f'''
        EDITOR=nano
      ''')),

      File("/home/manuel/.config/tealdeer/config.toml", owner = "manuel", content = cleandoc('''
        [updates]
        auto_update = true
      ''')),
    ),

    Section("git + config"): (
      Package("git"),
      Package("git-lfs"),
      Package("tig"),

      File("/home/manuel/.gitconfig", owner = "manuel", content = cleandoc('''
        [user]
        email = mbleichner@gmail.com
        name = Manuel Bleichner
        [pull]
        rebase = true
      ''')),
    ),

    Section("networking tools"): (
      Package("bind"),
      Package("openbsd-netcat"),
      Package("traceroute"),
      Package("wireguard-tools"),
      Package("wget"),
      Package("ethtool"),
      Package("tcpdump"),
      Package("bandwhich"),
      Package("nload"),
    ),

    Section("borgmatic"): (
      Package("borgmatic"),

      Option[str]("/etc/borgmatic/config.yaml/Patterns", value = [
        'R /etc',
        'R /home/manuel',
        '! sh:/home/manuel/.local/share/Trash',
        '! sh:/home/manuel/.local/state/Beyond All Reason',
        '! sh:/home/manuel/.local/share/Steam/steamrt*',
        '! sh:/home/manuel/.local/share/Steam/ubuntu*',
        '! sh:/home/manuel/.local/share/Steam/steamapps/temp',
        '! sh:/home/manuel/.local/share/Steam/steamapps/common',
        '! sh:/home/manuel/.local/share/Steam/steamapps/downloading',
        '! sh:/home/manuel/.local/share/Steam/steamapps/shadercache',
        '! sh:/home/manuel/.local/share/Steam/steamapps/compatdata/*/pfx/drive_c/windows',
        '! sh:/home/manuel/.cargo',
        '! sh:/home/manuel/.dotnet',
        '! sh:/home/manuel/.npm',
        '! sh:/home/manuel/.nuget',
        '! sh:/home/manuel/.pyenv',
        '! sh:/home/manuel/.yarn',
        '! sh:/home/manuel/**/*[Cc]ache*',
        '! sh:**/.venv',
      ]),

      File("/etc/borgmatic/config.yaml", requires = User("manuel"), content = lambda model: cleandoc(f'''
        verbosity: 1
        lock_wait: 3600
        ssh_command: ssh -i /home/manuel/.ssh/id_ed25519
        list_details: true
        
        keep_daily: 7
        keep_weekly: 4
        keep_monthly: 12
        keep_within: 2d
        
        repositories:
        - path: ssh://borg@192.168.1.100/home/borg/repo
          label: mserver
        
        checks:
        - name: repository
          frequency: 1 month
        
        patterns: [ {", ".join(f"'{pattern}'" for pattern in model.item(Option[str]("/etc/borgmatic/config.yaml/Patterns")).distinct())} ]
      ''')),

      File("/etc/systemd/system/borgmatic.service", content = cleandoc(f'''
        [Unit]
        Description=borgmatic
        Wants=network-online.target
        After=network-online.target
        
        [Service]
        Type=oneshot
        Nice=19
        CPUSchedulingPolicy=batch
        IOSchedulingClass=best-effort
        IOSchedulingPriority=7
        IOWeight=100
        Restart=no
        LogRateLimitIntervalSec=0
        ExecStart=borgmatic --verbosity -2 --syslog-verbosity 1
      ''')),

      File("/etc/systemd/system/borgmatic.timer", content = cleandoc(f'''
        [Unit]
        Description=borgmatic
        
        [Timer]
        OnCalendar=*-*-* 18:00:00
        RandomizedDelaySec=30m
        Persistent=true
        
        [Install]
        WantedBy=timers.target
      ''')),

      SystemdUnit("borgmatic.timer"),
    ),

    Section("filesystem tools"): (
      Package("gparted"),
      Package("ntfs-3g"),
      Package("dosfstools"),
      Package("cryptsetup"),
      Package("samba"),
    ),

    Section("syncthing"): PostHookScope(
      Package("syncthing"),
      File("/usr/local/bin/update-syncthing-config", permissions = "r-x", content = cleandoc("""
        syncthing cli config options natenabled set false;
        syncthing cli config options global-ann-enabled set false;
        syncthing cli config options relays-enabled set false;
        syncthing cli config gui insecure-skip-host-check set true;
      """)),
      SystemdUnit("syncthing@manuel.service", requires = User("manuel")),
      PostHook("update-syncthing-config", execute = lambda: shell("update-syncthing-config", user = "manuel")),
      PostHook("restart-syncthing", execute = lambda: shell("systemctl daemon-reload && systemctl restart syncthing@manuel.service")),
    ),

    Section("koti executable and runtime dependencies"): (
      Package("python"),
      Package("python-urllib3"),
      Package("python-pyscipopt"),
      Package("python-numpy"),

      # convenience executable
      File("/usr/local/bin/koti", permissions = "r-x", content = cleandoc(r'''
        #!/bin/sh
        cd /home/manuel/koti/example
        git pull --rebase
        sudo PYTHONPATH=/home/manuel/koti/src ./koti-apply
      ''')),
    ),

    Section("ananicy-cpp and configuration"): PostHookScope(
      Package("ananicy-cpp"),

      File("/etc/ananicy.d/ananicy.conf", content = cleandoc('''
        check_freq = 30
        loglevel = info
        rule_load = true
        type_load = true
        cgroup_load = false
        apply_nice = true
        apply_latnice = true
        apply_ionice = true
        apply_sched = true
        log_applied_rule = true
      ''')),

      AnanicyConfigFile("/etc/ananicy.d/audio-system.rules",
        options = {"nice": -10, "latency_nice": -10},
        processes = ["pipewire", "wireplumber", "pipewire-pulse"],
      ),

      AnanicyConfigFile("/etc/ananicy.d/kwin.rules",
        options = {"nice": -5, "latency_nice": -5},
        processes = ["kwin_wayland"],
      ),

      AnanicyConfigFile("/etc/ananicy.d/games.rules",
        options = {"nice": -5, "latency_nice": -5},
        processes = ["steam", "ryujinx", "eden", "lutris", "heroic"],
      ),

      AnanicyConfigFile("/etc/ananicy.d/compilers.rules",
        options = {"nice": 19, "latency_nice": 19, "sched": "batch", "ioclass": "idle"},
        processes = ["cc", "gcc", "make", "clang", "rustc", "fossilize_replay"],
      ),

      AnanicyConfigFile("/etc/ananicy.d/syncthing.rules",
        options = {"nice": 10, "latency_nice": 10, "sched": "batch", "ioclass": "idle"},
        processes = ["syncthing"],
      ),

      SystemdUnit("ananicy-cpp.service"),

      PostHook(
        name = "restart-ananicy-cpp",
        execute = lambda: shell("systemctl daemon-reload && systemctl restart ananicy-cpp.service"),
      ),
    ),

    Section("docker and containers"): (
      Package("docker"),
      Package("docker-buildx"),
      Package("docker-compose"),
      Package("containerd"),
      UserGroupAssignment("manuel", "docker", requires = User("manuel")),
      SystemdUnit("docker.socket"),  # activate the socket, but not the service by default
    ),

    Section("rate-mirrors"): PostHookScope(
      Package("rate-mirrors"),
      File("/usr/local/bin/update-mirrors", permissions = "r-x", content = cleandoc(r'''
        #!/bin/sh
        RATE_MIRRORS_ARGS=()
        RATE_MIRRORS_ARGS+=("--protocol=https")
        RATE_MIRRORS_ARGS+=("--concurrency=8")
        RATE_MIRRORS_ARGS+=("--max-jumps=2")
        RATE_MIRRORS_ARGS+=("--entry-country=DE")
        RATE_MIRRORS_ARGS+=("--exclude-countries RU,BY")
        RATE_MIRRORS_ARGS+=("--max-mirrors-to-output=10")
        sudo -u nobody rate-mirrors ${RATE_MIRRORS_ARGS[@]} arch    | sudo tee /etc/pacman.d/mirrorlist
        sudo -u nobody rate-mirrors ${RATE_MIRRORS_ARGS[@]} cachyos | sudo tee /etc/pacman.d/cachyos-mirrorlist
        sed 's|$arch|$arch_v3|g' /etc/pacman.d/cachyos-mirrorlist   | sudo tee /etc/pacman.d/cachyos-v3-mirrorlist
      ''')),
      PostHook("update mirrorlist", execute = lambda: shell("/usr/local/bin/update-mirrors")),
    ),

    Section("ssh daemon"): (
      Package("openssh"),
      File("/etc/ssh/sshd_config", owner = "root", content = cleandoc('''
        Include /etc/ssh/sshd_config.d/*.conf
        PermitRootLogin yes
        AuthorizedKeysFile .ssh/authorized_keys
        Subsystem sftp /usr/lib/ssh/sftp-server
        PasswordAuthentication no
        ChallengeResponseAuthentication no
        Match Address 192.168.0.0/16
          PasswordAuthentication yes
      ''')),
      File("/home/manuel/.ssh/authorized_keys", owner = "manuel", content = cleandoc(f'''
        ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILHYYC3eJGcl/X9eM8f6BnUtBvekI2ZUzkfLY5ltjPTw manuel@dan
        ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINL1K4/a2LLS6qrB5cNMIyVk6skyhRAVE++tIj6UTL0s manuel@lenovo
        ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKa8TBfPVjdfsMkhki/j3PjOLcNJMV5OMb7sDu6ld6ek manuel@mserver
      ''')),
      SystemdUnit("sshd.service"),
    ),

    Section("flatpak and flathub"): (
      # flatpak currently required by plasma-meta
      Package("flatpak", before = lambda item: isinstance(item, FlatpakRepo) or isinstance(item, FlatpakPackage)),
      FlatpakRepo("flathub", spec_url = "https://dl.flathub.org/repo/flathub.flatpakrepo"),
    ),

    Section("fish"): (
      Package("fish"),
      Package("pyenv"),
      Package("fastfetch"),
      Package("imagemagick"),  # notwendig für png-Anzeige in fastfetch

      UserShell("manuel", shell = "/usr/bin/fish"),

      File("/etc/fish/config.fish", content = cleandoc(r'''
        set fish_greeting ""
        pyenv init - fish | source
        if status is-interactive
        
          # Theme wählen und Hintergrundfarbe für interaktive Selektion fixen
          fish_config theme choose "Base16 Default Dark"
          set -x fish_pager_color_selected_background --background=333
          
          bind alt-backspace backward-kill-word
          bind alt-m "history merge"
          
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

      File("/home/manuel/.config/fastfetch/fastfetch-logo.png", owner = "manuel", source = "files/fastfetch-logo.png"),

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


def AnanicyConfigFile(filename: str, options: dict[str, str | int], processes: Sequence[str]) -> File:
  return File(
    filename = filename,
    content = "\n".join(str({"name": proc, **options}).replace("'", '"') for proc in processes),
  )
