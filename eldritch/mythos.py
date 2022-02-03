import operator

from eldritch import events
from eldritch import gates
from eldritch import monsters
from eldritch import places
from eldritch import values


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
    seq = []
    if self.gate_location is not None:
      seq.append(events.OpenGate(self.gate_location))
    if self.clue_location is not None:
      seq.append(events.SpawnClue(self.clue_location))
    seq.append(events.MoveMonsters(self.white_dimensions, self.black_dimensions))
    return events.Sequence(seq)

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


class Rumor(MythosCard):

  def __init__(self, name, gate_location, white_dimensions, black_dimensions, activity_location):
    super().__init__(name, gate_location, None, white_dimensions, black_dimensions)
    self.activity_location = activity_location
    self.start_turn = float("inf")
    self.progress = 0  # Not used for all rumors, but useful to have.
    self.failed = False

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.StartRumor(self))
    return seq

  def progress_event(self, state):  # pylint: disable=unused-argument
    return events.ProgressRumor(self)

  def get_trigger(self, event, state):
    if self.failed:
      return None
    if isinstance(event, events.Mythos) and state.turn_number >= self.start_turn:
      return self.progress_event(state)
    return None

  def json_repr(self):
    return {
        "name": self.name,
        "activity_location": self.activity_location if not self.failed else None,
        "progress": self.progress if not self.failed else None,
    }


class Mythos1(Headline):

  def __init__(self):
    super().__init__("Mythos1", "Woods", "Society", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super().create_event(state)
    for char in state.characters:
      if char.gone:
        continue
      check = events.Check(char, "luck", -1)
      bless = events.Bless(char)
      seq.events.append(events.PassFail(char, check, bless, events.Nothing()))
    return seq


class Mythos2(Environment):

  def __init__(self):
    super().__init__("Mythos2", "Isle", "Science", {"square", "diamond"}, {"circle"}, "urban")

  def get_modifier(self, thing, attribute):
    if isinstance(thing, monsters.Monster) and thing.name == "Pinata" and attribute == "toughness":
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
    if isinstance(getattr(thing, "place", None), places.CityPlace):
      if attribute == "will":
        return -1
      if attribute == "sneak":
        return 1
    return 0

  def get_interrupt(self, event, state):
    if isinstance(event, events.MoveMonster) and event.monster.has_attribute("flying", state, None):
      return None  # TODO: prevent movement
    return None


class Mythos11(Headline):

  def __init__(self):
    super().__init__("Mythos11", "Cave", "Roadhouse", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ReturnToCup(from_places={"Southside", "House", "Church", "Society"}))
    return seq


class Mythos27(Rumor):

  def __init__(self):
    super().__init__("Mythos27", "Isle", {"slash", "triangle", "star"}, {"hex"}, "Easttown")
    self.progress = 6

  def get_interrupt(self, event, state):
    if not isinstance(event, events.EncounterPhase):
      return None
    if event.character.place != state.places["Easttown"]:
      return None
    spend = values.RangeSpendPrerequisite("clues", 1, self.progress)
    choice = events.SpendChoice(
        event.character, "Spend clues to slow down or stop the rumor?", ["Spend", "Don't"],
        spends=[spend, None],
    )
    spend_count = values.SpendCount(choice, "clues")
    neg_amount = values.Calculation(spend_count, None, operator.neg)
    cond = events.Conditional(
        event.character, spend_count, "",
        {0: events.Nothing(), 1: events.ProgressRumor(self, neg_amount)},
    )
    return events.Sequence([choice, cond])

  def progress_event(self, state):
    first_player = state.characters[state.first_player]
    dice1 = events.DiceRoll(first_player, 1)
    dice2 = events.DiceRoll(first_player, 1)
    prog1 = events.ProgressRumor(self)
    prog2 = events.ProgressRumor(self)
    cond1 = events.Conditional(first_player, values.Die(dice1), "", {0: prog1, 3: events.Nothing()})
    cond2 = events.Conditional(first_player, values.Die(dice2), "", {0: prog2, 3: events.Nothing()})
    return events.Sequence([dice1, cond1, dice2, cond2])

  def get_trigger(self, event, state):
    if isinstance(event, events.ProgressRumor) and event.rumor == self and self.progress >= 10:
      return events.Sequence([events.EndRumor(self, failed=True), events.RemoveAllSeals()])
    if isinstance(event, events.ProgressRumor) and event.rumor == self and self.progress <= 0:
      draws = [events.Draw(char, "unique", 1) for char in state.characters if not char.gone]
      return events.Sequence([events.EndRumor(self, failed=False)] + draws)
    return super().get_trigger(event, state)


class Mythos45(Environment):

  def __init__(self):
    super().__init__(
        "Mythos45", "Woods", "Society", {"slash", "triangle", "star"}, {"hex"}, "mystic")

  def get_modifier(self, thing, attribute):
    if isinstance(thing, monsters.Monster):
      if thing.name in ("Maniac", "Octopoid") and attribute == "toughness":
        return 1
    if isinstance(thing, gates.Gate) and thing.name == "Sunken City" and attribute == "difficulty":
      return -1
    return 0


class Mythos59(Rumor):

  def __init__(self):
    super().__init__("Mythos59", "Graveyard", {"slash", "triangle", "star"}, {"hex"}, "FrenchHill")

  def get_modifier(self, thing, attribute):
    if self.failed:
      return 0
    if not isinstance(thing, monsters.Monster):
      return 0
    if isinstance(thing, monsters.Cultist) or thing.name in ["High Priest", "Warlock", "Witch"]:
      return {"toughness": 2}.get(attribute, 0)
    return 0

  def get_interrupt(self, event, state):
    if self.failed and isinstance(event, events.Mythos):
      return self.get_failure_interrupt(event, state)
    if not self.failed and isinstance(event, events.EncounterPhase):
      return self.get_pass_interrupt(event, state)
    return None

  def get_failure_interrupt(self, event, state):  # pylint: disable=unused-argument
    draw = events.DrawMythosCard(state.characters[state.first_player])
    return events.Sequence([draw, events.OpenGate(draw)])

  def get_pass_interrupt(self, event, state):
    if event.character.place != state.places["FrenchHill"]:
      return None
    num_spells = 3 if len(state.characters) <= 4 else 4
    discard_choice = events.ItemCountChoice(
        event.character, "Choose spells to discard", num_spells, decks={"spells"},
    )
    success = [
        discard_choice,
        events.DiscardSpecific(event.character, discard_choice),
        events.EndRumor(self, failed=False),
    ]
    success.extend([events.Gain(char, {"clues": 2}) for char in state.characters if not char.gone])
    prereq = values.ItemDeckPrerequisite(event.character, "spells", num_spells, "at least")
    return events.BinaryChoice(
        event.character, f"Discard {num_spells} spells to end the rumor?", "Yes", "No",
        events.Sequence(success), events.Nothing(), prereq,
    )

  def get_trigger(self, event, state):
    if isinstance(event, events.ProgressRumor) and event.rumor == self and self.progress >= 5:
      return events.EndRumor(self, failed=True, add_global=True)
    return super().get_trigger(event, state)


class ShuffleMythos(MythosCard):

  def __init__(self):  # pylint: disable=super-init-not-called
    self.name = "ShuffleMythos"


def CreateMythos():
  return [
      Mythos1(), Mythos2(), Mythos3(), Mythos4(), Mythos5(), Mythos6(), Mythos11(), Mythos27(),
      Mythos45(), Mythos59(), ShuffleMythos(),
  ]
