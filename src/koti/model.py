from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any, Callable, Generator, Iterable, Literal, Sequence, Type, TypedDict, cast, overload

type Phase = Literal["planning", "execution"]
type ConfigItems = Sequence[ConfigItem | None] | Iterable[ConfigItem | None] | ConfigItem | None
type ConfigDict = dict[Section, ConfigItems]


class Section:
  description: str
  enabled: bool

  def __init__(self, description: str, enabled: bool | None = None, disabled: bool | None = None):
    self.description = description
    if enabled is not None and disabled is not None:
      raise AssertionError("only one of enabled/disabled may be specified")
    elif enabled is not None:
      self.enabled = enabled
    elif disabled is not None:
      self.enabled = not disabled
    else:
      self.enabled = True

  def __eq__(self, other: Any):
    return self is other

  def __hash__(self):
    return super().__hash__()


class ConfigItem(metaclass = ABCMeta):
  tags: set[str] = set()

  def __init__(self, tags: Iterable[str] | str | None = None):
    self.tags = {tags} if isinstance(tags, str) else {*(tags or [])}

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


class ManagedConfigItemBaseArgs(TypedDict, total = False):
  """Convenience type to avoid repetition in implemenations."""
  tags: Iterable[str] | str | None
  requires: ManagedConfigItem | Iterable[ManagedConfigItem] | None
  before: ManagedConfigItem | Iterable[ManagedConfigItem] | Callable[[ManagedConfigItem], bool] | None
  after: ManagedConfigItem | Iterable[ManagedConfigItem] | Callable[[ManagedConfigItem], bool] | None


class ManagedConfigItem(ConfigItem, metaclass = ABCMeta):
  """ConfigItems that can be installed to the system. ManagedConfigItem require a corresponding
  ConfigManager being registered in koti."""
  requires: Sequence[ManagedConfigItem]
  after: Sequence[ManagedConfigItem | Callable[[ManagedConfigItem], bool]]
  before: Sequence[ManagedConfigItem | Callable[[ManagedConfigItem], bool]]

  def __init__(
    self,
    tags: Iterable[str] | str | None = None,
    requires: ManagedConfigItem | Iterable[ManagedConfigItem] | None = None,
    before: ManagedConfigItem | Iterable[ManagedConfigItem] | Callable[[ManagedConfigItem], bool] | None = None,
    after: ManagedConfigItem | Iterable[ManagedConfigItem] | Callable[[ManagedConfigItem], bool] | None = None,
  ):
    super().__init__(tags)
    self.requires = self.init_requires(requires)
    self.before = self.init_before_after(before)
    self.after = self.init_before_after(after)

  @classmethod
  def init_before_after(cls, arg: ManagedConfigItem | Iterable[ManagedConfigItem] | Callable[[ManagedConfigItem], bool] | None) -> Sequence[ManagedConfigItem | Callable[[ManagedConfigItem], bool]]:
    if arg is None:
      return []
    if isinstance(arg, ManagedConfigItem):
      return [arg]
    if callable(arg):
      return [arg]
    return list(arg)

  @classmethod
  def init_requires(cls, arg: ManagedConfigItem | Iterable[ManagedConfigItem] | None) -> Sequence[ManagedConfigItem]:
    if arg is None:
      return []
    if isinstance(arg, ManagedConfigItem):
      return [arg]
    return list(arg)

  @staticmethod
  def merge_base_attrs(item1: ManagedConfigItem, item2: ManagedConfigItem) -> dict[str, Any]:
    return {
      "tags": item1.tags.union(item2.tags),
      "requires": [*item1.requires, *item2.requires],
      "before": [*item1.before, *item2.before],
      "after": [*item1.after, *item2.after],
    }


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
  cleanup_order: float = 0.0
  cleanup_order_before: Sequence[type[ConfigManager]] = []  # Restrictions to override the numeric ordering
  cleanup_order_after: Sequence[type[ConfigManager]] = []  # Restrictions to override the numeric ordering

  @abstractmethod
  def assert_installable(self, item: T, model: ConfigModel):
    """Used to check if an item has a consistent configuration suitable for later installation.
    Can depend on the model, as some items may need to inspect their execution order, such as PostHooks."""
    pass

  @abstractmethod
  def get_state_current(self, item: T) -> S | None:
    """Returns an object representing the state of a currently installed item on the system."""
    pass

  @abstractmethod
  def get_state_target(self, item: T, model: ConfigModel, phase: Phase) -> S:
    """Returns an object representing the state that the item will have after installation/updating.
    Can depend on the config model, as there might be e.g. Option()s that need to be considered.
    Also the method can behave different during planning phase (e.g. PostHooks assume that their triggers
    have already been updated to their respective target states)."""
    pass

  def get_states(self, item: T, model: ConfigModel, phase: Phase) -> tuple[S | None, S]:
    """Convenience method to get both current and target state of an item."""
    return self.get_state_current(item), self.get_state_target(item, model, phase)

  @abstractmethod
  def get_install_actions(self, items_to_check: Sequence[T], model: ConfigModel, phase: Phase) -> Generator[Action]:
    """Called during install phases. This method checks a set of items if any actions need to be
    performed and returns them via a Generator. Returned ExecutionPlans will immediately be executed."""
    pass

  @abstractmethod
  def get_cleanup_actions(self, items_to_keep: Sequence[T], model: ConfigModel, phase: Phase) -> Generator[Action]:
    """Called during cleanup phase. This method is repsonsible for uninstalling items that are no longer needed.
    Returned ExecutionPlans will immediately be executed."""
    pass

  def initialize(self, model: ConfigModel, phase: Phase):
    """Called at the start of a run. Can be used to initialize internal states (such as caches)."""
    pass

  def finalize(self, model: ConfigModel, phase: Phase):
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

  def is_covered_by(self, other: Action) -> bool:
    # FIXME: check description?
    if not (set(self.installs) <= set(other.installs)):
      return False
    if not (set(self.updates) <= set(other.updates)):
      return False
    if not (set(self.removes) <= set(other.removes)):
      return False
    return True


