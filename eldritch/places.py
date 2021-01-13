import eldritch.events as events


class Place(object):

  MOVEMENT_OPPOSITES = {"black": "white", "white": "black"}

  def __init__(self, name, long_name):
    assert name is not None
    assert long_name is not None
    self.name = name
    self.long_name = long_name
    self.connections = set()
    self.movement = {"white": None, "black": None}
    self.monsters = []
    self.neighborhood = None
    self.closed = False

  def __eq__(self, other):
    return type(self) == type(other) and self.name == other.name

  def __hash__(self):
    return hash(self.name)

  def json_repr(self):
    return {
        "name": self.name,
        "long_name": self.long_name,
        "connections": [x.name for x in self.connections],
        "movement": {"white": self.movement["white"].name, "black": self.movement["black"].name},
        "neighborhood": self.neighborhood.name,
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


class Street(Place):

  def __init__(self, name, long_name):
    super(Street, self).__init__(name, long_name)
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


class Location(Place):

  def __init__(self, name, long_name, fixed_encounter=None):
    super(Location, self).__init__(name, long_name)
    self.encounters = []
    self.fixed_encounter = fixed_encounter

  def _add_connections(self, *other_places):
    super(Location, self)._add_connections(*other_places)
    for other in other_places:
      if self.neighborhood is None and isinstance(other, Street):
        self.neighborhood = other
        self.movement["black"] = other
        self.movement["white"] = other

  def _add_encounters(self, *encouters):
    pass


class OtherWorld(Place):
  pass


Newspaper = Location("Newspaper", "Newspaper")
Train = Location("Train", "Train Station")
Shop = Location("Shop", "Curiositie Shoppe", None)
Northside = Street("Northside", "Northside")
Northside._add_connections(Newspaper, Train, Shop)
Bank = Location("Bank", "Bank", None)
Asylum = Location("Asylum", "Asylum", None)
Square = Location("Square", "Independence Square")
Downtown = Street("Downtown", "Downtown")
Downtown._add_connections(Bank, Asylum, Square)
Roadhouse = Location("Roadhouse", "Hibb's Roadhouse")
Diner = Location("Diner", "Velma's Diner")
Police = Location("Police", "Police Station", None)  # TODO: jail?
Easttown = Street("Easttown", "Easttown")
Easttown._add_connections(Roadhouse, Diner, Police)
Graveyard = Location("Graveyard", "Graveyard")
Cave = Location("Cave", "Black Cave")
Store = Location("Store", "General Store", None)
Rivertown = Street("Rivertown", "Rivertown")
Rivertown._add_connections(Graveyard, Cave, Store)
Witch = Location("Witch", "Witch House")
Lodge = Location("Lodge", "Silver Twilight Lodge")
FrenchHill = Street("FrenchHill", "French Hill")
FrenchHill._add_connections(Witch, Lodge)
House = Location("House", "Ma's Boarding House", None)
Church = Location("Church", "South Church", None)
Society = Location("Society", "Historical Society")
Southside = Street("Southside", "Southside")
Southside._add_connections(House, Church, Society)
Woods = Location("Woods", "Woods")
Shoppe = Location("Shoppe", "Þe Old Magick Shoppe", None)
Hospital = Location("Hospital", "St. Mary's Hospital", None)
Uptown = Street("Uptown", "Uptown")
Uptown._add_connections(Woods, Shoppe, Hospital)
Library = Location("Library", "Library")
Administration = Location("Administration", "Administration", None)
Science = Location("Science", "Science Building", None)
University = Street("University", "Miskatonic University")
University._add_connections(Library, Administration, Science)
Unnamable = Location("Unnamable", "The Unnamable")
Docks = Location("Docks", "River Docks", None)
Isle = Location("Isle", "The Unvisited Isle", None)
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

# TODO: move these to a separate file with all the cards
def Diner2(char):
  return events.DrawSpecific(char, "common", "Food")
def Diner3(char):
  adj = events.GainOrLoss(char, {"stamina": 2}, {"dollars": 1})
  choice = events.BinaryChoice(char, "Pay $1 for pie?", "Pay $1", "Go Hungry", adj, events.Nothing());
  prereq = events.AttributePrerequisite(char, "dollars", 1, "at least")
  return events.PassFail(char, prereq, choice, events.Nothing())
def Diner4(char):
  gain = events.Gain(char, {"dollars": 5})
  check = events.Check(char, "will", -2)
  return events.PassFail(char, check, gain, events.Nothing())
def Diner7(char):
  move = events.ForceMovement(char, "Easttown")
  die = events.DiceRoll(char, 1)
  gain = events.Gain(char, {"dollars": die})
  check = events.Check(char, "sneak", -1)
  return events.PassFail(char, check, events.Sequence([die, gain]), move)
Diner.encounters.append(Diner2)
Diner.encounters.append(Diner3)
Diner.encounters.append(Diner4)
Diner.encounters.append(Diner7)


LOCATIONS = {
    loc.name: loc for loc in [
      Shop, Newspaper, Train, Bank, Asylum, Square, 
      Roadhouse, Diner, Police, Graveyard, Cave, Store,
      Witch, Lodge, House, Church, Society, Woods, Shoppe, Hospital,
      Library, Administration, Science, Unnamable, Docks, Isle,
    ]
}
STREETS = {
    street.name: street for street in [
      Northside, Downtown, Easttown, Rivertown,
      FrenchHill, Southside, Uptown, University, Merchant,
    ]
}
# TODO: otherworld locations
