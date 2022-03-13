import abc
import collections
import math
import operator
from random import SystemRandom
from typing import List, Dict, Optional, Union, NoReturn

from eldritch import places
from eldritch import values


random = SystemRandom()


# pylint: disable=attribute-defined-outside-init
# TODO: turn this back on when all events call super().__init__() to get a cancelled attribute


class Event(metaclass=abc.ABCMeta):
  """An Event represents an Event that is resolved by the event loop.

  An Event must implement two methods: resolve(self, state) and is_resolved(self)

  resolve(self, state) must do the work of the actual event. The event loop may call resolve()
  multiple times. Each time it is called, resolve() must do one of the following
    (a) change the state and its internal state so that is_resolved() returns True
    (b) set self.cancelled to True so that is_cancelled() returns True
    (c) append one (and only one) new event to the stack
  ChoiceEvents are exempt from this requirement (see below).

  It is guaranteed that when an Event's resolve() method is called, then that Event is
  currently at the top of the event stack.
  If a parent Event has added a child Event onto the stack, the parent may assume that the child
  Event has been resolved or cancelled before the parent Event's resolve() is called again.

  An Event's is_resolved() method must use information from the Event's internal state to
  decide whether to return True or False; it should not use references to game objects.
  """

  @abc.abstractmethod
  def resolve(self, state) -> NoReturn:
    # resolve should return True if the event was resolved, False otherwise.
    # For example, an event that requires a check to be made should add that check to the end
    # of the event stack, and then return False. It will be called again when the check is
    # finished with the results of the check accessible.
    raise NotImplementedError

  @abc.abstractmethod
  def is_resolved(self) -> bool:
    raise NotImplementedError

  def is_cancelled(self) -> bool:
    return getattr(self, "cancelled", False)

  def is_done(self) -> bool:
    return self.is_cancelled() or self.is_resolved()

  @abc.abstractmethod
  def start_str(self) -> str:
    raise NotImplementedError

  @abc.abstractmethod
  def finish_str(self) -> str:
    raise NotImplementedError


class ChoiceEvent(Event):

  @abc.abstractmethod
  def resolve(self, state, choice=None) -> NoReturn:  # pylint: disable=arguments-differ
    raise NotImplementedError

  @abc.abstractmethod
  def prompt(self) -> str:
    raise NotImplementedError

  def compute_choices(self, state) -> NoReturn:
    pass

  def annotations(self, state) -> Optional[List[str]]:  # pylint: disable=unused-argument
    return None


class Nothing(Event):

  def __init__(self):
    self.done = False

  def resolve(self, state):
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return "Nothing happens"


class Sequence(Event):

  def __init__(self, events, character=None):
    self.events: List[Event] = events
    self.idx = 0
    self.character = character

  def resolve(self, state):
    while self.idx < len(self.events) and self.events[self.idx].is_done():
      self.idx += 1
    if self.idx == len(self.events):
      return
    state.event_stack.append(self.events[self.idx])

  def is_resolved(self):
    return self.idx == len(self.events)

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class CancelEvent(Event):

  def __init__(self, to_cancel):
    self.to_cancel = to_cancel

  def resolve(self, state):
    self.to_cancel.cancelled = True

  def is_resolved(self):
    return self.to_cancel.is_cancelled()

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.to_cancel.__class__.__name__} was cancelled"


class Turn(Event):

  # pylint: disable=abstract-method

  def check_lose_turn(self) -> bool:
    char = getattr(self, "character", None)
    if not char:
      return False
    if char.lose_turn_until is not None:
      self.done = True  # pylint: disable=attribute-defined-outside-init
      return True
    return False


class Upkeep(Turn):

  def __init__(self, character):
    self.character = character
    self.focus_given = False
    self.reappear: Optional[Event] = None
    self.refresh: Optional[RefreshAssets] = None
    self.actions: Optional[UpkeepActions] = None
    self.sliders: Optional[SliderInput] = None
    self.done = False

  def resolve(self, state):
    if self.check_lose_turn():
      return
    if self.character.place.name == "Lost":
      place_choice = PlaceChoice(self.character, "Choose a place to return to")
      move = ForceMovement(self.character, place_choice)
      self.reappear = Sequence([place_choice, move], self.character)
      state.event_stack.append(self.reappear)
      return
    if not self.focus_given:
      self.character.focus_points = self.character.focus
      self.focus_given = True
    if self.refresh is None:
      self.refresh = RefreshAssets(self.character)
      state.event_stack.append(self.refresh)
      return
    if self.actions is None:
      self.actions = UpkeepActions(self.character)
      state.event_stack.append(self.actions)
      return
    if self.sliders is None:
      self.sliders = SliderInput(self.character)
      state.event_stack.append(self.sliders)
      return
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name}'s upkeep"

  def finish_str(self):
    return ""


class UpkeepActions(Nothing):

  def __init__(self, character):
    super().__init__()
    self.character = character


class SliderInput(Event):

  def __init__(self, character, free=False):
    self.character = character
    self.pending = self.character.sliders()
    assert len(self.pending) >= 3
    self.free = free
    self.done = False

  def resolve(self, state, name, value):  # pylint: disable=arguments-differ
    assert isinstance(name, str), "invalid slider name"
    assert name in self.pending.keys() | {"done", "reset"}
    if name == "done":
      if not self.free:
        if self.character.focus_cost(self.pending) > self.character.focus_points:
          raise AssertionError("You do not have enough focus.")
        self.character.focus_points -= self.character.focus_cost(self.pending)
      for slider_name, slider_value in self.pending.items():
        setattr(self.character, slider_name + "_slider", slider_value)
      self.done = True
      return
    if name == "reset":
      self.pending = self.character.sliders()
      return

    assert isinstance(value, int), "invalid slider value"
    assert value >= 0, f"invalid slider value {value}"
    assert value < len(getattr(self.character, "_" + name)), f"invalid slider value {value}"
    pending = self.pending.copy()
    pending[name] = value
    if not self.free:
      if self.character.focus_cost(pending) > self.character.focus_points:
        raise AssertionError("You do not have enough focus.")
    self.pending = pending

  def prompt(self):
    if self.free:
      return f"{self.character.name} to set sliders anywhere"
    remaining_focus = self.character.focus_points - self.character.focus_cost(self.pending)
    return f"{self.character.name} to set sliders ({remaining_focus} focus remaining)"

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class Movement(Turn):

  def __init__(self, character):
    self.character = character
    self.move: Optional[Event] = None
    self.done = False

  def resolve(self, state):
    self.character.avoid_monsters = []
    if self.check_lose_turn():
      return
    if self.character.delayed_until is not None:
      if self.character.delayed_until <= state.turn_number:
        self.character.delayed_until = None
      else:
        self.done = True
        return

    if self.move is None:
      if isinstance(self.character.place, places.OtherWorld):
        if self.character.place.order == 1:
          world_name = self.character.place.info.name + "2"
          self.move = ForceMovement(self.character, world_name)
        else:
          self.move = Return(self.character, self.character.place.info.name)
      elif isinstance(self.character.place, places.CityPlace):
        self.character.movement_points = self.character.speed(state)
        self.move = CityMovement(self.character)
      else:
        self.move = Nothing()  # TODO: handle lost in time and space?
      state.event_stack.append(self.move)
      return

    assert self.move.is_done()
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name}'s movement"

  def finish_str(self):
    return ""


class CityMovement(ChoiceEvent):

  def __init__(self, character):
    self.character = character
    self.routes = {}
    self.none_choice = "done"
    self.done = False

  def resolve(self, state, choice=None):
    if choice == self.none_choice:
      self.done = True
      return
    assert choice in self.routes
    state.event_stack.append(
        Sequence([MoveOne(self.character, dest) for dest in self.routes[choice]], self.character))

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return ""

  def prompt(self):
    return f"{self.character.name} to move ({self.character.movement_points} move remaining)"

  @property
  def choices(self):
    return sorted(self.routes.keys())

  def annotations(self, state):
    return [f"Move ({len(self.routes[dest])})" for dest in sorted(self.routes.keys())]

  def compute_choices(self, state):
    self.routes = self.get_routes(state)

  def get_distances(self, state):
    routes = self.get_routes(state)
    return {loc: len(route) for loc, route in routes.items()}

  def get_routes(self, state):
    if self.character.movement_points == 0:
      return {}
    routes = {self.character.place.name: []}
    if self.character.place.closed:
      return routes

    monster_counts = collections.defaultdict(int)
    for monster in state.monsters:
      if monster.place is not None:
        monster_counts[monster.place.name] += 1

    queue = collections.deque()
    for place in self.character.place.connections:
      if not place.closed:
        queue.append((place, []))
    while queue:
      place, route = queue.popleft()
      if place.name in routes:
        continue
      if place.closed:  # TODO: more possibilities?
        continue
      routes[place.name] = route + [place.name]
      if len(routes[place.name]) == self.character.movement_points:
        continue
      if monster_counts[place.name] > 0:
        continue
      for next_place in place.connections:
        queue.append((next_place, route + [place.name]))
    return routes


class EncounterPhase(Turn):

  def __init__(self, character):
    self.character = character
    self.action: Optional[Event] = None
    self.done = False

  def resolve(self, state):
    if self.check_lose_turn():
      return
    if self.action is None:
      if not isinstance(self.character.place, places.Location):
        self.done = True
        return
      if self.character.place.gate and self.character.explored:
        self.action = GateCloseAttempt(self.character, self.character.place.name)
      elif self.character.place.gate:
        self.action = Travel(self.character, self.character.place.gate.name)
      elif self.character.place.fixed_encounters:
        choices = [self.character.place.neighborhood.name + " Card"]
        prereqs = [None]
        spends = [None]
        results = {0: Encounter(self.character, self.character.place.name)}
        for idx, fixed in enumerate(self.character.place.fixed_encounters):
          choices.append(fixed.name)
          prereqs.append(fixed.prereq(self.character))
          spends.append(fixed.spend(self.character))
          results[idx+1] = fixed.encounter(self.character)
        choice = CardSpendChoice(self.character, "Encounter?", choices, prereqs, spends=spends)
        cond = Conditional(self.character, choice, "choice_index", results)
        self.action = Sequence([choice, cond], self.character)
      else:
        self.action = Encounter(self.character, self.character.place.name)
      state.event_stack.append(self.action)
      return

    assert self.action.is_done()
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name}'s encounter phase"

  def finish_str(self):
    return ""


class OtherWorldPhase(Turn):

  def __init__(self, character):
    self.character = character
    self.action: Optional[Event] = None
    self.done = False

  def resolve(self, state):
    if self.check_lose_turn():
      return
    if self.action is None:
      if not isinstance(self.character.place, places.OtherWorld):
        self.done = True
        return
      self.action = GateEncounter(
          self.character, self.character.place.info.name, self.character.place.info.colors)
      state.event_stack.append(self.action)
      return

    assert self.action.is_done()
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name}'s other world phase"

  def finish_str(self):
    return ""


class Mythos(Turn):

  def __init__(self, _):
    self.draw: Optional[Event] = None
    self.action: Optional[Event] = None
    self.done = False

  def resolve(self, state):
    first_player = state.characters[state.first_player]

    if self.draw is None:
      self.draw = DrawMythosCard(first_player)
      state.event_stack.append(self.draw)
      return

    if self.action is None:
      # TODO: what if the world changes before the event is added to the queue? that is, what
      # if a character is devoured after we create an event that iterates through all the chars,
      # but before we make a choice?
      self.action = self.draw.card.create_event(state)
      if not state.test_mode:
        choice = CardChoice(first_player, "Choose a Mythos Card", [self.draw.card.name])
        cond = Conditional(first_player, choice, "choice_index", {0: self.action})
        self.action = Sequence([choice, cond])
      state.event_stack.append(self.action)
      return

    assert self.action.is_done()
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return "Mythos phase"

  def finish_str(self):
    return ""


class DiceRoll(Event):

  def __init__(self, character, count):
    self.character = character
    self.count = count
    self.roll = None
    self.sum = None
    self.successes = None

  def resolve(self, state):
    self.roll = [random.randint(1, 6) for _ in range(self.count)]
    self.sum = sum(self.roll)
    # Some encounters have: "Roll a die for each X. On a success..."
    self.successes = self.character.count_successes(self.roll, None)

  def is_resolved(self):
    return self.roll is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.roll:
      return f"{self.character.name} rolled no dice"
    # pylint: disable=consider-using-f-string
    return "%s rolled %s" % (self.character.name, " ".join([str(x) for x in self.roll]))


class BonusDiceRoll(DiceRoll):
  pass


