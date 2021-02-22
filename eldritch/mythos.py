import eldritch.events as events


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

  def __init__(
      self, name, mythos_type, gate_location, clue_location, white_dimensions, black_dimensions,
      environment_type=None,
    ):
    assert mythos_type in {"headline", "environment", "rumor"}
    if mythos_type == "environment":
      assert environment_type in {"urban", "mystic", "weather"}
    else:
      assert environment_type is None
    self.name = name
    self.mythos_type = mythos_type
    self.gate_location = gate_location
    self.clue_location = clue_location
    self.white_dimensions = white_dimensions
    self.black_dimensions = black_dimensions
    self.environment_type = environment_type

  def create_event(self, state):
    return events.Sequence([
      events.OpenGate(self.gate_location),
      events.SpawnClue(self.clue_location),
      events.MoveMonsters(self.white_dimensions, self.black_dimensions),
    ])


class Mythos1(MythosCard):

  def __init__(self):
    super(Mythos1, self).__init__(
        "Mythos1", "headline", "Woods", "Society", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super(Mythos1, self).create_event(state)
    for char in state.characters:
      check = events.Check(char, "luck", -1)
      bless = events.Bless(char)
      seq.events.append(events.PassFail(char, check, bless, events.Nothing()))
    return seq


class Mythos2(MythosCard):

  def __init__(self):
    super(Mythos2, self).__init__(
        "Mythos2", "environment", "Isle", "Science", {"square", "diamond"}, {"circle"},
        environment_type="urban",
    )

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


class Mythos3(MythosCard):

  def __init__(self):
    super(Mythos3, self).__init__(
        "Mythos3", "environment", "Square", "Unnamable", {"square", "diamond"}, {"circle"},
        environment_type="mystic",
    )

  def get_interrupt(self, event, owner, state):
    return None  # TODO: prevent stamina gain


class Mythos4(MythosCard):

  def __init__(self):
    super(Mythos4, self).__init__(
        "Mythos4", "headline", "Science", "Witch", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super(Mythos4, self).create_event(state)
    seq.events.append(events.ReturnToCup(names={"Furry Beast", "Dream Flier"}))
    # TODO: raise the terror level
    return seq


class Mythos5(MythosCard):

  def __init__(self):
    super(Mythos5, self).__init__("Mythos5", "headline", "Square", "Unnamable", {"moon"}, {"plus"})

  def create_event(self, state):
    seq = super(Mythos5, self).create_event(state)
    seq.events.append(events.ReturnToCup(places={"Sky", "Outskirts"}))
    return seq


class Mythos11(MythosCard):

  def __init__(self):
    super(Mythos11, self).__init__(
        "Mythos11", "headline", "Cave", "Roadhouse", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super(Mythos11, self).create_event(state)
    seq.events.append(events.ReturnToCup(places={"Southside", "House", "Church", "Society"}))
    return seq


def CreateMythos():
  return [Mythos1(), Mythos2(), Mythos3(), Mythos4(), Mythos5(), Mythos11()]
