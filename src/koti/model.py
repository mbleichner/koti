from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any, Callable, Generator, Iterable, Literal, Sequence, Type, cast, overload


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


class ConfigItem(metaclass = ABCMeta):
  tags: set[str] = set()

  @abstractmethod
  def __str__(self):
    """Used whenever this item gets printed (during planning and in logs/exceptions). Also, items
    that are different with respect to __eq__ should als return different string representations
    (e.g. PostHookManager relies on this property)."""
    pass

  def __eq__(self, other: Any) -> bool:
    """Should return true if the two object refer to the same thing (with possibly differing attributes).
    Multiple ConfigItems that are equal will be merged together by koti."""
    return str(self) == str(other)

  def __hash__(self):
    """Needs to be consistent with __eq__ (https://docs.python.org/3/reference/datamodel.html#object.__hash__)"""
    return hash(str(self))

  @abstractmethod
  def merge(self, other: ConfigItem) -> ConfigItem:
    """This function is called whenever there are multiple items with the same identifier. It can
    attempt to merge those definitions together (or throw an error if they're incompatible)."""
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.merge()")


class ManagedConfigItem(ConfigItem, metaclass = ABCMeta):
  """ConfigItems that can be installed to the system. ManagedConfigItem require a corresponding
  ConfigManager being registered in koti."""
  pass


class UnmanagedConfigItem(ConfigItem, metaclass = ABCMeta):
  """ConfigItems that only provide some kind of meta information (e.g. for declaring dependencies)
  or values that are being used by other ConfigItems (e.g. options that get merged into some file)."""
  pass


class ConfigItemState(metaclass = ABCMeta):
  @abstractmethod
  def sha256(self) -> str:
    """Method that condenses the whole state into a hash-string that can easily be stored or
    used by foreign managers without having to inspect the implementation of the item state."""
    pass

  def __eq__(self, other: Any) -> bool:
    return self.sha256() == other.sha256() if other.__class__ == self.__class__ else False

  def __hash__(self):
    return hash(self.sha256())


class ConfigManager[T: ManagedConfigItem, S: ConfigItemState](metaclass = ABCMeta):
  managed_classes: list[Type] = []
  order_in_cleanup_phase: Literal["reverse_install_order", "first", "last"] = "reverse_install_order"

  @abstractmethod
  def assert_installable(self, item: T, model: ConfigModel):
    """Used to check if an item has a consistent configuration suitable for later installation.
    Can depend on the model, as some items may need to inspect their execution order, such as PostHooks."""
    pass

  @abstractmethod
  def state_current(self, item: T) -> S | None:
    """Returns an object representing the state of a currently installed item on the system."""
    pass

  @abstractmethod
  def state_target(self, item: T, model: ConfigModel, dryrun: bool) -> S:
    """Returns an object representing the state that the item will have after installation/updating.
    Can depend on the config model, as there might be e.g. Option()s that need to be considered.
    Also the method can behave different during dryrun (e.g. PostHooks assume that their triggers
    have already been updated to their respective target states)."""
    pass

  def states(self, item: T, model: ConfigModel, dryrun: bool) -> tuple[S | None, S | None]:
    """Convenience method to get both current and target state of an item."""
    return self.state_current(item), self.state_target(item, model, dryrun)

  @abstractmethod
  def plan_install(self, items_to_check: Sequence[T], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    """Called during install phases. This method checks a set of items if any actions need to be
    performed and returns them via a Generator. Returned ExecutionPlans will immediately be executed."""
    pass

  @abstractmethod
  def plan_cleanup(self, items_to_keep: Sequence[T], model: ConfigModel, dryrun: bool) -> Generator[Action]:
    """Called during cleanup phase. This method is repsonsible for uninstalling items that are no longer needed.
    Returned ExecutionPlans will immediately be executed."""
    pass

  def initialize(self, model: ConfigModel, dryrun: bool):
    pass

  def finalize(self, model: ConfigModel, dryrun: bool):
    """Called at the end of a successful run. This method is primarily used to synchronise internal persistent
    state with the model (e.g. the list of koti-managed files currently installed on the system)."""
    pass


class Action:
  """Represents an executable action to update one or multiple ManagedConfigItems on the system."""
  installs: Sequence[ManagedConfigItem]
  updates: Sequence[ManagedConfigItem]
  removes: Sequence[ManagedConfigItem]
  execute: Callable[[], None]
  description: str
  additional_info: list[str]
  hash: str

  def __init__(
    self,
    description: str,
    execute: Callable[[], None],
    additional_info: list[str] | str | None = None,
    installs: Sequence[ManagedConfigItem] | None = None,
    updates: Sequence[ManagedConfigItem] | None = None,
    removes: Sequence[ManagedConfigItem] | None = None,
  ):
    self.installs = installs or []
    self.updates = updates or []
    self.removes = removes or []
    self.description = description
    self.execute = execute
    self.additional_info = [additional_info] if isinstance(additional_info, str) else (additional_info or [])

  def __tuple(self):
    return self.description, self.additional_info, self.installs, self.updates, self.removes

  def __hash__(self) -> int:
    return hash(self.__tuple())

  def __eq__(self, other) -> bool:
    return self.__tuple() == other.__tuple() if isinstance(other, Action) else False


class ExecutionPlan:
  model: ConfigModel
  expected_actions: Sequence[Action]

  def __init__(self, model: ConfigModel, actions: Sequence[Action]):
    self.model = model
    self.expected_actions = actions


class ConfigModel:
  """Models the target system state and all phases for installation and cleanup during the koti run."""
  managers: Sequence[ConfigManager]
  phases: Sequence[InstallPhase]

  def __init__(self, managers: Sequence[ConfigManager], phases: Sequence[InstallPhase]):
    self.managers = managers
    self.phases = phases

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
    result = next((cast(T, item) for phase in self.phases for item in phase.items if item == reference), None)
    assert result is not None or optional, f"Item not found: {reference}"
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
        if isinstance(needle, ConfigItem) and needle == item:
          return True
        if callable(needle) and needle(item):
          return True
    return False

  def manager[T: ManagedConfigItem](self, reference: T) -> ConfigManager[T, ConfigItemState]:
    for manager in self.managers:
      if reference.__class__ in manager.managed_classes:
        return manager
    raise AssertionError(f"manager not found for {reference}")


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
  items_to_keep: Sequence[ManagedConfigItem]
  steps: Sequence[CleanupStep]

  def __init__(self, steps: list[CleanupStep]):
    self.items_to_keep = [item for step in steps for item in step.items_to_keep]
    self.steps = steps


class CleanupStep:
  manager: ConfigManager
  items_to_keep: list[ManagedConfigItem]

  def __init__(self, manager: ConfigManager, items_to_keep: list[ManagedConfigItem]):
    self.items_to_keep = items_to_keep
    self.manager = manager