class MoveOne(Event):

  def __init__(self, character, dest):
    self.character = character
    self.dest = dest
    self.done = False
    self.moved = None

  def resolve(self, state):
    if self.character.movement_points <= 0:
      self.done = True
      self.moved = False
      return
    assert self.dest in [conn.name for conn in self.character.place.connections]
    if not (self.character.place.closed or state.places[self.dest].closed):
      self.character.place = state.places[self.dest]
      self.character.movement_points -= 1
      self.character.explored = False
      self.character.avoid_monsters = []
      self.moved = True
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name} moving from {self.character.place.name}"

  def finish_str(self):
    if self.moved:
      return f"{self.character.name} moved to {self.dest}"
    return f"{self.character.name} stayed in {self.character.place.name}"


class GainOrLoss(Event):

  def __init__(self, character, gains, losses):
    assert not gains.keys() - {"stamina", "sanity", "dollars", "clues"}
    assert not losses.keys() - {"stamina", "sanity", "dollars", "clues"}
    assert not gains.keys() & losses.keys()
    assert all(isinstance(val, (int, values.Value)) or math.isinf(val) for val in gains.values())
    assert all(isinstance(val, (int, values.Value)) or math.isinf(val) for val in losses.values())
    self.character = character
    self.gains = gains
    self.losses = losses
    self.final_adjustments = None

  def resolve(self, state):
    assert not self.gains.keys() & self.losses.keys()
    adjustments = {}
    for attr, gain in self.gains.items():
      val = gain.value(state) if isinstance(gain, values.Value) else gain
      if val > 0:
        adjustments[attr] = val
    for attr, loss in self.losses.items():
      val = loss.value(state) if isinstance(loss, values.Value) else loss
      if val > 0:
        adjustments[attr] = -val

    self.final_adjustments = {}
    for attr, adjustment in adjustments.items():
      old_val = getattr(self.character, attr)
      new_val = old_val + adjustment
      new_val = max(new_val, 0)
      if attr == "stamina":
        new_val = min(new_val, self.character.max_stamina(state))
      if attr == "sanity":
        new_val = min(new_val, self.character.max_sanity(state))
      self.final_adjustments[attr] = new_val - old_val
      setattr(self.character, attr, new_val)

  def is_resolved(self):
    return self.final_adjustments is not None

  def start_str(self):
    return ""

  def finish_str(self):
    gains = ", ".join([
        f"{count} {attr}" for attr, count in self.final_adjustments.items() if count > 0])
    losses = ", ".join([
        f"{-count} {attr}" for attr, count in self.final_adjustments.items() if count < 0])
    if not gains and not losses:
      return ""
    # pylint: disable=consider-using-f-string
    result = "gained %s" % gains if gains else ""
    result += " and " if (gains and losses) else ""
    result += "lost %s" % losses if losses else ""
    return self.character.name + " " + result


def Gain(character, gains):
  return GainOrLoss(character, gains, {})


def Loss(character, losses):
  return GainOrLoss(character, {}, losses)


class SplitGain(Event):

  def __init__(self, character, attr1, attr2, amount):
    assert isinstance(amount, (int, values.Value))
    self.character = character
    self.attr1 = attr1
    self.attr2 = attr2
    self.amount = amount
    self.choice: Optional[ChoiceEvent] = None
    self.gain: Optional[Event] = None

  def resolve(self, state):
    if self.gain is not None:
      assert self.gain.is_done()
      return

    amount = self.amount.value(state) if isinstance(self.amount, values.Value) else self.amount

    if self.choice is not None:
      assert self.choice.is_done()
      if self.choice.is_cancelled():
        self.cancelled = True
        return
      attr1_amount = self.choice.choice
      self.gain = GainOrLoss(
          self.character, {self.attr1: attr1_amount, self.attr2: amount - attr1_amount}, {})
      state.event_stack.append(self.gain)
      return

    prompt = f"How much of the {amount} do you want to go to {self.attr1}?"
    self.choice = MultipleChoice(self.character, prompt, list(range(0, amount+1)))
    state.event_stack.append(self.choice)

  def is_resolved(self):
    return self.gain is not None and self.gain.is_done()

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class LossPrevention(Event):

  def __init__(self, prevention_source, source_event, attribute, amount):
    assert isinstance(source_event, GainOrLoss)
    assert isinstance(amount, (int, values.Value)) or math.isinf(amount)
    assert attribute in source_event.losses
    self.prevention_source = prevention_source
    self.source_event: Event = source_event
    self.attribute = attribute
    self.amount = amount
    self.prevented = None

  def resolve(self, state):
    reduced_loss = values.Calculation(
        self.source_event.losses[self.attribute], None, operator.sub, self.amount)
    self.source_event.losses[self.attribute] = reduced_loss
    self.prevented = self.amount
    if isinstance(self.amount, values.Value):
      self.prevented = self.amount.value(state)

  def is_resolved(self):
    return self.prevented is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.prevented:
      return ""
    return f"{self.prevention_source.name} prevented {self.prevented} {self.attribute} loss"


class CollectClues(Event):

  def __init__(self, character, place):
    self.character = character
    self.place = place
    self.gain: Optional[Event] = None
    self.picked_up = None
    self.done = False

  def resolve(self, state):
    if self.picked_up is None:
      if self.character.place.name != self.place:
        self.done = True
        return
      self.picked_up = state.places[self.place].clues

    if not self.picked_up:
      self.done = True
      return

    if self.gain is None:
      self.gain = Gain(self.character, {"clues": self.picked_up})
      state.event_stack.append(self.gain)
      return

    if self.gain.is_cancelled():
      self.picked_up = None
      self.cancelled = True
      return
    state.places[self.place].clues -= self.picked_up
    self.done = True
    return

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    if self.picked_up is None:
      return ""
    return f"{self.character.name} picked up {self.picked_up} clues at {self.place}"


class StackClearMixin:

  def clear_stack(self, state):
    saved_interrupts = state.interrupt_stack[-1]
    saved_triggers = state.trigger_stack[-1]
    while state.event_stack:
      event = state.event_stack[-1]
      if hasattr(event, "character") and event.character == self.character:
        state.pop_event(event)
        if event != self:
          event.cancelled = True
      else:
        break
    # Note that when we cleared the stack, we also cleared this event. But this event should still
    # be on the stack and get finished, so we have to put it (and its corresponding interrupts
    # and triggers) back on the stack.
    state.interrupt_stack.append(saved_interrupts)
    state.trigger_stack.append(saved_triggers)
    state.event_stack.append(self)
    assert len(state.event_stack) == len(state.trigger_stack)
    assert len(state.event_stack) == len(state.interrupt_stack)


class InsaneOrUnconscious(StackClearMixin, Event):

  def __init__(self, character, attribute, desc):
    assert attribute in {"sanity", "stamina"}
    self.character = character
    self.attribute = attribute
    self.desc = desc
    self.stack_cleared = False
    self.lose_clues: Optional[Event] = None
    self.lose_items: Optional[Event] = None
    self.lose_turn: Optional[Event] = None
    self.force_move: Optional[Event] = None

  def resolve(self, state):
    if not self.stack_cleared:
      assert getattr(self.character, self.attribute) <= 0
      setattr(self.character, self.attribute, 1)

      self.clear_stack(state)
      self.stack_cleared = True

    if not self.lose_clues:
      self.lose_clues = Loss(self.character, {"clues": self.character.clues // 2})
      state.event_stack.append(self.lose_clues)
      return

    if not self.lose_items:
      item_count = values.ItemDeckCount(self.character, {"common", "unique", "spells"})
      lose_count = values.Calculation(item_count, None, operator.floordiv, 2)
      self.lose_items = LoseItems(self.character, lose_count)
      state.event_stack.append(self.lose_items)
      return

    if not self.lose_turn:
      self.lose_turn = DelayOrLoseTurn(self.character, "lose_turn", "this")
      state.event_stack.append(self.lose_turn)
      return

    if not self.force_move:
      if isinstance(self.character.place, places.CityPlace):
        dest = "Asylum" if self.attribute == "sanity" else "Hospital"
        self.force_move = ForceMovement(self.character, dest)
      else:
        self.force_move = LostInTimeAndSpace(self.character)
      state.event_stack.append(self.force_move)

  def is_resolved(self):
    steps = [self.lose_clues, self.lose_items, self.lose_turn, self.force_move]
    return all(steps) and all(step.is_done() for step in steps)

  def start_str(self):
    return f"{self.character.name} {self.desc}"

  def finish_str(self):
    if isinstance(self.force_move, ForceMovement):
      return f"{self.character.name} woke up in the {self.force_move.location_name}"
    return ""


def Insane(character):
  return InsaneOrUnconscious(character, "sanity", "went insane")


def Unconscious(character):
  return InsaneOrUnconscious(character, "stamina", "passed out")


class Devoured(StackClearMixin, Event):

  def __init__(self, character):
    self.character = character
    self.stack_cleared = False

  def resolve(self, state):
    if not self.stack_cleared:
      self.clear_stack(state)
      self.stack_cleared = True
      self.character.gone = True
      self.character.lose_turn_until = float("inf")
      self.character.place = None
      for pos in self.character.possessions:
        if hasattr(pos, "deck"):
          getattr(state, getattr(pos, "deck")).append(pos)
      self.character.possessions.clear()

  def is_resolved(self):
    return self.stack_cleared

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.character.name} was devoured"


class DelayOrLoseTurn(Event):

  def __init__(self, character, status, which="next"):
    assert status in {"delayed", "lose_turn"}
    assert which in {"this", "next"}
    self.character = character
    self.attr = status + "_until"
    self.num_turns = 2 if which == "next" else 1
    self.until = None

  def resolve(self, state):
    current = getattr(self.character, self.attr) or 0
    self.until = max(current, state.turn_number + self.num_turns)
    setattr(self.character, self.attr, self.until)

  def is_resolved(self):
    return self.until is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if self.attr == "delayed_until":
      return f"{self.character.name} is delayed"
    if self.num_turns == 1:
      return f"{self.character.name} loses the remainder of their turn"
    return f"{self.character.name} loses their next turn"


def Delayed(character):
  return DelayOrLoseTurn(character, "delayed")


def LoseTurn(character):
  return DelayOrLoseTurn(character, "lose_turn")


class LostInTimeAndSpace(Sequence):

  def __init__(self, character):
    super().__init__([ForceMovement(character, "Lost"), LoseTurn(character)], character)


class BlessCurse(Event):

  def __init__(self, character, positive):
    self.character = character
    self.adjustment = 1 if positive else -1
    self.change = None

  def resolve(self, state):
    old_val = self.character.bless_curse
    new_val = min(max(old_val + self.adjustment, -1), 1)
    self.character.bless_curse = new_val
    self.change = new_val - old_val
    if new_val != 0:
      self.character.bless_curse_start = state.turn_number + 2
    else:
      self.character.bless_curse_start = None

  def is_resolved(self):
    return self.change is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.change:
      return ""
    if self.character.bless_curse:
      return f"{self.character.name} became " + ("blessed" if self.change > 0 else "cursed")
    return f"{self.character.name} lost their " + ("blessing" if self.change < 0 else "curse")


def Bless(character):
  return BlessCurse(character, True)


def Curse(character):
  return BlessCurse(character, False)


class MembershipChange(Event):

  def __init__(self, character, positive):
    self.character = character
    self.positive = positive
    self.change = None

  def resolve(self, state):
    old_status = self.character.lodge_membership
    self.character.lodge_membership = self.positive
    self.change = int(self.character.lodge_membership) - int(old_status)

  def is_resolved(self):
    return self.change is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.change:
      return ""
    if self.change < 0:
      return f"{self.character.name} lost their Lodge membership"
    return f"{self.character.name} became a member of the Silver Twilight Lodge"


class StatusChange(Event):

  def __init__(self, character, status, positive=True):
    assert status in {"retainer", "bank_loan"}
    self.character = character
    self.attr = status + "_start"
    self.positive = positive
    self.change = None

  def resolve(self, state):
    old_status = getattr(self.character, self.attr)
    new_status = (state.turn_number + 2) if self.positive else None
    setattr(self.character, self.attr, new_status)
    self.change = int(new_status is not None) - int(old_status is not None)

  def is_resolved(self):
    return self.change is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.change:
      return ""
    status_map = {
        "retainer_start": {-1: " lost their retainer", 1: " received a retainer"},
        "bank_loan_start": {-1: " lost their bank loan??", 1: " received a bank loan"},
    }
    return self.character.name + status_map[self.attr][self.change]


class ForceMovement(Event):

  def __init__(self, character, location_name):
    self.character = character
    self.location_name: Union[MapChoice, str] = location_name
    self.done = False

  def resolve(self, state):
    if isinstance(self.location_name, MapChoice):
      assert self.location_name.is_done()
      if self.location_name.choice is None:
        # No need to reset explored, since the character did not move.
        self.cancelled = True
        return
      self.location_name = self.location_name.choice
    self.character.place = state.places[self.location_name]
    self.character.explored = False
    self.character.avoid_monsters = []
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return self.character.name + " moved to " + self.character.place.name


class DrawItems(Event):

  def __init__(self, character, deck, draw_count, prompt="Choose a card", target_type=None):
    assert deck in {"common", "unique", "spells", "skills", "allies"}
    self.character = character
    self.deck = deck
    self.prompt = prompt
    self.draw_count = draw_count
    self.drawn = None
    self.target_type = target_type

  def resolve(self, state):
    if self.drawn is None:
      self.drawn = []
      deck = getattr(state, self.deck)
      i = 0
      decksize = len(deck)
      while len(self.drawn) < self.draw_count:
        i += 1
        if not deck:
          break
        top = deck.popleft()
        if self.target_type is None or isinstance(top, self.target_type):
          self.drawn.append(top)
        else:
          deck.append(top)

        if i >= decksize:
          break
      deck.extend(self.drawn)

  def is_resolved(self):
    return self.drawn is not None

  def start_str(self):
    if self.target_type is None:
      return f"{self.character.name} draws {self.draw_count} cards from the {self.deck} deck"
    return (f"{self.character.name} draws {self.draw_count} {self.target_type} "
            + f"cards from the {self.deck} deck")

  def finish_str(self):
    return f"{self.character.name} drew " + ", ".join(c.name for c in self.drawn)


class KeepDrawn(Event):
  def __init__(self, character, draw, prompt="Choose a card", sort_uniq=False):
    self.character = character
    self.draw: DrawItems = draw
    self.keep_count = 1  # TODO: allow the player to keep more than one?
    self.drawn = None
    self.kept = None
    self.choice: Optional[ChoiceEvent] = None
    self.prompt = prompt
    self.sort_uniq = sort_uniq

  def resolve(self, state):
    if self.draw.is_cancelled():
      self.kept = []
      return

    if self.drawn is None:
      assert self.draw.is_resolved()
      self.drawn = self.draw.drawn

    if self.choice is not None:
      assert self.choice.is_done()
      if self.choice.is_cancelled():
        self.cancelled = True
        return
      kept_cards = [self.drawn[self.choice.choice_index]]
      self.kept = [card.name for card in kept_cards]
      for card in kept_cards:
        getattr(state, self.draw.deck).remove(card)
      self.character.possessions.extend(kept_cards)
      return

    if self.keep_count < len(self.drawn):
      self.choice = CardChoice(
          self.character, self.prompt, [card.name for card in self.drawn], sort_uniq=self.sort_uniq,
      )
      state.event_stack.append(self.choice)
      return

    self.kept = [card.name for card in self.drawn]
    for card in self.drawn:
      getattr(state, self.draw.deck).remove(card)
    self.character.possessions.extend(self.drawn)

  def is_resolved(self):
    return self.kept is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.character.name} kept " + ", ".join(self.kept)


