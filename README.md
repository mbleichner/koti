# koti - a declarative configuration manager

(koti = home in Finnish)

(also coincidentally: Kot = shit in German 💩)

## Project state

This project is still very new and in an alpha state. Use at your own risk.

## Motivation

Messing around with NixOS, I was charmed by how nicely it lets you describe your systems using just a few config files.
The declarative nature of it made sure that your system always looks just like described by your config and prevents any
drift due to changing package dependencies or leftovers from earlier experiments.

Unfortunately, using NixOS as a daily driver has been a bit of a disappointment, because customizing it is extremely
time-consuming and sometimes downright frustrating. After a few days, I already missed the simplicity and
straightforwardness of Arch.

So I went back to my beloved Arch and looked for similar solutions - that would allow me to describe my whole system in
a similar manner. There are a few, but none of them managed to get that declarative approach quite right. They all had
their problems:

- Not being able to detect stuff that has been removed from your config and uninstalling it from the system
- Not being able to control the order of execution in a fine-grained way (unlike NixOS, configuration in Arch is done in
  an incremental way, so the order of things matters quite a lot)
- Not being able to write easy-to-read + modular configs that can be applied to multiple systems

So I thought I'll give it a shot myself - and the result is koti.

## Summary and features

- koti allows writing a NixOS-inspired modular declarative configuration for your system in **Python**. It is aimed at
  users with at least some kind of programming knowledge (again, similar to NixOS here), but since it is mostly
  declarative in nature, it should be easy enough to learn, even with minimal programming experience.
- koti gives you fine-grained control over the **order of execution**, without sacrificing a lot of performance (
  compared to Ansible for example). This is done using a linear optimization approach to merge all configs and settings,
  and rearrange them in a way to optimize execution speed (i.e. install as many packages in one go)
- koti is able to track installed items (files, packages, systemd units, etc) and **clean them up** if they are removed
  from your config to avoid configuration drift.
- koti will give you an extensive summary about everything that will be adjusted on your system (in the so called
  planning phase). Because some changes are impossible to predict perfectly without actually executing them, koti will
  ask again during execution if something unexpected happens. It won't change anything on the system without user
  confirmation.
- koti can make use of **AUR helpers** with pacman-compatible syntax (e.g. paru, yay).
- koti is written with **extensibility** in mind - it's easy to extend or customize the behavior in (almost) any way.

## Installation (Arch)

```bash
curl https://raw.githubusercontent.com/mbleichner/koti/refs/heads/master/PKGBUILD --create-dirs -o /tmp/koti/PKGBUILD
makepkg -si -D /tmp/koti
```

## Example usage

See the `examples` folder, specifically `koti-apply` and all the stuff in the `modules` subdirectory.

## The building blocks of a koti config

- The whole system config is basically a large collection of **config items**, divided into **sections**.
- Config items declare individual things to install, such as `Package("htop")`, or `File("/etc/fstab", content="...")`.
- Sections contain multiple config items that belong together - for example `Package("nginx")`,
  `File("/etc/nginx/nginx.conf")` and `SystemdUnit("nginx")`.
- **Config managers** are responsible for applying config items to your system. They are largely part of koti itself and
  are not meant to be implemented by the user (although it can be done in case you need some special behavior)

```python
config_example_snippet = {

  Section("ssh daemon + config"): (
    Package("openssh"),
    File("/etc/ssh/sshd_config", owner = "root", content = cleandoc('''
      Include /etc/ssh/sshd_config.d/*.conf
      PermitRootLogin yes
      AuthorizedKeysFile .ssh/authorized_keys
      Subsystem sftp /usr/lib/ssh/sftp-server
    ''')),
    SystemdUnit("sshd.service"),
  ),

  Section("arch-update"): (
    Package("arch-update"),
    File("/home/manuel/.config/arch-update/arch-update.conf", owner = "manuel", content = cleandoc('''
      NoNotification
      KeepOldPackages=2
      KeepUninstalledPackages=0
      DiffProg=diff
      TrayIconStyle=light
    ''')),
    SystemdUnit("arch-update-tray.service", user = "manuel"),
    SystemdUnit("arch-update.timer", user = "manuel"),
    PostHook(
      "restart-arch-update-tray",
      execute = lambda: shell("systemctl --user -M manuel@ restart arch-update-tray.service"),
      trigger = File("/home/manuel/.config/arch-update/arch-update.conf"),
    )
  ),
}
```

### Predefined items:

