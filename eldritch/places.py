from collections import namedtuple


class Place(object):
  pass


class LostInTimeAndSpace(Place):

  def __init__(self):
    self.name = "Lost"

  def json_repr(self):
    return {"name": self.name}


class CityPlace(Place):

  MOVEMENT_OPPOSITES = {"black": "white", "white": "black"}

  def __init__(self, name, long_name):
    assert name is not None
    assert long_name is not None
    self.name = name
    self.long_name = long_name
    self.connections = set()
    self.movement = {"white": None, "black": None}
    self.neighborhood = None
    self.encounters = None
    self.closed = False

  def __eq__(self, other):
    return type(self) == type(other) and self.name == other.name

  def __hash__(self):
    return hash(self.name)

  def json_repr(self):
    movement = {
        "white": self.movement["white"].name if self.movement["white"] else None,
        "black": self.movement["black"].name if self.movement["black"] else None,
    }
    return {
        "name": self.name,
        "long_name": self.long_name,
        "connections": [x.name for x in self.connections],
        "movement": movement,
        "neighborhood": self.neighborhood.name if self.neighborhood else None,
        "closed": self.closed,
    }

  def _add_connections(self, *other_places):
    for other in other_places:
      self.connections.add(other)
      other.connections.add(self)

  def _add_monster_movement(self, color, destination):
    assert destination in self.connections
    assert color in self.MOVEMENT_OPPOSITES
    self.movement[color] = destination


class Sky(CityPlace):

  def __init__(self):
    super(Sky, self).__init__("Sky", "Sky")


class Outskirts(CityPlace):

  def __init__(self):
    super(Outskirts, self).__init__("Outskirts", "Outskirts")


class Street(CityPlace):

  def __init__(self, name, long_name):
    super(Street, self).__init__(name, long_name)
    self.encounters = []
    self.neighborhood = self

  def _add_connections(self, *other_places):
    super(Street, self)._add_connections(*other_places)
    for other in other_places:
      if other.neighborhood is None and isinstance(other, Location):
        other.neighborhood = self
        other.movement["black"] = self
        other.movement["white"] = self

  def _add_monster_movement(self, color, destination):
    super(Street, self)._add_monster_movement(color, destination)
    if isinstance(destination, Street):
      destination.movement[self.MOVEMENT_OPPOSITES[color]] = self


class Location(CityPlace):

  def __init__(self, name, long_name, unstable, fixed_encounter=None):
    super(Location, self).__init__(name, long_name)
    self.unstable = unstable
    self.fixed_encounter = fixed_encounter
    self.clues = 0
    self.gate = None
    self.sealed = False

  def _add_connections(self, *other_places):
    super(Location, self)._add_connections(*other_places)
    for other in other_places:
      if self.neighborhood is None and isinstance(other, Street):
        self.neighborhood = other
        self.movement["black"] = other
        self.movement["white"] = other

  def json_repr(self):
    data = super(Location, self).json_repr()
    data.update({attr: getattr(self, attr) for attr in ["unstable", "clues", "gate", "sealed"]})
    return data