def Draw(character, deck, draw_count, prompt="Choose a card", target_type=None):
  cards = DrawItems(character, deck, draw_count, target_type=target_type)
  keep = KeepDrawn(character, cards, prompt, sort_uniq=math.isinf(draw_count))
  return Sequence([cards, keep], character)


def GainAllyOrReward(character, ally: str, reward: Event):
  has_ally = values.ContainsPrerequisite("allies", ally)
  gain_ally = DrawSpecific(character, "allies", ally)
  return PassFail(character, has_ally, gain_ally, reward)


class SellChosen(Event):

  def __init__(self, character, choice, discount_type="fixed", discount=0):
    assert discount_type in {"fixed", "rate"}
    self.character = character
    self.choice: ChoiceEvent = choice
    self.discount_type = discount_type
    self.discount = discount
    self.prices = []
    self.resolved = False
    self.sold = None

  def resolve(self, state):
    if self.choice.is_cancelled():
      self.cancelled = True
      return
    if self.resolved:
      # This should never happen??
      return
    self.prices = [self.discounted_price(card) for card in self.choice.chosen]
    self.character.dollars += sum(self.prices)  # TODO: this should be a Gain(dollars) event
    for card in self.choice.chosen:
      self.character.possessions.remove(card)
      getattr(state, card.deck).append(card)
    self.resolved = True
    self.sold = [card.name for card in self.choice.chosen]

  def is_resolved(self):
    return self.resolved

  def start_str(self):
    if not self.choice.chosen:
      return ""
    return f"{self.character.name} selling " + ", ".join(i.name for i in self.choice.chosen)

  def finish_str(self):
    if not self.sold:
      return f"{self.character.name} sold nothing"
    return f"{self.character.name} sold " + ", ".join(self.sold)

  def discounted_price(self, card):
    if self.discount_type == "fixed":
      return card.price - self.discount
    # self.discount_type == "rate"
    return card.price - int(self.discount * card.price)  # Discounts round up


def Sell(char, decks, sell_count=1, discount_type="fixed", discount=0, prompt="Sell item?"):
  items = ItemCountChoice(char, prompt, sell_count, min_count=0, decks=decks)
  sell = SellChosen(char, items, discount_type=discount_type, discount=discount)
  return Sequence([items, sell], char)


class PurchaseDrawn(Event):
  def __init__(
      self, character, draw, discount_type="fixed", discount=0, keep_count=1, prompt="Buy items?",
      sort_uniq=False,
  ):
    # TODO: draw could be something other than DrawItems (Northside 5)
    assert discount_type in {"fixed", "rate"}
    self.character = character
    self.prompt = prompt
    self.sort_uniq = sort_uniq
    self.keep_count = keep_count
    self.discount_type = discount_type
    self.discount = discount
    self.draw: DrawItems = draw
    self.drawn = None
    self.choice: Optional[ChoiceEvent] = None
    self.kept: List[str] = []
    self.resolved = False

  def resolve(self, state):
    if self.resolved:
      # This should never happen??
      return
    if self.drawn is None:
      if self.draw.is_cancelled():
        self.cancelled = True
        return
      assert self.draw.is_resolved()
      self.drawn = self.draw.drawn

    if self.choice is not None:
      if self.choice.is_cancelled():
        self.cancelled = True
        return
      if self.choice.choice == "Nothing":
        self.resolved = True
        return
      kept_card = self.drawn.pop(self.choice.choice_index)
      self.kept.append(self.choice.choice)
      getattr(state, self.draw.deck).remove(kept_card)
      self.character.possessions.append(kept_card)  # TODO: should be KeepDrawn
      self.keep_count -= 1

    if self.keep_count == 0 or len(self.drawn) == 0:
      self.resolved = True
      return

    # self.keep_count > 0
    choices = [card.name for card in self.drawn] + ["Nothing"]
    prices = [self.discounted_price(card) for card in self.drawn]
    spends = [values.ExactSpendPrerequisite({"dollars": price}) for price in prices] + [None]
    # TODO: In some circumstances, you must purchase at least
    # one card if able (e.g. General Store)

    self.choice = CardSpendChoice(
        self.character, self.prompt, choices, spends=spends, sort_uniq=self.sort_uniq,
    )
    state.event_stack.append(self.choice)

  def is_resolved(self):
    return self.resolved

  def start_str(self):
    return f"{self.character.name} chooses among cards to buy"

  def finish_str(self):
    if not self.kept:
      return f"{self.character.name} kept nothing"
    return f"{self.character.name} bought " + ", ".join(self.kept)

  def discounted_price(self, card):
    if self.discount_type == "fixed":
      return max(card.price - self.discount, 0)
    # self.discount_type == "rate"
    return card.price - int(self.discount * card.price)  # Discounts round up


def Purchase(char, deck, draw_count, discount_type="fixed", discount=0, keep_count=1,
             target_type=None, prompt="Buy items?"):
  items = DrawItems(char, deck, draw_count, target_type=target_type)
  buy = PurchaseDrawn(
      char, items, discount_type=discount_type, discount=discount, keep_count=keep_count,
      prompt=prompt, sort_uniq=math.isinf(draw_count),
  )
  return Sequence([items, buy], char)


class Encounter(Event):

  def __init__(self, character, location_name, count=1):
    self.character = character
    self.location_name: Union[MapChoice, str] = location_name
    self.draw: Optional[DrawEncounter] = None
    self.encounter: Optional[Event] = None
    self.count = count

  def resolve(self, state):
    if isinstance(self.location_name, MapChoice):
      assert self.location_name.is_done()
      name = self.location_name.choice
      if name is None or not isinstance(state.places[name], places.Location):
        self.cancelled = True
        return
      self.location_name = name

    if self.character.lodge_membership and self.location_name == "Lodge":
      self.location_name = "Sanctum"

    if self.draw is None:
      if self.location_name == "Sanctum":
        neighborhood = state.places["FrenchHill"]
      else:
        neighborhood = state.places[self.location_name].neighborhood
      self.draw = DrawEncounter(self.character, neighborhood, self.count)

    if not self.draw.is_done():
      state.event_stack.append(self.draw)
      return

    if self.draw.is_cancelled():
      self.cancelled = True
      return

    if self.encounter and self.encounter.is_done():
      return

    if len(self.draw.cards) == 1 and state.test_mode:  # TODO: test this
      self.encounter = self.draw.cards[0].encounter_event(self.character, self.location_name)
      state.event_stack.append(self.encounter)
      return

    encounters = [
        card.encounter_event(self.character, self.location_name) for card in self.draw.cards]
    choice = CardChoice(
        self.character, "Choose an Encounter", [card.name for card in self.draw.cards],
    )
    cond = Conditional(self.character, choice, "choice_index", dict(enumerate(encounters)))
    self.encounter = Sequence([choice, cond], self.character)
    state.event_stack.append(self.encounter)

  def is_resolved(self):
    return self.encounter and self.encounter.is_done()

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class DrawEncounter(Event):

  def __init__(self, character, neighborhood, count):
    assert count > 0
    self.character = character
    self.neighborhood = neighborhood
    self.count = count
    self.cards = []

  def resolve(self, state):
    encounters = self.neighborhood.encounters
    assert len(encounters) >= self.count
    self.cards.extend(random.sample(encounters, self.count))

  def is_resolved(self):
    return len(self.cards) == self.count

  def start_str(self):
    return f"{self.character.name} draws {self.count} encounter cards"

  def finish_str(self):
    return f"{self.character.name} drew " + ", ".join([card.name for card in self.cards])


class GateEncounter(Event):

  def __init__(self, character, name, colors):
    self.character = character
    self.world_name = name
    self.colors = colors
    self.draw_count = 1
    self.draw: Optional[DrawGateCard] = None
    self.cards = []
    self.encounter: Optional[Event] = None

  def resolve(self, state):
    if self.encounter is not None:
      assert self.encounter.is_done()
      state.gate_cards.extend(self.cards)
      self.cards = []
      return

    if self.draw is not None:
      assert self.draw.is_done()
      if self.draw.is_cancelled():
        state.gate_cards.extend(self.cards)
        self.cards = []
        self.cancelled = True
        return
      self.cards.append(self.draw.card)
      self.draw = None

    if len(self.cards) < self.draw_count:
      self.draw = DrawGateCard(self.character, self.colors)
      state.event_stack.append(self.draw)
      return

    if len(self.cards) == 1 and state.test_mode:  # TODO: test this
      self.encounter = self.cards[0].encounter_event(self.character, self.world_name)
      state.event_stack.append(self.encounter)
      return

    encounters = [card.encounter_event(self.character, self.world_name) for card in self.cards]
    choice = CardChoice(self.character, "Choose an Encounter", [card.name for card in self.cards])
    cond = Conditional(self.character, choice, "choice_index", dict(enumerate(encounters)))
    self.encounter = Sequence([choice, cond], self.character)
    state.event_stack.append(self.encounter)

  def is_resolved(self):
    return self.encounter is not None and self.encounter.is_done() and not self.cards

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class DrawGateCard(Event):

  def __init__(self, character, colors):
    self.character = character
    self.colors = colors
    self.shuffled = False
    self.card = None

  def resolve(self, state):
    while True:
      card = state.gate_cards.popleft()
      if card.colors & self.colors:
        break
      state.gate_cards.append(card)
      if card.name == "ShuffleGate":
        random.shuffle(state.gate_cards)
        self.shuffled = True
    self.card = card

  def is_resolved(self):
    return self.card is not None

  def start_str(self):
    return f"{self.character.name} must draw a " + " or ".join(self.colors) + " gate card"

  def finish_str(self):
    if self.shuffled:
      return f"{self.character.name} shuffled the deck and then drew {self.card.name}"
    return f"{self.character.name} drew {self.card.name}"


