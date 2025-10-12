from __future__ import annotations

import sys
from collections import defaultdict

from pyscipopt import Constraint as Cons, Expr, Model, Variable  # type: ignore

from koti.model import *
from koti.utils.json_store import *


class Optimizer:
  managers: Sequence[ConfigManager]
  merged_configs: Sequence[ConfigGroup]
  same_value_groups: list[list[ManagedConfigItem]]
  different_value_pairs: list[tuple[ManagedConfigItem, ManagedConfigItem]]
  items: list[ManagedConfigItem]
  item_to_index: dict[ManagedConfigItem, int]

  def __init__(
    self,
    merged_configs: Sequence[ConfigGroup],
    managers: Sequence[ConfigManager],
  ):
    self.managers = managers
    self.merged_configs = merged_configs
    self.same_value_groups = []
    self.different_value_pairs = []
    self.items = []
    self.item_to_index: dict[ManagedConfigItem, int] = {}
    for group in self.merged_configs:
      for other in group.provides:
        if isinstance(other, ManagedConfigItem) and other not in self.item_to_index.keys():
          idx = len(self.items)
          self.item_to_index[other] = idx
          self.items.append(other)

  def run(self) -> ConfigModel:
    sys.stdout.write("calculating execution order...")
    sys.stdout.flush()
    solution = self.optimize()
    while self.adjust_constraints(solution):
      sys.stdout.write(".")
      sys.stdout.flush()
      solution = self.optimize()
    print()

    execution_group_count = max(solution.values()) + 1
    execution_groups: list[list[ManagedConfigItem]] = [[] for i in range(execution_group_count)]
    for item in self.items:
      idx = solution[item]
      execution_groups[idx].append(item)

    # FIXME: einzelne ExecutionGroups nochmal nachsortieren, sodass die Ordnung jeder ConfigGroup eingehalten wird?
    # print(f"GROUP COUNT = {execution_group_count}")

    return ConfigModel(
      managers = self.managers,
      groups = self.merged_configs,
      steps = [InstallStep(manager = self.manager_for(group[0]), items_to_install = group) for group in execution_groups],
    )

  def optimize(self) -> dict[ManagedConfigItem, int]:
    model = Model("koti")
    objective = model.addVar("objective")

    # create a variable for each item
    item_to_pos_var: dict[ConfigItem, Variable] = {}
    for other in self.items:
      idx = self.item_to_index[other]
      pos_var = model.addVar(f"pos_{idx}", vtype = "I")
      item_to_pos_var[other] = pos_var

    # apply constraints enforcing the order within each group
    for group in self.merged_configs:
      group_provides = [i for i in group.provides if isinstance(i, ManagedConfigItem)]
      last_item = group_provides[-1]
      pos_var = item_to_pos_var[last_item]
      model.addCons(objective >= pos_var)  # only the last item in each group can influence the objective function
      for idx1, item1 in enumerate(group_provides):
        for idx2, item2 in enumerate(group_provides):
          if idx1 < idx2:
            pos1_var = item_to_pos_var[item1]
            pos2_var = item_to_pos_var[item2]
            abstand = 1 if self.manager_for(item1) != self.manager_for(item2) else 0
            model.addCons(pos2_var - pos1_var >= abstand)

    # apply constraints that are defined by the items themselves
    # (if there is a dependency between two items, they should NEVER end up in the same group, or else their
    # manager would later be allowed to rearrange them - which in turn can break the dependency)
    for subject in self.items:
      for required_item in subject.requires:
        pos1 = item_to_pos_var[required_item]
        pos2 = item_to_pos_var[subject]
        model.addCons(pos2 - pos1 >= 1)
      for other in self.items:
        if subject != other and subject.before is not None and subject.before(other):
          pos1 = item_to_pos_var[subject]
          pos2 = item_to_pos_var[other]
          model.addCons(pos2 - pos1 >= 1)
        if subject != other and subject.after is not None and subject.after(other):
          pos1 = item_to_pos_var[other]
          pos2 = item_to_pos_var[subject]
          model.addCons(pos2 - pos1 >= 1)

    # apply constraints that are added during the optimization process
    for bound_group in (self.same_value_groups or []):
      for item1, item2 in zip(bound_group[:-1], bound_group[1:]):
        pos1 = item_to_pos_var[item1]
        pos2 = item_to_pos_var[item2]
        model.addCons(pos1 == pos2)
    for item1, item2 in (self.different_value_pairs or []):
      pos1 = item_to_pos_var[item1]
      pos2 = item_to_pos_var[item2]
      model.addCons(abs(pos1 - pos2) >= 1)

    model.hideOutput(True)
    model.setMinimize()
    model.setObjective(objective)
    model.optimize()
    sol = model.getBestSol()
    return dict((item, round(sol[item_to_pos_var[item]])) for item in self.items)

  def adjust_constraints(self, solution: dict[ManagedConfigItem, int]) -> bool:

    items_by_pos: dict[int, list[ManagedConfigItem]] = defaultdict(list)
    for item, idx in solution.items():
      items_by_pos[idx].append(item)

    result = False
    same_value_groups_new: list[list[ManagedConfigItem]] = []
    for grouped in items_by_pos.values():
      items_by_manager: dict[ConfigManager, list[ManagedConfigItem]] = defaultdict(list)
      for other in grouped:
        items_by_manager[self.manager_for(other)].append(other)
      for manager, items_for_manager in items_by_manager.items():
        same_value_groups_new.append(items_for_manager)
      subgroups = list(items_by_manager.values())
      for subgroup1, subgroup2 in zip(subgroups[:-1], subgroups[1:]):
        self.different_value_pairs.append((subgroup1[0], subgroup2[0]))
        result = True

    self.same_value_groups = same_value_groups_new
    return result

  def manager_for(self, item: ConfigItem) -> ConfigManager:
    for manager in self.managers:
      if item.__class__ in manager.managed_classes:
        return manager
    raise AssertionError(f"no manager found for {item}")
