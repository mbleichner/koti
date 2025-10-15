from __future__ import annotations

import sys
from collections import defaultdict

from pyscipopt import Constraint as Cons, Expr, Model, Model, SCIP_PARAMEMPHASIS, Variable  # type: ignore

from koti.utils.text import printc, RED
from koti.model import *
from koti.utils.json_store import *


class ExtraConstraints:
  same_value_groups: list[list[ManagedConfigItem]] = []
  different_value_pairs: list[tuple[ManagedConfigItem, ManagedConfigItem]] = []

  def __init__(self,
    same_value_groups: list[list[ManagedConfigItem]] | None = None,
    different_value_pairs: list[tuple[ManagedConfigItem, ManagedConfigItem]] | None = None,
  ):
    self.same_value_groups = same_value_groups or []
    self.different_value_pairs = different_value_pairs or []


class KotiOptimizer:
  """Runs an algorithm to calculate a (near) optimal installation order that minimizes ConfigManager invocations."""
  managers: Sequence[ConfigManager]
  configs: Sequence[Sequence[ManagedConfigItem]]

  def __init__(self, configs: Sequence[Sequence[ManagedConfigItem]], managers: Sequence[ConfigManager]):
    self.managers = managers
    self.configs = configs

  def calc_install_steps(self) -> Sequence[InstallStep]:
    """Runs the solver repeatedly an a partially specified problem, adding additional constraints
    to avoid undesired results whenever necessary.
    (This is a lot faster than specifying the full-scale problem, because the number of constraints grows
    quadratically and involves integer variables. We sacrifice a bit of optimality, but in practice, this
    seems to be barely ever noticeable.)"""
    sys.stdout.write("calculating execution order...")
    sys.stdout.flush()

    try:
      solution: dict[ManagedConfigItem, int] = {}
      constraints: ExtraConstraints | None = ExtraConstraints()
      while constraints is not None:
        solution = self.solve(
          configs = self.configs,
          extra_constraints = constraints,
          is_iis_search = False
        )
        sys.stdout.write(".")
        sys.stdout.flush()
        constraints = self.adjust_constraints(solution, constraints)
    finally:
      print()

    execution_group_count = max(solution.values()) + 1
    execution_groups: list[list[ManagedConfigItem]] = [[] for i in range(execution_group_count)]
    for config in self.configs:
      for item in config:
        execution_groups[solution[item]].append(item)

    # Der Optimierungs-Algorithmus arbeitet unter der Annahme, dass Items innerhalb einer Gruppe beliebig
    # umsortiert werden dürfen. Das kann im Endergebnis u.U. problematisch sein, z.B. wenn man zwei PostHooks
    # hat, die aufeinander aufsetzen. Deshalb müsste man eigentlich nochmal alle von der Optimierung ermittelten
    # Gruppen per linearer Optimierung nachsortieren, sodass die Ordnung jeder einzelnen ConfigGroup eingehalten
    # wird.
    # Bei dieser Nachsortierung könnte es allerdings passieren, dass verschiedene ConfigGroups wild vermischt
    # werden, was im Listing dann wiederum sehr chaotisch aussieht. Da die Result-Liste aus den ConfigGroups
    # erzeugt wird, sollte die Sortierung weitestgehend damit übereinstimmen, weshalb die fehlende Nachsortierung
    # möglicherweise nie zu einem echten Problem wird. Falls doch, ließe sich als Workaround auch eine explizite
    # Ordnung per requires/after/before definieren.

    return [
      InstallStep(manager = self.manager_for(group[0]), items_to_install = group)
      for group in execution_groups
    ]

  def solve(
    self,
    is_iis_search: bool,
    configs: Sequence[Sequence[ManagedConfigItem]],
    extra_constraints: ExtraConstraints = ExtraConstraints(),
  ) -> dict[ManagedConfigItem, int]:
    model = Model("koti")
    objective = model.addVar("objective")

    # create a variable for each item
    items: list[ManagedConfigItem] = list(dict.fromkeys([item for config in configs for item in config]))
    item_to_pos_var: dict[ConfigItem, Variable] = {}
    for other in items:
      item_to_pos_var[other] = model.addVar(vtype = "I")

    # apply constraints enforcing the order within each group
    for config in configs:
      last_item = config[-1]
      pos_var = item_to_pos_var[last_item]
      model.addCons(objective >= pos_var)  # only the last item in each group can influence the objective function
      for idx1, item1 in enumerate(config):
        for idx2, item2 in enumerate(config):
          if idx1 < idx2:
            pos1_var = item_to_pos_var[item1]
            pos2_var = item_to_pos_var[item2]
            abstand = 1 if self.manager_for(item1) != self.manager_for(item2) else 0
            model.addCons(pos2_var - pos1_var >= abstand)

    # apply constraints that are defined by the items themselves
    # (if there is a dependency between two items, they should NEVER end up in the same group, or else their
    # manager would later be allowed to rearrange them - which in turn can break the dependency)
    for subject in items:
      for required_item in subject.requires:
        pos1 = item_to_pos_var.get(required_item, None)
        pos2 = item_to_pos_var[subject]
        if pos1 is not None:
          model.addCons(pos2 - pos1 >= 1)
        elif not is_iis_search:
          raise AssertionError(f"{subject}: required item {required_item} not found")
      for other in items:
        if subject != other and subject.before is not None and subject.before(other):
          pos1 = item_to_pos_var[subject]
          pos2 = item_to_pos_var[other]
          model.addCons(pos2 - pos1 >= 1)
        if subject != other and subject.after is not None and subject.after(other):
          pos1 = item_to_pos_var[other]
          pos2 = item_to_pos_var[subject]
          model.addCons(pos2 - pos1 >= 1)

    # apply constraints that are added during the optimization process
    for bound_group in extra_constraints.same_value_groups:
      for item1, item2 in zip(bound_group[:-1], bound_group[1:]):
        pos1 = item_to_pos_var[item1]
        pos2 = item_to_pos_var[item2]
        model.addCons(pos1 == pos2)
    for item1, item2 in extra_constraints.different_value_pairs:
      pos1 = item_to_pos_var[item1]
      pos2 = item_to_pos_var[item2]
      model.addCons(abs(pos1 - pos2) >= 1)

    model.hideOutput(True)
    model.setMinimize()
    model.setObjective(objective)
    if is_iis_search:
      model.setEmphasis(SCIP_PARAMEMPHASIS.FEASIBILITY)
    model.optimize()
    sol = model.getBestSol()

    if model.getStatus() == "infeasible":
      raise InfeasibleError()

    return dict((item, round(sol[item_to_pos_var[item]])) for item in items)

  def adjust_constraints(
    self,
    solution: dict[ManagedConfigItem, int],
    constraints: ExtraConstraints
  ) -> ExtraConstraints | None:
    """Checks the solution for inconsistencies and adjusts future constraints accordingly."""
    items_by_pos: dict[int, list[ManagedConfigItem]] = defaultdict(list)
    for item, idx in solution.items():
      items_by_pos[idx].append(item)

    new_same_value_groups: list[list[ManagedConfigItem]] = []
    new_different_value_pairs = list(constraints.different_value_pairs)
    result = False
    for grouped in items_by_pos.values():
      items_by_manager: dict[ConfigManager, list[ManagedConfigItem]] = defaultdict(list)
      for other in grouped:
        items_by_manager[self.manager_for(other)].append(other)
      for manager, items_for_manager in items_by_manager.items():
        new_same_value_groups.append(items_for_manager)
      subgroups = list(items_by_manager.values())
      for subgroup1, subgroup2 in zip(subgroups[:-1], subgroups[1:]):
        new_different_value_pairs.append((subgroup1[0], subgroup2[0]))
        result = True

    if result:
      return ExtraConstraints(new_same_value_groups, new_different_value_pairs)
    else:
      return None

  def find_iis(self) -> Sequence[ManagedConfigItem]:
    sys.stdout.write("calculating irreducible infeasible subset...")
    sys.stdout.flush()
    configs: Sequence[Sequence[ManagedConfigItem]] = self.configs

    # successively remove whole item classes
    item_classes = list(dict.fromkeys([item.__class__ for config in configs for item in config]))
    for item_class in item_classes:
      reduced_config = self.remove_item_class(configs, item_class)
      if not self.is_feasible(reduced_config):
        configs = reduced_config
      sys.stdout.write(".")
      sys.stdout.flush()

    # successively remove singular items
    for item in [item for config in configs for item in config]:
      reduced_config = self.remove_item(configs, item)
      if not self.is_feasible(reduced_config):
        configs = reduced_config
        sys.stdout.write(".")
        sys.stdout.flush()

    print()
    return list(dict.fromkeys([item for config in configs for item in config]))

  @classmethod
  def remove_item(cls, configs: Sequence[Sequence[ManagedConfigItem]], item: ManagedConfigItem) -> Sequence[Sequence[ManagedConfigItem]]:
    result: list[Sequence[ManagedConfigItem]] = []
    for config in configs:
      if item in config:
        reduced_items = [x for x in config if x != item]
        if reduced_items:
          result.append(reduced_items)
      else:
        result.append(config)
    return result

  @classmethod
  def remove_item_class(cls, configs: Sequence[Sequence[ManagedConfigItem]], item_class: type[ManagedConfigItem]) -> Sequence[Sequence[ManagedConfigItem]]:
    result: list[Sequence[ManagedConfigItem]] = []
    for config in configs:
      reduced_items = [x for x in config if x.__class__ != item_class]
      if len(reduced_items) != len(config):
        if reduced_items:
          result.append(reduced_items)
      else:
        result.append(config)
    return result

  def is_feasible(self, configs: Sequence[Sequence[ManagedConfigItem]]) -> bool:
    try:
      self.solve(configs = configs, is_iis_search = True)
      return True
    except InfeasibleError:
      return False

  def manager_for(self, item: ConfigItem) -> ConfigManager:
    for manager in self.managers:
      if item.__class__ in manager.managed_classes:
        return manager
    raise AssertionError(f"no manager found for {item}")


class InfeasibleError(AssertionError): pass
