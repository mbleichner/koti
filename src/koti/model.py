from __future__ import annotations

from abc import ABCMeta, abstractmethod
from functools import reduce
from typing import Iterable, Sequence, Type, cast, overload

from koti.logging import *


class ConfigGroup:
  """The purpose of ConfigGroups is to provide ConfigItems that should be installed on the system.
  It's good practice to create a ConfigGroup for related ConfigItems that should be installed
  within the same phase. Also, ConfigGroups allow to define dependencies on other ConfigGroups
  so they are split into separate phases to control the order of installation."""
  description: str
  requires: Sequence[ConfigItem]
  provides: Sequence[ConfigItem]

  def __init__(
    self,
    description: str,
    provides: Sequence[ConfigItem | None],
    requires: Sequence[ConfigItem | None] | None = None,
    tags: Iterable[str] | None = None,
  ):
    self.description = description
    self.requires = [item for item in (requires or []) if item is not None]
    self.provides = [item for item in (provides or []) if item is not None]
    for item in self.provides:
      for tag in tags or set():
        item.tags.add(tag)


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


class ManagedConfigItem(ConfigItem, metaclass = ABCMeta):
  """ConfigItems that can be installed to the system. ManagedConfigItem require a corresponding
  ConfigManager being registered in koti."""


class UnmanagedConfigItem(ConfigItem, metaclass = ABCMeta):
  """ConfigItems that only provide some kind of meta information (e.g. for declaring dependencies)
  or values that are being used by other ConfigItems (e.g. options that get merged into some file)."""
  pass


class SystemState(metaclass = ABCMeta):
  """Represents a state of the system at a specific time. Might be the real system state, but
  might also be a 'simulated' state used to predict updates in later steps."""

  def checksum(self, item: ManagedConfigItem) -> str | None:
    pass


class ConfigManager[T: ManagedConfigItem](metaclass = ABCMeta):
  managed_classes: list[Type] = []
  order_in_cleanup_phase: Literal["reverse_install_order", "first", "last"] = "reverse_install_order"
  log: list[LogMessage]

  def __init__(self):
    self.log = []

  @abstractmethod
  def check_configuration(self, item: T, model: ConfigModel):
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.check_configuration()")

  @abstractmethod
  def installed(self, model: ConfigModel) -> Sequence[T]:
    """Returns a list of all items currently installed on the system. This may depend on the model, as it may
    be beneficial to check if newly added ConfigItems already exist on the system and display them accordingly."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.installed()")

  @abstractmethod
  def checksum_current(self, item: T) -> str:
    """Returns the checksum of a currently installed item on the system."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.checksum_current()")

  @abstractmethod
  def checksum_target(self, item: T, model: ConfigModel, state: SystemState) -> str:
    """Returns the checksum that the item will have after installation/updating.
    Can depend on the config model, as there might be e.g. Option()s that need to be considered.
    Can also depend on the system state, as e.g. PostHooks need to be triggered in response to other changes."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.checksum_target()")

  @abstractmethod
  def install(self, items: list[T], model: ConfigModel, state: SystemState):
    """Installs one or multiple items on the system.
    Can depend on the config model, as there might be e.g. Option()s that need to be considered.
    Can also depend on the system state, as e.g. PostHooks need to be triggered in response to other changes."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.install()")

  @abstractmethod
  def uninstall(self, items: list[T], model: ConfigModel):
    """Removes one or multiple items from the system."""
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

  def __init__(self, order: list[CleanupStep]):
    self.items_to_uninstall = [item for step in order for item in step.items_to_uninstall]
    self.items_to_keep = [item for step in order for item in step.items_to_keep]
    self.steps = order


class CleanupStep:
  manager: ConfigManager
  items_to_uninstall: list[ManagedConfigItem]
  items_to_keep: list[ManagedConfigItem]

  def __init__(self, manager: ConfigManager, items_to_uninstall: list[ManagedConfigItem], items_to_keep: list[ManagedConfigItem]):
    self.items_to_uninstall = items_to_uninstall
    self.items_to_keep = items_to_keep
    self.manager = manager
