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


def USA():
  city_list = [
    City("SAN FRANCISCO", Color.CYAN),
    City("LOS ANGELES", Color.CYAN),
    City("SAN DIEGO", Color.CYAN),
    City("LAS VEGAS", Color.CYAN),
    City("SALT LAKE CITY", Color.CYAN),
    City("PHOENIX", Color.CYAN),
    City("SANTA FE", Color.CYAN),
    City("KANSAS CITY", Color.RED),
    City("OKLAHOMA CITY", Color.RED),
    City("DALLAS", Color.RED),
    City("HOUSTON", Color.RED),
    City("NEW ORLEANS", Color.RED),
    City("MEMPHIS", Color.RED),
    City("BIRMINGHAM", Color.RED),
    City("ATLANTA", Color.BLUE),
    City("SAVANNAH", Color.BLUE),
    City("JACKSONVILLE", Color.BLUE),
    City("TAMPA", Color.BLUE),
    City("MIAMI", Color.BLUE),
    City("RALEIGH", Color.BLUE),
    City("NORFOLK", Color.BLUE),
    City("SEATTLE", Color.PURPLE),
    City("PORTLAND", Color.PURPLE),
    City("BOISE", Color.PURPLE),
    City("BILLINGS", Color.PURPLE),
    City("CHEYENNE", Color.PURPLE),
    City("DENVER", Color.PURPLE),
    City("OMAHA", Color.PURPLE),
    City("FARGO", Color.YELLOW),
    City("MINNEAPOLIS", Color.YELLOW),
    City("DULUTH", Color.YELLOW),
    City("CHICAGO", Color.YELLOW),
    City("ST LOUIS", Color.YELLOW),
    City("CINCINNATI", Color.YELLOW),
    City("KNOXVILLE", Color.YELLOW),
    City("DETROIT", Color.BROWN),
    City("BUFFALO", Color.BROWN),
    City("PITTSBURGH", Color.BROWN),
    City("WASHINGTON", Color.BROWN),
    City("PHILADELPHIA", Color.BROWN),
    City("NEW YORK", Color.BROWN),
    City("BOSTON", Color.BROWN),
  ]
  cities = {city.name: city for city in city_list}
  connect(cities, "SAN FRANCISCO", "PORTLAND", 24)
  connect(cities, "SAN FRANCISCO", "BOISE", 23)
  connect(cities, "SAN FRANCISCO", "SALT LAKE CITY", 27)
  connect(cities, "SAN FRANCISCO", "LAS VEGAS", 14)
  connect(cities, "SAN FRANCISCO", "LOS ANGELES", 9)
  connect(cities, "LAS VEGAS", "SALT LAKE CITY", 18)
  connect(cities, "LAS VEGAS", "SANTA FE", 27)
  connect(cities, "LAS VEGAS", "PHOENIX", 15)
  connect(cities, "LAS VEGAS", "SAN DIEGO", 9)
  connect(cities, "LAS VEGAS", "LOS ANGELES", 9)
  connect(cities, "LOS ANGELES", "SAN DIEGO", 3)
  connect(cities, "PHOENIX", "SAN DIEGO", 14)
  connect(cities, "PHOENIX", "SANTA FE", 18)
  connect(cities, "SANTA FE", "HOUSTON", 21)
  connect(cities, "SANTA FE", "DALLAS", 16)
  connect(cities, "SANTA FE", "OKLAHOMA CITY", 15)
  connect(cities, "SANTA FE", "KANSAS CITY", 16)
  connect(cities, "SANTA FE", "DENVER", 13)
  connect(cities, "SANTA FE", "SALT LAKE CITY", 28)
  connect(cities, "SALT LAKE CITY", "DENVER", 21)
  connect(cities, "SALT LAKE CITY", "BOISE", 8)
  connect(cities, "BOISE", "CHEYENNE", 24)
  connect(cities, "BOISE", "BILLINGS", 12)
  connect(cities, "BOISE", "SEATTLE", 12)
  connect(cities, "BOISE", "PORTLAND", 13)
  connect(cities, "SEATTLE", "PORTLAND", 3)
  connect(cities, "SEATTLE", "BILLINGS", 9)
  connect(cities, "CHEYENNE", "DENVER", 0)
  connect(cities, "BILLINGS", "CHEYENNE", 9)
  connect(cities, "BILLINGS", "FARGO", 17)
  connect(cities, "BILLINGS", "MINNEAPOLIS", 18)
  connect(cities, "CHEYENNE", "MINNEAPOLIS", 18)
  connect(cities, "CHEYENNE", "OMAHA", 14)
  connect(cities, "DENVER", "KANSAS CITY", 16)
  connect(cities, "FARGO", "MINNEAPOLIS", 6)
  connect(cities, "FARGO", "DULUTH", 6)
  connect(cities, "DULUTH", "MINNEAPOLIS", 5)
  connect(cities, "MINNEAPOLIS", "OMAHA", 8)
  connect(cities, "OMAHA", "KANSAS CITY", 5)
  connect(cities, "KANSAS CITY", "OKLAHOMA CITY", 8)
  connect(cities, "OKLAHOMA CITY", "DALLAS", 3)
  connect(cities, "DALLAS", "HOUSTON", 5)
  connect(cities, "DULUTH", "DETROIT", 15)
  connect(cities, "DULUTH", "CHICAGO", 12)
  connect(cities, "MINNEAPOLIS", "CHICAGO", 8)
  connect(cities, "OMAHA", "CHICAGO", 13)
  connect(cities, "KANSAS CITY", "CHICAGO", 8)
  connect(cities, "KANSAS CITY", "ST LOUIS", 6)
  connect(cities, "KANSAS CITY", "MEMPHIS", 12)
  connect(cities, "OKLAHOMA CITY", "MEMPHIS", 14)
  connect(cities, "DALLAS", "MEMPHIS", 12)
  connect(cities, "DALLAS", "NEW ORLEANS", 12)
  connect(cities, "HOUSTON", "NEW ORLEANS", 8)
  connect(cities, "CHICAGO", "ST LOUIS", 10)
  connect(cities, "ST LOUIS", "MEMPHIS", 7)
  connect(cities, "MEMPHIS", "NEW ORLEANS", 7)
  connect(cities, "CHICAGO", "DETROIT", 7)
  connect(cities, "CHICAGO", "CINCINNATI", 7)
  connect(cities, "ST LOUIS", "CINCINNATI", 12)
  connect(cities, "ST LOUIS", "ATLANTA", 12)
  connect(cities, "MEMPHIS", "BIRMINGHAM", 6)
  connect(cities, "BIRMINGHAM", "ATLANTA", 3)
  connect(cities, "NEW ORLEANS", "BIRMINGHAM", 11)
  connect(cities, "NEW ORLEANS", "JACKSONVILLE", 16)
  connect(cities, "DETROIT", "CINCINNATI", 4)
  connect(cities, "CINCINNATI", "KNOXVILLE", 6)
  connect(cities, "KNOXVILLE", "ATLANTA", 5)
  connect(cities, "DETROIT", "BUFFALO", 7)
  connect(cities, "DETROIT", "PITTSBURGH", 6)
  connect(cities, "CINCINNATI", "PITTSBURGH", 7)
  connect(cities, "CINCINNATI", "RALEIGH", 15)
  connect(cities, "ATLANTA", "RALEIGH", 7)
  connect(cities, "ATLANTA", "SAVANNAH", 7)
  connect(cities, "BIRMINGHAM", "JACKSONVILLE", 9)
  connect(cities, "BUFFALO", "PITTSBURGH", 7)
  connect(cities, "PITTSBURGH", "RALEIGH", 7)
  connect(cities, "RALEIGH", "SAVANNAH", 7)
  connect(cities, "SAVANNAH", "JACKSONVILLE", 0)
  connect(cities, "JACKSONVILLE", "TAMPA", 4)
  connect(cities, "TAMPA", "MIAMI", 4)
  connect(cities, "BUFFALO", "NEW YORK", 8)
  connect(cities, "PITTSBURGH", "WASHINGTON", 6)
  connect(cities, "BOSTON", "NEW YORK", 3)
  connect(cities, "NEW YORK", "PHILADELPHIA", 0)
  connect(cities, "PHILADELPHIA", "WASHINGTON", 3)
  connect(cities, "WASHINGTON", "NORFOLK", 5)
  connect(cities, "NORFOLK", "RALEIGH", 3)
  return cities


def CreateCities(region):
  if region == "Germany":
    return Germany()
  if region == "USA":
    return USA()
  raise RuntimeError(f"Unknown region {region}")


def StartingResources(region):
  if region in ["Germany", "USA"]:
    return {Resource.COAL: 24, Resource.OIL: 18, Resource.GAS: 6, Resource.URANIUM: 2}
  raise RuntimeError(f"Unknown region {region}")