| Config Item                                                     | Description                                                                                                                                                                    |
|-----------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `File("/etc/pacman.conf", owner, permissions, source, content)` | Creates a file by either copying an existing file (`source`) or specifying the content directly (`content`). This can also be a (lambda), that has access to all config items. |
| `Directory("/etc/nginx/sites-available.d", owner, source)`      | Creates a directory that contains exactly the same files as the `source` directory. `source` may also refer to a zip file.                                                     |
| `FlatpakRepo("flathub", repo_url, spec_url)`                    | Installs a flatpak repository.                                                                                                                                                 |
| `FlatpakPackage("us.zoom.Zoom")`                                | Installs a flatpak application by ID.                                                                                                                                          |
| `Pacman("htop", script, url)`                                   | Installs a pacman package (or AUR package, in case `PacmanPackageManager` uses one).                                                                                           |
| `PacmanKey("F3B607488DB35A47", keyserver)`                      | Installs a pacman packages signing key. Keyserver is the ubuntu one by default.                                                                                                |
| `Swapfile("/swapfile", size_bytes)`                             | Creates a swapfile with the specified size.                                                                                                                                    |
| `SystemdUnit("nginx.service", user)`                            | Enables (and starts) a systemd unit. Can also be a --user unit.                                                                                                                |
| `User("manuel", password)`                                      | Creates a user. The `password` boolean specifies if the user should have a password. If true, it is asked interactively upon setup.                                            |
| `UserGroupAssignment("manuel", "wheel")`                        | Assigns a user to a group.                                                                                                                                                     |
| `UserHome("manuel", homedir)`                                   | Sets (and creates) the homedir of a user.                                                                                                                                      |
| `UserShell("manuel", shell)`                                    | Sets the default login shell of a user.                                                                                                                                        |
| `PostHook("locale-gen", trigger, execute)`                      | Executes a python function (`execute`) whenever the state of the `trigger` item(s) change.                                                                                     |
| `Checkpoint("moep")`                                            | Allows to break up the execution of a group of same-type items into separate manager invocations                                                                               |
| `Option("/etc/pacman.conf/NoUpgrade", value)`                   | Helper item to collect Options that can e.g. be merged into a `File()`                                                                                                         |

## How koti works

- **Planning phase**
  - Multiple occurrences of the same config items will be merged (to prevent inconsistencies).
  - All config items of all sections will be merged into a linear order; in a way such that similar items get grouped
    together in order to reduce manager invocations.
  - Managers will be called on each group of items to plan their respective operations. Nothing will be executed here -
    all actions will only be printed to the console.
  - Managers will try to predict what needs to be removed from the system. As before, nothing will be executed here -
    all actions will only be printed to the console.
- **Execution phase**
  - All managers will be called again, this time actually executing everything. Because this time the system actually
    gets modified, it can happen that a previously predicted action is no longer correct and some unexpected actions
    have to be taken. In this case koti asks for explicit confirmation before continuing. (The most common example is
    koti predicting to create a new file during planning, but during execution that file has already been created by
    some pacman package. So koti would have to modify an existing file instead of creating a new one - which will
    trigger an additional confirmation.)
  - After everything has been installed, all managers will run their cleanup routine to remove items from the system
    that should no longer be present.

## Controlling the order of execution

There are two mechanisms to control the order of installation:

- **Within sections**: in each section, all items will be installed in the order they are listed (items of the same type
  are allowed to be installed in a single step for performance reasons).
- **Between sections**: koti allows to define explicit dependencies between items residing in different sections. To
  define such a dependency, use the `requires`, `before` and `after` parameters:
  - `requires` specifies one or more items that need to be installed before the current one. This is a hard dependency,
    meaning the program will fail to execute if it isn't satisfied. A typical example would be
    `File("/etc/fstab", requires = Swapfile("/var/swapfile"))`.
  - `after` is basically the same as `requires`, but doesn't fail if the dependency can't be found in the config. It can
    also be specified as a (lambda) function to allow dynamic dependencies.
  - `before` is like `after`, but reversed. It allows to declare an item as prerequisite for others. Since this also can
    be given a (lambda) function, it's possible to define something as a system-wide prerequisite - an example would be
    `File("/etc/pacman.conf", before = lambda other: isinstane(other, Package))` to make sure
    `/etc/pacman.conf` has been set up before any packages may be installed.
  - Please note that some items have inherent dependencies, such as `File("...", owner = "example")` will by default
    have a dependency `after = User("example")`.

Sometimes it may happen that you accidentally define dependencies that are impossible to satisfy (i.e. circular
dependencies). In this case, koti will calculate and output the minimal set of inconsistent items.

### Recommendations

- Try to use the same order within each section if possible - e.g. `Package()`s first, then `File()`s, then
  `SystemdUnit()`s. Because koti isn't allowed to change the item order within each section, inconsistent ordering will 
  prevent koti from merging multiple sections in an efficient way (i.e. minimizing pacman invocations).
- Split up your config in multiple sections to keep it flexible. Each section is meant to describe one singular coherent
  aspect of your system. By keeping them small and focused, it will be much easier to manage your configs - compared to
  having a giant blob of everything.
- You have the full power of python at your fingertips. Use it to compose and parameterize your configs, create
  dynamic configs, whatever you want.

## Limitations and known problems

- Currently, only Arch (pacman) and flatpak is supported. In the future, I might add support for apt, yum, etc.
- Pacman pretty aggressively asks for possible package alternatives - even if they are explicitly given. I don't know if
  bug or intended behavior, but it can be a bit annoying during system setup to be asked something that's literally in
  your config.