class ExecutionPlan:
  """The result of the koti planning phase. It contains the ConfigModel representing the system target
  state and all actions that are expected to be run during the apply() phase. Note: additional actions
  might show up during apply() - in this case koti will ask interactively before running them."""
  model: ConfigModel
  expected_actions: Sequence[Action]

  def __init__(self, model: ConfigModel, expected_actions: Sequence[Action]):
    self.model = model
    self.expected_actions = expected_actions


class ConfigModel:
  """Models the target system state and all phases for installation/cleanup during the koti run. Also
  provides a set of convenience functions to access ConfigItems (useful for dynamic configuration items
  such as files that have their content written by inspecting other items)."""
  configs: Sequence[MergedConfig]
  managers: Sequence[ConfigManager]
  steps: Sequence[InstallStep]

  def __init__(
    self,
    configs: Sequence[MergedConfig],
    managers: Sequence[ConfigManager],
    steps: Sequence[InstallStep],
  ):
    self.configs = configs
    self.managers = managers
    self.steps = steps

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
    result = next((cast(T, item) for group in self.configs for item in group.provides if item == reference), None)
    assert result is not None or optional, f"Item not found: {reference}"
    return result

  @overload
  def contains(self, needle: ConfigItem) -> bool:
    pass

  @overload
  def contains(self, needle: Callable[[ConfigItem], bool]) -> bool:
    pass

  def contains(self, needle: ConfigItem | Callable[[ConfigItem], bool]) -> bool:
    for group in self.configs:
      for item in group.provides:
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


class MergedConfig:
  description: str
  provides: Sequence[ConfigItem]

  def __init__(self, description: str, provides: Sequence[ConfigItem]):
    self.description = description
    self.provides = provides
