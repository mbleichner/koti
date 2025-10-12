from __future__ import annotations

import re
from typing import Iterable, Unpack

from urllib3 import request

from koti.model import ConfigItem, ManagedConfigItem, ManagedConfigItemBaseArgs


class FlatpakRepo(ManagedConfigItem):
  name: str
  repo_url: str | None
  spec_url: str | None

  def __init__(
    self,
    name: str,
    spec_url: str | None = None,
    repo_url: str | None = None,
    **kwargs: Unpack[ManagedConfigItemBaseArgs],
  ):
    super().__init__(**kwargs)
    self.name = name
    self.spec_url = spec_url
    if repo_url is not None:
      self.repo_url = repo_url
    elif spec_url is not None:
      self.repo_url = FlatpakRepo.get_repo_url_from_spec(spec_url)
    else:
      self.repo_url = None

  def __str__(self) -> str:
    return f"FlatpakRepo('{self.name}')"

  def merge(self, other: ConfigItem) -> FlatpakRepo:
    assert isinstance(other, FlatpakRepo) and self == other
    assert other.spec_url == self.spec_url, f"Conflicting spec_url in {self}"
    assert other.repo_url == self.repo_url, f"Conflicting repo_url in {self}"
    return FlatpakRepo(
      name = self.name,
      spec_url = self.spec_url,
      repo_url = self.repo_url,
      **self.merge_base_attrs(self, other),
    )

  @staticmethod
  def get_repo_url_from_spec(install_url: str) -> str:
    response = request("GET", install_url)
    assert response.status == 200
    data = response.data.decode("utf-8")
    match = re.findall("Url=(.+)", data)
    assert match
    return match[0]
