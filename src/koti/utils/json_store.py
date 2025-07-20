from __future__ import annotations

import json
import os
from pathlib import Path


class JsonStore:
  store_file: str
  store: dict

  # noinspection PyBroadException
  def __init__(self, store_file: str):
    self.store_file = store_file
    try:
      with open(self.store_file, encoding = 'utf-8') as fh:
        self.store = json.load(fh)
    except:
      self.store = {}

  def mapping[K, V](self, name) -> JsonMapping[K, V]:
    return JsonMapping[K, V](self, name)

  def collection[T](self, name) -> JsonCollection[T]:
    return JsonCollection[T](self, name)

  def get(self, key, default = None):
    return self.store.get(key, default)

  def put(self, key, value):
    self.store[key] = value
    Path(os.path.dirname(self.store_file)).mkdir(parents = True, exist_ok = True)
    with open(self.store_file, 'w+', encoding = 'utf-8') as fh:
      # noinspection PyTypeChecker
      json.dump(self.store, fh)


class JsonMapping[K, V]:
  store: JsonStore
  name: str

  def __init__(self, store: JsonStore, name: str):
    self.name = name
    self.store = store

  def clear(self):
    self.store.put(self.name, {})

  def get[F](self, key: K, default: F) -> V | F:
    mapping: dict[K, V] = self.store.get(self.name, {})
    return mapping.get(key, default)

  def put(self, key: K, value: V):
    mapping: dict[K, V] = self.store.get(self.name, {})
    mapping[key] = value
    self.store.put(self.name, mapping)

  def remove(self, key: K):
    mapping: dict[K, V] = self.store.get(self.name, {})
    mapping.pop(key, None)
    self.store.put(self.name, mapping)

  def keys(self) -> list[K]:
    mapping: dict[K, V] = self.store.get(self.name, {})
    return list(mapping.keys())


class JsonCollection[T]:
  store: JsonStore
  name: str

  def __init__(self, store: JsonStore, name: str):
    self.name = name
    self.store = store

  def elements(self) -> list[T]:
    collection = self.store.get(self.name, [])
    return collection

  def add(self, value: T):
    collection = self.store.get(self.name, [])
    new_collection = set(collection).union({value})
    self.store.put(self.name, list(new_collection))

  def remove(self, value: T):
    collection = self.store.get(self.name, [])
    new_collection = set(collection).difference({value})
    self.store.put(self.name, list(new_collection))