def CreatePlaces():
  Newspaper = Location("Newspaper", "Newspaper", False)
  Train = Location("Train", "Train Station", False)
  Shop = Location("Shop", "Curiositie Shoppe", False, None)
  Northside = Street("Northside", "Northside")
  Northside._add_connections(Newspaper, Train, Shop)
  Bank = Location("Bank", "Bank", False, None)
  Asylum = Location("Asylum", "Asylum", False, None)
  Square = Location("Square", "Independence Square", True)
  Downtown = Street("Downtown", "Downtown")
  Downtown._add_connections(Bank, Asylum, Square)
  Roadhouse = Location("Roadhouse", "Hibb's Roadhouse", True)
  Diner = Location("Diner", "Velma's Diner", True)
  Police = Location("Police", "Police Station", False, None)  # TODO: jail?
  Easttown = Street("Easttown", "Easttown")
  Easttown._add_connections(Roadhouse, Diner, Police)
  Graveyard = Location("Graveyard", "Graveyard", True)
  Cave = Location("Cave", "Black Cave", True)
  Store = Location("Store", "General Store", False, None)
  Rivertown = Street("Rivertown", "Rivertown")
  Rivertown._add_connections(Graveyard, Cave, Store)
  Witch = Location("Witch", "Witch House", True)
  Lodge = Location("Lodge", "Silver Twilight Lodge", True)
  FrenchHill = Street("FrenchHill", "French Hill")
  FrenchHill._add_connections(Witch, Lodge)
  House = Location("House", "Ma's Boarding House", False, None)
  Church = Location("Church", "South Church", False, None)
  Society = Location("Society", "Historical Society", True)
  Southside = Street("Southside", "Southside")
  Southside._add_connections(House, Church, Society)
  Woods = Location("Woods", "Woods", True)
  Shoppe = Location("Shoppe", "Þe Old Magick Shoppe", False, None)
  Hospital = Location("Hospital", "St. Mary's Hospital", False, None)
  Uptown = Street("Uptown", "Uptown")
  Uptown._add_connections(Woods, Shoppe, Hospital)
  Library = Location("Library", "Library", False)
  Administration = Location("Administration", "Administration", False, None)
  Science = Location("Science", "Science Building", True, None)
  University = Street("University", "Miskatonic University")
  University._add_connections(Library, Administration, Science)
  Unnamable = Location("Unnamable", "The Unnamable", True)
  Docks = Location("Docks", "River Docks", False, None)
  Isle = Location("Isle", "The Unvisited Isle", True, None)
  Merchant = Street("Merchant", "Merchant District")
  Merchant._add_connections(Unnamable, Docks, Isle)

  Northside._add_connections(Downtown, Merchant)
  Easttown._add_connections(Downtown, Rivertown)
  Merchant._add_connections(Northside, Downtown, Rivertown, University)
  FrenchHill._add_connections(Rivertown, University, Southside)
  Uptown._add_connections(University, Southside)

  Northside._add_monster_movement("black", Merchant)
  Northside._add_monster_movement("white", Downtown)
  Easttown._add_monster_movement("black", Downtown)
  Easttown._add_monster_movement("white", Rivertown)
  University._add_monster_movement("black", Uptown)
  University._add_monster_movement("white", Merchant)
  FrenchHill._add_monster_movement("black", Rivertown)
  FrenchHill._add_monster_movement("white", Southside)
  Southside._add_monster_movement("white", Uptown)
  # TODO: assert that each color makes a full circle.
  # TODO: assert that each location and street has both black and white monster movement

  return {
      place.name: place for place in [
        # Locations
        Shop, Newspaper, Train, Bank, Asylum, Square,
        Roadhouse, Diner, Police, Graveyard, Cave, Store,
        Witch, Lodge, House, Church, Society, Woods, Shoppe, Hospital,
        Library, Administration, Science, Unnamable, Docks, Isle,
        # Streets
        Northside, Downtown, Easttown, Rivertown,
        FrenchHill, Southside, Uptown, University, Merchant,
        # Other
        Sky(), Outskirts(), LostInTimeAndSpace(),
      ]
  }


OtherWorldInfo = namedtuple("OtherWorldInfo", ["name", "colors"])


class OtherWorld(Place):

  def __init__(self, info, order):
    self.info = info
    self.order = order

  @property
  def name(self):
    return f"{self.info.name}{self.order}"

  @property
  def colors(self):
    return self.info.colors

  def json_repr(self):
    return {"name": self.name, "colors": sorted(list(self.colors))}


def CreateOtherWorlds():
  infos = [
      OtherWorldInfo("Abyss", {"blue", "red"}),
      OtherWorldInfo("Another Dimension", {"blue", "green", "red", "yellow"}),
      OtherWorldInfo("City", {"green", "yellow"}),
      OtherWorldInfo("Great Hall", {"blue", "green"}),
      OtherWorldInfo("Plateau", {"green", "red"}),
      OtherWorldInfo("Sunken City", {"red", "yellow"}),
      OtherWorldInfo("Dreamlands", {"blue", "green", "red", "yellow"}),
      OtherWorldInfo("Pluto", {"blue", "yellow"}),
  ]
  worlds = []
  for info in infos:
    worlds.extend([OtherWorld(info, 1), OtherWorld(info, 2)])
  return infos, {world.name: world for world in worlds}
