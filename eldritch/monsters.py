class MonsterCup:

  def __init__(self):
    self.name = "cup"

  def json_repr(self):
    return self.name


class Monster:

  MOVEMENTS = {"normal", "fast", "stationary", "flying", "stalker", "aquatic", "unique"}
  DIMENSIONS = {"circle", "triangle", "moon", "hex", "square", "diamond", "star", "slash", "plus"}
  DIFFICULTIES = {"horror", "combat", "evade"}
  DAMAGES = {"horror", "combat"}
  ATTRIBUTES = {
      "magical resistance", "magical immunity", "physical resistance", "physical immunity",
      "undead", "ambush", "elusive", "endless", "mask", "spawn",
  }
  ALL_ATTRIBUTES = ATTRIBUTES | {"nightmarish", "overwhelming"}

  def __init__(
      self, name, movement, dimension, ratings, damages, toughness, attributes=None, bypass=None,
  ):
    if attributes is None:
      attributes = set()
    if bypass is None:
      bypass = {}
    assert movement in self.MOVEMENTS
    assert dimension in self.DIMENSIONS
    assert not {"evade", "combat"} - ratings.keys()
    assert not ratings.keys() - self.DIFFICULTIES
    assert not damages.keys() - self.DAMAGES
    assert not damages.keys() - ratings.keys()
    assert not attributes - self.ATTRIBUTES
    assert not bypass.keys() - damages.keys()
    assert len(attributes & {"magical resistance", "magical immunity"}) < 2
    assert len(attributes & {"physical resistance", "physical immunity"}) < 2
    self.name = name
    self.movement = movement
    self.dimension = dimension
    self.difficulties = ratings
    self.damages = damages
    self._toughness = toughness
    self._attributes = attributes
    self.bypass = bypass
    if "combat" in bypass:
      self._attributes.add("overwhelming")
    if "horror" in bypass:
      self._attributes.add("nightmarish")
    self.idx = None
    self.place = None

  def __repr__(self):
    if self.place is None:
      return f"<Monster: {self.name} {id(self)} at nowhere>"
    return f"<Monster: {self.name} {id(self)} at {self.place}>"

  @property
  def handle(self):
    if self.idx is None:
      return self.name
    return f"{self.name}{self.idx}"

  def json_repr(self):
    return {
        "name": self.name,
        "handle": self.handle,
        "movement": self.movement,
        "dimension": self.dimension,
        "idx": self.idx,
        "place": getattr(self.place, "name", None),
    }

  def difficulty(self, check_type, state, char):
    state_modifier = state.get_modifier(self, check_type + "difficulty") or 0
    char_modifier = char.get_modifier(self, check_type + "difficulty") or 0
    if state_modifier or char_modifier:
      return (self.difficulties.get(check_type) or 0) + state_modifier + char_modifier
    return self.difficulties.get(check_type)

  def damage(self, check_type, state, char):
    state_modifier = state.get_modifier(self, check_type + "damage") or 0
    char_modifier = char.get_modifier(self, check_type + "damage") or 0
    if state_modifier or char_modifier:
      return min((self.damages.get(check_type) or 0) + state_modifier + char_modifier, 0)
    return self.damages.get(check_type)

  def bypass_damage(self, check_type, state):  # pylint: disable=unused-argument
    return self.bypass.get(check_type)

  def toughness(self, state, char):
    state_modifier = state.get_modifier(self, "toughness")
    char_modifier = char.get_modifier(self, "toughness")
    return max(self._toughness + (state_modifier or 0) + (char_modifier or 0), 1)

  def attributes(self, state, char):
    attrs = set()
    for attr in self.ALL_ATTRIBUTES:
      if self.has_attribute(attr, state, char):
        attrs.add(attr)
    return attrs

  def has_attribute(self, attribute, state, char):
    state_override = state.get_override(self, attribute)
    char_override = char.get_override(self, attribute)
    # Prefer specific overrides (at the item level) over general ones (environment, ancient one).
    if char_override is not None:
      return char_override
    if state_override is not None:
      return state_override
    return attribute in self._attributes

  def get_movement(self, state):
    ancient_modifier = state.ancient_one.get_modifier(self, 'movement')
    weather_modifier = (state.environment and state.environment.get_modifier(self, 'movement'))
    return weather_modifier or ancient_modifier or self.movement


def GiantInsect():
  return Monster(
      "Giant Insect", "flying", "circle", {"evade": -2, "horror": -1, "combat": 0},
      {"horror": 1, "combat": 2}, 1,
  )


def LandSquid():
  return Monster(
      "Land Squid", "unique", "triangle", {"evade": 1, "horror": -2, "combat": -3},
      {"horror": 2, "combat": 3}, 3,
  )


def Cultist():
  return Monster("Cultist", "normal", "moon", {"evade": -3, "combat": 1}, {"combat": 1}, 1)


def TentacleTree():
  return Monster(
      "Tentacle Tree", "stationary", "hex", {"evade": -2, "horror": 0, "combat": -1},
      {"horror": 3, "combat": 3}, 3, {"physical resistance"}, {"horror": 1},
  )