class DrawSpecific(Event):

  def __init__(self, character, deck, item_name):
    assert deck in {"common", "unique", "spells", "skills", "allies"}
    self.character = character
    self.deck = deck
    self.item_name = item_name
    self.received = None

  def resolve(self, state):
    deck = getattr(state, self.deck)
    for item in deck:
      if item.name == self.item_name:
        deck.remove(item)
        self.character.possessions.append(item)
        self.received = True
        # TODO: Shuffle the deck after drawing the item
        break
    else:
      self.received = False

  def is_resolved(self):
    return self.received is not None

  def start_str(self):
    return self.character.name + " searches the " + self.deck + " deck for a " + self.item_name

  def finish_str(self):
    if self.received:
      return self.character.name + " drew a " + self.item_name + " from the " + self.deck + " deck"
    return "There were no " + self.item_name + "s left in the " + self.deck + " deck"


class ExhaustAsset(Event):

  def __init__(self, character, item):
    assert item in character.possessions
    self.character = character
    self.item = item
    self.exhausted = None

  def resolve(self, state):
    if self.item not in self.character.possessions:
      self.exhausted = False
      return
    self.item._exhausted = True  # pylint: disable=protected-access
    self.exhausted = True

  def is_resolved(self):
    return self.exhausted is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.exhausted:
      return ""
    return f"{self.character.name} exhausted their {self.item.name}"


class RefreshAsset(Event):

  def __init__(self, character, item):
    assert item in character.possessions
    self.character = character
    self.item = item
    self.refreshed = None

  def resolve(self, state):
    if self.item not in self.character.possessions:
      self.refreshed = False
      return
    self.item._exhausted = False  # pylint: disable=protected-access
    self.refreshed = True

  def is_resolved(self):
    return self.refreshed is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.refreshed:
      return ""
    return f"{self.character.name} refreshed their {self.item.name}"


class RefreshAssets(Event):

  def __init__(self, character):
    self.character = character
    self.refreshes: Optional[List[Event]] = None
    self.idx = 0

  def resolve(self, state):
    if self.refreshes is None:
      to_refresh = [asset for asset in self.character.possessions if asset.exhausted]
      self.refreshes = [RefreshAsset(self.character, asset) for asset in to_refresh]
    while self.idx < len(self.refreshes):
      if not self.refreshes[self.idx].is_done():
        state.event_stack.append(self.refreshes[self.idx])
        return
      self.idx += 1

  def is_resolved(self):
    return self.refreshes is not None and all(refresh.is_done() for refresh in self.refreshes)

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class ActivateItem(Event):

  def __init__(self, character, item):
    assert item in character.possessions
    self.character = character
    self.item = item
    self.activated = None

  def resolve(self, state):
    if self.item not in self.character.possessions:
      self.activated = False
      return
    self.item._active = True  # pylint: disable=protected-access
    if hasattr(self.item, "activate"):
      self.item.activate()
    self.activated = True

  def is_resolved(self):
    return self.activated is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.activated:
      return ""
    return f"{self.character.name} is using their {self.item.name}"


class ActivateChosenItems(Event):

  def __init__(self, character, item_choice):
    self.character = character
    self.item_choice = item_choice
    self.activations: Optional[List[Event]] = None
    self.idx = 0

  def resolve(self, state):
    assert self.item_choice.is_done()
    if self.item_choice.is_cancelled():
      self.cancelled = True
      return

    if self.activations is None:
      self.activations = [ActivateItem(self.character, item) for item in self.item_choice.chosen]
    while self.idx < len(self.activations):
      if not self.activations[self.idx].is_done():
        state.event_stack.append(self.activations[self.idx])
        return
      self.idx += 1

  def is_resolved(self):
    return self.item_choice.is_resolved() and self.idx == len(self.item_choice.chosen)

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class DeactivateItem(Event):

  def __init__(self, character, item):
    assert item in character.possessions
    self.character = character
    self.item = item
    self.deactivated = None

  def resolve(self, state):
    if self.item not in self.character.possessions:
      self.deactivated = False
      return
    self.item._active = False  # pylint: disable=protected-access
    if hasattr(self.item, "deactivate"):
      self.item.deactivate()
    self.deactivated = True

  def is_resolved(self):
    return self.deactivated is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class DeactivateItems(Event):

  def __init__(self, character):
    self.character = character
    self.deactivations: Optional[List[Event]] = None
    self.idx = 0

  def resolve(self, state):
    if self.deactivations is None:
      self.deactivations = [
          DeactivateItem(self.character, item) for item in self.character.possessions
          if getattr(item, "deck", None) in {"common", "unique"} and item.active
      ]

    while self.idx < len(self.deactivations):
      if not self.deactivations[self.idx].is_done():
        state.event_stack.append(self.deactivations[self.idx])
        return
      self.idx += 1

  def is_resolved(self):
    return self.deactivations is not None and all(event.is_done() for event in self.deactivations)

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class CastSpell(Event):

  def __init__(self, character, spell, choice=None):
    assert spell in character.possessions
    self.character = character
    self.spell = spell
    self.choice: Optional[SpendMixin] = choice
    self.exhaust: Event = ExhaustAsset(character, spell)
    self.check: Optional[Event] = None
    self.activation: Optional[Event] = None
    self.success = None
    self.fail_message = ""

  def resolve(self, state):
    if self.spell not in self.character.possessions:
      self.success = False
      self.fail_message = "(Not in possessions?)"
      return

    if self.choice is None:
      spend = values.ExactSpendPrerequisite({"sanity": self.spell.sanity_cost})
      self.choice = SpendChoice(
          self.character, f"Cast {self.spell.name}", ["Cast", "Cancel"], spends=[spend, None],
      )

    if not self.choice.is_done():
      state.event_stack.append(self.choice)
      return

    if self.choice.is_cancelled() or getattr(self.choice, "choice", None) == "Cancel":
      self.cancelled = True
      return

    self.spell.in_use = True
    self.spell.deactivatable = False
    self.spell.choice = self.choice
    if not self.check:
      self.check = Check(self.character, "spell", self.spell.get_difficulty(state))
      state.event_stack.append(self.check)
      return
    assert self.check.is_done()

    if not self.exhaust.is_done():
      state.event_stack.append(self.exhaust)
      return

    if (self.check.successes or 0) < self.spell.get_required_successes(state):
      self.success = False
      self.fail_message = f"({self.check.successes} < {self.spell.get_required_successes(state)})"
      return

    self.success = True
    if not self.activation:
      self.activation = self.spell.get_cast_event(self.character, state)
      state.event_stack.append(self.activation)
      return

  def is_resolved(self):
    if self.success is False:
      return True
    return self.success is not None and self.activation.is_done()

  def start_str(self):
    return f"{self.character.name} is casting {self.spell.name}"

  def finish_str(self):
    if self.success:
      return f"{self.character.name} successfully cast {self.spell.name}"
    return f"{self.character.name} failed to cast {self.spell.name} {self.fail_message}"


class MarkDeactivatable(Event):

  def __init__(self, character, spell):
    assert spell in character.possessions
    self.character = character
    self.spell = spell
    self.done = False

  def resolve(self, state):
    self.spell.deactivatable = True
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class DeactivateSpell(Event):

  def __init__(self, character, spell):
    assert spell in character.possessions
    self.character = character
    self.spell = spell
    self.done = False

  def resolve(self, state):
    self.spell._active = False  # pylint: disable=protected-access
    self.spell.in_use = False
    self.spell.deactivatable = False
    if hasattr(self.spell, "deactivate"):
      self.spell.deactivate()
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.spell.name} deactivated"


class DeactivateSpells(Event):

  def __init__(self, character):
    self.character = character
    self.deactivations: Optional[List[Event]] = None
    self.idx = 0

  def resolve(self, state):
    if self.deactivations is None:
      self.deactivations = [
          DeactivateSpell(self.character, spell) for spell in self.character.possessions
          if getattr(spell, "deck", None) == "spells" and spell.in_use
      ]
    while self.idx < len(self.deactivations):
      if not self.deactivations[self.idx].is_done():
        state.event_stack.append(self.deactivations[self.idx])
        return
      self.idx += 1

  def is_resolved(self):
    return self.deactivations is not None and all(event.is_done() for event in self.deactivations)

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


def LoseItems(character, count, prompt=None, decks=None, item_type="item"):
  prompt = prompt or "Choose items to lose"
  choice = ItemLossChoice(character, prompt, count, decks=decks, item_type=item_type)
  loss = DiscardSpecific(character, choice)
  return Sequence([choice, loss], character)


class DiscardSpecific(Event):

  def __init__(self, character, items):
    self.character = character
    self.items = items
    self.discarded = None

  def resolve(self, state):
    if isinstance(self.items, ItemChoice):
      assert self.items.is_done()
      if self.items.is_cancelled():
        self.cancelled = True
        return
      self.items = self.items.chosen

    self.discarded = []
    for item in self.items:
      if item not in self.character.possessions:
        continue
      self.character.possessions.remove(item)
      getattr(state, item.deck).append(item)
      self.discarded.append(item)

  def is_resolved(self):
    return self.discarded is not None

  def start_str(self):
    if isinstance(self.items, ItemChoice):
      return f"{self.character.name} will discard the chosen items"
    return f"{self.character.name} will discard " + ", ".join(item.name for item in self.items)

  def finish_str(self):
    if not self.discarded:
      return f"{self.character.name} did not have items to discard"
    return f"{self.character.name} discarded " + ", ".join(item.name for item in self.discarded)


class DiscardNamed(Event):

  def __init__(self, character, item_name):
    self.character = character
    self.item_name = item_name
    self.discarded = None

  def resolve(self, state):
    for item in self.character.possessions:
      if item.name == self.item_name:
        self.character.possessions.remove(item)
        deck = getattr(state, item.deck)
        deck.append(item)
        self.discarded = item
        return
    self.discarded = False

  def is_resolved(self):
    return self.discarded is not None

  def start_str(self):
    return f"{self.character.name} will discard a {self.item_name}"

  def finish_str(self):
    if not self.discarded:
      return f"{self.character.name} did not have a {self.item_name} to discard"
    return f"{self.character.name} discarded their {self.item_name}"


class ReturnMonsterFromBoard(Event):  # TODO: merge the three return monster to cup events

  def __init__(self, character, monster):
    self.character = character
    self.monster = monster
    self.returned = False

  def resolve(self, state):
    if not isinstance(self.monster.place, (places.Outskirts, places.CityPlace)):
      self.cancelled = True
      return
    self.monster.place = state.monster_cup
    self.returned = True

  def is_resolved(self):
    return self.returned

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.monster.name} was returned to the cup"


class ReturnMonsterToCup(Event):

  def __init__(self, character, handle):
    self.character = character
    self.handle = handle
    self.returned = None

  def resolve(self, state):
    monsters = [monster for monster in self.character.trophies if monster.handle == self.handle]
    self.returned = []
    for monster in monsters:
      self.character.trophies.remove(monster)
      monster.place = state.monster_cup
      self.returned.append(monster.name)

  def is_resolved(self):
    return self.returned is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.character.name} returned " + ", ".join(self.returned) + " to the cup"


class ReturnGateToStack(Event):

  def __init__(self, character, handle):
    self.character = character
    self.handle = handle
    self.returned = None

  def resolve(self, state):
    gates = [gate for gate in self.character.trophies if gate.handle == self.handle]
    self.returned = []
    for gate in gates:
      self.character.trophies.remove(gate)
      state.gates.append(gate)
      self.returned.append(gate.name)

  def is_resolved(self):
    return self.returned is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.character.name} returned " + ", ".join(self.returned)


class Check(Event):

  def __init__(self, character, check_type, modifier, attributes=None):
    # TODO: assert on check type
    self.character = character
    self.check_type = check_type
    self.modifier = modifier
    self.attributes = attributes
    self.dice: Optional[Event] = None
    self.roll = None
    self.successes = None
    self.spend: Optional[SpendChoice] = None
    self.bonus_dice: Optional[Event] = None
    self.done = False

  def resolve(self, state):
    if self.dice is None:
      if self.check_type == "combat":
        num_dice = self.character.combat(state, self.attributes) + self.modifier
      else:
        num_dice = getattr(self.character, self.check_type)(state) + self.modifier
      self.dice = DiceRoll(self.character, num_dice)
      state.event_stack.append(self.dice)
      return

    if self.dice.is_cancelled():
      self.cancelled = True
      return

    if self.roll is None:
      self.roll = self.dice.roll[:]
      self.count_successes()

    if self.bonus_dice is not None:
      if not self.bonus_dice.is_cancelled():
        self.roll.extend(self.bonus_dice.roll[:])
        self.count_successes()
      self.bonus_dice = None

    if self.spend is None:
      if state.test_mode and self.character.clues == 0:
        self.done = True
        return
      spend = values.ExactSpendPrerequisite({"clues": 1})
      self.spend = SpendChoice(
          self.character, "Spend Clues?", ["Spend", "Done"], spends=[spend, None],
      )
      state.event_stack.append(self.spend)
      return

    if self.spend.is_cancelled() or self.spend.choice == "Done":
      self.done = True
      return

    # self.spend finished, and self.bonus_dice is None
    self.spend = None
    self.bonus_dice = BonusDiceRoll(self.character, 1)
    state.event_stack.append(self.bonus_dice)

  @property
  def count(self):
    if self.roll is not None:
      return len(self.roll)
    if self.dice is None:
      return None
    return self.dice.count

  def count_successes(self):
    self.successes = self.character.count_successes(self.roll, self.check_type)

  def is_resolved(self):
    return self.done

  def check_str(self):
    return f"{self.check_type} {self.modifier:+d} check"

  def start_str(self):
    return self.character.name + " makes a " + self.check_str()

  def finish_str(self):
    if not self.successes:
      return f"{self.character.name} failed a {self.check_str()}"
    return f"{self.character.name} had {self.successes} successes on a {self.check_str()}"


