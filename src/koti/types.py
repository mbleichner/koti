from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import Literal, Sequence, Type, Optional, Generator, cast

from koti.confirmmode import ConfirmModeValues, highest_confirm_mode


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

  # ConfigItems with the same identifier are considered to be the same thing (with possibly
  # differing attributes) that will be merged together before running the installation process.
  @abstractmethod
  def identifier(self) -> str:
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.identifier()")

  # Usually, the identifier will be printed in all outputs by koti. Sometimes it may be necessary to
  # add some human-readable information. This can be done by overriding this function.
  def description(self) -> str:
    return self.identifier()

  # This function is called whenever there are multiple items with the same identifier. It can
  # attempt to merge those definitions together (or throw an error if they're incompatible).
  @abstractmethod
  def merge(self, other: ConfigItem) -> ConfigItem:
    raise NotImplementedError(f"method not implemented: {self.__class__.__name__}.merge()")


# ConfigItems that can be installed to the system. ManagedConfigItem require a corresponding
# ConfigManager being registered in koti.
class ManagedConfigItem(ConfigItem, metaclass = ABCMeta):
  confirm_mode: Optional[ConfirmModeValues] = None


# ConfigItems that only provide some kind of meta information (e.g. for declaring dependencies)
# or values that are being used by other ConfigItems (e.g. options that get merged into some file).
class UnmanagedConfigItem(ConfigItem, metaclass = ABCMeta):
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
  default_confirm_mode: ConfirmModeValues
  install_phases: Sequence[InstallPhase]
  cleanup_phase: CleanupPhase
  managers:Sequence[ConfigManager]

  def __init__(
    self,
    managers:Sequence[ConfigManager],
    default_confirm_mode: ConfirmModeValues,
    install_phases: Sequence[InstallPhase],
    cleanup_phase: CleanupPhase,
  ):
    self.managers = managers
    self.install_phases = install_phases
    self.cleanup_phase = cleanup_phase
    self.default_confirm_mode = default_confirm_mode

  def find[T: ConfigItem](self, reference: T) -> T | None:
    return next((
      cast(T, item)
      for phase in self.install_phases
      for item in phase.items
      if item.identifier() == reference.identifier()
    ), None)

  def iter[T: ConfigItem](self, reference: T) -> Generator[T]:
    result = self.find(reference)
    if result is not None: yield result

  def get_confirm_mode(self, *args: ManagedConfigItem | ConfirmModeValues) -> ConfirmModeValues:
    confirm_modes_from_strings = [item for item in args if isinstance(item, str)]
    confirm_modes_from_items = [item.confirm_mode for item in args if isinstance(item, ManagedConfigItem)]
    highest = highest_confirm_mode(*confirm_modes_from_items, *confirm_modes_from_strings)
    if highest: return highest
    return self.default_confirm_mode


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
