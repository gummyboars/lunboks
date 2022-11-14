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

  def json_repr(self, state):
    return {}


class MythosCard(GlobalEffect):

  def __init__(
      self, name, gate_location, clue_location, white_dimensions, black_dimensions,
      activity_location=None,
  ):
    self.name = name
    self.gate_location = gate_location
    self.clue_location = clue_location
    self.white_dimensions = white_dimensions
    self.black_dimensions = black_dimensions
    self.activity_location = activity_location

  def create_event(self, state):  # pylint: disable=unused-argument
    seq = []
    if self.gate_location is not None:
      seq.append(events.OpenGate(self.gate_location))
    if self.clue_location is not None:
      seq.append(events.SpawnClue(self.clue_location))
    seq.append(events.MoveMonsters(self.white_dimensions, self.black_dimensions))
    return events.Sequence(seq)

  def json_repr(self, state):  # pylint: disable=unused-argument
    return {"name": self.name, "activity_location": self.activity_location}


class Headline(MythosCard):
  pass


class Environment(MythosCard):

  def __init__(
      self, name, gate_location, clue_location, white_dimensions, black_dimensions, env_type,
      activity_location=None,
  ):
    super().__init__(
        name, gate_location, clue_location, white_dimensions, black_dimensions, activity_location,
    )
    assert env_type in {"weather", "urban", "mystic"}
    self.environment_type = env_type

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ActivateEnvironment(self))
    return seq