class AddExtraDie(Event):

  def __init__(self, character, event):
    assert isinstance(event, BonusDiceRoll)
    self.character = character
    self.dice: BonusDiceRoll = event
    self.done = False

  def resolve(self, state):
    assert not self.dice.is_done()
    self.dice.count += 1
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name} gets an extra die from their skill"

  def finish_str(self):
    return ""


class RerollCheck(Event):

  def __init__(self, character, check):
    assert isinstance(check, Check)
    self.character = character
    self.check: Check = check
    self.dice: Optional[DiceRoll] = None
    self.done = False

  def resolve(self, state):
    if self.dice is None:
      self.dice = DiceRoll(self.character, len(self.check.roll))
      state.event_stack.append(self.dice)
      return

    if self.dice.is_cancelled():
      self.cancelled = True
      return

    self.check.roll = self.dice.roll[:]
    self.check.count_successes()
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name} rerolls a {self.check.check_type} check"

  def finish_str(self):
    return ""


class Conditional(Event):

  def __init__(self, character, condition, attribute, result_map):
    assert isinstance(condition, values.Value) or hasattr(condition, attribute)
    assert all(isinstance(key, int) for key in result_map)
    assert min(result_map.keys()) == 0
    self.character = character
    self.condition: Union[values.Value, Event] = condition
    self.attribute = attribute
    self.result_map: Dict[int, Event] = result_map
    self.result: Optional[Event] = None

  def resolve(self, state):
    assert isinstance(self.condition, values.Value) or self.condition.is_done()
    if not isinstance(self.condition, values.Value) and self.condition.is_cancelled():
      self.cancelled = True
      return

    if self.result is not None:
      if not self.result.is_done():  # NOTE: this should never happen
        state.event_stack.append(self.result)
        return
      return

    if isinstance(self.condition, values.Value):
      value = self.condition.value(state)
    else:
      value = getattr(self.condition, self.attribute)

    for min_result in reversed(sorted(self.result_map)):
      if value >= min_result:
        self.result = self.result_map[min_result]
        state.event_stack.append(self.result)
        return
    raise RuntimeError(f"result map without result for {value}: {self.result_map}")

  def is_resolved(self):
    return self.result is not None and self.result.is_done()

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


def PassFail(character, condition, pass_result, fail_result):
  outcome = Conditional(character, condition, "successes", {0: fail_result, 1: pass_result})
  if isinstance(condition, values.Value):
    return outcome
  return Sequence([condition, outcome], character)


class Arrested(Sequence):

  def __init__(self, character):
    super().__init__([
        ForceMovement(character, "Police"), LoseTurn(character),
        Loss(character, {"dollars": values.Calculation(character, "dollars", operator.floordiv, 2)})
    ], character)


class MultipleChoice(ChoiceEvent):

  def __init__(self, character, prompt, choices, prereqs=None, annotations=None):
    if prereqs is None:
      prereqs = [None] * len(choices)
    assert len(choices) == len(prereqs)
    assert all(prereq is None or isinstance(prereq, values.Value) for prereq in prereqs)
    self.character = character
    self._prompt = prompt
    self.choices = choices
    self.prereqs: List[Optional[values.Value]] = prereqs
    self._annotations = annotations
    self.invalid_choices = []
    self.choice = None

  def compute_choices(self, state):
    # Any unsatisfied prerequisite means that choice is invalid.
    self.invalid_choices.clear()
    for idx in range(len(self.choices)):
      if self.prereqs[idx] is not None and self.prereqs[idx].value(state) < 1:
        self.invalid_choices.append(idx)

  def resolve(self, state, choice=None):
    assert not self.is_resolved()
    self.validate_choice(choice)
    self.choice = choice

  def validate_choice(self, choice):
    assert choice in self.choices
    assert self.choices.index(choice) not in self.invalid_choices

  def is_resolved(self):
    return self.choice is not None

  def start_str(self):
    return f"{self.character.name} must choose one of " + ", ".join([str(c) for c in self.choices])

  def finish_str(self):
    return f"{self.character.name} chose {str(self.choice)}"

  def prompt(self):
    return self._prompt

  def annotations(self, state):
    return self._annotations

  @property
  def choice_index(self):
    if self.choice is None:
      return None
    return self.choices.index(self.choice)


class SpendMixin:

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.spend_map = collections.defaultdict(dict)  # Map from type -> map from handle: amount

  def resolve(self, state, choice=None):
    super().resolve(state, choice)
    if self.is_cancelled():
      return
    if not self.is_resolved():  # For itemchoice, resolve() will be called multiple times.
      return
    # Spend the basic spendables.
    for spend_count in self.spend_map.values():
      for handle, count in spend_count.items():
        if handle in {"stamina", "sanity", "dollars", "clues"}:
          setattr(self.character, handle, getattr(self.character, handle) - count)
    # Get the set of items that were spent.
    handles = self.spent_handles() - {"stamina", "sanity", "dollars", "clues"}
    # Add spend events in a sequence to the stack. NOTE:
    # - this happens only after all validation (which happens in super().resolve(...). this means
    #   that at the time these are added to the stack, the choice is already resolved.
    # - resolve is never called inside the event loop for choice events. if it were called
    #   inside the event loop, this event would be marked as resolved but still have appended an
    #   event to the stack, confusing the event loop. instead, the spend sequence gets picked up
    #   on the next entry into the resolve loop.
    spend_seq = [self.character.get_spend_event(handle) for handle in handles]
    state.event_stack.append(Sequence(spend_seq, self.character))

  def spent_handles(self):
    # Items that have multiple spend types should only be counted once.
    handles = set()
    for spend_count in self.spend_map.values():
      handles |= spend_count.keys()
    return handles

  def spend_handle(self, handle, spend_map):
    assert not spend_map.keys() - self.spendable
    assert handle not in self.spent_handles()
    for key, val in spend_map.items():
      self.spend_map[key][handle] = val

  def unspend_handle(self, handle):
    for spend_count in self.spend_map.values():
      if handle in spend_count:
        del spend_count[handle]

  def spend(self, spend_type):
    assert spend_type in self.spendable & {"stamina", "sanity", "dollars", "clues"}
    already_spent = self.spend_map[spend_type].get(spend_type, 0)
    assert getattr(self.character, spend_type) - already_spent > 0
    self.spend_map[spend_type][spend_type] = already_spent + 1

  def unspend(self, spend_type):
    assert spend_type in self.spend_map.keys() & {"stamina", "sanity", "dollars", "clues"}
    already_spent = self.spend_map[spend_type].get(spend_type, 0)
    assert already_spent >= 1
    self.spend_map[spend_type][spend_type] -= 1


class SpendItemChoiceMixin(SpendMixin):

  def __init__(self, *args, **kwargs):
    spend = kwargs.pop("spend")
    super().__init__(*args, **kwargs)
    assert isinstance(spend, values.SpendValue)
    self.spend_prereq = spend
    self.spendable = spend.spend_types()
    self.remaining_spend = True
    spend.spend_event = self

  def compute_choices(self, state):
    super().compute_choices(state)
    self.remaining_spend = self.spend_prereq.remaining_spend(state) or False

  def resolve(self, state, choice=None):
    if choice == "done" and not self.chosen:
      self.cancelled = True
      return
    super().resolve(state, choice)

  def validate_choice(self, state, chosen, final):
    if len(chosen) > 0:
      assert not self.spend_prereq.remaining_spend(state)
    super().validate_choice(state, chosen, final)

  def annotations(self, state):  # pylint: disable=unused-argument
    return None


class SpendMultiChoiceMixin(SpendMixin):

  def __init__(self, *args, **kwargs):
    spends = kwargs.pop("spends")
    super().__init__(*args, **kwargs)
    assert len(spends) == len(self.choices)
    assert any(value is None for value in spends)  # must have at least one choice w/ no spending

    self.spends = []
    self.spendable = set()
    self.remaining_spend = [value is not None for value in spends]
    for spend in spends:
      spend = spend or values.SpendNothing()
      assert isinstance(spend, values.SpendValue)
      self.spends.append(spend)
      spend.spend_event = self
      self.spendable |= spend.spend_types()

  def compute_choices(self, state):
    super().compute_choices(state)
    self.remaining_spend = [spend.remaining_spend(state) or False for spend in self.spends]

  def resolve(self, state, choice=None):
    assert choice in self.choices
    choice_idx = self.choices.index(choice)
    assert not self.remaining_spend[choice_idx]
    super().resolve(state, choice)

  def annotations(self, state):
    return [spend.annotation(state) for spend in self.spends]


class SpendChoice(SpendMultiChoiceMixin, MultipleChoice):
  pass


class Spend(Event):

  def __init__(self, character, spend_event, handle, spend_count):
    self.character = character
    self.spend_event: Event = spend_event
    self.handle = handle
    self.spend_count = spend_count
    self.done = False

  def resolve(self, state):
    self.spend_event.spend_handle(self.handle, self.spend_count)
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class Unspend(Event):

  def __init__(self, character, spend_event, handle):
    self.character = character
    self.spend_event: Event = spend_event
    self.handle = handle
    self.done = False

  def resolve(self, state):
    self.spend_event.unspend_handle(self.handle)
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class ChangeMovementPoints(Event):

  def __init__(self, character, count):
    self.character = character
    self.count = count
    self.change = None

  def resolve(self, state):
    orig = self.character.movement_points
    self.character.movement_points += self.count
    self.character.movement_points = max(self.character.movement_points, 0)
    self.change = self.character.movement_points - orig

  def is_resolved(self):
    return self.change is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class ReadTome(Sequence):

  def __init__(self, events, character):
    super().__init__(events, character)


def BinaryChoice(
        character, prompt, first_choice, second_choice, first_event, second_event, prereq=None):
  choice = MultipleChoice(character, prompt, [first_choice, second_choice], [prereq, None])
  sequence = [
      choice, Conditional(character, choice, "choice_index", {0: first_event, 1: second_event})]
  return Sequence(sequence, character)


def BinarySpend(
    character, spend_type, quantity, prompt, rich_choice, poor_choice, rich_event, poor_event=None,
):
  poor_event = poor_event or Nothing()
  if spend_type == "toughness":
    spend = values.ToughnessSpend(quantity)
  else:
    spend = values.ExactSpendPrerequisite({spend_type: quantity})
  choice = SpendChoice(character, prompt, [rich_choice, poor_choice], spends=[spend, None])
  cond = Conditional(character, choice, "choice_index", {0: rich_event, 1: poor_event})
  return Sequence([choice, cond], character)


class ItemChoice(ChoiceEvent):

  def __init__(self, character, prompt, decks=None, item_type="item"):
    self.character = character
    self._prompt = prompt
    self.choices = None
    self.chosen = []
    if decks is None:
      decks = {"spells", "common", "unique", "skills", "allies"}  # TODO: keep in sync with assets
    assert not decks - {"spells", "common", "unique", "skills", "allies"}, f"invalid decks {decks}"
    self.decks = decks
    assert item_type in {None, "item", "weapon", "tome"}
    self.item_type = item_type
    self.done = False

  def resolve(self, state, choice=None):
    assert isinstance(choice, str)
    if choice == "done":
      self.validate_choice(state, self.chosen, final=True)
      self.done = True
      return

    # If the character is trying to deselect an item, remove it from the list.
    chosen_copy = [pos for pos in self.chosen if pos.handle != choice]
    if len(chosen_copy) >= len(self.chosen):  # Otherwise, add it to the list.
      chosen_copy += [pos for pos in self.character.possessions if pos.handle == choice]
      assert len(chosen_copy) > len(self.chosen)

    self.validate_choice(state, chosen_copy, final=False)
    self.chosen = chosen_copy

  def validate_choice(self, state, chosen, final):  # pylint: disable=unused-argument
    assert all(pos.handle in self.choices for pos in chosen)

  def compute_choices(self, state):
    self.choices = [
        pos.handle for pos in self.character.possessions
        if (getattr(pos, "deck", None) in self.decks) and self._matches_type(pos)
    ]

  def _matches_type(self, pos):
    if self.item_type is None:
      return True
    if self.item_type != "item":
      return getattr(pos, "item_type", None) == self.item_type
    # TODO: deputy's revolver, patrol wagon, rail pass
    return getattr(pos, "deck", None) in {"spells", "common", "unique"}

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name} must " + self.prompt()

  def finish_str(self):
    return f"{self.character.name} chose some stuff"

  def prompt(self):
    return self._prompt

  @property
  def choice_count(self):
    return len(self.chosen) if self.chosen else 0


