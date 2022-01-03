from eldritch import events


class GlobalEffect:

  # pylint: disable=unused-argument

  def get_modifier(self, thing, attribute):
    return 0

  def get_override(self, thing, attribute):
    return None

  def get_interrupt(self, event, state):
    return None

  def get_usable_interrupt(self, event, state):
    return None

  def get_trigger(self, event, state):
    return None

  def get_usable_trigger(self, event, state):
    return None


class MythosCard(GlobalEffect):

  def __init__(self, name, gate_location, clue_location, white_dimensions, black_dimensions):
    self.name = name
    self.gate_location = gate_location
    self.clue_location = clue_location
    self.white_dimensions = white_dimensions
    self.black_dimensions = black_dimensions

  def create_event(self, state):  # pylint: disable=unused-argument
    return events.Sequence([
        events.OpenGate(self.gate_location),
        events.SpawnClue(self.clue_location),
        events.MoveMonsters(self.white_dimensions, self.black_dimensions),
    ])

  def json_repr(self):
    return self.name


class Headline(MythosCard):
  pass


class Environment(MythosCard):

  def __init__(
          self, name, gate_location, clue_location, white_dimensions, black_dimensions, env_type):
    super().__init__(name, gate_location, clue_location, white_dimensions, black_dimensions)
    assert env_type in {"weather", "urban", "mystic"}
    self.environment_type = env_type

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ActivateEnvironment(self))
    return seq


class Mythos1(Headline):

  def __init__(self):
    super().__init__("Mythos1", "Woods", "Society", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super().create_event(state)
    for char in state.characters:
      check = events.Check(char, "luck", -1)
      bless = events.Bless(char)
      seq.events.append(events.PassFail(char, check, bless, events.Nothing()))
    return seq


class Mythos2(Environment):

  def __init__(self):
    super().__init__("Mythos2", "Isle", "Science", {"square", "diamond"}, {"circle"}, "urban")

  def get_modifier(self, thing, attribute):
    if thing.name == "Pinata" and attribute == "toughness":
      return 2
    return 0

  def get_interrupt(self, event, state):
    if not isinstance(event, events.DrawItems) or event.deck != "unique":
      return None
    if len(state.event_stack) < 2:
      return None
    prev_event = state.event_stack[-2]
    if not isinstance(prev_event, events.Check) or prev_event.check_type != "combat":
      return None
    return None  # TODO: draw and keep an extra card


class Mythos3(Environment):

  def __init__(self):
    super().__init__("Mythos3", "Square", "Unnamable", {"square", "diamond"}, {"circle"}, "mystic")

  def get_interrupt(self, event, state):
    return None  # TODO: prevent stamina gain


class Mythos4(Headline):

  def __init__(self):
    super().__init__("Mythos4", "Science", "WitchHouse", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ReturnToCup(names={"Furry Beast", "Dream Flier"}))
    # TODO: raise the terror level
    return seq


class Mythos5(Headline):

  def __init__(self):
    super().__init__("Mythos5", "Square", "Unnamable", {"moon"}, {"plus"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ReturnToCup(from_places={"Sky", "Outskirts"}))
    return seq


class Mythos6(Environment):

  def __init__(self):
    super().__init__("Mythos6", "Graveyard", "Isle", {"plus"}, {"moon"}, "weather")

  def get_modifier(self, thing, attribute):
    if attribute == "will":
      return -1
    if attribute == "sneak":
      return 1
    return 0

  def get_interrupt(self, event, state):
    if isinstance(event, events.MoveMonster) and event.monster.get_movement(state) == "flying":
      return None  # TODO: prevent movement
    return None


class Mythos11(Headline):

  def __init__(self):
    super().__init__("Mythos11", "Cave", "Roadhouse", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ReturnToCup(from_places={"Southside", "House", "Church", "Society"}))
    return seq


class Mythos45(Environment):

  def __init__(self):
    super().__init__(
        "Mythos45", "Woods", "Society", {"slash", "triangle", "star"}, {"hex"}, "mystic")

  def get_modifier(self, thing, attribute):
    if thing.name in ("Maniac", "Octopoid") and attribute == "toughness":
      return 1
    if thing.name == "Sunken City" and attribute == "difficulty":
      return -1
    return 0


class ShuffleMythos(MythosCard):

  def __init__(self):  # pylint: disable=super-init-not-called
    self.name = "ShuffleMythos"


def CreateMythos():
  return [
      Mythos1(), Mythos2(), Mythos3(), Mythos4(), Mythos5(), Mythos6(), Mythos11(), Mythos45(),
      ShuffleMythos(),
  ]
