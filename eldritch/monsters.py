class MonsterCup(object):

  def __init__(self):
    self.name = "cup"


class Monster(object):

  MOVEMENTS = {"normal", "fast", "stationary", "flying", "stalker", "aquatic", "unique"}
  DIMENSIONS = {"circle", "triangle", "moon", "hex", "square", "diamond", "star", "slash", "plus"}
  DIFFICULTIES = {"horror", "combat", "evade"}
  DAMAGES = {"horror", "combat"}
  ATTRIBUTES = {
      "magical resistance", "magical immunity", "physical resistance", "physical immunity",
      "undead", "ambush", "elusive", "endless", "mask", "spawn",
  }

  def __init__(self, name, movement, dimension, difficulties, damages, toughness, attributes=None):
    if attributes is None:
      attributes = []
    assert movement in self.MOVEMENTS
    assert dimension in self.DIMENSIONS
    assert not {"evade", "combat"} - difficulties.keys()
    assert not difficulties.keys() - self.DIFFICULTIES
    assert not damages.keys() - self.DAMAGES
    assert not damages.keys() - difficulties.keys()
    assert not set(attributes) - self.ATTRIBUTES
    self.name = name
    self.movement = movement
    self.dimension = dimension
    self.difficulties = difficulties
    self.damages = damages
    self._toughness = toughness
    self.attributes = attributes
    self.place = None

  def json_repr(self):
    return {
        "name": self.name,
        "movement": self.movement,
        "dimension": self.dimension,
        "attributes": sorted(list(self.attributes)),
        "place": getattr(self.place, "name", None),
    }

  @property
  def undead(self):
    return "undead" in self.attributes

  def difficulty(self, check_type, state):
    modifier = state.get_modifier(self, check_type + "difficulty")
    if modifier:
      return (self.difficulties.get(check_type) or 0) + modifier
    return self.difficulties.get(check_type)

  def damage(self, check_type, state):
    modifier = state.get_modifier(self, check_type + "damage")
    if modifier:
      return (self.damages.get(check_type) or 0) + modifier
    return self.damages.get(check_type)

  def toughness(self, state):
    return self._toughness + state.get_modifier(self, "toughness")


def Cultist():
  return Monster("Cultist", "normal", "moon", {"evade": -3, "combat": 1}, {"combat": 1}, 1)
def DimensionalShambler():
  return Monster(
      "Dimensional Shambler", "fast", "square", {"evade": -3, "horror": -2, "combat": -2},
      {"horror": 2, "combat": 0}, 1,
  )
def ElderThing():  # TODO: custom class after adding item discarding
  return Monster(
      "Elder Thing", "normal", "diamond", {"evade": -2, "horror": -3, "combat": 0},
      {"horror": 2, "combat": 1}, 2,
  )
def FormlessSpawn():
  return Monster(
      "Formless Spawn", "normal", "hex", {"evade": 0, "horror": -1, "combat": -2},
      {"horror": 2, "combat": 2}, 2, {"physical immunity"},
  )
def Ghost():
  return Monster(
      "Ghost", "stationary", "moon", {"evade": -3, "horror": -2, "combat": -3},
      {"horror": 2, "combat": 2}, 1, {"physical immunity", "undead"},
  )
def Ghoul():
  return Monster(
      "Ghoul", "normal", "hex", {"evade": -3, "horror": 0, "combat": -1},
      {"horror": 1, "combat": 1}, 1, {"ambush"},
  )
def FurryBeast():
  return Monster(
      "Furry Beast", "normal", "slash", {"evade": -2, "horror": -1, "combat": -2},
      {"horror": 2, "combat": 4}, 3,  # TODO: overwhelming
  )
def Maniac():  # TODO: custom class when we add globals
  return Monster("Maniac", "normal", "moon", {"evade": -1, "combat": 1}, {"combat": 1}, 1)
def DreamFlier():  # TODO: failing a combat check sends you through a gate
  return Monster(
      "Dream Flier", "flying", "slash", {"evade": -2, "horror": -1, "combat": -2},
      {"horror": 1, "combat": 0}, 2,
  )
def Octopoid():
  return Monster(
      "Octopoid", "normal", "plus", {"evade": -1, "horror": -3, "combat": -3},
      {"horror": 2, "combat": 3}, 3,
  )
def Warlock():  # TODO: succeeding at a combat check returns it to the box
  return Monster(
      "Warlock", "stationary", "circle", {"evade": -2, "horror": -1, "combat": -3},
      {"horror": 1, "combat": 1}, 2, {"magical immunity"},
  )
def Zombie():
  return Monster(
      "Zombie", "normal", "moon", {"evade": 1, "horror": -1, "combat": -1},
      {"horror": 1, "combat": 2}, 1, {"undead"},
  )


MONSTERS = {
    x().name: x for x in [
      Cultist, DimensionalShambler, ElderThing, FormlessSpawn, Ghost, Ghoul, FurryBeast, Maniac,
      DreamFlier, Octopoid, Warlock, Zombie,
    ]
}


def CreateMonsters():
  counts = {
      "Cultist": 6,
      "Dimensional Shambler": 2,
      "Elder Thing": 2,
      "Formless Spawn": 2,
      "Ghost": 3,
      "Ghoul": 3,
      "Furry Beast": 2,
      "Maniac": 3,
      "Dream Flier": 2,
      "Octopoid": 2,
      "Warlock": 2,
      "Zombie": 3,
  }
  monsters = []
  for name, count in counts.items():
    monsters.extend([MONSTERS[name]() for _ in range(count)])
  return monsters
