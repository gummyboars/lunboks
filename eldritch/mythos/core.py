import operator

from eldritch import events
from eldritch import places
from eldritch import values


class GlobalEffect:
  # pylint: disable=unused-argument

  def get_modifier(self, thing, attribute, state):
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
    self,
    name,
    gate_location,
    clue_location,
    white_dimensions,
    black_dimensions,
    activity_location=None,
  ):
    self.name = name
    self.gate_location = gate_location
    self.clue_location = clue_location
    self.white_dimensions = white_dimensions
    self.black_dimensions = black_dimensions
    self.activity_location = activity_location

  def create_event(self, state) -> events.Sequence:  # pylint: disable=unused-argument
    seq: list[events.Event] = []
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
    self,
    name,
    gate_location,
    clue_location,
    white_dimensions,
    black_dimensions,
    env_type,
    activity_location=None,
  ):
    super().__init__(
      name, gate_location, clue_location, white_dimensions, black_dimensions, activity_location
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
      name, gate_location, None, white_dimensions, black_dimensions, activity_location
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


class CityBonus(Environment):
  def __init__(
    self,
    name,
    gate_location,
    clue_location,
    white_dimensions,
    black_dimensions,
    env_type,
    bonus_skill,
    penalty_skill,
  ):
    super().__init__(
      name, gate_location, clue_location, white_dimensions, black_dimensions, env_type
    )
    self.bonus_skill = bonus_skill
    self.penalty_skill = penalty_skill

  def get_modifier(self, thing, attribute, state):
    if isinstance(getattr(thing, "place", None), places.CityPlace):
      if attribute == self.penalty_skill + "_check":
        return -1
      if attribute == self.bonus_skill + "_check":
        return 1
    return 0


class GainPrevention(Environment):
  def __init__(
    self,
    name,
    gate_location,
    clue_location,
    white_dimensions,
    black_dimensions,
    env_type,
    attribute,
  ):
    assert attribute in ("sanity", "stamina")
    super().__init__(
      name, gate_location, clue_location, white_dimensions, black_dimensions, env_type
    )
    self.attr = attribute
    self.names = ("Psychology", "Asylum") if self.attr == "sanity" else ("Physician", "Hospital")

  def get_interrupt(self, event, state):
    if not isinstance(event, events.GainOrLoss):
      return None
    gain = values.Calculation(event.gains.get(self.attr, 0), operand=operator.gt, right=0)
    if gain.value(state) and getattr(event.source, "name", "") not in self.names:
      return events.GainPrevention(self, event, self.attr, event.gains[self.attr])
    return None

  def get_override(self, thing, attribute):
    if attribute == f"can_gain_{self.attr}":
      return False
    return None


class ReturnMonstersHeadline(Headline):
  def __init__(
    self, name, gate_location, clue_location, white_dimensions, black_dimensions, from_places
  ):
    super().__init__(name, gate_location, clue_location, white_dimensions, black_dimensions)
    assert from_places is not None
    self.from_places = from_places

  def create_event(self, state) -> events.Sequence:
    seq = super().create_event(state)
    seq.events.append(events.ReturnToCup(from_places=self.from_places))
    return seq


class ReturnAndIncreaseHeadline(Headline):
  def __init__(
    self, name, gate_location, clue_location, white_dimensions, black_dimensions, monster_names
  ):
    super().__init__(name, gate_location, clue_location, white_dimensions, black_dimensions)
    assert monster_names is not None
    self.monster_names = monster_names

  def create_event(self, state) -> events.Sequence:
    seq = super().create_event(state)
    cup_return = events.ReturnToCup(names=self.monster_names)
    terrorize = events.Conditional(
      None, cup_return, "returned", {0: events.Nothing(), 1: events.IncreaseTerror()}
    )
    seq.events.extend([cup_return, terrorize])
    return seq


class ReleaseMonstersHeadline(Headline):
  def __init__(
    self,
    name,
    gate_location,
    clue_location,
    white_dimensions,
    black_dimensions,
    to_places,
    num_monsters=2,
  ):
    super().__init__(name, gate_location, clue_location, white_dimensions, black_dimensions)
    # In the expansions, there are some "Release to multiple locations" cards
    self.to_places = [to_places] if isinstance(to_places, str) else to_places
    self.num_monsters = num_monsters

  def create_event(self, state) -> events.Sequence:
    seq = super().create_event(state)
    draw = events.DrawMonstersFromCup(self.num_monsters)
    place = events.MonsterSpawnChoice(draw, None, open_gates=self.to_places)
    seq.events.extend([draw, place])
    return seq


class CloseLocationsHeadline(Headline):
  def __init__(
    self,
    name,
    gate_location,
    clue_location,
    white_dimensions,
    black_dimensions,
    close_places,
    evict=True,
  ):
    super().__init__(name, gate_location, clue_location, white_dimensions, black_dimensions)
    self.close_places = close_places
    self.active_until = None
    self.evict = evict

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.extend(
      [events.CloseLocation(place, for_turns=1, evict=self.evict) for place in self.close_places]
    )
    seq.events.append(
      events.AddGlobalEffect(self, active_until=state.turn_number + 1, source_deck="mythos")
    )
    return seq

  def get_trigger(self, event, state):
    if (
      isinstance(event, events.Mythos)
      and self.active_until is not None
      and state.turn_number >= self.active_until
    ):
      return events.RemoveGlobalEffect(self, source_deck="mythos")
    return None


def HealthWager(source, character, attribute, prompt, prize):
  dice = events.DiceRoll(character, values.Calculation(character, attribute), name=source.name)
  amount = values.Calculation(
    left=character, left_attr=attribute, operand=operator.sub, right=dice, right_attr="successes"
  )
  loss = events.Loss(character, {attribute: amount}, source=source)
  final = events.PassFail(
    character, values.Calculation(character, attribute), prize, events.Nothing()
  )
  yes_sequence = events.Sequence([dice, loss, final], character)
  return events.BinaryChoice(
    character, prompt, "Yes", "No", yes_sequence, events.Nothing(), visual=source.name
  )


class ShuffleMythos(MythosCard):
  def __init__(self):  # pylint: disable=super-init-not-called
    self.name = "ShuffleMythos"