class Rumor(MythosCard):

  def __init__(self, name, gate_location, white_dimensions, black_dimensions, activity_location):
    super().__init__(
        name, gate_location, None, white_dimensions, black_dimensions, activity_location,
    )
    self.start_turn = float("inf")
    self.progress = 0  # Not used for all rumors, but useful to have.
    self._max_progress = 0
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

  def get_progress(self, state):  # pylint: disable=unused-argument
    return self.progress

  def max_progress(self, state):  # pylint: disable=unused-argument
    return self._max_progress

  def should_fail(self, state):
    return self.get_progress(state) >= self.max_progress(state)

  def json_repr(self, state):
    return {
        "name": self.name,
        "activity_location": self.activity_location if not self.failed else None,
        "annotation": "Failed Rumor" if self.failed else None,
        "progress": self.get_progress(state) if not self.failed else None,
        "max_progress": self.max_progress(state) if not self.failed else None,
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
    if len(state.event_stack) < 3:
      return None
    trophy = state.event_stack[-3]
    if not isinstance(trophy, events.TakeTrophy) or getattr(trophy.monster, "name", "") != "Pinata":
      return None
    if isinstance(event, events.DrawItems):
      return events.ChangeCount(event, "draw_count", 1)
    if isinstance(event, events.KeepDrawn):
      return events.ChangeCount(event, "keep_count", 1)
    return None


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


class Mythos7(Headline):
  def __init__(self):
    super().__init__("Mythos7", "Unnamable", "Woods", {"hex"}, {"slash", "triangle", "star"})
    self.active_until = None

  def create_event(self, state):
    seq = super().create_event(state)
    for char in state.characters:
      if char.arrested_until is not None:
        seq.events.append(events.ClearStatus(char, "arrested"))
    seq.events.append(events.AddGlobalEffect(
        self, source_deck="mythos", active_until=state.turn_number + 1
    ))
    return seq

  def get_interrupt(self, event, state):
    if isinstance(event, events.Arrested):
      return events.CancelEvent(event)
    return None

  def get_trigger(self, event, state):
    if (self.active_until is not None
        and state.turn_number >= self.active_until
            and isinstance(event, events.Mythos)):
      return events.RemoveGlobalEffect(self, source_deck="mythos")
    return None


class Mythos8(Environment):
  def __init__(self):
    super().__init__(
        "Mythos8", "Square", "Unnamable", {"square", "diamond"}, {"circle"}, "mystic", "Rivertown"
    )

  def get_trigger(self, event, state):
    if isinstance(event, events.Movement) and event.character.place.name == self.activity_location:
      dice = events.DiceRoll(event.character, values.Calculation(event.character, "stamina"))
      loss = events.Loss(
          event.character,
          {"stamina": values.Calculation(
              left=event.character, left_attr="stamina",
              operand=operator.sub,
              right=dice, right_attr="successes",
          )}, source=self)
      final = events.PassFail(
          event.character,
          values.Calculation(event.character, "stamina"),
          events.Gain(event.character, {"clues": 3}),
          events.Nothing()
      )
      yes_sequence = events.Sequence([dice, loss, final], event.character)
      return events.BinaryChoice(
          event.character,
          "Delve into mysteries with your life force?",
          "Yes", "No", yes_sequence, events.Nothing()
      )
    return None

  def get_interrupt(self, event, state):
    if (
        isinstance(event, events.InsaneOrUnconscious)
        and len(state.event_stack) > 1
        and isinstance(state.event_stack[-2], events.GainOrLoss)
        and state.event_stack[-2].source == self
    ):
      return events.Devoured(event.character)
    return None


class Mythos9(Environment):
  def __init__(self):
    super().__init__(
        "Mythos9", "Cave", "Roadhouse", {"square", "diamond"}, {"circle"}, "mystic"
    )

  def get_modifier(self, thing, attribute):
    if attribute == "luck":
      return -1
    if attribute == "sneak":
      return 1
    return 0


class Mythos10(Headline):
  def __init__(self):
    super().__init__("Mythos10", "Isle", "Science", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.CloseLocation("Store", for_turns=1))
    seq.events.append(events.CloseLocation("Shop", for_turns=1))
    seq.events.append(events.CloseLocation("Shoppe", for_turns=1))
    return seq


class Mythos11(Headline):

  def __init__(self):
    super().__init__("Mythos11", "Cave", "Roadhouse", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ReturnToCup(from_places={"Southside", "House", "Church", "Society"}))
    return seq


class Mythos12(Headline):
  def __init__(self):
    super().__init__("Mythos12", "Square", "Unnamable", {"circle"}, {"square", "diamond"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ReturnToCup(
        from_places={"University", "Library", "Administration", "Science"}
    ))
    return seq


class Mythos13(Rumor):
  def __init__(self):
    super().__init__(
        "Mythos13", "Cave", {"slash", "triangle", "star"}, {"hex"}, "Rivertown"
    )

  def should_fail(self, state):
    return state.terror >= 10

  def get_interrupt(self, event, state):
    if not self.failed and isinstance(event, events.EncounterPhase):
      return self.get_pass_interrupt(event, state)
    return None

  def get_pass_interrupt(self, event, state):
    if event.character.place != state.places["Rivertown"]:
      return None
    seq = events.Sequence([
        events.EndRumor(self, failed=False),
    ] + [events.Draw(char, "spells", 1) for char in state.characters if not char.gone])
    return events.BinarySpend(
        event.character, "gates", 2, "Spend 2 gate trophies to end the rumor?",
        "Yes", "No", seq
    )

  def get_trigger(self, event, state):
    if isinstance(event, events.IncreaseTerror) and self.should_fail(state):
      curses = [events.Curse(char) for char in state.characters if not char.gone]
      return events.Sequence(curses + [events.EndRumor(self, failed=True)])
    return super().get_trigger(event, state)

  def progress_event(self, state):
    first_player = state.characters[state.first_player]
    dice1 = events.DiceRoll(first_player, 1)
    prog1 = events.IncreaseTerror()
    cond1 = events.Conditional(first_player, values.Die(dice1), "", {0: prog1, 3: events.Nothing()})
    return events.Sequence([dice1, cond1])

  def get_progress(self, state):
    return state.terror

  def max_progress(self, state):
    return 10


class Mythos14(Environment):
  def __init__(self):
    super().__init__(
        "Mythos14", "Unnamable", "Woods", {"square", "diamond"}, {"circle"}, "urban", "Northside"
    )

  def get_trigger(self, event, state):
    if isinstance(event, events.Movement) and event.character.place.name == "Northside":
      clues = events.Gain(event.character, {"clues": 1})
      check = events.Check(event.character, "will", -1)
      loss = events.Loss(event.character, {"sanity": 1})
      return events.Sequence(
          [clues, events.PassFail(event.character, check, events.Nothing(), loss)],
          event.character
      )
    return None


class Mythos15(Environment):

  def __init__(self):
    super().__init__("Mythos15", "Isle", "Science", {"plus"}, {"moon"}, "urban")

  def get_trigger(self, event, state):
    if isinstance(event, events.Movement) and isinstance(event.character.place, places.Street):
      is_deputy = values.ItemNameCount(event.character, "Deputy")
      check = events.Check(event.character, "will", 0)
      arrested = events.Arrested(event.character)
      make_check = events.PassFail(event.character, check, events.Nothing(), arrested)
      return events.PassFail(event.character, is_deputy, events.Nothing(), make_check)
    return None


class Mythos16(Environment):
  def __init__(self):
    super().__init__(
        "Mythos16", "WitchHouse", "Cave",
        {"square", "diamond"}, {"circle"},
        "urban", activity_location="Uptown"
    )

  def get_trigger(self, event, state):
    if not isinstance(event, events.Movement):
      return None
    if event.character.place.name != self.activity_location:
      return None
    return events.Purchase(event.character, "unique", draw_count=2, keep_count=2)


class Mythos17(Environment):
  def __init__(self):
    super().__init__(
        "Mythos17", "WitchHouse", "Cave",
        {"plus"}, {"moon"},
        "urban", activity_location="University"
    )

  def get_trigger(self, event, state):
    if not isinstance(event, events.Movement):
      return None
    if event.character.place.name != self.activity_location:
      return None
    check = events.Check(event.character, "lore", -1)
    gain = events.Gain(event.character, {"clues": 1})
    return events.PassFail(event.character, check, gain, events.Nothing)


class Mythos18(Environment):
  def __init__(self):
    super().__init__("Mythos18", "Square", "Unnamable", {"plus"}, {"moon"}, "mystic")

  def get_interrupt(self, event, state):
    if (
        isinstance(event, events.GainOrLoss)
        and values.Calculation(event.gains["sanity"], operand=values.operator.gt, right=0).value(
            state)
        and (event.source is None or event.source.name not in ("Psychology", "Asylum"))
    ):
      return events.GainPrevention(self, event, "sanity", event.gains["sanity"])
    return None


class Mythos19(Headline):
  def __init__(self):
    super().__init__("Mythos19", "WitchHouse", "Cave", {"moon"}, {"plus"}, activity_location="Cave")
    self.active_until = None

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.extend([
        events.CloseLocation("Merchant", for_turns=1, evict=False),
        events.AddGlobalEffect(self, active_until=state.turn_number + 1, source_deck="mythos")
    ])
    return seq

  def get_trigger(self, event, state):
    if (
        isinstance(event, events.Mythos)
            and self.active_until is not None
            and state.turn_number >= self.active_until):
      return events.RemoveGlobalEffect(self, source_deck="mythos")
    return None


class Mythos20(Headline):
  def __init__(self):
    super().__init__("Mythos20", "Cave", "Roadhouse", {"moon"}, {"plus"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ReturnToCup(from_places=[
        p.name for p in state.places if isinstance(p, places.Street)
    ]))


class Mythos21(Headline):
  def __init__(self):
    super().__init__("Mythos21", "Graveyard", "Isle", {"moon"}, {"plus"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.IncreaseTerror())
    return seq


class Mythos22(Headline):
  def __init__(self):
    super().__init__("Mythos22", "Square", "Unnamable", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super().create_event(state)
    cup_return = events.ReturnToCup(names=["Tentacle Tree"])
    terrorize = events.Conditional(
        None, cup_return, "returned", {0: events.Nothing(), 1: events.IncreaseTerror()}
    )
    seq.events.extend([cup_return, terrorize])
    return seq


class Mythos23(Headline):
  def __init__(self):
    super().__init__("Mythos23", "Unnamable", "Woods", {"moon"}, {"plus"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ReleaseMonstersToLocation("Merchant"))
    return seq


class Mythos24(Headline):
  def __init__(self):
    super().__init__("Mythos24", "WitchHouse", "Cave", {"circle"}, {"square", "diamond"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ReturnToCup(from_places=["Easttown", "Roadhouse", "Diner", "Police"]))


class Mythos25(Environment):
  def __init__(self):
    super().__init__("Mythos25", "Woods", "Square", {"square", "diamond"}, {"circle"}, "weather")

  def get_modifier(self, thing, attribute):
    if attribute == "fight":
      return -1
    if attribute == "lore":
      return 1
    if thing.name == "Flame Matrix" and attribute == "toughness":
      return 1
    return 0


class Mythos26(Environment):
  def __init__(self):
    super().__init__("Mythos26", "Woods", "Society", {"square", "diamond"}, {"circle"}, "urban")

  def get_interrupt(self, event, state):
    if isinstance(event, events.IncreaseTerror):
      return events.CancelEvent(event)
    return None


class Mythos27(Rumor):

  def __init__(self):
    super().__init__("Mythos27", "Isle", {"slash", "triangle", "star"}, {"hex"}, "Easttown")
    self.progress = 6
    self._max_progress = 10

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
    if isinstance(event, events.ProgressRumor) and event.rumor == self and self.should_fail(state):
      return events.Sequence([events.EndRumor(self, failed=True), events.RemoveAllSeals()])
    if isinstance(event, events.ProgressRumor) and event.rumor == self and self.progress <= 0:
      draws = [events.Draw(char, "unique", 1) for char in state.characters if not char.gone]
      return events.Sequence([events.EndRumor(self, failed=False)] + draws)
    return super().get_trigger(event, state)


class Mythos28(Headline):
  def __init__(self):
    super().__init__("Mythos28", "Graveyard", "Isle", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    first_player = state.characters[state.first_player]
    seq = super().create_event(state)
    check = events.Check(first_player, "luck", -1)
    pass_fail = events.PassFail(first_player, check, events.Nothing(), events.Curse(first_player))
    seq.events.extend([check, pass_fail])
    return seq


class Mythos29(Environment):
  def __init__(self):
    super().__init__("Mythos30", "Society", "Lodge", {"plus"}, {"moon"}, "weather")

  def get_override(self, thing, attribute):
    if isinstance(thing, monsters.Monster) and attribute == "fast":
      return "normal"
    return None

  def get_interrupt(self, event, state):
    if isinstance(event, events.Movement):
      return events.ChangeMovementPoints(event.character, -1)
    return None


class Mythos30(Headline):
  def __init__(self):
    super().__init__("Mythos30", "Society", "Lodge", {"moon"}, {"plus"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ReleaseMonstersToLocation("University"))
    return seq


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
    self._max_progress = 5

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
    if isinstance(event, events.ProgressRumor) and event.rumor == self and self.should_fail(state):
      return events.EndRumor(self, failed=True, add_global=True)
    return super().get_trigger(event, state)


class ShuffleMythos(MythosCard):

  def __init__(self):  # pylint: disable=super-init-not-called
    self.name = "ShuffleMythos"


def CreateMythos():
  return [
      Mythos1(), Mythos2(), Mythos3(), Mythos4(), Mythos5(), Mythos6(), Mythos7(), Mythos8(),
      Mythos9(), Mythos10(), Mythos11(), Mythos12(), Mythos13(), Mythos14(), Mythos15(),
      Mythos27(), Mythos45(), Mythos59(), ShuffleMythos(),
  ]
