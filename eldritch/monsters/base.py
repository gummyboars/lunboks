from eldritch import events
from eldritch.monsters.core import Monster
from eldritch import places
from eldritch import values


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


def TongueGod():
  return Monster(
    "Tongue God",
    "normal",
    "triangle",
    {"evade": 1, "horror": -3, "combat": -4},
    {"horror": 3, "combat": 4},
    4,
    {"mask", "endless"},
    {"combat": 1, "horror": 1},
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

  def difficulty(self, check_type, state, char):
    modifier = 0
    if check_type == "combat" and state.terror >= 6:
      modifier = -3
    orig = super().difficulty(check_type, state, char)
    return orig + modifier if orig is not None else orig

  def damage(self, check_type, state, char):
    modifier = 0
    if check_type == "combat" and state.terror >= 6:
      modifier = 2
    orig = super().damage(check_type, state, char)
    return orig + modifier if orig is not None else orig

  def has_attribute(self, attribute, state, char):
    if attribute == "endless" and state.terror >= 6:
      state_override = state.get_override(self, attribute)
      char_override = char.get_override(self, attribute) if char else None
      if state_override is None and char_override is None:
        return True
    return super().has_attribute(attribute, state, char)


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


class ManInBlack(Monster):
  def __init__(self):
    super().__init__(
      "Man in Black",
      "normal",
      "moon",
      {"evade": -3, "horror": None, "combat": None},
      {"horror": None, "combat": None},
      1,
      {"mask", "endless"},
    )

  def get_interrupt(self, event, state):
    if not isinstance(event, events.Combat):
      return super().get_interrupt(event, state)
    success = events.Sequence(
      [
        events.CancelEvent(event),
        events.ReturnToCup(character=event.character, handles=[self.handle]),
        events.Gain(event.character, {"clues": 2}),
      ],
      event.character,
    )
    failure = events.Sequence(
      [
        events.CancelEvent(event),
        events.ReturnToCup(character=event.character, handles=[self.handle]),
        events.Devoured(event.character),
      ],
      event.character,
    )
    check = events.Check(event.character, "luck", -1, name=self.visual_name)
    return events.PassFail(event.character, check, success, failure)


class BloatedWoman(Monster):
  def __init__(self):
    super().__init__(
      "Bloated Woman",
      "normal",
      "hex",
      {"evade": -1, "horror": -1, "combat": -2},
      {"horror": 2, "combat": 2},
      2,
      {"mask", "endless"},
    )

  def get_interrupt(self, event, state):
    if not isinstance(event, events.MonsterCheck) or event.check_type != "horror":
      return super().get_interrupt(event, state)
    if len(state.event_stack) < 2 or not isinstance(state.event_stack[-2], events.Combat):
      return super().get_interrupt(event, state)
    failure = events.Sequence(
      [
        events.CancelEvent(event),  # Cancelling the check makes them auto-fail
        events.FailCombatRound(event.character, state.event_stack[-2]),
      ],
      event.character,
    )
    check = events.Check(event.character, "will", -2, name=self.visual_name)
    return events.PassFail(event.character, check, events.Nothing(), failure)


class DarkPharaoh(Monster):
  def __init__(self):
    super().__init__(
      "Dark Pharaoh",
      "normal",
      "slash",
      {"evade": -1, "horror": -1, "combat": -3},
      {"horror": 1, "combat": 3},
      2,
      {"mask", "endless"},
    )

  def get_interrupt(self, event, state):
    if not isinstance(event, events.MonsterCheck) or event.check_type != "combat":
      return super().get_interrupt(event, state)
    if len(state.event_stack) < 2 or not isinstance(state.event_stack[-2], events.CombatRound):
      return super().get_interrupt(event, state)
    if event != state.event_stack[-2].check:
      return super().get_interrupt(event, state)
    return events.ChangeCheckBaseType(event, "lore")


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
    TongueGod,
    FurryBeast,
    Haunter,
    HighPriest,
    Hound,
    Maniac,
    Pinata,
    DreamFlier,
    GiantAmoeba,
    Octopoid,
    ManInBlack,
    BloatedWoman,
    DarkPharaoh,
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
    "Tongue God": 1,
    "Furry Beast": 2,
    "Haunter": 1,
    "High Priest": 1,
    "Hound": 2,
    "Maniac": 3,
    "Pinata": 3,
    "Dream Flier": 2,
    "Giant Amoeba": 2,
    "Octopoid": 2,
    "Man in Black": 1,
    "Bloated Woman": 1,
    "Dark Pharaoh": 1,
    "Vampire": 1,
    "Warlock": 2,
    "Witch": 2,
    "Zombie": 3,
  }
  monsters = []
  for name, count in counts.items():
    monsters.extend([MONSTERS[name]() for _ in range(count)])
  return monsters
