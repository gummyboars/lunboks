from dataclasses import dataclass, field
from typing import Dict

from powerplant.materials import Resource


@dataclass(order=True)
class Plant:
  cost: int = field(compare=True)
  resource: Resource = field(compare=False)
  intake: int = field(compare=False)
  output: int = field(compare=False)
  plus: bool = field(compare=True, default=False)
  storage: Dict[Resource, int] = field(default_factory=dict, compare=False)

  def can_take(self, resource):
    if self.resource is resource:
      return True
    return self.resource is Resource.HYBRID and resource in [Resource.COAL, Resource.OIL]


def OldPlants():
  return [
      Plant(cost=4, resource=Resource.COAL, intake=2, output=1),
      Plant(cost=8, resource=Resource.COAL, intake=3, output=2),
      Plant(cost=10, resource=Resource.COAL, intake=2, output=2),
      Plant(cost=15, resource=Resource.COAL, intake=2, output=3),
      Plant(cost=20, resource=Resource.COAL, intake=3, output=5),
      Plant(cost=25, resource=Resource.COAL, intake=2, output=5),
      Plant(cost=31, resource=Resource.COAL, intake=3, output=6),
      Plant(cost=36, resource=Resource.COAL, intake=3, output=7),
      Plant(cost=42, resource=Resource.COAL, intake=2, output=6),
      Plant(cost=3, resource=Resource.OIL, intake=2, output=1),
      Plant(cost=7, resource=Resource.OIL, intake=3, output=2),
      Plant(cost=9, resource=Resource.OIL, intake=1, output=1),
      Plant(cost=16, resource=Resource.OIL, intake=2, output=3),
      Plant(cost=26, resource=Resource.OIL, intake=2, output=5),
      Plant(cost=32, resource=Resource.OIL, intake=3, output=6),
      Plant(cost=35, resource=Resource.OIL, intake=1, output=5),
      Plant(cost=40, resource=Resource.OIL, intake=2, output=6),
      Plant(cost=5, resource=Resource.HYBRID, intake=2, output=1),
      Plant(cost=12, resource=Resource.HYBRID, intake=2, output=2),
      Plant(cost=21, resource=Resource.HYBRID, intake=2, output=4),
      Plant(cost=29, resource=Resource.HYBRID, intake=1, output=4),
      Plant(cost=46, resource=Resource.HYBRID, intake=3, output=7),
      Plant(cost=6, resource=Resource.GAS, intake=1, output=1),
      Plant(cost=14, resource=Resource.GAS, intake=2, output=2),
      Plant(cost=19, resource=Resource.GAS, intake=2, output=3),
      Plant(cost=24, resource=Resource.GAS, intake=2, output=4),
      Plant(cost=30, resource=Resource.GAS, intake=3, output=6),
      Plant(cost=38, resource=Resource.GAS, intake=3, output=7),
      Plant(cost=11, resource=Resource.URANIUM, intake=1, output=2),
      Plant(cost=17, resource=Resource.URANIUM, intake=1, output=2),
      Plant(cost=23, resource=Resource.URANIUM, intake=1, output=3),
      Plant(cost=28, resource=Resource.URANIUM, intake=1, output=4),
      Plant(cost=34, resource=Resource.URANIUM, intake=1, output=5),
      Plant(cost=39, resource=Resource.URANIUM, intake=1, output=6),
      Plant(cost=13, resource=Resource.GREEN, intake=0, output=1),
      Plant(cost=18, resource=Resource.GREEN, intake=0, output=2),
      Plant(cost=22, resource=Resource.GREEN, intake=0, output=2),
      Plant(cost=27, resource=Resource.GREEN, intake=0, output=3),
      Plant(cost=33, resource=Resource.GREEN, intake=0, output=4),
      Plant(cost=37, resource=Resource.GREEN, intake=0, output=4),
      Plant(cost=44, resource=Resource.GREEN, intake=0, output=5),
      Plant(cost=50, resource=Resource.GREEN, intake=0, output=6),
  ]


def CreatePlants(which):
  if which == "old":
    return OldPlants()
  raise RuntimeError(f"Unknown power plants {which}")


def FixedPlants(which):
  if which == "old":
    return [3, 4, 5, 6, 7, 8, 9, 10]
  raise RuntimeError(f"Unknown power plants {which}")


def TopPlant(which):
  if which == "old":
    return 13
  raise RuntimeError(f"Unknown power plants {which}")
