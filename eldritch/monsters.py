from eldritch import events
from eldritch import places
from eldritch import values


class MonsterCup:
  def __init__(self):
    self.name = "cup"

  def json_repr(self):
    return self.name


class Monster:
  MOVEMENTS = ("unique", "flying", "stalker", "aquatic", "fast", "stationary", "normal")
  DIMENSIONS = frozenset(
    {"circle", "triangle", "moon", "hex", "square", "diamond", "star", "slash", "plus"}
  )
  DIFFICULTIES = frozenset({"horror", "combat", "evade"})
  DAMAGES = frozenset({"horror", "combat"})
  ATTRIBUTES = frozenset(
    {
      "magical resistance",
      "magical immunity",
      "physical resistance",
      "physical immunity",
      "undead",
      "ambush",
      "elusive",
      "endless",
      "mask",
      "spawn",
    }
  )
  ALL_ATTRIBUTES = ATTRIBUTES | {"nightmarish", "overwhelming"}

  def __init__(
    self, name, movement, dimension, ratings, damages, toughness, attributes=None, bypass=None
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
    self._movement = movement
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

  @property
  def visual_name(self):
    return self.handle

  def json_repr(self, state, char):
    return {
      "name": self.name,
      "handle": self.handle,
      "movement": self.movement(state),
      "dimension": self.dimension,
      "idx": self.idx,
      "place": getattr(self.place, "name", None),
      "horror_difficulty": self.difficulty("horror", state, char),
      "horror_damage": self.damage("horror", state, char),
      "horror_bypass": self.bypass_damage("horror", state),
      "combat_difficulty": self.difficulty("combat", state, char),
      "combat_damage": self.damage("combat", state, char),
      "combat_bypass": self.bypass_damage("combat", state),
      "toughness": self.toughness(state, char),
      "attributes": sorted(self.attributes(state, char)),
    }

  def difficulty(self, check_type, state, char):
    state_modifier = state.get_modifier(self, check_type + "difficulty") or 0
    char_modifier = char.get_modifier(self, check_type + "difficulty") or 0 if char else 0
    if state_modifier or char_modifier:
      return (self.difficulties.get(check_type) or 0) + state_modifier + char_modifier
    return self.difficulties.get(check_type)

  def damage(self, check_type, state, char):
    state_modifier = state.get_modifier(self, check_type + "damage") or 0
    char_modifier = char.get_modifier(self, check_type + "damage") or 0 if char else 0
    if state_modifier or char_modifier:
      return max((self.damages.get(check_type) or 0) + state_modifier + char_modifier, 0)
    return self.damages.get(check_type)

  def bypass_damage(self, check_type, state):  # pylint: disable=unused-argument
    return self.bypass.get(check_type)

  def toughness(self, state, char):
    state_modifier = state.get_modifier(self, "toughness")
    char_modifier = char.get_modifier(self, "toughness") if char else 0
    return max(self._toughness + (state_modifier or 0) + (char_modifier or 0), 1)

  def attributes(self, state, char):
    attrs = set()
    for attr in self.ALL_ATTRIBUTES:
      if self.has_attribute(attr, state, char):
        attrs.add(attr)
    return attrs

  def has_attribute(self, attribute, state, char):
    state_override = state.get_override(self, attribute)
    char_override = char.get_override(self, attribute) if char else None
    # Prefer specific overrides (at the item level) over general ones (environment, ancient one).
    if char_override is not None:
      return char_override
    if state_override is not None:
      return state_override
    return attribute in self._attributes or attribute == self._movement

  def movement(self, state):
    for movement in self.MOVEMENTS:
      if self.has_attribute(movement, state, None):
        return movement
    return "normal"

  def get_interrupt(self, event, state):
    endless = self.has_attribute("endless", state, event.character)
    if isinstance(event, events.TakeTrophy) and endless:
      # TODO: Should this be coded into TakeTrophy instead?
      cup = events.ReturnToCup(handles=[self.handle], character=event.character)
      return events.Sequence([events.CancelEvent(event), cup], event.character)
    return None

  def get_trigger(self, event, state):  # pylint: disable=unused-argument
    return None


def GiantInsect():
  return Monster(
    "Giant Insect",
    "flying",
    "circle",
    {"evade": -2, "horror": -1, "combat": 0},
    {"horror": 1, "combat": 2},
    1,
  )


class LandSquid(Monster):
  def __init__(self):
    super().__init__(
      "Land Squid",
      "unique",
      "triangle",
      {"evade": 1, "horror": -2, "combat": -3},
      {"horror": 2, "combat": 3},
      3,
    )

  def move_event(self, state):
    seq = events.Sequence(
      [
        events.Loss(char, {"stamina": 1})
        for char in state.characters
        if isinstance(char.place, places.CityPlace)
      ]
    )
    first_player = state.characters[state.first_player]
    roll = events.DiceRoll(first_player, 1, name=self.handle, bad=[4, 5, 6])
    cond = events.Conditional(first_player, roll, "sum", {0: events.Nothing(), 4: seq})
    return events.Sequence([roll, cond])


class Cultist(Monster):
  def __init__(self):
    super().__init__("Cultist", "normal", "moon", {"evade": -3, "combat": 1}, {"combat": 1}, 1)


def TentacleTree():
  return Monster(
    "Tentacle Tree",
    "stationary",
    "hex",
    {"evade": -2, "horror": 0, "combat": -1},
    {"horror": 3, "combat": 3},
    3,
    {"physical resistance"},
    {"horror": 1},
  )


class DimensionalShambler(Monster):
  def __init__(self):
    super().__init__(
      "Dimensional Shambler",
      "fast",
      "square",
      {"evade": -3, "horror": -2, "combat": -2},
      {"horror": 1, "combat": 0},
      1,
    )

  def get_trigger(self, event, state):
    if not isinstance(event, (events.CombatRound, events.EvadeRound)):
      return None
    if getattr(event, "defeated", False) or getattr(event, "evaded", False):
      return None
    events_to_cancel = []
    if len(state.event_stack) >= 4:
      if isinstance(state.event_stack[-4], (events.Combat, events.EvadeOrCombat)):
        events_to_cancel.append(state.event_stack[-4])
        if len(state.event_stack) >= 7 and isinstance(state.event_stack[-7], events.EvadeOrCombat):
          events_to_cancel.append(state.event_stack[-7])
    seq = [events.CancelEvent(to_cancel) for to_cancel in events_to_cancel]
    seq.append(events.LostInTimeAndSpace(event.character))
    return events.Sequence(seq, event.character)


def GiantWorm():
  return Monster(
    "Giant Worm",
    "normal",
    "circle",
    {"evade": -1, "horror": -1, "combat": -3},
    {"horror": 4, "combat": 4},
    3,
    {"physical resistance", "magical resistance"},
    {"combat": 1, "horror": 1},
  )


class ElderThing(Monster):
  def __init__(self):
    super().__init__(
      "Elder Thing",
      "normal",
      "diamond",
      {"evade": -2, "horror": -3, "combat": 0},
      {"horror": 2, "combat": 1},
      2,
    )

  def get_trigger(self, event, state):
    if not isinstance(event, (events.CombatRound, events.EvadeRound)):
      return None
    if getattr(event, "defeated", False) or getattr(event, "evaded", False):
      return None
    loss = events.WeaponOrSpellLossChoice(
      event.character, "Choose a weapon or spell to lose", 1, self
    )
    return events.Sequence([loss, events.DiscardSpecific(event.character, loss)], event.character)


def FlameMatrix():
  return Monster(
    "Flame Matrix",
    "flying",
    "star",
    {"evade": 0, "combat": -2},
    {"combat": 2},
    1,
    {"physical immunity", "ambush"},
  )


def SubterraneanFlier():
  return Monster(
    "Subterranean Flier",
    "flying",
    "hex",
    {"evade": 0, "horror": -2, "combat": -3},
    {"horror": 4, "combat": 3},
    3,
    {"physical resistance"},
    {"combat": 1, "horror": 1},
  )


def FormlessSpawn():
  return Monster(
    "Formless Spawn",
    "normal",
    "hex",
    {"evade": 0, "horror": -1, "combat": -2},
    {"horror": 2, "combat": 2},
    2,
    {"physical immunity"},
  )


def Ghost():
  return Monster(
    "Ghost",
    "stationary",
    "moon",
    {"evade": -3, "horror": -2, "combat": -3},
    {"horror": 2, "combat": 2},
    1,
    {"physical immunity", "undead"},
  )


def Ghoul():
  return Monster(
    "Ghoul",
    "normal",
    "hex",
    {"evade": -3, "horror": 0, "combat": -1},
    {"horror": 1, "combat": 1},
    1,
    {"ambush"},
  )


def FurryBeast():
  return Monster(
    "Furry Beast",
    "normal",
    "slash",
    {"evade": -2, "horror": -1, "combat": -2},
    {"horror": 2, "combat": 4},
    3,
    None,
    {"combat": 1},
  )


def Haunter():
  return Monster(
    "Haunter",
    "flying",
    "square",
    {"evade": -3, "horror": -2, "combat": -2},
    {"horror": 2, "combat": 2},
    2,
    {"mask", "endless"},
  )


def HighPriest():
  return Monster(
    "High Priest",
    "normal",
    "plus",
    {"evade": -2, "horror": 1, "combat": -2},
    {"horror": 1, "combat": 2},
    2,
    {"magical immunity"},
  )


class Hound(Monster):
  def __init__(self):
    super().__init__(
      "Hound",
      "unique",
      "square",
      {"evade": -1, "horror": -2, "combat": -1},
      {"horror": 4, "combat": 3},
      2,
      {"physical immunity"},
    )

  def move_event(self, state):
    return events.HoundLowestSneakChoice(state.characters[state.first_player], self)


class Maniac(Monster):
  def __init__(self):
    super().__init__("Maniac", "normal", "moon", {"evade": -1, "combat": 1}, {"combat": 1}, 1)


class Pinata(Monster):
  def __init__(self):
    super().__init__(
      "Pinata",
      "flying",
      "circle",
      {"evade": -2, "horror": -1, "combat": 0},
      {"horror": 2, "combat": 1},
      1,
    )

  def get_interrupt(self, event, state):
    if not isinstance(event, events.TakeTrophy):
      return super().get_interrupt(event, state)
    seq = [
      events.CancelEvent(event),
      events.ReturnToCup(handles=[self.handle], character=event.character, to_box=True),
    ]
    seq += events.Draw(event.character, "unique", 1).events
    return events.Sequence(seq, event.character)


class DreamFlier(Monster):
  def __init__(self):
    super().__init__(
      "Dream Flier",
      "flying",
      "slash",
      {"evade": -2, "horror": -1, "combat": -2},
      {"horror": 1, "combat": 0},
      2,
    )

  def get_trigger(self, event, state):
    if not isinstance(event, (events.CombatRound, events.EvadeRound)):
      return None
    if getattr(event, "defeated", False) or getattr(event, "evaded", False):
      return None

    events_to_cancel = []
    if len(state.event_stack) >= 4:
      if isinstance(state.event_stack[-4], (events.Combat, events.EvadeOrCombat)):
        events_to_cancel.append(state.event_stack[-4])
        if len(state.event_stack) >= 7 and isinstance(state.event_stack[-7], events.EvadeOrCombat):
          events_to_cancel.append(state.event_stack[-7])
    seq = [events.CancelEvent(to_cancel) for to_cancel in events_to_cancel]

    world_name = values.OtherWorldName(event.character)
    return_city = events.Return(event.character, world_name, get_lost=False)
    prompt = "Choose the gate you are pulled through"
    nearest_gate = events.NearestGateChoice(event.character, prompt, "Choose", monster=self)
    travel = events.Travel(event.character, nearest_gate)
    pulled_through = events.Sequence([nearest_gate, travel], event.character)
    results = {0: return_city, 1: pulled_through}
    seq.append(events.Conditional(event.character, values.InCity(event.character), None, results))
    return events.Sequence(seq, event.character)


def GiantAmoeba():
  return Monster(
    "Giant Amoeba",
    "fast",
    "diamond",
    {"evade": -1, "horror": -1, "combat": -1},
    {"horror": 3, "combat": 3},
    3,
    {"physical resistance"},
    {"horror": 1},
  )


def Octopoid():
  return Monster(
    "Octopoid",
    "normal",
    "plus",
    {"evade": -1, "horror": -3, "combat": -3},
    {"horror": 2, "combat": 3},
    3,
  )


def Vampire():
  return Monster(
    "Vampire",
    "normal",
    "moon",
    {"evade": -3, "horror": 0, "combat": -3},
    {"horror": 2, "combat": 3},
    2,
    {"undead", "physical resistance"},
  )


class Warlock(Monster):
  def __init__(self):
    super().__init__(
      "Warlock",
      "stationary",
      "circle",
      {"evade": -2, "horror": -1, "combat": -3},
      {"horror": 1, "combat": 1},
      2,
      {"magical immunity"},
    )

  def get_interrupt(self, event, state):
    if not isinstance(event, events.TakeTrophy):
      return super().get_interrupt(event, state)
    if len(state.event_stack) < 2 or not isinstance(state.event_stack[-2], events.PassCombatRound):
      return super().get_interrupt(event, state)
    seq = [
      events.CancelEvent(event),
      events.ReturnToCup(handles=[self.handle], character=event.character, to_box=True),
      events.Gain(event.character, {"clues": 2}),
    ]
    return events.Sequence(seq, event.character)


def Witch():
  return Monster(
    "Witch",
    "normal",
    "circle",
    {"evade": -1, "combat": -3},
    {"combat": 2},
    1,
    {"magical resistance"},
  )


def Zombie():
  return Monster(
    "Zombie",
    "normal",
    "moon",
    {"evade": 1, "horror": -1, "combat": -1},
    {"horror": 1, "combat": 2},
    1,
    {"undead"},
  )


class EventMonster(Monster):
  """A pseudo-monster used for events like Bank3, Hospital2, and Graveyard3."""

  def __init__(self, name, rating, pass_event, fail_event, toughness=1, attributes=None):
    super().__init__(
      name, "normal", "moon", {"evade": 0, **rating}, {"combat": 0}, toughness, attributes or set()
    )
    self.pass_event = pass_event
    self.fail_event = fail_event

  @property
  def visual_name(self):
    return None

  def get_interrupt(self, event, state):
    if isinstance(event, events.TakeTrophy):
      return events.CancelEvent(event)
    return super().get_interrupt(event, state)

  def get_trigger(self, event, state):
    if isinstance(event, events.PassCombatRound):
      return self.pass_event

    if (
      (not isinstance(event, events.CombatRound))
      or event.check is None
      or not event.check.is_done()
    ):
      return None

    if not event.check.success:
      return self.fail_event
    return None


MONSTERS = {
  x().name: x
  for x in [
    GiantInsect,
    LandSquid,
    Cultist,
    TentacleTree,
    DimensionalShambler,
    GiantWorm,
    ElderThing,
    FlameMatrix,
    SubterraneanFlier,
    FormlessSpawn,
    Ghost,
    Ghoul,
    FurryBeast,
    Haunter,
    HighPriest,
    Hound,
    Maniac,
    Pinata,
    DreamFlier,
    GiantAmoeba,
    Octopoid,
    Vampire,
    Warlock,
    Witch,
    Zombie,
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