class CombatChoice(ItemChoice):

  def __init__(self, character, prompt, combat_round=None):
    super().__init__(character, prompt, decks=None, item_type="weapon")
    self.combat_round = combat_round

  def validate_choice(self, state, chosen, final):
    super().validate_choice(state, chosen, final)
    for pos in chosen:
      assert getattr(pos, "hands", None) is not None
      assert getattr(pos, "deck", None) != "spells"
    hands_used = sum([pos.hands for pos in chosen])
    assert hands_used <= self.character.hands_available()

  def hands_used(self):
    return sum([pos.hands for pos in self.chosen])


class ItemCountChoice(ItemChoice):

  def __init__(self, character, prompt, count, min_count=None, decks=None, item_type="item"):
    super().__init__(character, prompt, decks=decks, item_type=item_type)
    self.count = count
    self.min_count = count if min_count is None else min_count

  def validate_choice(self, state, chosen, final):
    super().validate_choice(state, chosen, final)
    min_count = self.min_count
    if isinstance(self.min_count, values.Value):
      min_count = self.min_count.value(state)
    max_count = self.count
    if isinstance(self.count, values.Value):
      max_count = self.count.value(state)
    if final:
      assert min_count <= len(chosen) <= max_count
    else:
      assert len(chosen) <= max_count


class ItemLossChoice(ItemChoice):

  def __init__(self, character, prompt, count, decks=None, item_type="item"):
    super().__init__(character, prompt, decks=decks, item_type=item_type)
    self.count = count

  def validate_choice(self, state, chosen, final=False):
    super().validate_choice(state, chosen, final)
    count = self.count.value(state) if isinstance(self.count, values.Value) else self.count
    assert len(chosen) <= count
    if not final:
      return

    if len(chosen) == count:
      return
    # If the user has not chosen as many items as they need to lose, go through all of their items
    # and validate that every viable option is either (a) not losable or (b) already chosen.
    for pos in self.character.possessions:
      if pos.handle not in self.choices:
        continue
      assert pos in chosen or not getattr(pos, "losable", True)


class SinglePhysicalWeaponChoice(SpendItemChoiceMixin, ItemCountChoice):

  def __init__(self, character, prompt, spend):
    super().__init__(character, prompt, 1, min_count=0, item_type="weapon", spend=spend)

  def compute_choices(self, state):
    super().compute_choices(state)
    self.choices = [
        pos.handle for pos in self.character.possessions
        if pos.handle in self.choices
        and (pos.active_bonuses["physical"] or pos.passive_bonuses["physical"])
    ]


class CardChoice(MultipleChoice):

  def __init__(self, *args, **kwargs):
    self.sort_uniq = kwargs.pop("sort_uniq", False)
    super().__init__(*args, **kwargs)


class CardSpendChoice(SpendMultiChoiceMixin, CardChoice):
  pass


class MapChoice(ChoiceEvent, metaclass=abc.ABCMeta):

  def __init__(self, character, prompt, none_choice=None):
    self.character = character
    self._prompt = prompt
    self.choices = None
    self.none_choice = none_choice
    self.choice = None

  @abc.abstractmethod
  def compute_choices(self, state):
    raise NotImplementedError

  def resolve(self, state, choice=None):
    if choice is not None and choice == self.none_choice:
      self.cancelled = True
      return
    assert choice in self.choices
    self.choice = choice

  def is_resolved(self):
    # It is possible to have no choices (e.g. with "gate" when there are no gates on the board).
    # In the case where there are no choices, the choice reader must account for it.
    # pylint: disable=use-implicit-booleaness-not-comparison
    return self.choice is not None or self.choices == []

  def prompt(self):
    return self._prompt


class PlaceChoice(MapChoice):

  VALID_FILTERS = {"streets", "locations", "open", "closed"}

  def __init__(self, character, prompt, choices=None, choice_filters=None, none_choice=None):
    assert choice_filters is None or choices is None
    super().__init__(character, prompt, none_choice=none_choice)
    if choices:
      self.fixed_choices = choices
      self.choice_filters = None
    else:
      choice_filters = choice_filters or set()
      assert choice_filters <= self.VALID_FILTERS
      if not choice_filters & {"streets", "locations"}:
        choice_filters |= {"streets", "locations"}
      if not choice_filters & {"open", "closed"}:
        choice_filters |= {"open"}
      self.fixed_choices = None
      self.choice_filters = choice_filters

  def compute_choices(self, state):
    if self.fixed_choices is not None:
      self.choices = self.fixed_choices
      return
    self.choices = []
    for name, place in state.places.items():
      if not isinstance(place, (places.Location, places.Street)):
        continue
      if "locations" not in self.choice_filters and isinstance(place, places.Location):
        continue
      if "streets" not in self.choice_filters and isinstance(place, places.Street):
        continue
      if "closed" not in self.choice_filters and getattr(place, "closed", False):
        continue
      if "open" not in self.choice_filters and not getattr(place, "closed", False):
        continue
      self.choices.append(name)

  def start_str(self):
    if self.choices:
      return f"{self.character.name} must choose one of " + ", ".join(self.choices)
    return ""  # TODO

  def finish_str(self):
    if self.choice is None:
      return f"there were no valid choices, or {self.character.name} chose none"  # TODO
    return f"{self.character.name} chose {self.choice}"


class GateChoice(MapChoice):

  def __init__(self, character, prompt, gate_name=None, none_choice=None, annotation=None):
    super().__init__(character, prompt, none_choice=none_choice)
    self.gate_name = gate_name
    self.annotation = annotation

  def compute_choices(self, state):
    self.choices = []
    for name, place in state.places.items():
      if not isinstance(place, (places.Location, places.Street)):
        continue
      if getattr(place, "gate", None) is not None:
        if place.gate.name == self.gate_name or self.gate_name is None:
          self.choices.append(name)
    if len(self.choices) == 1 and self.none_choice is None:
      self.choice = self.choices[0]

  def start_str(self):
    if self.gate_name is not None:
      return f"{self.character.name} must choose a gate to {self.gate_name}"
    return f"{self.character.name} must choose a gate"

  def finish_str(self):
    if self.choice is None:
      return f"there were no open gates to {self.gate_name}"  # TODO
    return f"{self.character.name} chose the gate at {self.choice}"

  def annotations(self, state):
    if self.annotation and self.choices is not None:
      return [self.annotation for _ in self.choices]
    return None


class MonsterOnBoardChoice(ChoiceEvent):

  def __init__(self, character, prompt):
    self.character = character
    self._prompt = prompt
    self.choices = []
    self.chosen = None

  def compute_choices(self, state):
    # TODO: other ways of narrowing choices (e.g. streets only)
    self.choices = [
        mon.handle for mon in state.monsters
        if isinstance(mon.place, (places.CityPlace, places.Outskirts))
    ]
    if not self.choices:
      self.cancelled = True

  def resolve(self, state, choice=None):
    assert choice in self.choices
    chosen = [mon for mon in state.monsters if mon.handle == choice]
    assert len(chosen) == 1
    self.chosen = chosen[0]

  def is_resolved(self):
    return self.chosen is not None

  def start_str(self):
    pass

  def finish_str(self):
    pass

  def prompt(self):
    return self._prompt


class EvadeOrFightAll(Sequence):

  def __init__(self, character, monsters):
    self.monsters = monsters
    self.character = character
    super().__init__(
        [
            EvadeOrCombat(character, monster)
            for monster in monsters
            if monster not in character.avoid_monsters
        ], character)

  def start_str(self):
    return f"{self.character.name} must evade or fight all of: " \
           + ", ".join(mon.name for mon in self.monsters)


# TODO: let the player choose the order in which they fight/evade the monsters
# class EvadeOrFightAll(Event):
#
#   def __init__(self, character, monsters):
#     assert monsters
#     self.character = character
#     self.monsters = monsters
#     self.result = []
#
#   def resolve(self, state):
#     if not self.result:
#       self.add_choice(state, self.monsters[0])
#       return False
#     if self.result[-1].is_resolved():
#       if len(self.result) == len(self.monsters):
#         return True
#       self.add_choice(state, self.monsters[len(self.result)])
#       return False
#     return True
#
#   def add_choice(self, state, monster):
#     choice = EvadeOrCombat(self.character, monster)
#     self.result.append(choice)
#     state.event_stack.append(choice)
#
#   def is_resolved(self):
#     return len(self.result) == len(self.monsters) and self.result[-1].is_resolved()
#
#   def start_str(self):
#     return ""
#
#   def finish_str(self):
#     return ""


class EvadeOrCombat(Event):

  def __init__(self, character, monster):
    self.character = character
    self.monster = monster
    self.combat: Combat = Combat(character, monster)
    self.evade: EvadeRound = EvadeRound(character, monster)
    prompt = f"Fight the {monster.name} or evade it?"
    self.choice: Event = BinaryChoice(character, prompt, "Fight", "Evade", self.combat, self.evade)
    self.choice.events[0].monster = monster

  def resolve(self, state):
    if not self.choice.is_done():
      state.event_stack.append(self.choice)
      return
    if self.evade.is_resolved() and self.evade.evaded:
      return
    if not self.combat.is_done():
      state.event_stack.append(self.combat)
      return

  def is_resolved(self):
    return self.combat.is_done() or (self.evade.is_resolved() and self.evade.evaded)

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class Combat(Event):

  def __init__(self, character, monster):
    self.character = character
    self.monster = monster
    self.horror: Optional[Event] = None
    self.sanity_loss: Optional[Event] = None
    self.choice: Optional[ChoiceEvent] = None
    self.evade: Optional[EvadeRound] = None
    self.combat: Optional[CombatRound] = None
    self.done = False

  def resolve(self, state):
    # Horror check
    if self.monster.difficulty("horror", state, self.character) is not None and self.horror is None:
      self.horror = Check(
          self.character, "horror", self.monster.difficulty("horror", state, self.character))
      self.sanity_loss = Loss(
          self.character, {"sanity": self.monster.damage("horror", state, self.character)})
    if self.horror is not None:
      if not self.horror.is_done():
        state.event_stack.append(self.horror)
        return
      if not self.sanity_loss.is_done():
        # Failed horror check
        if (self.horror.successes or 0) < 1:
          state.event_stack.append(self.sanity_loss)
          return
        # Nightmarish for successful horror check
        nightmarish = self.monster.has_attribute("nightmarish", state, self.character)
        if self.horror.successes >= 1 and nightmarish:
          self.sanity_loss = Loss(
              self.character, {"sanity": self.monster.bypass_damage("horror", state)})
          state.event_stack.append(self.sanity_loss)
          return

    # Combat or flee choice.
    self.combat = CombatRound(self.character, self.monster)
    self.evade = EvadeRound(self.character, self.monster)
    no_ambush = values.NoAmbushPrerequisite(self.monster, self.character)
    prompt = f"Fight the {self.monster.name} or flee from it?"
    self.choice = BinaryChoice(
        self.character, prompt, "Flee", "Fight", self.evade, self.combat, no_ambush)
    self.choice.events[0].monster = self.monster  # TODO: this is hacky
    state.event_stack.append(self.choice)

  def is_resolved(self):
    if self.evade is None or self.combat is None:
      return False
    return self.evade.evaded or self.combat.defeated

  def start_str(self):
    return f"{self.character.name} entered combat with a {self.monster.name}"

  def finish_str(self):
    return ""


class EvadeRound(Event):

  def __init__(self, character, monster):
    self.character = character
    self.monster = monster
    self.check: Optional[Check] = None
    self.damage: Optional[Event] = None
    self.evaded = None

  def resolve(self, state):
    if self.evaded is not None:
      return
    if self.check is None:
      self.check = Check(
          self.character, "evade", self.monster.difficulty("evade", state, self.character))
    if not self.check.is_done():
      state.event_stack.append(self.check)
      return
    if not self.check.is_cancelled() and self.check.successes >= 1:
      self.evaded = True
      self.character.avoid_monsters.append(self.monster)
      return
    self.character.movement_points = 0
    self.evaded = False
    self.damage = Loss(
        self.character, {"stamina": self.monster.damage("combat", state, self.character)})
    state.event_stack.append(self.damage)

  def is_resolved(self):
    return self.evaded or (self.damage is not None and self.damage.is_done())

  def start_str(self):
    return f"{self.character.name} attempted to flee from {self.monster.name}"

  def finish_str(self):
    if self.evaded:
      return f"{self.character.name} evaded a {self.monster.name}"
    return (f"{self.character.name} did not evade the {self.monster.name}"
            + " and lost any remaining movement")


