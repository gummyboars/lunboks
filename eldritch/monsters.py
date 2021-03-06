class Monster(object):

  MOVEMENTS = {"normal", "fast", "stationary", "flying", "stalker", "unique"}
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

  def json_repr(self):
    return {"name": self.name}

  @property
  def undead(self):
    return "undead" in self.attributes

  def difficulty(self, check_type):
    return self.difficulties.get(check_type)

  def damage(self, check_type):
    return self.damages.get(check_type)

  @property
  def toughness(self):
    return self._toughness


def Cultist():
  return Monster("Cultist", "normal", "moon", {"evade": -3, "combat": 1}, {"combat": 1}, 1)
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
def Ghoul():
  return Monster(
      "Ghoul", "normal", "hex", {"evade": -3, "horror": 0, "combat": -1},
      {"horror": 1, "combat": 1}, 1, {"ambush"},
  )
def Maniac():  # TODO: custom class when we add globals
  return Monster("Maniac", "normal", "moon", {"evade": -1, "combat": 1}, {"combat": 1}, 1)
def Zombie():
  return Monster(
      "Zombie", "normal", "moon", {"evade": 1, "horror": -1, "combat": -1},
      {"horror": 1, "combat": 2}, 1, {"undead"},
  )

MONSTERS = {x().name: x for x in [Cultist, ElderThing, FormlessSpawn, Ghoul, Maniac, Zombie]}
