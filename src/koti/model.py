from __future__ import annotations

from abc import ABCMeta, abstractmethod
from functools import reduce
from typing import Any, Callable, Iterable, Literal, Sequence, Type, cast, overload


class ConfigGroup:
  """The purpose of ConfigGroups is to provide ConfigItems that should be installed on the system.
  It's good practice to create a ConfigGroup for related ConfigItems that should be installed
  within the same phase. Also, ConfigGroups allow to define dependencies on other ConfigGroups
  so they are split into separate phases to control the order of installation."""
  description: str
  requires: Sequence[ConfigItem]
  provides: Sequence[ConfigItem]
  before: Callable[[ConfigItem], bool]
  after: Callable[[ConfigItem], bool]

  def __init__(
    self,
    description: str,
    provides: Sequence[ConfigItem | None],
    requires: Sequence[ConfigItem | None] | None = None,
    before: Callable[[ConfigItem], bool] | Sequence[ConfigItem | None] | None = None,
    after: Callable[[ConfigItem], bool] | Sequence[ConfigItem | None] | None = None,
    tags: Iterable[str] | None = None,
  ):
    self.description = description
    self.requires = [item for item in (requires or []) if item is not None]
    self.provides = [item for item in (provides or []) if item is not None]

    if callable(before):
      self.before = before
    elif isinstance(before, Sequence):
      self.before = lambda item: item in before
    else:
      self.before = lambda item: False

    if callable(after):
      self.after = after
    elif isinstance(after, Sequence):
      self.after = lambda item: item in after
    else:
      self.after = lambda item: False

    for item in self.provides:
      for tag in tags or set():
        item.tags.add(tag)

  # @classmethod
  # def derive_from(cls, other: ConfigGroup, provides: list[ConfigItem]):
  #   return ConfigGroup(
  #     provides = provides,
  #     description = other.description,
  #     requires = other.requires,
  #     before = other.before,
  #     after = other.after,
  #   )


class ConfigItem(metaclass = ABCMeta):
  tags: set[str] = set()

  @abstractmethod
  def identifier(self) -> str:
    """ConfigItems with the same identifier are considered to be the same thing (with possibly
    differing attributes) that will be merged together before running the installation process."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.identifier()")

  def description(self) -> str:
    """Usually, the identifier will be printed in all outputs by koti. Sometimes it may be necessary to
    add some human-readable information. This can be done by overriding this function."""
    return self.identifier()

  @abstractmethod
  def merge(self, other: ConfigItem) -> ConfigItem:
    """This function is called whenever there are multiple items with the same identifier. It can
    attempt to merge those definitions together (or throw an error if they're incompatible)."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.merge()")

  def __eq__(self, other: Any) -> bool:
    return self.identifier() == other.identifier() if other.__class__ == self.__class__ else False

  def __hash__(self):
    return hash(self.identifier())


class ManagedConfigItem(ConfigItem, metaclass = ABCMeta):
  """ConfigItems that can be installed to the system. ManagedConfigItem require a corresponding
  ConfigManager being registered in koti."""


class UnmanagedConfigItem(ConfigItem, metaclass = ABCMeta):
  """ConfigItems that only provide some kind of meta information (e.g. for declaring dependencies)
  or values that are being used by other ConfigItems (e.g. options that get merged into some file)."""
  pass


class ConfigItemState(metaclass = ABCMeta):
  @abstractmethod
  def hash(self) -> str:
    """Method that condenses the whole state into a hash-string that can easily be stored or
    used by foreign managers without having to inspect the implementation of the item state."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.hash()")


class ConfigManager[T: ManagedConfigItem, S: ConfigItemState](metaclass = ABCMeta):
  managed_classes: list[Type] = []
  order_in_cleanup_phase: Literal["reverse_install_order", "first", "last"] = "reverse_install_order"
  warnings: list[str]  # collects warnings during evaluation and execution

  def __init__(self):
    self.warnings = []

  @abstractmethod
  def check_configuration(self, item: T, model: ConfigModel):
    """Used to check if an item has a consistent configuration suitable for later installation."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.check_configuration()")

  @abstractmethod
  def installed(self, model: ConfigModel) -> Sequence[T]:
    """Returns a list of all items currently installed on the system. This may depend on the model, as it may
    be beneficial to check if newly added ConfigItems already exist on the system and display them accordingly.
    In case the installed items cannot be queried from the system (e.g. due to missing tools), a warning should
    be logged and an empty list should be returned."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.installed()")

  @abstractmethod
  def state_current(self, item: T) -> S | None:
    """Returns an object representing the state of a currently installed item on the system."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.checksum_current()")

  @abstractmethod
  def state_target(self, item: T, model: ConfigModel, planning: bool) -> S:
    """Returns an object representing the state that the item will have after installation/updating.
    Can depend on the config model, as there might be e.g. Option()s that need to be considered.
    Also the method can behave different during planning (e.g. PostHooks assume that their triggers
    have already been updated to their respective target states)."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.checksum_target()")

  @abstractmethod
  def diff(self, current: S | None, target: S | None) -> Sequence[str]:
    """Describes the changes between current and target state in a human-friendly fashion.
    Each returned list entry will be printed in a separate line and may contain colors for better readability."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.diff()")

  @abstractmethod
  def install(self, items: list[T], model: ConfigModel):
    """Installs one or multiple items on the system. Can depend on the config model, as there might
    be e.g. Option()s that need to be considered. If the install fails for some reason, a python error
    should be raised, so the whole process gets halted (to avoid getting into inconsistent states)."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.install()")

  @abstractmethod
  def uninstall(self, items: list[T]):
    """Removes one or multiple items from the system. If the uninstall fails for some reason, the manager
    can decide to kill the process by raising a python error or just log a warning in case the failed
    uninstall is unlikely to cause any problems."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.uninstall()")