def DimensionalShambler():
  return Monster(
      "Dimensional Shambler", "fast", "square", {"evade": -3, "horror": -2, "combat": -2},
      {"horror": 2, "combat": 0}, 1,
  )


def GiantWorm():
  return Monster(
      "Giant Worm", "normal", "circle", {"evade": -1, "horror": -1, "combat": -3},
      {"horror": 4, "combat": 4}, 3, {"physical resistance", "magical resistance"},
      {"combat": 1, "horror": 1},
  )


def ElderThing():  # TODO: custom class after adding item discarding
  return Monster(
      "Elder Thing", "normal", "diamond", {"evade": -2, "horror": -3, "combat": 0},
      {"horror": 2, "combat": 1}, 2,
  )


def FlameMatrix():
  return Monster(
      "Flame Matrix", "flying", "star", {"evade": 0, "combat": -2}, {"combat": 2}, 1,
      {"physical immunity", "ambush"},
  )


def SubterraneanFlier():
  return Monster(
      "Subterranean Flier", "flying", "hex", {"evade": 0, "horror": -2, "combat": -3},
      {"horror": 4, "combat": 3}, 3, {"physical resistance"}, {"combat": 1, "horror": 1},
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
      {"horror": 2, "combat": 4}, 3, None, {"combat": 1},
  )


def Haunter():
  return Monster(
      "Haunter", "flying", "square", {"evade": -3, "horror": -2, "combat": -2},
      {"horror": 2, "combat": 2}, 2, {"mask", "endless"},
  )


def HighPriest():
  return Monster(
      "High Priest", "normal", "plus", {"evade": -2, "horror": 1, "combat": -2},
      {"horror": 1, "combat": 2}, 2, {"magical immunity"},
  )


def Hound():
  return Monster(
      "Hound", "unique", "square", {"evade": -1, "horror": -2, "combat": -1},
      {"horror": 4, "combat": 3}, 2, {"physical immunity"},
  )


def Maniac():  # TODO: custom class when we add globals
  return Monster("Maniac", "normal", "moon", {"evade": -1, "combat": 1}, {"combat": 1}, 1)


def Pinata():
  return Monster(
      "Pinata", "flying", "circle", {"evade": -2, "horror": -1, "combat": 0},
      {"horror": 2, "combat": 1}, 1,
  )


def DreamFlier():  # TODO: failing a combat check sends you through a gate
  return Monster(
      "Dream Flier", "flying", "slash", {"evade": -2, "horror": -1, "combat": -2},
      {"horror": 1, "combat": 0}, 2,
  )


def GiantAmoeba():
  return Monster(
      "Giant Amoeba", "fast", "diamond", {"evade": -1, "horror": -1, "combat": -1},
      {"horror": 3, "combat": 3}, 3, {"physical resistance"}, {"horror": 1},
  )


def Octopoid():
  return Monster(
      "Octopoid", "normal", "plus", {"evade": -1, "horror": -3, "combat": -3},
      {"horror": 2, "combat": 3}, 3,
  )


def Vampire():
  return Monster(
      "Vampire", "normal", "moon", {"evade": -3, "horror": 0, "combat": -3},
      {"horror": 2, "combat": 3}, 2, {"undead", "physical resistance"},
  )


def Warlock():  # TODO: succeeding at a combat check returns it to the box
  return Monster(
      "Warlock", "stationary", "circle", {"evade": -2, "horror": -1, "combat": -3},
      {"horror": 1, "combat": 1}, 2, {"magical immunity"},
  )


def Witch():
  return Monster(
      "Witch", "normal", "circle", {"evade": -1, "combat": -3}, {"combat": 2}, 1,
      {"magical resistance"},
  )


def Zombie():
  return Monster(
      "Zombie", "normal", "moon", {"evade": 1, "horror": -1, "combat": -1},
      {"horror": 1, "combat": 2}, 1, {"undead"},
  )


MONSTERS = {
    x().name: x for x in [
        GiantInsect, LandSquid, Cultist, TentacleTree, DimensionalShambler, GiantWorm, ElderThing,
        FlameMatrix, SubterraneanFlier, FormlessSpawn, Ghost, Ghoul, FurryBeast, Haunter,
        HighPriest, Hound, Maniac, Pinata, DreamFlier, GiantAmoeba, Octopoid, Vampire, Warlock,
        Witch, Zombie,
    ]
}


def CreateMonsters():
  counts = {
      "Giant Insect": 3,
      "Land Squid": 2,
      "Cultist": 6,
      "Tentacle Tree": 3,
      "Dimensional Shambler": 2,
      "Giant Worm": 1,
      "Elder Thing": 2,
      "Flame Matrix": 2,
      "Subterranean Flier": 1,
      "Formless Spawn": 2,
      "Ghost": 3,
      "Ghoul": 3,
      "Furry Beast": 2,
      "High Priest": 1,
      "Hound": 2,
      "Maniac": 3,
      "Pinata": 3,
      "Dream Flier": 2,
      "Giant Amoeba": 2,
      "Octopoid": 2,
      "Vampire": 1,
      "Warlock": 2,
      "Witch": 2,
      "Zombie": 3,
  }
  monsters = []
  for name, count in counts.items():
    monsters.extend([MONSTERS[name]() for _ in range(count)])
  return monsters