class CombatRound(Event):

  def __init__(self, character, monster):
    self.character = character
    self.monster = monster
    self.choice: Event = CombatChoice(
        character, f"Choose weapons to fight the {monster.name}", combat_round=self
    )
    self.choice.monster = self.monster
    self.activate: Optional[Event] = None
    self.check: Optional[Check] = None
    self.defeated = None
    self.take_trophy: Optional[Event] = None
    self.damage: Optional[Event] = None
    self.pass_combat: Optional[Event] = None
    self.done = False

  def resolve(self, state):
    self.character.movement_points = 0
    if not self.choice.is_done():
      state.event_stack.append(self.choice)
      return
    if len(self.choice.choices or []) > 0 and self.activate is None:
      self.activate = ActivateChosenItems(self.character, self.choice)
      state.event_stack.append(self.activate)
      return

    if self.check is None:
      attrs = self.monster.attributes(state, self.character)
      self.check = Check(
          self.character, "combat", self.monster.difficulty("combat", state, self.character), attrs)
    if not self.check.is_done():
      state.event_stack.append(self.check)
      return

    if self.defeated is None:
      self.defeated = (self.check.successes or 0) >= self.monster.toughness(state, self.character)

    if not self.defeated:
      self.damage = Loss(
          self.character, {"stamina": self.monster.damage("combat", state, self.character)})
      state.event_stack.append(self.damage)
      return

    if self.defeated and not self.pass_combat:
      self.pass_combat = PassCombatRound(self)
      state.event_stack.append(self.pass_combat)
      return

    self.done = True

  def is_resolved(self):
    if self.defeated is None:
      return False
    if not self.defeated:
      return self.damage.is_done()
    return self.done

  def start_str(self):
    return f"{self.character.name} started a combat round against a {self.monster.name}"

  def finish_str(self):
    if self.defeated:
      return f"{self.character.name} defeated a {self.monster.name}"
    return f"{self.character.name} did not defeat the {self.monster.name}"


class PassCombatRound(Event):
  def __init__(
      self,
      combat_round,
      log_message="{char_name} passed a combat round against {monster_name}"
  ):
    self.combat_round = combat_round
    self.character = combat_round.character
    self.log_message = log_message.format(
        char_name=combat_round.character.name,
        monster_name=getattr(combat_round.monster, "name", "No Monster")
        # TODO: might look weird if no monster (e.g. Bank3)
    )
    self.take_trophy: Optional[Event] = None
    self.damage: Optional[Event] = None
    self.done = False

  def resolve(self, state):
    if self.combat_round.pass_combat is None:
      # Can happen if passing combat is the effect of a spell, e.g. Bind Monster
      self.combat_round.pass_combat = self
    self.combat_round.defeated = True
    if self.combat_round.choice is not None and not self.combat_round.choice.is_resolved():
      self.combat_round.choice.cancelled = True
    char = self.combat_round.character
    monster = self.combat_round.monster
    if self.take_trophy is None and monster is not None:
      self.take_trophy = TakeTrophy(char, monster)
      state.event_stack.append(self.take_trophy)
      return

    if monster.has_attribute("overwhelming", state, char) and self.damage is None:
      self.damage = Loss(
          char, {"stamina": monster.bypass_damage("combat", state)})
      state.event_stack.append(self.damage)
      return

    self.done = True

  def is_resolved(self) -> bool:
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return self.log_message


class TakeTrophy(Event):

  def __init__(self, character, monster):
    self.character = character
    self.monster = monster
    self.done = False

  def resolve(self, state):
    if isinstance(self.monster, MonsterOnBoardChoice):
      if self.monster.is_cancelled():
        self.cancelled = True
        return
      self.monster = self.monster.chosen
    self.monster.place = None
    self.character.trophies.append(self.monster)
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.character.name} took a {self.monster.name} as a trophy"


class Travel(Event):

  def __init__(self, character, world_name):
    self.character = character
    self.world_name = world_name
    self.done = False

  def resolve(self, state):
    self.character.place = state.places[self.world_name + "1"]
    self.character.explored = False  # just in case
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.character.name} moved to {self.world_name}"


class Return(Event):

  def __init__(self, character, world_name):
    self.character = character
    self.world_name = world_name
    self.return_choice: Optional[ChoiceEvent] = None
    self.lost: Optional[Event] = None
    self.returned = None

  def resolve(self, state):
    if self.return_choice is None:
      self.return_choice = GateChoice(
          self.character, "Choose a gate to return to", self.world_name, annotation="Return")
      state.event_stack.append(self.return_choice)
      return
    assert self.return_choice.is_done()

    if self.return_choice.is_cancelled() or self.return_choice.choice is None:  # Unable to return
      if self.lost is None:
        self.lost = LostInTimeAndSpace(self.character)
        state.event_stack.append(self.lost)
        return
      self.returned = False
      return
    self.character.place = state.places[self.return_choice.choice]
    self.character.explored = True
    self.returned = True

  def is_resolved(self):
    return self.returned is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.character.name} returned"


class PullThroughGate(Sequence):

  def __init__(self, chars, world_name):  # TODO: cleanup
    assert chars
    self.chars = chars
    self.world_name = world_name
    seq = []
    for char in chars:
      seq.extend([Travel(char, world_name), Delayed(char)])
    super().__init__(seq)

  def start_str(self):
    return f"{len(self.chars)} will be pulled through to {self.world_name}"


class GateCloseAttempt(Event):

  def __init__(self, character, location_name):
    self.character = character
    self.location_name = location_name
    self.choice: Optional[ChoiceEvent] = None
    self.check: Optional[Check] = None
    self.closed = None

  def resolve(self, state):
    if self.choice is None:
      self.choice = MultipleChoice(
          self.character, "Close the gate?", ["Close with fight", "Close with lore", "Don't close"])
      state.event_stack.append(self.choice)
      return

    assert self.choice.is_done()
    if self.choice.is_cancelled() or self.choice.choice == "Don't close":
      self.closed = False
      return

    if self.check is None:
      difficulty = state.places[self.location_name].gate.difficulty(state)
      attribute = "lore" if self.choice.choice == "Close with lore" else "fight"
      self.check = Check(self.character, attribute, difficulty)
      state.event_stack.append(self.check)
      return

    assert self.check.is_done()
    if self.check.is_cancelled() or not self.check.successes:
      self.closed = False
      return

    self.closed = CloseGate(self.character, self.location_name, can_take=True, can_seal=True)
    state.event_stack.append(self.closed)

  def is_resolved(self):
    if self.closed is False:
      return True
    if self.closed is None:
      return False
    return self.closed.is_done()

  def start_str(self):
    return ""

  def finish_str(self):
    if self.choice.is_cancelled() or self.choice.choice == "Don't close":
      return f"{self.character.name} chose not to close the gate at {self.location_name}"
    if not self.closed:
      return f"{self.character.name} failed to close the gate at {self.location_name}"
    return ""


class CloseGate(Event):

  def __init__(self, character, location_name, can_take, can_seal):
    self.character = character
    self.location_name: Union[MapChoice, str] = location_name
    self.gate = None
    self.can_take = can_take
    self.can_seal = can_seal
    self.return_monsters = None
    self.seal_choice: Optional[ChoiceEvent] = None
    self.sealed = None

  def resolve(self, state):
    if isinstance(self.location_name, MapChoice):
      if self.location_name.is_cancelled() or self.location_name.choice is None:
        self.cancelled = True
        return
      self.location_name = self.location_name.choice

    if self.gate is None:
      self.gate = state.places[self.location_name].gate
      if self.gate is None:
        self.cancelled = True
        return

      if self.can_take:
        # TODO: event for taking a gate trophy
        self.character.trophies.append(self.gate)
      else:
        state.gates.append(self.gate)
      state.places[self.location_name].gate = None
      closed_until = state.places[self.location_name].closed_until or -1
      if closed_until > state.turn_number:
        state.event_stack.append(
            CloseLocation(self.location_name, closed_until - state.turn_number - 1)
        )
        return

    if not self.return_monsters:
      monsters_to_return = []
      for monster in state.monsters:
        if not isinstance(monster.place, (places.Outskirts, places.CityPlace)):
          continue
        if monster.dimension == self.gate.dimension:
          monsters_to_return.append(monster)
      self.return_monsters = Sequence([
          ReturnMonsterFromBoard(self.character, monster) for monster in monsters_to_return
      ], self.character)
      state.event_stack.append(self.return_monsters)
      return

    if not self.can_seal:
      self.sealed = False
      return

    if self.seal_choice is None:
      seal_clues = 5
      seal_clues += state.get_modifier(self, "seal_clues")
      spend = values.ExactSpendPrerequisite({"clues": seal_clues})
      self.seal_choice = SpendChoice(
          self.character, "Spend clues to seal the gate?", ["Yes", "No"], spends=[spend, None],
      )
      state.event_stack.append(self.seal_choice)
      return

    assert self.seal_choice.is_done()
    if self.seal_choice.is_cancelled() or self.seal_choice.choice == "No":
      self.sealed = False
      return

    state.places[self.location_name].sealed = True
    self.sealed = True

  def is_resolved(self):
    return self.gate is not None and self.sealed is not None

  def start_str(self):
    return ""

  def finish_str(self):
    verb = "closed and sealed" if self.sealed else "closed"
    return f"{self.character.name} {verb} the gate at {self.location_name}"


class RemoveAllSeals(Event):

  def __init__(self):
    self.done = False

  def resolve(self, state):
    for place in state.places.values():
      if getattr(place, "sealed", False):
        place.sealed = False
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return "All locations were unsealed."


class DrawMythosCard(Event):

  def __init__(self, character):
    self.character = character
    self.shuffled = False
    self.card = None

  def resolve(self, state):
    while True:
      card = state.mythos.popleft()
      state.mythos.append(card)
      if card.name != "ShuffleMythos":
        break
      random.shuffle(state.mythos)
      self.shuffled = True
    self.card = card

  def is_resolved(self):
    return self.card is not None

  def start_str(self):
    return f"{self.character.name} draws a mythos card"

  def finish_str(self):
    if self.shuffled:
      return f"{self.character.name} shuffled the deck and then drew {self.card.name}"
    return f"{self.character.name} drew {self.card.name}"


class OpenGate(Event):

  def __init__(self, location_name):
    self.location_name = location_name
    self.opened = None
    self.draw_monsters: Optional[Event] = None
    self.spawn: Optional[Event] = None

  def resolve(self, state):
    if self.spawn is not None:
      assert self.spawn.is_done()
      return

    if isinstance(self.location_name, DrawMythosCard):
      if getattr(self.location_name.card, "gate_location", None) is None:
        self.cancelled = True
        return
      self.location_name = self.location_name.card.gate_location

    if not state.places[self.location_name].is_unstable(state):
      self.opened = False
      return

    if self.draw_monsters is None:
      if state.places[self.location_name].gate is not None:  # Monster surge
        self.opened = False
        open_gates = [place for place in state.places.values() if getattr(place, "gate", None)]
        count = max(len(open_gates), len(state.characters))
      else:  # Regular gate opening
        self.opened = True
        count = 2 if len(state.characters) > 4 else 1
      self.draw_monsters = DrawMonstersFromCup(count)
      state.event_stack.append(self.draw_monsters)
      return

    if not self.opened:  # Monster surge
      gates = [name for name, place in state.places.items() if getattr(place, "gate", None)]
      self.spawn = MonsterSpawnChoice(self.draw_monsters, self.location_name, gates)
      state.event_stack.append(self.spawn)
      return

    # TODO: if there are no gates tokens left, the ancient one awakens
    state.places[self.location_name].gate = state.gates.popleft()
    state.places[self.location_name].clues = 0
    # TODO: AddDoom event
    self.spawn = MonsterSpawnChoice(self.draw_monsters, self.location_name, [self.location_name])
    state.event_stack.append(self.spawn)

  def is_resolved(self):
    if self.draw_monsters is not None:
      return self.spawn is not None and self.spawn.is_done()
    return self.opened is not None

  def start_str(self):
    return f"Gate will open at {self.location_name}"

  def finish_str(self):
    if self.opened:
      return f"A gate appeared at {self.location_name}."
    if self.spawn:
      return f"A monster surge occurred at {self.location_name}."
    return f"A gate did not appear at {self.location_name}."