class ConfigModel:
  managers: Sequence[ConfigManager]
  phases: Sequence[InstallPhase]
  tags_archive: dict[str, set[str]]

  def __init__(
    self,
    managers: Sequence[ConfigManager],
    phases: Sequence[InstallPhase],
    tags_archive: dict[str, set[str]],
  ):
    self.managers = managers
    self.phases = phases
    self.tags_archive = tags_archive

  @overload
  def item[T: ConfigItem](self, reference: T) -> T:
    pass

  @overload
  def item[T: ConfigItem](self, reference: T, optional: Literal[False]) -> T:
    pass

  @overload
  def item[T: ConfigItem](self, reference: T, optional: Literal[True]) -> T | None:
    pass

  def item[T: ConfigItem](self, reference: T, optional: bool = False) -> T | None:
    result = next((
      cast(T, item) for phase in self.phases for item in phase.items
      if item.identifier() == reference.identifier()
    ), None)
    assert result is not None or optional, f"Item not found: {reference.identifier()}"
    return result

  @overload
  def contains(self, needle: ConfigItem) -> bool:
    pass

  @overload
  def contains(self, needle: Callable[[ConfigItem], bool]) -> bool:
    pass

  def contains(self, needle: ConfigItem | Callable[[ConfigItem], bool]) -> bool:
    for phase in self.phases:
      for item in phase.items:
        if isinstance(needle, ConfigItem) and needle.identifier() == item.identifier():
          return True
        if callable(needle) and needle(item):
          return True
    return False

  def manager[T: ManagedConfigItem](self, reference: T) -> ConfigManager[T, ConfigItemState]:
    for manager in self.managers:
      if reference.__class__ in manager.managed_classes:
        return manager
    raise AssertionError(f"manager not found for {reference.identifier()}")

  def tags(self, *args: ManagedConfigItem) -> set[str]:
    return reduce(lambda a, b: a.union(b), (self.__tags(arg) for arg in args), set())

  def __tags(self, arg: ManagedConfigItem) -> set[str]:
    if arg.tags:
      return arg.tags
    item = self.item(arg, optional = True)
    if item is not None:
      return item.tags
    return self.tags_archive.get(arg.identifier(), set())


class InstallPhase:
  groups: Sequence[ConfigGroup]
  items: Sequence[ConfigItem]
  steps: Sequence[InstallStep]

  def __init__(self, groups: Sequence[ConfigGroup], order: Sequence[InstallStep], items: Sequence[ConfigItem]):
    self.items = items
    self.groups = groups
    self.steps = order


class InstallStep:
  manager: ConfigManager
  items_to_install: Sequence[ManagedConfigItem]

  def __init__(self, manager: ConfigManager, items_to_install: Sequence[ManagedConfigItem]):
    self.items_to_install = items_to_install
    self.manager = manager


class CleanupPhase:
  items_to_uninstall: Sequence[ManagedConfigItem]
  items_to_keep: Sequence[ManagedConfigItem]
  steps: Sequence[CleanupStep]

  def __init__(self, steps: list[CleanupStep]):
    self.items_to_uninstall = [item for step in steps for item in step.items_to_uninstall]
    self.items_to_keep = [item for step in steps for item in step.items_to_keep]
    self.steps = steps


class CleanupStep:
  manager: ConfigManager
  items_to_uninstall: list[ManagedConfigItem]
  items_to_keep: list[ManagedConfigItem]

  def __init__(self, manager: ConfigManager, items_to_uninstall: list[ManagedConfigItem], items_to_keep: list[ManagedConfigItem]):
    self.items_to_uninstall = items_to_uninstall
    self.items_to_keep = items_to_keep
    self.manager = manager
