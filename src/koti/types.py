from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Literal, Optional, Sequence, Type, cast, overload

from koti.confirmmodes import ConfirmModeValues, highest_confirm_mode


class ConfigGroup:
  description: str
  confirm_mode: ConfirmModeValues | None
  requires: Sequence[ConfigItem]
  provides: Sequence[ConfigItem]

  def __init__(self, description: str, provides: Sequence[ConfigItem | None], requires: Sequence[ConfigItem | None] | None = None, confirm_mode: ConfirmModeValues | None = None):
    self.description = description
    self.confirm_mode = confirm_mode
    self.requires = [item for item in (requires or []) if item is not None]
    self.provides = [item for item in (provides or []) if item is not None]
    for item in [i for i in self.provides if isinstance(i, ManagedConfigItem)]:
      item.confirm_mode = highest_confirm_mode(item.confirm_mode, confirm_mode)

  def __str__(self):
    return f"ConfigGroup('{self.description}')"


class ConfigItem(metaclass = ABCMeta):

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
  confirm_mode: Optional[ConfirmModeValues] = None


class UnmanagedConfigItem(ConfigItem, metaclass = ABCMeta):
  """ConfigItems that only provide some kind of meta information (e.g. for declaring dependencies)
  or values that are being used by other ConfigItems (e.g. options that get merged into some file)."""
  pass


class ConfigManager[T: ManagedConfigItem](metaclass = ABCMeta):
  managed_classes: list[Type] = []
  order_in_cleanup_phase: Literal["reverse_install_order", "first", "last"] = "reverse_install_order"

  @abstractmethod
  def check_configuration(self, item: T, model: ExecutionModel):
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.check_configuration()")

  @abstractmethod
  def checksums(self, model: ExecutionModel) -> Checksums[T]:
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.checksums()")

  @abstractmethod
  def install(self, items: list[T], model: ExecutionModel):
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.install()")

  @abstractmethod
  def cleanup(self, items_to_keep: list[T], model: ExecutionModel):
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.cleanup()")


class Checksums[T:ConfigItem]:

  def current(self, item: T) -> str | None:
    pass

  def target(self, item: T) -> str | None:
    pass


class ExecutionModel:
  managers: Sequence[ConfigManager]
  install_phases: Sequence[InstallPhase]
  cleanup_phase: CleanupPhase
  confirm_mode_fallback: ConfirmModeValues

  def __init__(
    self,
    managers: Sequence[ConfigManager],
    confirm_mode_fallback: ConfirmModeValues,
    install_phases: Sequence[InstallPhase],
    cleanup_phase: CleanupPhase,
  ):
    self.managers = managers
    self.install_phases = install_phases
    self.cleanup_phase = cleanup_phase
    self.confirm_mode_fallback = confirm_mode_fallback

  @overload
  def item[T: ConfigItem, F](self, reference: T) -> T:
    pass

  @overload
  def item[T: ConfigItem, F](self, reference: T, optional: Literal[False]) -> T:
    pass

  @overload
  def item[T: ConfigItem, F](self, reference: T, optional: Literal[True]) -> T | None:
    pass

  def item[T: ConfigItem, F](self, reference: T, optional: bool = False) -> T | None:
    result = next((
      cast(T, item)
      for phase in self.install_phases
      for item in phase.items
      if item.identifier() == reference.identifier()
    ), None)
    assert result is not None or optional, f"Item not found: {reference.identifier()}"
    return result

  def confirm_mode(self, *args: ManagedConfigItem | ConfirmModeValues) -> ConfirmModeValues:
    confirm_modes_from_strings = [item for item in args if isinstance(item, str)]
    confirm_modes_from_items = [item.confirm_mode for item in args if isinstance(item, ManagedConfigItem)]
    highest = highest_confirm_mode(*confirm_modes_from_items, *confirm_modes_from_strings)
    if highest: return highest
    return self.confirm_mode_fallback


class InstallPhase:
  groups: Sequence[ConfigGroup]
  items: Sequence[ConfigItem]
  order: Sequence[tuple[ConfigManager, list[ManagedConfigItem]]]

  def __init__(self, groups: Sequence[ConfigGroup], order: Sequence[tuple[ConfigManager, list[ManagedConfigItem]]], items: Sequence[ConfigItem]):
    self.items = items
    self.groups = groups
    self.order = order


class CleanupPhase:
  order: Sequence[tuple[ConfigManager, list[ManagedConfigItem]]]

  def __init__(self, order: Sequence[tuple[ConfigManager, list[ManagedConfigItem]]]):
    self.order = order
