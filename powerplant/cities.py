from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

from powerplant.materials import Resource


class Color(str, Enum):
  BLUE = "blue"
  RED = "red"
  YELLOW = "yellow"
  PURPLE = "purple"
  BROWN = "brown"
  CYAN = "cyan"


@dataclass
class City:
  name: str = field(compare=True)
  color: Color = field(compare=False)
  occupants: List[int] = field(compare=False, default_factory=list)
  connections: Dict[str, int] = field(compare=False, default_factory=dict)

  @classmethod
  def parse_json(cls, data):
    data["color"] = Color(data["color"])
    return cls(**data)


def connect(cities, name1, name2, cost):
  cities[name1].connections[name2] = cost
  cities[name2].connections[name1] = cost


def Germany():
  city_list = [
      City("FLENSBURG", Color.CYAN),
      City("KIEL", Color.CYAN),
      City("HAMBURG", Color.CYAN),
      City("HANNOVER", Color.CYAN),
      City("BREMEN", Color.CYAN),
      City("CUXHAVEN", Color.CYAN),
      City("WILHELMSHAVEN", Color.CYAN),
      City("OSNABRUCK", Color.RED),
      City("MUNSTER", Color.RED),
      City("ESSEN", Color.RED),
      City("DUISBURG", Color.RED),
      City("DUSSELDORF", Color.RED),
      City("DORTMUND", Color.RED),
      City("KASSEL", Color.RED),
      City("AACHEN", Color.BLUE),
      City("KOLN", Color.BLUE),
      City("TRIER", Color.BLUE),
      City("WIESBADEN", Color.BLUE),
      City("SAARBRUCKEN", Color.BLUE),
      City("MANNHEIM", Color.BLUE),
      City("FRANKFURT-M", Color.BLUE),
      City("STUTTGART", Color.PURPLE),
      City("FREIBURG", Color.PURPLE),
      City("KONSTANZ", Color.PURPLE),
      City("AUGSBURG", Color.PURPLE),
      City("MUNCHEN", Color.PURPLE),
      City("REGENSBURG", Color.PURPLE),
      City("PASSAU", Color.PURPLE),
      City("NURNBERG", Color.YELLOW),
      City("WURZBURG", Color.YELLOW),
      City("FULDA", Color.YELLOW),
      City("ERFURT", Color.YELLOW),
      City("HALLE", Color.YELLOW),
      City("LEIPZIG", Color.YELLOW),
      City("DRESDEN", Color.YELLOW),
      City("MAGDEBURG", Color.BROWN),
      City("BERLIN", Color.BROWN),
      City("FRANKFURT-D", Color.BROWN),
      City("SCHWERIN", Color.BROWN),
      City("TORGELOW", Color.BROWN),
      City("ROSTOCK", Color.BROWN),
      City("LUBECK", Color.BROWN),
  ]
  cities = {city.name: city for city in city_list}
  connect(cities, "FLENSBURG", "KIEL", 4)
  connect(cities, "HAMBURG", "KIEL", 8)
  connect(cities, "LUBECK", "KIEL", 4)
  connect(cities, "HAMBURG", "LUBECK", 6)
  connect(cities, "HAMBURG", "SCHWERIN", 8)
  connect(cities, "HAMBURG", "HANNOVER", 17)
  connect(cities, "HAMBURG", "BREMEN", 11)
  connect(cities, "HAMBURG", "CUXHAVEN", 11)
  connect(cities, "BREMEN", "CUXHAVEN", 8)
  connect(cities, "BREMEN", "WILHELMSHAVEN", 11)
  connect(cities, "BREMEN", "OSNABRUCK", 11)
  connect(cities, "BREMEN", "HANNOVER", 10)
  connect(cities, "HANNOVER", "SCHWERIN", 19)
  connect(cities, "HANNOVER", "MAGDEBURG", 15)
  connect(cities, "HANNOVER", "ERFURT", 19)
  connect(cities, "HANNOVER", "KASSEL", 15)
  connect(cities, "HANNOVER", "OSNABRUCK", 16)
  connect(cities, "OSNABRUCK", "WILHELMSHAVEN", 14)
  connect(cities, "OSNABRUCK", "MUNSTER", 7)
  connect(cities, "OSNABRUCK", "KASSEL", 20)
  connect(cities, "ESSEN", "MUNSTER", 6)
  connect(cities, "ESSEN", "DUISBURG", 0)
  connect(cities, "ESSEN", "DUSSELDORF", 2)
  connect(cities, "ESSEN", "DORTMUND", 4)
  connect(cities, "MUNSTER", "DORTMUND", 2)
  connect(cities, "DUSSELDORF", "KOLN", 4)
  connect(cities, "DUSSELDORF", "AACHEN", 9)
  connect(cities, "KASSEL", "DORTMUND", 18)
  connect(cities, "KASSEL", "FRANKFURT-M", 13)
  connect(cities, "KASSEL", "FULDA", 8)
  connect(cities, "KASSEL", "ERFURT", 15)
  connect(cities, "KOLN", "DUSSELDORF", 4)
  connect(cities, "KOLN", "DORTMUND", 10)
  connect(cities, "KOLN", "AACHEN", 7)
  connect(cities, "KOLN", "TRIER", 20)
  connect(cities, "KOLN", "WIESBADEN", 21)
  connect(cities, "FRANKFURT-M", "DORTMUND", 20)
  connect(cities, "FRANKFURT-M", "WIESBADEN", 0)
  connect(cities, "FRANKFURT-M", "FULDA", 8)
  connect(cities, "FRANKFURT-M", "WURZBURG", 13)
  connect(cities, "TRIER", "AACHEN", 19)
  connect(cities, "TRIER", "WIESBADEN", 18)
  connect(cities, "TRIER", "SAARBRUCKEN", 11)
  connect(cities, "WIESBADEN", "SAARBRUCKEN", 10)
  connect(cities, "WIESBADEN", "MANNHEIM", 11)
  connect(cities, "MANNHEIM", "SAARBRUCKEN", 11)
  connect(cities, "MANNHEIM", "WURZBURG", 10)
  connect(cities, "MANNHEIM", "STUTTGART", 6)
  connect(cities, "STUTTGART", "SAARBRUCKEN", 17)
  connect(cities, "STUTTGART", "FREIBURG", 16)
  connect(cities, "STUTTGART", "KONSTANZ", 16)
  connect(cities, "FREIBURG", "KONSTANZ", 14)
  connect(cities, "STUTTGART", "AUGSBURG", 15)
  connect(cities, "STUTTGART", "WURZBURG", 12)
  connect(cities, "AUGSBURG", "KONSTANZ", 17)
  connect(cities, "AUGSBURG", "MUNCHEN", 6)
  connect(cities, "AUGSBURG", "REGENSBURG", 13)
  connect(cities, "AUGSBURG", "NURNBERG", 18)
  connect(cities, "AUGSBURG", "WURZBURG", 19)
  connect(cities, "MUNCHEN", "PASSAU", 14)
  connect(cities, "REGENSBURG", "PASSAU", 12)
  connect(cities, "REGENSBURG", "MUNCHEN", 10)
  connect(cities, "REGENSBURG", "AUGSBURG", 13)
  connect(cities, "REGENSBURG", "NURNBERG", 12)
  connect(cities, "NURNBERG", "WURZBURG", 8)
  connect(cities, "NURNBERG", "ERFURT", 21)
  connect(cities, "WURZBURG", "FULDA", 11)
  connect(cities, "ERFURT", "FULDA", 13)
  connect(cities, "ERFURT", "HALLE", 6)
  connect(cities, "ERFURT", "DRESDEN", 19)
  connect(cities, "HALLE", "LEIPZIG", 0)
  connect(cities, "HALLE", "BERLIN", 17)
  connect(cities, "HALLE", "MAGDEBURG", 11)
  connect(cities, "LEIPZIG", "DRESDEN", 13)
  connect(cities, "FRANKFURT-D", "LEIPZIG", 21)
  connect(cities, "FRANKFURT-D", "DRESDEN", 16)
  connect(cities, "FRANKFURT-D", "BERLIN", 6)
  connect(cities, "BERLIN", "MAGDEBURG", 10)
  connect(cities, "BERLIN", "SCHWERIN", 18)
  connect(cities, "BERLIN", "TORGELOW", 15)
  connect(cities, "TORGELOW", "ROSTOCK", 19)
  connect(cities, "SCHWERIN", "MAGDEBURG", 16)
  connect(cities, "SCHWERIN", "TORGELOW", 19)
  connect(cities, "SCHWERIN", "ROSTOCK", 6)
  connect(cities, "SCHWERIN", "LUBECK", 6)
  return cities


def CreateCities(region):
  if region == "Germany":
    return Germany()
  raise RuntimeError(f"Unknown region {region}")


def StartingResources(region):
  if region == "Germany":
    return {Resource.COAL: 24, Resource.OIL: 18, Resource.GAS: 6, Resource.URANIUM: 2}
  raise RuntimeError(f"Unknown region {region}")
