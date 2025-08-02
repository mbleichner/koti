# koti

Declarative configuration manager

(koti = home in Finnish)

(also coincidentally: Kot = shit in German 💩)

## Project state

This project is still very new and in an experimental state. Use at your own risk.

## Motivation

After trying NixOS, I was charmed by how nicely I could describe my whole system using config files. Unfortunately I wasn't able to stay with NixOS due to performance/technical issues that were
unfortunately rooted in the way Nix works.

So I went back to my beloved Arch and looked for similar solutions that would allow me to describe my whole system in a similar manner. There are a few, but none of them managed to get that
declarative approach quite right, in my opinion. They all had their problems:

- Not being able to detect stuff that has been removed from your config and uninstalling it from the system
- Not being able to control the order of execution in a fine-grained way (unlike NixOS, configuration in Arch is done in an incremental way, so the order of things matters)
- Not being able to write easy-to-read + modular configs that can be applied to multiple systems

So I thought I'll give it a shot myself and the result is koti.

## Summary and features

- Koti allows writing a NixOS-inspired modular declarative configuration for your system **in Python**. It is aimed at users with at least some kind of **programming knowledge** (again, similar
  to NixOS here), but it should be easy enough to learn, even with minimal programming experience.
- Koti gives you fine-grained control over the **order of execution**: sometimes it may be necessary to first install a package and then add a config file - sometimes it may be the other way around.
  By declaring dependencies between your configuration items, this can be solved in an elegant way (look for `requires` in the examples).
- Koti is able to track installed items (files, packages, systemd units, etc) and **clean them up** if they are removed from your config to avoid configuration drift.
- Koti can make use of **AUR helpers** with pacman-compatible syntax (e.g. paru, yay).
- Koti is written with **extensibility** in mind - it's easy to extend or customize the behavior in (almost) any way.

## Limitations

- Currently, only Arch/pacman is supported. In the future, I plan to add support for apt, yum, flatpak, etc.

## Installation (Arch)

```bash
curl https://raw.githubusercontent.com/mbleichner/koti/refs/heads/master/PKGBUILD --create-dirs -o /tmp/koti/PKGBUILD
makepkg -si -D /tmp/koti
```

## Example usage

See the `examples` folder, specifically `koti-apply` and all the stuff in the `modules` subdirectory.

## Key concepts, explanations

- **Config items** declare individual things to install, such as `Package("htop")`, or `File("/etc/fstab", content="...")`
- **Config managers** are responsible for applying config items to your system. They are largely part of koti itself and are not meant to be implemented by the user (although it can be done in case
  you need some special behavior)
- **Config groups** consist of multiple config items that belong together (and will be applied together), such as `Package("cpupower")` and `File("/etc/default/cpupower")`
- Config groups also allow declaring dependencies between each other in order to influence the order of execution
- Absent any dependencies, koti will throw all config groups onto one big heap and apply all of their config items in the following order (a bit simplified, though):
    - Install pacman packages
    - Install files
    - Enable systemd units
    - Run post-hooks
- If there are dependencies present, this will happen in multiple rounds (so-called phases) where koti will bundle mutually compatible config groups together and run an installation phase on each
  bundle.
- When all config items have been installed, koti performs a system cleanup - looking for old items that have been removed from the koti config and uninstalls them from the system (in reverse
  installation order).

## How does koti compare to...

- **Nix/NixOS** has a really nice concept and the most elegant solution to system configuration that I have encountered so far. Unfortunately, it is also very inflexible. You have to do everything the
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
- Meldungen für nicht vorhersehbare Änderungen
    - PostHooks
    - FlatpakPackage (wenn flatpak nicht installiert)