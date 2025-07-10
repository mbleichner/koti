# koti

Declarative configuration manager

_(koti = "home" in Finnish)_

_(also coincidentally; Kot = shit in German 💩)_

## Project State

This project is still very new and in an experimental state. Use at your own risk.

## Motivation

After trying NixOS, I was charmed by how nicely I could describe my whole system using config files. Unfortunately I wasn't able to stay with NixOS due to performance/technical issues that were
unfortunately rooted in the way Nix works.

So I went back to my beloved Arch and looked for similar solutions that would allow me to describe my whole system in a similar manner. There are a few, but none of them managed to get that
declarative approach quite right, imo.
Because in Arch you do stuff in an incremental way instead of rebuilding the system from scratch every time, a declarative management tool will face two hurdles:

- During system setup, things need to happen in a certain order (for example, when installing a package from another repository, you need to set up pacman keys, install the keyring package, edit
  `pacman.conf` to include the repo and finally install the desired package)
- During system maintenance, stuff needs to be removed from the system if it is no longer present in the config (in NixOS this is a non-issue; on other distros this can only be achieved with some kind
  of tracking mechanism)

Among the tools I know and tested, I couldn't find one that solved both challenges at the same time (at the end of this readme I wrote down some thoughts about other tools and why I didn't stick
with them).

So I thought I'll give it a shot myself and the result is koti.

## Features

- Allows writing a NixOS-inspired modular declarative configuration for your system in Python
- Very easy to read and flexible syntax
- Execution order can easily be influenced by declaring dependencies
- Extensible and customizable behavior
- Supports AUR helpers with pacman-compatible syntax (e.g. paru, yay)

## Limitations

- Currently, only Arch/pacman is supported. In the future, I plan to add support for apt, yum, flatpak, etc.
- No versioning - updates to koti might break your configuration. Ideally, future versions will support some kind of backward compatibility.

## Installation (Arch)

```bash
curl https://raw.githubusercontent.com/mbleichner/koti/refs/heads/master/PKGBUILD --create-dirs -o /tmp/koti/PKGBUILD
makepkg -si -D /tmp/koti
```

## Example Usage

See the `examples` folder, specifically `main.py` and all the stuff in the `modules` subdirectory.

## Key Concepts

- **config items** declare individual things to install, such as `Package("htop")`, or `File("/etc/fstab", content="...")`
- **config managers** are responsible for applying config items to your system. They are largely part of koti itself and are not meant to be implemented by the user (although it can be done in case
  you need some special behavior)
- a **config group** consists of multiple config items that belong together (and will be applied together), such as the `Package("cpupower")` and the `File("/etc/default/cpupower")`
- config groups also allow to declare dependencies to other config groups (e.g. `Requires(Package("cpupower""))`) in order to influence the execution order

## Dependencies and Phases

Normally, koti will throw all config items onto a big heap and apply everything in one go. By default, this happens in the following order (a bit simplified, though):

- Install pacman packages
- Install files
- Enable systemd units
- Run post-hooks

Now, if a config group B declares a dependency on a config group A, koti has to make sure to run this whole installation process for all A-items before installing any B-items. This is achieved by
running the above operations multiple times, in so-called **phases**. Within each phase, all items of that phase are bunched together and installed in the above order.

Phases only add to the system, never remove anything. After all phases are finished, there is a separate cleanup phase, where the above operations run in reverse order and remove everything from your
system that is no longer present in the configs:

- Disable systemd units no longer present in config
- Delete files no longer present in config
- Uninstall pacman packages no longer present in config

## How does koti compare to...

- **Nix/NixOS** is a really nice concept and the most elegant solution to system configuration that I have encountered so far. Unfortunately, it is also very inflexible. You have to do everything the
  Nix way, which is often complicated as hell and once you have to start digging into the nixpkgs source code, it becomes downright frustrating compared to the simplicity of Arch.
- **aconfmgr** tries to snapshot the whole system on file-level. This approach leads to giant file collections that capture a lot of things that you don't care about or don't want to capture at all. I
  felt like it forces you into kind of the opposite thing you actually want to do - instead of specifying what is important to me on my system, I was more occupied with writing blacklists containing
  what is unimportant to me.
- **Ansible** is a well-tested tool that I use a lot at work, but felt like it's a bad match for my home systems. Ansible is meant to be idempotent, but not meant to be declarative. This makes it hard
  to keep your system from drifting over time. Also it's really slow and inefficient.
- **decman** is a really nice tool that I used for a while. Unfortunately, it makes a few assumptions about the order of things to execute that lead to technical problems. For example - usually you
  install packages and then set up the corresponding config files, but in other cases you need to set up some config files before installing packages (think of `pacman.conf`). Decman doesn't allow you
  to control this, which means when you try to setup a system from scratch, you will run into crashes that need to be fixed by hand.

# TODOs

- User anlegen und Gruppen zuordnen
- Directory() item => gamma-icc-profiles
- File(content_from_file) für große Dateien
