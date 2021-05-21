import eldritch.events as events
import eldritch.places as places


class GlobalEffect(object):

  def get_modifier(self, thing, attribute):
    return 0

  def get_interrupt(self, event, owner, state):
    return None

  def get_usable_interrupt(self, event, owner, state):
    return None

  def get_trigger(self, event, owner, state):
    return None

  def get_usable_trigger(self, event, owner, state):
    return None


class MythosCard(GlobalEffect):

  def __init__(self, name, gate_location, clue_location, white_dimensions, black_dimensions):
    self.name = name
    self.gate_location = gate_location
    self.clue_location = clue_location
    self.white_dimensions = white_dimensions
    self.black_dimensions = black_dimensions

  def create_event(self, state):
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
    super(Environment, self).__init__(
        name, gate_location, clue_location, white_dimensions, black_dimensions)
    assert env_type in {"weather", "urban", "mystic"}
    self.environment_type = env_type

  def create_event(self, state):
    seq = super(Environment, self).create_event(state)
    seq.events.append(events.ActivateEnvironment(self))
    return seq


class Mythos1(Headline):

  def __init__(self):
    super(Mythos1, self).__init__(
        "Mythos1", "Woods", "Society", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super(Mythos1, self).create_event(state)
    for char in state.characters:
      check = events.Check(char, "luck", -1)
      bless = events.Bless(char)
      seq.events.append(events.PassFail(char, check, bless, events.Nothing()))
    return seq


class Mythos2(Environment):

  def __init__(self):
    super(Mythos2, self).__init__(
        "Mythos2", "Isle", "Science", {"square", "diamond"}, {"circle"}, "urban")

  def get_modifier(self, thing, attribute):
    if thing.name == "Pinata" and attribute == "toughness":
      return 2
    return 0

  def get_interrupt(self, event, owner, state):
    if not isinstance(event, events.Draw) or event.deck != "unique":
      return None
    if len(state.event_stack) < 2:
      return None
    prev_event = state.event_stack[-2]
    if not isinstance(prev_event, events.Check) or prev_event.check_type != "combat":
      return None
    return None  # TODO: draw and keep an extra card


class Mythos3(Environment):

  def __init__(self):
    super(Mythos3, self).__init__(
        "Mythos3", "Square", "Unnamable", {"square", "diamond"}, {"circle"}, "mystic")

  def get_interrupt(self, event, owner, state):
    return None  # TODO: prevent stamina gain


class Mythos4(Headline):

  def __init__(self):
    super(Mythos4, self).__init__(
        "Mythos4", "Science", "Witch", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super(Mythos4, self).create_event(state)
    seq.events.append(events.ReturnToCup(names={"Furry Beast", "Dream Flier"}))
    # TODO: raise the terror level
    return seq


class Mythos5(Headline):

  def __init__(self):
    super(Mythos5, self).__init__("Mythos5", "Square", "Unnamable", {"moon"}, {"plus"})

  def create_event(self, state):
    seq = super(Mythos5, self).create_event(state)
    seq.events.append(events.ReturnToCup(places={"Sky", "Outskirts"}))
    return seq


class Mythos6(Environment):

  def __init__(self):
    super(Mythos6, self).__init__("Mythos6", "Graveyard", "Isle", {"plus"}, {"moon"}, "weather")

  def get_modifier(self, thing, attribute):
    if isinstance(thing.place, places.CityPlace):
      if attribute == "will":
        return -1
      if attribute == "sneak":
        return 1
    return 0

  def get_interrupt(self, event, owner, state):
    if isinstance(event, events.MoveMonster) and event.monster.movement == "flying":
      return None  # TODO: prevent movement
    return None

class Mythos7(Headline):
  def __init__(self):
    super(Mythos7, self).__init__(
        "Mythos7", "Unnamable", "Woods", {"hexagon"}, {"slash", "triangle", "star"}
    )
  #TODO: All players sprung from jail, cannot be arrested

class Mythos8(Environment):
  def __init__(self):
    super(Mythos8, self).__init__(
        "Mythos8", "Square", "Unnamable", {"square", "diamond"}, {"circle"}, "mystic"
    )
  #TODO: Rivertown blood magic, maybe devoured


class Mythos9(Environment):
  def __init__(self):
    super(Mythos9, self).__init__(
        "Mythos9", "Cave", "Roadhouse", {"square", "diamond"}, {"circle"}, "mystic"
    )

  def get_modifier(self, thing, attribute):
    if isinstance(thing.place, places.CityPlace):
      if attribute == "luck":
        return -1
      if attribute == "sneak":
        return 1
    return 0


class Mythos10(Headline):
  def __init__(self):
    super(Mythos10, self).__init__(
        "Mythos10", "Isle", "Science", {"hexagon"}, {"slash", "triangle", "star"}
    )
  #TODO: Close stores


class Mythos11(Headline):

  def __init__(self):
    super(Mythos11, self).__init__(
        "Mythos11", "Cave", "Roadhouse", {"hex"}, {"slash", "triangle", "star"}
    )

  def create_event(self, state):
    seq = super(Mythos11, self).create_event(state)
    seq.events.append(events.ReturnToCup(places={"Southside", "House", "Church", "Society"}))
    return seq


class Mythos12(Headline):
  def __init__(self):
    super(Mythos12, self).__init__(
        "Mythos12", "Square", "Unnamable", {"circle"}, {"square", "diamond"}
    )

  def create_event(self, state):
    seq = super(Mythos12, self).create_event(state)
    seq.events.append(
        events.ReturnToCup(places={"University", "Administration", "Library", "Science"})
    )
    return seq


class Mythos14(Environment):
  def __init__(self):
    super(Mythos14, self).__init__(
        "Mythos14", "Unnamable", "Woods", {"square", "diamond"}, {"circle"}, "urban"
    )

  def get_trigger(self, event, owner, state):
    char = getattr(event, 'character', None)
    if isinstance(event, events.EndMovement) and char.place.name == "Northside":
      gain = events.Gain(char, {'clues': 1})
      check = events.Check(char, 'will', -1)
      wonders = events.PassFail(char, check, events.Nothing(), events.Loss(char, {'sanity': 1}))
      return events.Sequence([gain, wonders], char)


class Mythos15(Environment):
  def __init__(self):
    super(Mythos15, self).__init__("Mythos15", "Isle", "Science", {"plus"}, {"moon"})

  def get_trigger(self, event, owner, state):
    char = getattr(event, 'character', None)
    if isinstance(event, events.EndMovement) and isinstance(char.place, places.Street):
      check = events.Check(char, 'will', 0)
      arrested = events.Arrested(char)
      return events.PassFail(char, check, events.Nothing, arrested)


class Mythos16(Environment):
  def __init__(self):
    super(Mythos16, self).__init__("Mythos16", "Witch", "Cave", {"square", "diamond"}, {"circle"}, "urban")

  def get_trigger(self, event, owner, state):
    char = getattr(event, 'character', None)
    if isinstance(event, events.EndMovement) and char.place.name == 'Uptown':
      return events.Purchase(char, 'unique', 2)


class Mythos17(Environment):
  def __init__(self):
    super(Mythos17, self).__init__("Mythos17", "Witch", "Cave", {"plus"}, {"moon"}, "urban")

  def get_trigger(self, event, owner, state):
    char = getattr(event, 'character', None)
    if isinstance(event, events.EndMovement) and char.place.name == "University":
      check = events.Check(char, "lore", -1)
      gain = events.Gain(char, {"clues": 1})
      return events.PassFail(char, check, gain, events.Nothing())

class Mythos18(Environment):
  def __init__(self):
    super(Mythos18, self).__init__("Mythos18", "Square", "Unnamable", {"plus"}, {"moon"}, "mystic")
  #TODO: Investigators cannot gain sanity except by receiving care at asylum or from the Psychologist


class Mythos19(Headline):
  def __init__(self):
    super(Mythos19, self).__init__("Mythos19", "Witch", "Cave", {"moon"}, {"plus"})
  #TODO: close merchant district streets (in or out)


class Mythos20(Headline):
  def __init__(self):
    super(Mythos20, self).__init__("Mythos20", "Cave", "Roadhouse", {"moon"}, {"plus"})

  def create_event(self, state):
    return events.ReturnToCup('streets')


class Mythos45(Environment):

  def __init__(self):
    super(Mythos45, self).__init__(
        "Mythos45", "Woods", "Society", {"slash", "triangle", "star"}, {"hex"}, "mystic")

  def get_modifier(self, thing, attribute):
    if thing.name in ("Maniac", "Octopoid") and attribute == "toughness":
      return 1
    if thing.name == "Sunken City" and attribute == "difficulty":
      return -1
    return 0


def CreateMythos():
  return [Mythos1(), Mythos2(), Mythos3(), Mythos4(), Mythos5(), Mythos6(), Mythos11(), Mythos45()]
