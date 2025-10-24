from functools import wraps
from typing import TypeVar

from koti.model import *
from koti.utils.json_store import *

FuncT = TypeVar("FuncT", bound = Callable[..., Any])


def handle_ctrl_c(func: FuncT) -> FuncT:
  @wraps(func)
  def wrapped(*args: Any, **kwargs: Any) -> Any:
    try:
      return func(*args, **kwargs)
    except KeyboardInterrupt:
      print()
      raise SystemExit("process interrupted by user")

  return cast(FuncT, wrapped)
