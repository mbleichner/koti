from __future__ import annotations

import sys
from os import getuid
from time import sleep

import koti.utils.shell as shell_module
from koti.model import *
from koti.optimizer import InfeasibleError, KotiOptimizer
from koti.utils.text import *
from koti.utils.confirm import confirm
from koti.utils.json_store import *
from koti.utils.logging import logger


class Koti:
  store: JsonStore
  managers: Sequence[ConfigManager]
  configs: ConfigDict

  def __init__(
    self,
    managers: Sequence[ConfigManager],
    configs: ConfigDict,
  ):
    assert getuid() == 0, "this program must be run as root (or through sudo)"
    self.store = JsonStore("/var/cache/koti/Koti.json")
    self.configs = configs
    self.managers = managers
    self.assert_manager_consistency(self.managers, self.configs)

  def create_model(self) -> ConfigModel:
    merged_configs = self.merge_configs(self.configs)
    optimizer = KotiOptimizer(
      configs = self.get_managed_items_grouped(merged_configs),
      managers = self.managers,
    )

    try:
      install_steps = optimizer.calc_install_steps()
    except InfeasibleError as ex:
      iis = optimizer.find_iis()
      print()
      printc(f"{RED}Koti was not able to calculate a consistent execution order.")
      print("Please check the following items. Very likely you accidentally defined some sort of circular dependency between them.")
      print()
      printc(f"{BOLD}Irreducible Inconsistent Subset:")
      for item in iis:
        print(f"- {item}")
      raise SystemExit()

    model = ConfigModel(
      configs = merged_configs,
      managers = self.managers,
      steps = install_steps,
    )

    self.assert_config_items_installable(model)
    return model

  def create_cleanup_phase(self, model: ConfigModel) -> CleanupPhase:
    items_to_install = [item for step in model.steps for item in step.items_to_install]
    steps: list[CleanupStep] = []
    for manager in self.get_cleanup_phase_manager_order(self.managers):
      steps.append(CleanupStep(
        manager = manager,
        items_to_keep = [item for item in items_to_install if item.__class__ in manager.managed_classes],
      ))
    return CleanupPhase(steps)

  def plan(self, section_summary: bool = False, item_summary: bool = False) -> ExecutionPlan:
    logger.clear()
    logger.info(f"Please note that koti cannot always predict every action accurately. In case some unexpected action needs to be performed during execution phase, you will be asked to review and confirm it.")

    dryrun = True
    model = self.create_model()

    actions: list[Action] = []
    sys.stdout.write("calculating actions to perform...")
    sys.stdout.flush()

    for manager in self.managers:
      manager.initialize(model, dryrun)
    for install_step in model.steps:
      sys.stdout.write(".")
      sys.stdout.flush()
      for action in install_step.manager.plan_install(install_step.items_to_install, model, dryrun):
        actions.append(action)
    cleanup_phase = self.create_cleanup_phase(model)
    for cleanup_step in cleanup_phase.steps:
      sys.stdout.write(".")
      sys.stdout.flush()
      for action in cleanup_step.manager.plan_cleanup(cleanup_step.items_to_keep, model, dryrun):
        actions.append(action)
    for manager in self.managers:
      manager.finalize(model, dryrun)

    print()
    print()

    # list all groups + items
    if section_summary:
      printc(f"{BOLD}Config Section Summary:")
      for group in model.configs:
        prefix = self.prefix_for_item(actions, *(item for item in group.provides if isinstance(item, ManagedConfigItem)))
        printc(f"{prefix} {group.description}")
      print()

    if item_summary:
      printc(f"{BOLD}Config Item Summary:")
      for install_step in model.steps:
        for idx, item in enumerate(install_step.items_to_install):
          prefix = self.prefix_for_item(actions, item)
          printc(f"{prefix} {item}")
      printc(f"{len([item for step in model.steps for item in step.items_to_install])} items total")
      print()

    # print warnings generated during evaluation
    if logger.messages:
      printc(f"{BOLD}Messages logged during planning:")
      for message in list(dict.fromkeys(logger.messages)):
        print_listitem(f"{message}")
      print()

    # list all changed items
    if len(actions) > 0:
      printc(f"{BOLD}Actions that will be executed (in order):")
      for action in actions:
        printc(f"- {self.color_for_action(action)}{action.description}")
        for info in action.additional_info:
          printc(f"  {info}")
      print()

    return ExecutionPlan(
      expected_actions = actions,
      model = model,
    )

  def apply(self, plan: ExecutionPlan):
    logger.clear()
    dryrun = False
    model = plan.model

    for manager in self.managers:
      manager.initialize(model, dryrun)

    # execute install phases
    for install_step in model.steps:
      for action in install_step.manager.plan_install(install_step.items_to_install, model, dryrun):
        self.execute_action(action, plan)

    # execute cleanup phase
    cleanup_phase = self.create_cleanup_phase(model)
    for cleanup_step in cleanup_phase.steps:
      for action in cleanup_step.manager.plan_cleanup(cleanup_step.items_to_keep, model, dryrun):
        self.execute_action(action, plan)

    # updating persistent data
    for manager in self.managers:
      manager.finalize(model, dryrun)

    self.print_divider_line()
    print("execution finished.")

    if logger.messages:
      print()
      printc(f"{BOLD}Messages logged during execution:")
      for message in set(logger.messages):
        printc(f"- {message}")

  def execute_action(self, action: Action, plan: ExecutionPlan):
    try:
      shell_module.verbose_mode = True
      self.print_divider_line()
      printc(f"executing: {self.color_for_action(action)}{action.description}")
      for info in action.additional_info:
        printc(f"{info}")
      if action not in plan.expected_actions:
        confirm("this action was not predicted during planning phase - please confirm to continue")
      action.execute()
      sleep(0.05)  # add a small delay so it's easier to follow when a lot of actions happen
    finally:
      shell_module.verbose_mode = False

  @classmethod
  def print_divider_line(cls):
    printc(f"{"-" * (get_terminal_size().columns - 1)}")

  @classmethod
  def get_managed_items_grouped(cls, merged_configs: Sequence[MergedSection]) -> Sequence[Sequence[ManagedConfigItem]]:
    result: list[list[ManagedConfigItem]] = []
    for config in merged_configs:
      managed_items_in_config = [item for item in config.provides if isinstance(item, ManagedConfigItem)]
      if managed_items_in_config:
        result.append(managed_items_in_config)
    return result

  @classmethod
  def get_cleanup_phase_manager_order(cls, managers: Sequence[ConfigManager]) -> Sequence[ConfigManager]:
    return [
      *[manager for manager in managers if manager.order_in_cleanup_phase == "first"],
      *reversed([manager for manager in managers if manager.order_in_cleanup_phase == "reverse_install_order"]),
      *[manager for manager in managers if manager.order_in_cleanup_phase == "last"],
    ]

  @classmethod
  def assert_config_items_installable(cls, model: ConfigModel):
    """Checks that every item is actually installable (fully configured according to their manager)"""
    for install_step in model.steps:
      for item in install_step.items_to_install:
        try:
          install_step.manager.assert_installable(item, model)
        except Exception as e:
          raise AssertionError(f"{install_step.manager.__class__.__name__}: {e}")

  @classmethod
  def assert_manager_consistency(cls, managers: Sequence[ConfigManager], configs: ConfigDict):
    """Checks that every item has a manager and only one manager"""
    for section, items in cls.iterate_configs(configs):
      for item in items:
        if not isinstance(item, ManagedConfigItem): continue
        matching_managers = [manager for manager in managers if item.__class__ in manager.managed_classes]
        assert len(matching_managers) > 0, f"no manager found for class {item.__class__.__name__}"
        assert len(matching_managers) < 2, f"multiple managers found for class {item.__class__.__name__}"

  @classmethod
  def iterate_configs(cls, configs: ConfigDict) -> Generator[tuple[Section, Sequence[ConfigItem]]]:
    sections_in_deterministic_order = list(configs.keys())
    sections_in_deterministic_order.sort(key = lambda x: x.name)
    for section in sections_in_deterministic_order:
      items = configs[section]
      if not section.enabled or items is None:
        continue  # skip empty or disabled sections
      elif isinstance(items, ConfigItem):
        yield section, [items]
      else:
        yield section, [item for item in items if isinstance(item, ConfigItem)]

  @classmethod
  def merge_configs(cls, configs: ConfigDict) -> list[MergedSection]:
    sections_in_deterministic_order = list(configs.keys())
    sections_in_deterministic_order.sort(key = lambda x: x.name)

    # merge all items with the same identifier
    merged_items: dict[ConfigItem, ConfigItem] = {}
    for section, items in cls.iterate_configs(configs):
      for item in items:
        item_prev = merged_items.get(item, None)
        item_merged = item_prev.merge(item) if item_prev is not None else item
        merged_items[item] = item_merged

    # create new groups with the items replaced by their merged versions
    result: list[MergedSection] = []
    for section, items_original in cls.iterate_configs(configs):
      items_replaced = list(items_original)
      for idx, item in enumerate(items_replaced):
        items_replaced[idx] = merged_items[item]
      merged_section = MergedSection(
        description = section.name,
        provides = items_replaced,
      )
      merged_section.provides = items_replaced
      result.append(merged_section)
    return result

  @classmethod
  def reduce_items(cls, items: list[ConfigItem]) -> ConfigItem:
    if len(items) == 1:
      return items[0]
    merged_item = items[0].merge(items[1])
    return cls.reduce_items([merged_item, *items[2:]])

  @classmethod
  def prefix_for_item(cls, actions: Sequence[Action], *items: ManagedConfigItem) -> str:
    changes: set[Literal["install", "update", "remove"]] = set()
    for item in items:
      for action in actions:
        if item in action.installs: changes.add("install")
        if item in action.updates: changes.add("update")
        if item in action.removes: changes.add("remove")
    if "remove" in changes: return f"{RED}~"
    if "update" in changes: return f"{YELLOW}~"
    if "install" in changes: return f"{GREEN}~"
    return "-"

  @classmethod
  def color_for_action(cls, action: Action) -> str:
    if action.removes:
      return RED
    elif action.updates:
      return YELLOW
    elif action.installs:
      return GREEN
    else:
      return PURPLE