class DrawMonstersFromCup(Event):

  def __init__(self, count=1, character=None):
    self.character = character
    self.count = count
    self.monsters = None

  def resolve(self, state):
    monster_indexes = [
        idx for idx, monster in enumerate(state.monsters) if monster.place == state.monster_cup
    ]
    # TODO: if there are no monsters left, the ancient one awakens.
    self.monsters = random.sample(monster_indexes, self.count)

  def is_resolved(self):
    return self.monsters is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class MonsterSpawnChoice(ChoiceEvent):

  def __init__(self, draw_monsters, location_name, open_gates):
    self.draw_monsters = draw_monsters
    self.location_name = location_name
    self.open_gates = open_gates
    self.spawned = None
    self.max_count = None
    self.min_count = None
    self.spawn_count = None
    self.outskirts_count = None
    self.num_clears = None
    self.character = None
    self.to_spawn = None

  @staticmethod
  def spawn_counts(to_spawn, on_board, in_outskirts, monster_limit, outskirts_limit):
    available_board_count = monster_limit - on_board
    if to_spawn <= available_board_count:
      return to_spawn, 0, 0, 0

    to_outskirts = to_spawn - available_board_count
    available_outskirts_count = outskirts_limit - in_outskirts
    if to_outskirts <= available_outskirts_count:
      return available_board_count, to_outskirts, 0, 0

    remaining = to_outskirts - available_outskirts_count
    in_outskirts = outskirts_limit
    num_clears = 0
    while remaining > 0:
      in_outskirts += 1
      remaining -= 1
      if in_outskirts > outskirts_limit:
        in_outskirts = 0
        num_clears += 1

    to_cup = to_spawn - available_board_count - in_outskirts
    return available_board_count, in_outskirts, to_cup, num_clears

  def compute_choices(self, state):
    if self.draw_monsters.is_cancelled() or len(self.draw_monsters.monsters) < 1:
      self.cancelled = True
      return
    if self.to_spawn is not None:
      return
    if self.location_name is not None:
      assert getattr(state.places[self.location_name], "gate", None) is not None
    open_count = len(self.open_gates)
    on_board = len([m for m in state.monsters if isinstance(m.place, places.CityPlace)])
    in_outskirts = len([m for m in state.monsters if isinstance(m.place, places.Outskirts)])
    self.spawn_count, self.outskirts_count, cup_count, self.num_clears = self.spawn_counts(
        len(self.draw_monsters.monsters), on_board, in_outskirts,
        state.monster_limit(), state.outskirts_limit(),
    )
    self.min_count = self.spawn_count // open_count
    self.max_count = (self.spawn_count + open_count - 1) // open_count
    self.character = state.characters[state.first_player]
    self.to_spawn = self.draw_monsters.monsters[:]

    # Don't ask the user for a choice in the simple case of one gate, no outskirts.
    if len(self.open_gates) == 1 and self.outskirts_count == 0 and cup_count == 0:
      self.resolve(state, {self.open_gates[0]: self.to_spawn})

  def resolve(self, state, choice=None):
    assert isinstance(choice, dict)
    assert all(isinstance(val, list) for val in choice.values())
    assert not set(choice.keys()) - set(self.open_gates) - {"Outskirts"}
    assert not set(sum(choice.values(), [])) - set(self.to_spawn)
    assert len(sum(choice.values(), [])) == self.spawn_count + self.outskirts_count
    assert len(choice.get("Outskirts") or []) == self.outskirts_count
    city_choices = [choice.get(key, []) for key in self.open_gates]
    if self.max_count > 0:
      assert len(sum(city_choices, [])) > 0
      assert max(len(indexes) for indexes in city_choices) == self.max_count
      assert min(len(indexes) for indexes in city_choices) == self.min_count
      if self.location_name:
        assert self.location_name in choice
        assert len(choice[self.location_name]) == self.max_count
    else:
      assert len(sum(city_choices, [])) == 0

    if self.num_clears > 0:
      for monster in state.monsters:
        if monster.place == state.places["Outskirts"]:
          monster.place = state.monster_cup
    for location_name, monster_indexes in choice.items():
      for monster_idx in monster_indexes:
        state.monsters[monster_idx].place = state.places[location_name]
    self.spawned = True

  def is_resolved(self):
    return self.spawned

  def prompt(self):
    return ""

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class SpawnClue(Event):

  def __init__(self, location_name):
    self.location_name = location_name
    self.spawned = None
    self.eligible = None
    self.choice: Optional[ChoiceEvent] = None

  def resolve(self, state):
    if self.spawned is not None:
      return

    if self.choice is not None:
      assert self.choice.is_done()
      self.eligible[self.choice.choice_index or 0].clues += 1
      self.spawned = True
      return

    if state.places[self.location_name].gate is not None:
      self.spawned = False
      return

    self.eligible = [
        char for char in state.characters if char.place == state.places[self.location_name]]

    if len(self.eligible) == 0:
      state.places[self.location_name].clues += 1
      self.spawned = True
      return
    if len(self.eligible) == 1:
      self.eligible[0].clues += 1
      self.spawned = True
      return
    self.choice = MultipleChoice(
        state.characters[state.first_player],
        f"Choose an investigator to receive the clue token at {self.location_name}",
        [char.name for char in self.eligible],
    )
    state.event_stack.append(self.choice)

  def is_resolved(self):
    return self.spawned is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.spawned:
      return "Clue does not appear."
    if not self.eligible:
      return f"A clue appeared at {self.location_name}."
    if len(self.eligible) == 1:
      receiving_player = self.eligible[0]
    else:
      receiving_player = self.eligible[self.choice.choice_index or 0]
    return f"{receiving_player.name} received a clue."


class MoveMonsters(Event):

  def __init__(self, white_dimensions, black_dimensions):
    self.white_dimensions = white_dimensions
    self.black_dimensions = black_dimensions
    self.moves: Optional[Event] = None

  def resolve(self, state):
    if self.moves is None:
      moves = []
      for monster in state.monsters:
        if not isinstance(monster.place, places.CityPlace):
          continue
        if monster.dimension not in self.white_dimensions | self.black_dimensions:
          continue

        move_color = "white" if monster.dimension in self.white_dimensions else "black"
        moves.append(MoveMonster(monster, move_color))
      self.moves = Sequence(moves)

    if not self.moves.is_done():
      state.event_stack.append(self.moves)
      return

  def is_resolved(self):
    return self.moves is not None and self.moves.is_done()

  def start_str(self):
    movement = ", ".join(self.white_dimensions) + " move on white, "
    return movement + ", ".join(self.black_dimensions) + " move on black"

  def finish_str(self):
    return ""


class MoveMonster(Event):

  def __init__(self, monster, color):
    self.monster = monster
    self.color = color
    self.source = None
    self.destination = None
    self.move_event: Optional[Event] = None

  def resolve(self, state):
    self.source = self.monster.place

    if self.monster.place is None:
      self.destination = False
      return

    if self.monster.has_attribute("stationary", state, None):
      self.destination = False
      return

    if self.monster.has_attribute("unique", state, None):
      if hasattr(self.monster, "get_destination"):
        self.destination = self.monster.get_destination(state)
        if self.destination:
          self.monster.place = self.destination
        return
      if self.move_event is None:
        self.move_event = self.monster.move_event(state)
        state.event_stack.append(self.move_event)
        return
      assert self.move_event.is_done()
      self.destination = False
      return

    local_chars = [char for char in state.characters if char.place == self.monster.place]
    if local_chars:
      self.destination = False
      return

    if self.monster.has_attribute("flying", state, None):
      if self.monster.place.name == "Sky":
        nearby_streets = [
            street for street in state.places.values() if isinstance(street, places.Street)
        ]
      else:
        nearby_streets = [
            street for street in self.monster.place.connections if isinstance(street, places.Street)
        ]
      eligible_chars = [char for char in state.characters if char.place in nearby_streets]
      if not eligible_chars:
        if self.monster.place.name == "Sky":
          self.destination = False
          return
        self.destination = state.places["Sky"]
        self.monster.place = self.destination
        return

      # TODO: allow the first player to break ties
      eligible_chars.sort(key=lambda char: char.sneak(state))
      self.destination = eligible_chars[0].place
      self.monster.place = self.destination
      return

    num_moves = 1
    if self.monster.has_attribute("fast", state, None):
      num_moves = 2

    self.destination = False
    for _ in range(num_moves):
      if self.color in getattr(self.monster.place, "movement", {}):
        self.destination = self.monster.place.movement[self.color]
        self.monster.place = self.destination
      if [char for char in state.characters if char.place == self.monster.place]:
        break

    # TODO: other movement types (unique, stalker, aquatic)

  def is_resolved(self):
    return self.destination is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.destination:
      return ""
    return f"{self.monster.name} moved from {self.source.name} to {self.destination.name}"


class ReturnToCup(Event):

  def __init__(self, names=None, from_places=None):
    assert names or from_places
    assert not (names and from_places)
    self.names = set(names if names else [])
    self.places = set(from_places if from_places else [])
    self.returned = None

  def resolve(self, state):
    if self.returned is not None:
      return

    count = 0
    if self.places:
      place_classes = []
      if "locations" in self.places:
        self.places.remove("locations")
        place_classes.append(places.Location)
      if "streets" in self.places:
        self.places.remove("streets")
        place_classes.append(places.Street)
      if place_classes:
        for name, place in state.places.items():
          if not isinstance(place, tuple(place_classes)):
            continue
          self.places.add(name)

      for monster in state.monsters:
        if getattr(monster.place, "name", None) in self.places:
          monster.place = state.monster_cup
          count += 1
    if self.names:
      for monster in state.monsters:
        if monster.name in self.names and isinstance(monster.place, places.CityPlace):
          monster.place = state.monster_cup
          count += 1
    self.returned = count

  def is_resolved(self):
    return self.returned is not None

  def start_str(self):
    if self.names is not None:
      return "All " + ", ".join(self.names) + " will be returned to the cup."
    return "All monsters in " + ", ".join(self.places) + " will be returned to the cup."

  def finish_str(self):
    return f"{self.returned} monsters returned to the cup"


class CloseLocation(Event):

  def __init__(self, location_name, for_turns=float("inf"), evict=True):
    self.location_name = location_name
    self.for_turns = for_turns
    self.evict = evict
    self.resolved = False

  def resolve(self, state):
    until = state.turn_number + self.for_turns + 1
    place = state.places[self.location_name]
    place.closed_until = until
    chars_in_place = [char for char in state.characters if char.place == place]
    monsters_in_place = [mon for mon in state.monsters if mon.place == place]

    if place.closed and self.evict:
      # TODO: is it possible for a street to evict on close?
      to_place = next(iter(place.connections))
      evictions = []
      for char in chars_in_place:
        evictions.append(ForceMovement(char, to_place.name))
      for monster in monsters_in_place:
        monster.place = to_place
      state.event_stack.append(Sequence(evictions))
      self.evict = False  # So we don't keep looping
      return

    self.resolved = True

  def is_resolved(self):
    return self.resolved

  def start_str(self):
    return f"Closing {self.location_name}"

  def finish_str(self):
    return ""


class ActivateEnvironment(Event):

  def __init__(self, environment):
    self.env = environment
    self.done = False

  def resolve(self, state):
    if state.environment is not None:
      state.mythos.append(state.environment)
    state.mythos.remove(self.env)
    state.environment = self.env
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.env.name} is the new environment"


class StartRumor(Event):

  def __init__(self, rumor):
    self.rumor = rumor
    self.started = None

  def resolve(self, state):
    if state.rumor is not None:
      self.started = False
      return
    state.mythos.remove(self.rumor)
    state.rumor = self.rumor
    self.rumor.start_turn = state.turn_number + 1
    self.started = True

  def is_resolved(self):
    return self.started is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.started:
      return ""
    return f"{self.rumor.name} entered play"


class ProgressRumor(Event):

  def __init__(self, rumor, amount=1):
    self.rumor = rumor
    self.amount = amount
    self.increase = None

  def resolve(self, state):
    if isinstance(self.amount, values.Value):
      self.amount = self.amount.value(state)
    self.rumor.progress += self.amount
    self.increase = self.amount

  def is_resolved(self):
    return self.increase is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class EndRumor(Event):

  def __init__(self, rumor, failed, add_global=False):
    self.rumor = rumor
    self.add_global = add_global
    self.failed = failed
    self.done = False

  def resolve(self, state):
    self.rumor.failed = self.failed
    state.rumor = None
    if self.add_global:
      state.other_globals.append(self.rumor)
    self.done = True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class AncientOneAttack(Sequence):
  pass


class AncientOneAwaken(Sequence):
  pass
