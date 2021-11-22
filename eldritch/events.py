import abc
import collections
import math
import operator
from random import SystemRandom
random = SystemRandom()

from eldritch import values
from eldritch import places
from eldritch import items


class Event(metaclass=abc.ABCMeta):
  """The event types are as follows:

  DiceRoll: One or more dice are rolled. The results are saved in the roll attribute.
  Movement: The character will be moved along a route, using movement points as they do so.
  GainOrLoss: The character's sanity, stamina, dollars, or clues will be changed. The resulting
    change will be stored in the final_adjustments attribute.
  StatusChange: The character will be blessed, cursed, a lodge member, gain a retainer, be delayed,
    be arrested, be lost in time and space, or be devoured. The final change will be stored in the
    status_change attribute (for example, status_change will be 0 if the character was supposed to
    be blessed, but was already blessed).
  ForceMovement: The character will move to another location, including other worlds or the street.
  Draw: The character will draw one or more items/skills/allies
  DrawSpecific: The character searches the given deck for a specific card and takes it.
  Purchase: The character will draw one or more items and purchase one of them, if possible.
  Check: The character makes a skill check. The result is stored in the successes attribute.
  Conditional: Has a map of minimum successes to events, along with an event that determines the
    number of successes (either a check or a prerequisite). After the first event is resolved, the
    success map is used to determine which event should be applied.
  Sequence: A sequence of events will be resolved sequentially.
  BinaryChoice: The character must choose one of two options.
  """

  @abc.abstractmethod
  def resolve(self, state):
    # resolve should return True if the event was resolved, False otherwise.
    # For example, an event that requires a check to be made should add that check to the end
    # of the event stack, and then return False. It will be called again when the check is
    # finished with the results of the check accessible.
    raise NotImplementedError

  @abc.abstractmethod
  def is_resolved(self):
    raise NotImplementedError

  @abc.abstractmethod
  def start_str(self):
    raise NotImplementedError

  @abc.abstractmethod
  def finish_str(self):
    raise NotImplementedError


class ChoiceEvent(Event):

  @abc.abstractmethod
  def resolve(self, state, choice=None):
    raise NotImplementedError

  @abc.abstractmethod
  def prompt(self):
    raise NotImplementedError

  def compute_choices(self, state):
    pass

  def annotations(self):
    return None


class Nothing(Event):

  def __init__(self):
    self.done = False

  def resolve(self, state):
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return "Nothing happens"


class Sequence(Event):

  def __init__(self, events, character=None):
    self.events = events
    self.idx = 0
    self.character = character

  def resolve(self, state):
    if self.idx == len(self.events):
      return True
    if not self.events[self.idx].is_resolved():
      state.event_stack.append(self.events[self.idx])
      return False
    self.idx += 1
    return self.idx == len(self.events)

  def is_resolved(self):
    return self.idx == len(self.events)

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class Turn(Event):

  def check_lose_turn(self):
    char = getattr(self, "character", None)
    if not char:
      return False
    if char.lose_turn_until is not None:
      self.done = True
      return True
    return False


class Upkeep(Turn):

  def __init__(self, character):
    self.character = character
    self.focus_given = False
    self.refresh = None
    self.actions = None
    self.sliders = None
    self.done = False

  def resolve(self, state):
    if self.check_lose_turn():
      return True
    if not self.focus_given:
      self.character.focus_points = self.character.focus
      self.focus_given = True
    if self.refresh is None:
      self.refresh = RefreshAssets(self.character)
      state.event_stack.append(self.refresh)
      return False
    if self.actions is None:
      self.actions = UpkeepActions(self.character)
      state.event_stack.append(self.actions)
      return False
    if self.sliders is None:
      self.sliders = SliderInput(self.character)
      state.event_stack.append(self.sliders)
      return False
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name}'s upkeep"

  def finish_str(self):
    return ""


class UpkeepActions(Nothing):

  def __init__(self, character):
    super(UpkeepActions, self).__init__()
    self.character = character


class SliderInput(Event):

  def __init__(self, character, free=False):
    self.character = character
    self.pending = self.character.sliders()
    assert len(self.pending) >= 3
    self.free = free
    self.done = False

  def resolve(self, state, name, value):
    assert isinstance(name, str), "invalid slider name"
    assert name in self.pending.keys() | {"done", "reset"}
    if name == "done":
      if not self.free:
        if self.character.focus_cost(self.pending) > self.character.focus_points:
          raise AssertionError("You do not have enough focus.")
        self.character.focus_points -= self.character.focus_cost(self.pending)
      for name, value in self.pending.items():
        setattr(self.character, name + "_slider", value)
      self.done = True
      return True
    if name == "reset":
      self.pending = self.character.sliders()
      return False

    assert isinstance(value, int), "invalid slider value"
    assert 0 <= value, "invalid slider value %s" % value
    assert value < len(getattr(self.character, "_" + name)), "invalid slider value %s" % value
    pending = self.pending.copy()
    pending[name] = value
    if not self.free:
      if self.character.focus_cost(pending) > self.character.focus_points:
        raise AssertionError("You do not have enough focus.")
    self.pending = pending
    return False

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class Movement(Turn):

  def __init__(self, character):
    self.character = character
    self.move = None
    self.done = False

  def resolve(self, state):
    self.character.avoid_monsters = []
    if self.check_lose_turn():
      return True
    if self.character.delayed_until is not None:
      if self.character.delayed_until <= state.turn_number:
        self.character.delayed_until = None
      else:
        self.done = True
        return True

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
      return False

    assert self.move.is_resolved()
    self.done = True
    return True

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
      return True
    assert choice in self.routes
    state.event_stack.append(
        Sequence([MoveOne(self.character, dest) for dest in self.routes[choice]], self.character))
    return False

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return ""

  def prompt(self):
    return "Move somewhere"

  def resolve(self, state):
      self.done = True
      self.character.avoid_monsters = False

  @property
  def choices(self):
    return sorted(self.routes.keys())

  def annotations(self):
    return [f"Move ({len(self.routes[dest])})" for dest in sorted(self.routes.keys())]

  def compute_choices(self, state):
    self.routes = self.get_routes(state)  # TODO: annotate

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
    self.action = None
    self.done = False

  def resolve(self, state):
    if self.check_lose_turn():
      return True
    if self.action is None:
      if not isinstance(self.character.place, places.Location):
        self.done = True
        return True
      if self.character.place.gate and self.character.explored:
        self.action = GateCloseAttempt(self.character, self.character.place.name)
      elif self.character.place.gate:
        self.action = Travel(self.character, self.character.place.gate.name)
      elif self.character.place.neighborhood.encounters:
        # TODO: fixed encounters
        self.action = Encounter(self.character, self.character.place.name)
      else:
        self.action = Nothing()
      state.event_stack.append(self.action)
      return False

    assert self.action.is_resolved()
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name}'s encounter phase"

  def finish_str(self):
    return ""


class OtherWorldPhase(Turn):

  def __init__(self, character):
    self.character = character
    self.action = None
    self.done = False

  def resolve(self, state):
    if self.check_lose_turn():
      return True
    if self.action is None:
      if not isinstance(self.character.place, places.OtherWorld):
        self.done = True
        return True
      self.action = GateEncounter(
          self.character, self.character.place.info.name, self.character.place.info.colors)
      state.event_stack.append(self.action)
      return False

    assert self.action.is_resolved()
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name}'s other world phase"

  def finish_str(self):
    return ""


class Mythos(Turn):

  def __init__(self, _):
    self.action = None
    self.done = False

  def resolve(self, state):
    if self.action is None:
      # TODO: drawing the mythos card needs to be its own event
      # TODO: account for the shuffle card
      chosen = state.mythos.popleft()
      state.mythos.append(chosen)
      self.action = chosen.create_event(state)
      state.event_stack.append(self.action)
      return False

    assert self.action.is_resolved()
    self.done = True
    return True

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
    return True

  def is_resolved(self):
    return self.roll is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.roll:
      return "%s rolled no dice" % self.character.name
    return "%s rolled %s" % (self.character.name, " ".join([str(x) for x in self.roll]))


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
      return True
    assert self.dest in [conn.name for conn in self.character.place.connections]
    if not (self.character.place.closed or state.places[self.dest].closed):
      self.character.place = state.places[self.dest]
      self.character.movement_points -= 1
      self.character.explored = False
      self.character.avoid_monsters = []
    self.done = True
    self.moved = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name} moving from {self.character.place.name}"

  def finish_str(self):
    if self.moved:
      return f"{self.character.name} moved to {self.dest.name}"
    else:
      return f"{self.character.name} stayed in {self.character.place.name}"


class GainOrLoss(Event):

  def __init__(self, character, gains, losses):
    assert not gains.keys() - {"stamina", "sanity", "dollars", "clues"}
    assert not losses.keys() - {"stamina", "sanity", "dollars", "clues"}
    assert not gains.keys() & losses.keys()
    assert all(isinstance(val, (int, values.Value)) or math.isinf(val) for val in gains.values())
    assert all(isinstance(val, (int, values.Value)) or math.isinf(val) for val in losses.values())
    self.character = character
    self.gains = collections.defaultdict(int)
    self.gains.update(gains)
    self.losses = collections.defaultdict(int)
    self.losses.update(losses)
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
      if new_val < 0:
        new_val = 0
      if attr == "stamina" and new_val > getattr(self.character, "max_stamina"):
        new_val = getattr(self.character, "max_stamina")
      if attr == "sanity" and new_val > getattr(self.character, "max_sanity"):
        new_val = getattr(self.character, "max_sanity")
      self.final_adjustments[attr] = new_val - old_val
      setattr(self.character, attr, new_val)
    return True

  def is_resolved(self):
    return self.final_adjustments is not None

  def start_str(self):
    return ""

  def finish_str(self):
    gains = ", ".join([
      "%s %s" % (count, attr) for attr, count in self.final_adjustments.items() if count > 0])
    losses = ", ".join([
      "%s %s" % (-count, attr) for attr, count in self.final_adjustments.items() if count < 0])
    if not gains and not losses:
      return ""
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
    self.choice = None
    self.gain = None

  def resolve(self, state):
    if self.gain is not None:
      assert self.gain.is_resolved()
      return True

    amount = self.amount.value(state) if isinstance(self.amount, values.Value) else self.amount

    if self.choice is not None:
      assert self.choice.is_resolved()
      attr1_amount = self.choice.choice
      self.gain = GainOrLoss(
          self.character, {self.attr1: attr1_amount, self.attr2: amount - attr1_amount}, {})
      state.event_stack.append(self.gain)
      return False

    prompt = f"How much of the {amount} do you want to go to {self.attr1}?"
    self.choice = MultipleChoice(self.character, prompt, [x for x in range(0, amount+1)])
    state.event_stack.append(self.choice)
    return False

  def is_resolved(self):
    return self.gain is not None and self.gain.is_resolved()

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
    self.source_event = source_event
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
    return True

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
    self.gain = None
    self.picked_up = None
    self.done = False

  def resolve(self, state):
    if self.picked_up is None:
      if self.character.place.name != self.place:
        self.done = True
        return True
      self.picked_up = state.places[self.place].clues

    if not self.picked_up:
      self.done = True
      return True

    if self.gain is None:
      self.gain = Gain(self.character, {"clues": self.picked_up})
      state.event_stack.append(self.gain)
      return False

    state.places[self.place].clues -= self.picked_up
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    if self.picked_up is None:
      return ""
    return f"{self.character.name} picked up {self.picked_up} clues at {self.place}"


class InsaneOrUnconscious(Event):

  def __init__(self, character, attribute, desc):
    assert attribute in {"sanity", "stamina"}
    self.character = character
    self.attribute = attribute
    self.desc = desc
    self.stack_cleared = False
    self.lose_clues = None
    self.lose_items = None
    self.force_move = None

  def resolve(self, state):
    if not self.stack_cleared:
      assert getattr(self.character, self.attribute) <= 0
      setattr(self.character, self.attribute, 1)

      saved_interrupts = state.interrupt_stack[-1]
      saved_triggers = state.trigger_stack[-1]
      while (state.event_stack):
        event = state.event_stack[-1]
        if hasattr(event, "character") and event.character == self.character:
          state.pop_event(event)
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
      self.stack_cleared = True

    if not self.lose_clues:
      self.lose_clues = Loss(self.character, {"clues": self.character.clues // 2})
      state.event_stack.append(self.lose_clues)
      return False

    if not self.lose_items:
      self.lose_items = Nothing()  # TODO: choosing items to lose
      state.event_stack.append(self.lose_items)
      return False

    if not self.force_move:
      if isinstance(self.character.place, places.CityPlace):
        dest = "Asylum" if self.attribute == "sanity" else "Hospital"
        self.force_move = ForceMovement(self.character, dest)
      else:
        self.force_move = LostInTimeAndSpace(self.character)
      state.event_stack.append(self.force_move)
      return False

    return True

  def is_resolved(self):
    steps = [self.lose_clues, self.lose_items, self.force_move]
    return all(steps) and all([step.is_resolved() for step in steps])

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


class DelayOrLoseTurn(Event):

  def __init__(self, character, status):
    assert status in {"delayed", "lose_turn"}
    self.character = character
    self.attr = status + "_until"
    self.until = None

  def resolve(self, state):
    current = getattr(self.character, self.attr) or 0
    self.until = max(current, state.turn_number + 2)
    setattr(self.character, self.attr, self.until)
    return True

  def is_resolved(self):
    return self.until is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if self.attr == "delayed_until":
      return f"{self.character.name} is delayed"
    else:
      return f"{self.character.name} loses their next turn"


def Delayed(character):
  return DelayOrLoseTurn(character, "delayed")


def LoseTurn(character):
  return DelayOrLoseTurn(character, "lose_turn")


class LostInTimeAndSpace(Sequence):

  def __init__(self, character):
    super(LostInTimeAndSpace, self).__init__([
      ForceMovement(character, "Lost"), LoseTurn(character)], character)


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
    return True

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
    return True

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
    return True

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
    self.location_name = location_name
    self.done = False

  def resolve(self, state):
    if isinstance(self.location_name, MapChoice):
      assert self.location_name.is_resolved()
      if self.location_name.choice is None:
        # No need to reset explored, since the character did not move.
        self.done = True
        return True
      self.location_name = self.location_name.choice
    self.character.place = state.places[self.location_name]
    self.character.explored = False
    self.done = True
    return True

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
        if not deck :
          break
        top = deck.popleft()
        if self.target_type is None or isinstance(top, self.target_type):
          self.drawn.append(top)
        else:
          deck.append(top)

        if i >= decksize:
          break
      # TODO: is there a scenario when the player can go insane/unconscious before they
      # successfully pick a card?

    return True

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
  def __init__(self, character, draw: DrawItems, prompt="Choose a card"):
      self.character = character
      self.draw = draw
      self.keep_count = 1 #TODO: allow the player to keep more than one?
      self.drawn = None
      self.kept = None
      self.choice = None
      self.prompt = prompt

  def resolve(self, state):
    if self.drawn is None:
      assert self.draw.is_resolved()
      self.drawn = self.draw.drawn

    if self.is_resolved():
      # This should never happen??
      return True

    if self.choice is not None:
      if not self.choice.is_resolved():  # This should never happen
        return False
      kept_cards = [self.drawn[self.choice.choice_index]]
      discarded_cards = [
        card for idx, card in enumerate(self.drawn) if idx != self.choice.choice_index]
      self.kept = [card.name for card in kept_cards]
      self.character.possessions.extend(kept_cards)
      for card in discarded_cards:
        getattr(state, self.draw.deck).append(card)
      return True

    if self.keep_count < len(self.drawn):
      self.choice = CardChoice(self.character, self.prompt, [card.name for card in self.drawn])
      state.event_stack.append(self.choice)
      return False

    self.character.possessions.extend(self.drawn)
    self.kept = [card.name for card in self.drawn]
    return True

  def is_resolved(self):
    return self.kept is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.character.name} kept " + ", ".join(self.kept)

def Draw(character, deck, draw_count, prompt="Choose a card", target_type=None):
  cards = DrawItems(character, deck, draw_count, target_type=target_type)
  keep = KeepDrawn(character, cards, prompt)
  return Sequence([cards, keep], character)

def GainAllyOrReward(character, ally: str, reward: Event):
  has_ally = values.ContainsPrerequisite("allies", ally)
  gain_ally = DrawSpecific(character, "allies", ally)
  return PassFail(character, has_ally, gain_ally, reward)


class SellChosen(Event):

  def __init__(self, character, choice, discount_type="fixed", discount=0):
    assert discount_type in {"fixed", "rate"}
    self.character = character
    self.choice = choice
    self.discount_type = discount_type
    self.discount = discount
    self.prices = []
    self.resolved = False
    self.sold = None

  def resolve(self, state):
    if self.resolved:
      # This should never happen??
      return True
    self.prices = [self.discounted_price(card) for card in self.choice.chosen]
    self.character.dollars += sum(self.prices)
    for card in self.choice.chosen:
      self.character.possessions.remove(card)
      getattr(state, card.deck).append(card)
    self.resolved = True
    self.sold = [card.name for card in self.choice.chosen]
    return True

  def is_resolved(self):
    return self.resolved

  def start_str(self):
    return f"{self.character.name} selling " + ", ".join(i.name for i in self.choice.chosen)

  def finish_str(self):
    if not self.sold:
      return f"{self.character.name} sold nothing"
    return f"{self.character.name} sold " + ", ".join(self.sold)

  def discounted_price(self, card):
    if self.discount_type == "fixed":
      return card.price - self.discount
    elif self.discount_type == 'rate':
      return card.price - int(self.discount * card.price) # Discounts round up


def Sell(char, decks, sell_count=1, discount_type="fixed", discount=0,
         prompt="Sell item?"):
    items = ItemCountChoice(char, prompt, sell_count, min_count=0, decks=decks)
    sell = SellChosen( char, items, discount_type=discount_type, discount=discount)
    return Sequence([items, sell], char)

class PurchaseDrawn(Event):
  def __init__(self, character, draw: DrawItems,
               discount_type="fixed", discount=0, keep_count=1, prompt="Buy items?"):
    # TODO: draw could be something other than DrawItems (Northside 5)
    assert discount_type in {"fixed", "rate"}
    self.character = character
    self.prompt = prompt
    self.keep_count = keep_count
    self.discount_type = discount_type
    self.discount = discount
    self.draw = draw
    self.drawn = None
    self.choice = None
    self.kept = []
    self.prices = None
    self.resolved = False

  def resolve(self, state):
    if self.resolved:
      # This should never happen??
      return True
    if self.drawn is None:
      assert self.draw.is_resolved()
      self.drawn = self.draw.drawn

    if self.choice is not None:
      if not self.choice.is_resolved():  # This should never happen
        return False
      if self.choice.choice == "Nothing":
        self.resolved = True
        getattr(state, self.draw.deck).extend(self.drawn)
        return True
      # Note that by now, we should have returned the unavailable cards to the deck
      kept_card = self.drawn.pop(self.choice.choice_index)
      cost = self.prices.pop(self.choice.choice_index)
      self.kept.append(self.choice.choice)
      assert cost <= self.character.dollars
      self.character.dollars -= cost
      self.character.possessions.append(kept_card)
      self.keep_count -= 1

    if self.keep_count == 0:
      for card in self.drawn:
        getattr(state, self.draw.deck).append(card)
      self.resolved = True
      return True

    # self.keep_count > 0
    choices = []
    available = []
    unavailable = []
    self.prices = []
    for card in self.drawn:
      price = self.discounted_price(card)
      if price <= self.character.dollars:
        available.append(card)
        self.prices.append(price)
        choices.append(f"{card.name}")
      else:
        getattr(state, self.draw.deck).append(card)
        unavailable.append(f"{card.name}")
    self.drawn = available
    choices.append("Nothing")
    #TODO: In some circumstances, you must purchase at least
    # one card if able (e.g. General Store)

    if unavailable:
      could_not_afford = " (Could not afford {})".format(",".join(unavailable))
    else:
      could_not_afford = ""
    if available:
      self.choice = CardChoice(
          self.character, self.prompt + could_not_afford, choices, [f"${p}" for p in self.prices])
      state.event_stack.append(self.choice)
      return False
    else:
      self.resolved = True
      return True

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
    elif self.discount_type == "rate":
      return card.price - int(self.discount * card.price) # Discounts round up


def Purchase(char, deck, draw_count, discount_type="fixed", discount=0, keep_count=1,
             target_type=None, prompt="Buy items?"):
    items = DrawItems(char, deck, draw_count, target_type=target_type)
    buy = PurchaseDrawn(
      char, items, discount_type=discount_type, discount=discount, keep_count=keep_count, prompt=prompt
    )
    return Sequence([items, buy], char)


class Encounter(Event):

  def __init__(self, character, location_name, count=1):
    self.character = character
    self.location_name = location_name
    self.draw = None
    self.encounter = None
    self.count = count

  def resolve(self, state):
    if isinstance(self.location_name, MapChoice):
      assert self.location_name.is_resolved()
      name = self.location_name.choice
      if name is None or not isinstance(state.places[name], places.Location):
        if self.encounter:
          return True
        self.encounter = Nothing()
        state.event_stack.append(self.encounter)
        return False
      self.location_name = self.location_name.choice

    if self.character.lodge_membership and self.location_name == "Lodge":
      self.location_name = "Sanctum"

    if self.draw is None:
      if self.location_name == "Sanctum":
        neighborhood = state.places["FrenchHill"]
      else:
        neighborhood = state.places[self.location_name].neighborhood
      self.draw = DrawEncounter(self.character, neighborhood, self.count)

    if not self.draw.is_resolved():
      state.event_stack.append(self.draw)
      return False

    if self.encounter and self.encounter.is_resolved():
      return True

    if len(self.draw.cards) == 1:
      self.encounter = self.draw.cards[0].encounter_event(self.character, self.location_name)
      state.event_stack.append(self.encounter)
      return False

    encounters = [
        card.encounter_event(self.character, self.location_name) for card in self.draw.cards]
    choice = CardChoice(self.character, "Choose an Encounter", [card.name for card in self.draw.cards])
    cond = Conditional(
        self.character, choice, "choice_index", {idx: enc for idx, enc in enumerate(encounters)})
    self.encounter = Sequence([choice, cond], self.character)
    state.event_stack.append(self.encounter)
    return False

  def is_resolved(self):
    return self.encounter and self.encounter.is_resolved()

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
    return True

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
    self.draw = None
    self.cards = []
    self.encounter = None

  def resolve(self, state):
    if self.encounter is not None:
      assert self.encounter.is_resolved()
      state.gate_cards.extend(self.cards)
      self.cards = []
      return True

    if self.draw is not None:
      assert self.draw.is_resolved()
      self.cards.append(self.draw.card)
      self.draw = None

    if len(self.cards) < self.draw_count:
      self.draw = DrawGateCard(self.character, self.colors)
      state.event_stack.append(self.draw)
      return False

    if len(self.cards) == 1:
      self.encounter = self.cards[0].encounter_event(self.character, self.world_name)
      state.event_stack.append(self.encounter)
      return False

    encounters = [card.encounter_event(self.character, self.world_name) for card in self.cards]
    choice = CardChoice(self.character, "Choose an Encounter", [card.name for card in self.cards])
    cond = Conditional(
        self.character, choice, "choice_index", {idx: enc for idx, enc in enumerate(encounters)})
    self.encounter = Sequence([choice, cond], self.character)
    state.event_stack.append(self.encounter)
    return False

  def is_resolved(self):
    return self.encounter is not None and self.encounter.is_resolved() and not self.cards

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
      if card.name == "Shuffle":
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
        #TODO: Shuffle the deck after drawing the item
        break
    else:
      self.received = False
    return True

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
      return True
    self.item._exhausted = True
    self.exhausted = True
    return True

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
      return True
    self.item._exhausted = False
    self.refreshed = True
    return True

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
    self.to_refresh = None
    self.idx = 0

  def resolve(self, state):
    if self.to_refresh is None:
      self.to_refresh = [item for item in self.character.possessions if item.exhausted]
    while self.idx < len(self.to_refresh):
      if self.to_refresh[self.idx].exhausted:
        state.event_stack.append(RefreshAsset(self.character, self.to_refresh[self.idx]))
        return False
      self.idx += 1
    return True

  def is_resolved(self):
    return self.to_refresh is not None and self.idx == len(self.to_refresh)

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
      return True
    self.item._active = True
    if hasattr(self.item, "activate"):
      self.item.activate()
    self.activated = True
    return True

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
    self.activated = 0

  def resolve(self, state):
    assert self.item_choice.is_resolved()
    self.activated = 0
    for item in self.item_choice.chosen:
      if not item.active:
        state.event_stack.append(ActivateItem(self.character, item))
        return False
      self.activated += 1
    return True

  def is_resolved(self):
    return self.item_choice.is_resolved() and self.activated == len(self.item_choice.chosen)

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
      return True
    self.item._active = False
    if hasattr(self.item, "deactivate"):
      self.item.deactivate()
    self.deactivated = True
    return True

  def is_resolved(self):
    return self.deactivated is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class DeactivateItems(Event):

  def __init__(self, character):
    self.character = character
    # TODO: this should be rewritten to deactivate each item exactly once

  def resolve(self, state):
    for item in self.character.possessions:
      if getattr(item, "deck", None) in ("common", "unique") and item.active:
        state.event_stack.append(DeactivateItem(self.character, item))
        return False
    return True

  def is_resolved(self):
    return not any([
      item.active for item in self.character.possessions
      if getattr(item, "deck", None) in ("common", "unique")
    ])

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class CastSpell(Event):

  def __init__(self, character, spell, choice=None, action="exhaust"):
    assert spell in character.possessions
    assert action in {"exhaust", "discard"}
    self.character = character
    self.spell = spell
    self.activation = None
    self.check = None
    self.cost = None
    self.success = None
    self.choice = choice
    if action == "discard":
      self.action = DiscardSpecific(character, spell)
    else:
      self.action = ExhaustAsset(character, spell)

  def resolve(self, state):
    if self.spell not in self.character.possessions:
      self.success = False
      return True

    self.spell.in_use = True
    self.spell.deactivatable = False
    self.spell.choice = self.choice
    # TODO: maybe they should pay the sanity cost first, but we check for insanity after
    # the spell is over.
    if not self.check:
      self.check = Check(self.character, "spell", self.spell.get_difficulty(state))
      state.event_stack.append(self.check)
      return False
    assert self.check.is_resolved()

    if not self.action.is_resolved():
      state.event_stack.append(self.action)
      return False

    if self.check.successes < self.spell.get_required_successes(state):
      self.success = False
      if not self.cost:
        self.cost = Loss(self.character, {"sanity": self.spell.sanity_cost})
        state.event_stack.append(self.cost)
        return False
      assert self.cost.is_resolved()
      return True

    self.success = True
    if not self.activation:
      self.activation = self.spell.get_cast_event(self.character, state)
      state.event_stack.append(self.activation)
      return False
    assert self.activation.is_resolved()

    if not self.cost:
      self.cost = Loss(self.character, {"sanity": self.spell.sanity_cost})
      state.event_stack.append(self.cost)
      return False
    assert self.cost.is_resolved()
    return True

  def is_resolved(self):
    return self.cost is not None and self.cost.is_resolved()

  def start_str(self):
    return f"{self.character.name} is casting {self.spell.name}"

  def finish_str(self):
    if self.success:
      return f"{self.character.name} successfully cast {self.spell.name}"
    return f"{self.character.name} failed to cast {self.spell.name}"


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
    self.spell._active = False
    self.spell.in_use = False
    self.spell.deactivatable = False
    if hasattr(self.spell, "deactivate"):
      self.spell.deactivate()
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.spell.name} deactivated"


class DeactivateSpells(Event):

  def __init__(self, character):
    self.character = character
    # TODO: this should be rewritten to deactivate each spell exactly once

  def resolve(self, state):
    for spell in self.character.possessions:
      if getattr(spell, "deck", None) == "spells" and spell.in_use:
        state.event_stack.append(DeactivateSpell(self.character, spell))
        return False
    return True

  def is_resolved(self):
    return not any([
      spell.in_use for spell in self.character.possessions
      if getattr(spell, "deck", None) == "spells"
    ])

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class DiscardSpecific(Event):

  def __init__(self, character, item):
    assert item in character.possessions
    self.character = character
    self.item = item
    self.discarded = None

  def resolve(self, state):
    if self.item not in self.character.possessions:
      self.discarded = False
      return True
    self.character.possessions.remove(self.item)
    deck = getattr(state, self.item.deck)
    deck.append(self.item)
    self.discarded = True
    return True

  def is_resolved(self):
    return self.discarded is not None

  def start_str(self):
    return f"{self.character.name} will discard a {self.item.name}"

  def finish_str(self):
    if not self.discarded:
      return f"{self.character.name} did not have a {self.item.name} to discard"
    return f"{self.character.name} discarded their {self.item.name}"


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
        self.discarded = True
        return True
    self.discarded = False
    return True

  def is_resolved(self):
    return self.discarded is not None

  def start_str(self):
    return f"{self.character.name} will discard a {self.item_name}"

  def finish_str(self):
    if not self.discarded:
      return f"{self.character.name} did not have a {self.item_name} to discard"
    return f"{self.character.name} discarded their {self.item_name}"


class Check(Event):

  def __init__(self, character, check_type, modifier, attributes=None):
    # TODO: assert on check type
    self.character = character
    self.check_type = check_type
    self.modifier = modifier
    self.attributes = attributes
    self.dice = None
    self.roll = None
    self.successes = None

  def resolve(self, state):
    if self.dice is None:
      if self.check_type == "combat":
        num_dice = self.character.combat(state, self.attributes) + self.modifier
      else:
        num_dice = getattr(self.character, self.check_type)(state) + self.modifier
      self.dice = DiceRoll(self.character, num_dice)
      state.event_stack.append(self.dice)
      return False
    self.roll = self.dice.roll[:]
    self.count_successes()
    return True

  def count_successes(self):
    self.successes = self.character.count_successes(self.roll, self.check_type)

  def is_resolved(self):
    return self.successes is not None

  def check_str(self):
    return self.check_type + " " + "{:+d}".format(self.modifier) + " check"

  def start_str(self):
    return self.character.name + " makes a " + self.check_str()

  def finish_str(self):
    check_str = self.check_str()
    if not self.successes:
      return self.character.name + " failed a " + check_str
    return self.character.name + " had " + str(self.successes) + " successes on a " + check_str


class SpendClue(Event):

  def __init__(self, character, check):
    self.character = character
    self.check = check
    self.dice = DiceRoll(character, 1)
    self.extra_successes = None

  def resolve(self, state):
    assert self.check.is_resolved()
    if not self.dice.is_resolved():
      assert self.character.clues > 0
      self.character.clues -= 1
      state.event_stack.append(self.dice)
      return False
    old_successes = self.check.successes
    self.check.roll.extend(self.dice.roll)
    self.check.count_successes()
    self.extra_successes = self.check.successes - old_successes
    return True

  def is_resolved(self):
    return self.extra_successes is not None

  def start_str(self):
    return f"{self.character.name} spent a clue token"

  def finish_str(self):
    return f"{self.character.name} got {self.extra_successes} extra successes"


class AddExtraDie(Event):

  def __init__(self, character, event):
    assert isinstance(event, DiceRoll)
    self.character = character
    self.dice = event
    self.done = False

  def resolve(self, state):
    assert not self.dice.is_resolved()
    self.dice.count += 1
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return f"{self.character.name} gets an extra die just because" # TODO

  def finish_str(self):
    return ""


class RerollCheck(Event):

  def __init__(self, character, check):
    assert isinstance(check, Check)
    self.character = character
    self.check = check
    self.dice = None
    self.done = False

  def resolve(self, state):
    assert self.check.is_resolved()
    if self.dice is None:
      self.dice = DiceRoll(self.character, len(self.check.roll))
      state.event_stack.append(self.dice)
      return False
    self.check.roll = self.dice.roll
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
    assert all([isinstance(key, int) for key in result_map])
    assert min(result_map.keys()) == 0
    self.character = character
    self.condition = condition
    self.attribute = attribute
    self.result_map = result_map
    self.result = None

  def resolve(self, state):
    assert isinstance(self.condition, values.Value) or self.condition.is_resolved()
    if self.result is not None:
      if not self.result.is_resolved():  # NOTE: this should never happen
        state.event_stack.append(self.result)
        return False
      return True

    if isinstance(self.condition, values.Value):
      value = self.condition.value(state)
    else:
      value = getattr(self.condition, self.attribute)

    for min_result in reversed(sorted(self.result_map)):
      if value >= min_result:
        self.result = self.result_map[min_result]
        state.event_stack.append(self.result)
        return False
    raise RuntimeError("result map without result for %s: %s" % (value, self.result_map))

  def is_resolved(self):
    return self.result is not None and self.result.is_resolved()

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
    super(Arrested, self).__init__([
      ForceMovement(character, "Police"), LoseTurn(character),
      Loss(character, {"dollars": values.Calculation(character, "dollars", operator.floordiv, 2)}),
    ], character)


class MultipleChoice(ChoiceEvent):

  def __init__(self, character, prompt, choices, annotations=None):
    self.character = character
    self._prompt = prompt
    self.choices = choices
    self.choice = None
    self._annotations = annotations

  def resolve(self, state, choice=None):
    assert not self.is_resolved()
    self.validate_choice(choice)
    self.choice = choice
    return True

  def validate_choice(self, choice):
    assert choice in self.choices

  def is_resolved(self):
    return self.choice is not None

  def start_str(self):
    return f"{self.character.name} must choose one of " + ", ".join([str(c) for c in self.choices])

  def finish_str(self):
    return f"{self.character.name} chose {str(self.choice)}"

  def prompt(self):
    return self._prompt

  def annotations(self):
    return self._annotations

  @property
  def choice_index(self):
    if self.choice is None:
      return None
    return self.choices.index(self.choice)


class PrereqChoice(MultipleChoice):

  def __init__(self, character, prompt, choices, prereqs, annotations=None):
    assert len(choices) == len(prereqs)
    assert all([prereq is None or isinstance(prereq, values.Value) for prereq in prereqs])
    super(PrereqChoice, self).__init__(character, prompt, choices, annotations)
    self.prereqs = prereqs
    self.invalid_choices = []

  def compute_choices(self, state):
    self.invalid_choices.clear()
    for idx in range(len(self.choices)):
      if self.prereqs[idx] is not None and self.prereqs[idx].value(state) < 1:
        self.invalid_choices.append(idx)

  def validate_choice(self, choice):
    super(PrereqChoice, self).validate_choice(choice)
    assert self.choices.index(choice) not in self.invalid_choices


def BinaryChoice(
    character, prompt, first_choice, second_choice, first_event, second_event, prereq=None):
  if prereq is not None:
    choice = PrereqChoice(character, prompt, [first_choice, second_choice], [prereq, None])
  else:
    choice = MultipleChoice(character, prompt, [first_choice, second_choice])
  sequence = [
      choice, Conditional(character, choice, "choice_index", {0: first_event, 1: second_event})]
  return Sequence(sequence, character)


class ItemChoice(ChoiceEvent):

  def __init__(self, character, prompt, decks=None, item_type=None):
    self.character = character
    self._prompt = prompt
    self.choices = None
    self.chosen = None
    if decks is None:
      decks = {'spells', 'common', 'unique', 'skills', 'allies'}
    assert decks.issubset({'spells', 'common', 'unique', 'skills', 'allies'}), f"{decks} contains invalid deck"
    self.decks = decks
    self.item_type = item_type

  def resolve(self, state, choice=None):
    if self.is_resolved():
      return True
    assert all([0 <= idx < len(self.character.possessions) for idx in choice])
    self.resolve_internal(choice)

  def resolve_internal(self, choices):
    assert all(idx in self.choices for idx in choices)
    self.chosen = [self.character.possessions[idx] for idx in choices]

  def compute_choices(self, state):
    self.choices = [
      idx for idx, pos in enumerate(self.character.possessions)
      if (getattr(pos, "deck", None) in self.decks)
         and (self.item_type is None or getattr(pos, "item_type") == self.item_type)
    ]

  def is_resolved(self):
    return self.chosen is not None

  def start_str(self):
    return f"{self.character.name} must " + self.prompt()

  def finish_str(self):
    return f"{self.character.name} chose some stuff"

  def prompt(self):
    return self._prompt

  @property
  def choice_count(self):
    return len(self.choices) if self.choices else 0


class CombatChoice(ItemChoice):

  def resolve_internal(self, choices):
    for idx in choices:
      assert getattr(self.character.possessions[idx], "item_type", None) == "weapon"
      assert getattr(self.character.possessions[idx], "hands", None) is not None
      assert getattr(self.character.possessions[idx], "deck", None) != "spells"
    hands_used = sum([self.character.possessions[idx].hands for idx in choices])
    assert hands_used <= self.character.hands_available()
    super(CombatChoice, self).resolve_internal(choices)


class ItemCountChoice(ItemChoice):

  def __init__(self, character, prompt, count, min_count=None, decks=None):
    super(ItemCountChoice, self).__init__(character, prompt, decks=decks)
    self.count = count
    self.min_count = count if min_count is None else min_count

  def resolve_internal(self, choices):
    assert self.min_count <= len(choices) <= self.count
    super(ItemCountChoice, self).resolve_internal(choices)


class SinglePhysicalWeaponChoice(ItemCountChoice):
  def __init__(self, char, prompt):
    super(SinglePhysicalWeaponChoice, self).__init__(char, prompt, 1, min_count=0)

  def compute_choices(self, state):
    self.choices = [
      idx for idx, pos in enumerate(self.character.possessions)
      if (getattr(pos, "deck", None) in self.decks)
         and getattr(pos, "item_type", None) == "weapon"
         and (pos.active_bonuses["physical"] or pos.passive_bonuses["physical"])
    ]



class CardChoice(MultipleChoice):
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
      self.choices = []  # Hack, mark as resolved without setting self.choice.
      return True
    assert choice in self.choices
    self.choice = choice
    return True

  def is_resolved(self):
    # It is possible to have no choices (e.g. with "gate" when there are no gates on the board).
    # In the case where there are no choices, the choice reader must account for it.
    return self.choice is not None or self.choices == []

  def prompt(self):
    return self._prompt


class PlaceChoice(MapChoice):

  VALID_FILTERS = {"streets", "locations", "open", "closed"}

  def __init__(self, character, prompt, choices=None, choice_filters=None, none_choice=None):
    assert choices or choice_filters
    assert not (choices and choice_filters)
    super(PlaceChoice, self).__init__(character, prompt, none_choice=none_choice)
    if choices:
      self.fixed_choices = choices
      self.choice_filters = None
    else:
      assert choice_filters & self.VALID_FILTERS
      assert not choice_filters - self.VALID_FILTERS
      for pair in [{"streets", "locations"}, {"open", "closed"}]:
        if not choice_filters & pair:
          choice_filters |= pair
      self.fixed_choices = None
      self.choice_filters = choice_filters

  def compute_choices(self, state):
    if self.fixed_choices:
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
    super(GateChoice, self).__init__(character, prompt, none_choice=none_choice)
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

  def start_str(self):
    if self.gate_name is not None:
      return f"{self.character.name} must choose a gate to {self.gate_name}"
    return f"{self.character.name} must choose a gate"

  def finish_str(self):
    if self.choice is None:
      return f"there were no open gates to {self.gate_name}"
    return f"{self.character.name} chose the gate at {self.choice}"

  def annotations(self):
    if self.annotation and self.choices is not None:
      return [self.annotation for _ in self.choices]
    return None


class EvadeOrFightAll(Sequence):
  
  def __init__(self, character, monsters):
   self.monsters = monsters
   self.character = character
   super(EvadeOrFightAll, self).__init__(
       [
         EvadeOrCombat(character, monster)
         for monster in monsters
         if monster not in character.avoid_monsters
       ], character)

  def start_str(self):
    return f"{self.character.name} must evade or fight all of: " \
           + ", ".join(mon.name for mon in self.monsters)


"""
# TODO: let the player choose the order in which they fight/evade the monsters
class EvadeOrFightAll(Event):

  def __init__(self, character, monsters):
    assert monsters
    self.character = character
    self.monsters = monsters
    self.result = []

  def resolve(self, state):
    if not self.result:
      self.add_choice(state, self.monsters[0])
      return False
    if self.result[-1].is_resolved():
      if len(self.result) == len(self.monsters):
        return True
      self.add_choice(state, self.monsters[len(self.result)])
      return False
    return True

  def add_choice(self, state, monster):
    choice = EvadeOrCombat(self.character, monster)
    self.result.append(choice)
    state.event_stack.append(choice)

  def is_resolved(self):
    return len(self.result) == len(self.monsters) and self.result[-1].is_resolved()

  def start_str(self):
    return ""

  def finish_str(self):
    return ""
    """


class EvadeOrCombat(Event):

  def __init__(self, character, monster):
    self.character = character
    self.monster = monster
    self.combat = Combat(character, monster)
    self.evade = EvadeRound(character, monster)
    prompt = f"Fight the {monster.name} or evade it?"
    self.choice = BinaryChoice(character, prompt, "Fight", "Evade", self.combat, self.evade)
    self.choice.events[0].monster = monster

  def resolve(self, state):
    if not self.choice.is_resolved():
      state.event_stack.append(self.choice)
      return False
    if self.evade.is_resolved() and self.evade.evaded:
      return True
    if not self.combat.is_resolved():
      state.event_stack.append(self.combat)
      return False
    return True

  def is_resolved(self):
    return self.combat.is_resolved() or (self.evade.is_resolved() and self.evade.evaded)

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class Combat(Event):

  def __init__(self, character, monster):
    self.character = character
    self.monster = monster
    self.horror = None
    self.sanity_loss = None
    self.choice = None
    self.evade = None
    self.combat = None
    self.done = False

  def resolve(self, state):
    # Horror check
    if self.monster.difficulty("horror", state, self.character) is not None and self.horror is None:
      self.horror = Check(
          self.character, "horror", self.monster.difficulty("horror", state, self.character))
      self.sanity_loss = Loss(
          self.character, {"sanity": self.monster.damage("horror", state, self.character)})
    if self.horror is not None:
      if not self.horror.is_resolved():
        state.event_stack.append(self.horror)
        return False
      if not self.sanity_loss.is_resolved():
        # Failed horror check
        if self.horror.successes < 1:
          state.event_stack.append(self.sanity_loss)
          return False
        # Nightmarish for successful horror check
        nightmarish = self.monster.has_attribute("nightmarish", state, self.character)
        if self.horror.successes >= 1 and nightmarish:
          self.sanity_loss = Loss(
              self.character, {"sanity": self.monster.bypass_damage("horror", state)})
          state.event_stack.append(self.sanity_loss)
          return False

    # Combat or flee choice.
    if self.choice is None:
      self.combat = CombatRound(self.character, self.monster)
      self.evade = EvadeRound(self.character, self.monster)
      no_ambush = values.NoAmbushPrerequisite(self.monster, self.character)
      prompt = f"Fight the {self.monster.name} or flee from it?"
      self.choice = BinaryChoice(
          self.character, prompt, "Flee", "Fight", self.evade, self.combat, no_ambush)
      self.choice.events[0].monster = self.monster
      state.event_stack.append(self.choice)
      return False

    assert self.choice.is_resolved()
    if self.evade.evaded:
      return True
    if self.combat.defeated:
      self.character.possessions.append(self.monster)
      return True
    self.choice = None
    return False

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
    self.check = None
    self.damage = None
    self.evaded = None

  def resolve(self, state):
    if self.evaded is not None:
      return True
    if self.check is None:
      self.check = Check(
          self.character, "evade", self.monster.difficulty("evade", state, self.character))
    if not self.check.is_resolved():
      state.event_stack.append(self.check)
      return False
    if self.check.successes >= 1:
      self.evaded = True
      self.character.avoid_monsters.append(self.monster)
      return True
    self.damage = Loss(
        self.character, {"stamina": self.monster.damage("combat", state, self.character)})
    self.character.movement_points = 0
    state.event_stack.append(self.damage)
    return False

  def is_resolved(self):
    return self.evaded or (self.damage is not None and self.damage.is_resolved())

  def start_str(self):
    return f"{self.character.name} attempted to flee from {self.monster.name}"

  def finish_str(self):
    if self.evaded:
      return f"{self.character.name} evaded a {self.monster.name}"
    return f"{self.character.name} did not evade the {self.monster.name} and lost any remaining movement"


class CombatRound(Event):

  def __init__(self, character, monster):
    self.character = character
    self.monster = monster
    self.check = None
    self.damage = None
    self.choice = CombatChoice(character, f"Choose weapons to fight the {monster.name}")
    self.choice.monster = self.monster
    self.activate = None
    self.defeated = None

  def resolve(self, state):
    self.character.movement_points = 0
    if self.defeated is not None:
      return True
    if not self.choice.is_resolved():
      state.event_stack.append(self.choice)
      return False
    if len(self.choice.choices) > 0 and self.activate is None:
      self.activate = ActivateChosenItems(self.character, self.choice)
      state.event_stack.append(self.activate)
      return False
    if self.check is None:
      attrs = self.monster.attributes(state, self.character)
      self.check = Check(
          self.character, "combat", self.monster.difficulty("combat", state, self.character), attrs)
    if not self.check.is_resolved():
      state.event_stack.append(self.check)
      return False
    if self.check.successes >= self.monster.toughness(state, self.character):
      if self.monster.has_attribute("overwhelming", state, self.character) and self.damage is None:
        self.damage = Loss(
            self.character, {"stamina": self.monster.bypass_damage("combat", state)})
        state.event_stack.append(self.damage)
        return False
      # TODO: take the monster as a trophy
      # Stand-in until we implement trophy code to allow MoveMultipleThroughMonster test to work
      self.monster.place = None
      self.defeated = True
      return True
    self.defeated = False
    self.damage = Loss(
        self.character, {"stamina": self.monster.damage("combat", state, self.character)})
    state.event_stack.append(self.damage)
    return False

  def is_resolved(self):
    if self.defeated is None:
      return False
    return self.damage is None or self.damage.is_resolved()

  def start_str(self):
    return f"{self.character.name} started a combat round against a {self.monster.name}"

  def finish_str(self):
    if self.defeated:
      return f"{self.character.name} defeated a {self.monster.name}"
    return f"{self.character.name} did not defeat the {self.monster.name}"


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
    self.return_choice = None
    self.returned = None

  def resolve(self, state):
    if self.return_choice is None:
      self.return_choice = GateChoice(
          self.character, "Choose a gate to return to", self.world_name, annotation="Return")
      state.event_stack.append(self.return_choice)
      return False
    assert self.return_choice.is_resolved()

    if self.return_choice.choice is None:  # Unable to return
      self.returned = False  # TODO: lost in time and space
      return True
    self.character.place = state.places[self.return_choice.choice]
    self.character.explored = True
    self.returned = True
    return True

  def is_resolved(self):
    return self.returned is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.character.name} returned"


class PullThroughGate(Sequence):

  def __init__(self, chars, world_name):
    assert chars
    self.chars = chars
    self.world_name = world_name
    seq = []
    for char in chars:
      seq.extend([Travel(char, world_name), Delayed(char)])
    super(PullThroughGate, self).__init__(seq)

  def start_str(self):
    return f"{len(self.chars)} will be pulled through to {self.world_name}"


class GateCloseAttempt(Event):

  def __init__(self, character, location_name):
    self.character = character
    self.location_name = location_name
    self.choice = None
    self.check = None
    self.seal_choice = None
    self.closed = None
    self.sealed = None

  def resolve(self, state):
    if self.choice is None:
      self.choice = MultipleChoice(
          self.character, "Close the gate?", ["Close with fight", "Close with lore", "Don't close"])
      state.event_stack.append(self.choice)
      return False

    assert self.choice.is_resolved()
    if self.choice.choice == "Don't close":
      self.closed = False
      self.sealed = False
      return True

    if self.check is None:
      difficulty = state.places[self.location_name].gate.difficulty(state)
      attribute = "lore" if self.choice.choice == "Close with lore" else "fight"
      self.check = Check(self.character, attribute, difficulty)
      state.event_stack.append(self.check)
      return False

    assert self.check.is_resolved()
    if not self.check.successes:
      self.closed = False
      self.sealed = False
      return True

    if not self.closed:
      self.closed = True
      state.gates.append(state.places[self.location_name].gate)  # TODO: take a gate trophy
      state.places[self.location_name].gate = None
      closed_until = state.places[self.location_name].closed_until or -1
      if closed_until > state.turn_number:
        state.event_stack.append(
            CloseLocation(self.location_name, closed_until - state.turn_number - 1)
        )
        return False

    if self.seal_choice is None:
      if self.character.clues < 5:  # TODO: this can also have modifiers
        self.sealed = False
        return True
      self.seal_choice = MultipleChoice(
          self.character, "Seal the gate with 5 clue tokens?", ["Yes", "No"])
      state.event_stack.append(self.seal_choice)
      return False

    assert self.seal_choice.is_resolved()
    if self.seal_choice.choice == "No":
      self.sealed = False
      return True

    self.character.clues -= 5  # TODO: spending clues in other ways
    state.places[self.location_name].sealed = True
    self.sealed = True
    return True

  def is_resolved(self):
    return self.closed is not None and self.sealed is not None

  def start_str(self):
    pass

  def finish_str(self):
    if self.choice.choice == "Don't close":
      return f"{self.character.name} chose not to close the gate at {self.location_name}"
    if not self.closed:
      return f"{self.character.name} failed to close the gate at {self.location_name}"
    if not self.sealed == 1:
      return f"{self.character.name} closed the gate at {self.location_name} but did not seal it"
    return f"{self.character.name} closed and sealed the gate at {self.location_name}"


class OpenGate(Event):

  def __init__(self, location_name):
    self.location_name = location_name
    self.opened = None
    self.spawn = None

  def resolve(self, state):
    if self.spawn is not None:
      assert self.spawn.is_resolved()
      return True

    if state.places[self.location_name].sealed:
      self.opened = False
      return True
    if state.places[self.location_name].gate is not None:
      self.opened = False
      self.spawn = MonsterSurge(self.location_name)
      state.event_stack.append(self.spawn)
      return False

    # TODO: if there are no gates tokens left, the ancient one awakens
    self.opened = state.gates.popleft()
    state.places[self.location_name].gate = self.opened
    state.places[self.location_name].clues = 0  # TODO: this should be its own event
    self.spawn = SpawnGateMonster(self.location_name)
    state.event_stack.append(self.spawn)
    return False

  def is_resolved(self):
    if self.spawn is not None:
      return self.spawn.is_resolved()
    return self.opened is not None

  def start_str(self):
    return f"Gate will open at {self.location_name}"

  def finish_str(self):
    if self.opened:
      return f"A gate to {self.opened.name} appeared at {self.location_name}."
    return f"A gate did not appear at {self.location_name}."


class MonsterSpawnChoice(ChoiceEvent):

  def __init__(self):
    self.location_name = None
    self.spawned = None
    self.open_gates = None
    self.max_count = None
    self.min_count = None
    self.spawn_count = None
    self.outskirts_count = None
    self.num_clears = None
    self.character = None
    self.to_spawn = None

  @abc.abstractmethod
  def compute_open_gates(self, state):
    pass

  @abc.abstractmethod
  def initial_count(self, state):
    pass

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
    if self.to_spawn is not None:
      return
    if self.location_name is not None:
      assert getattr(state.places[self.location_name], "gate", None) is not None
    self.compute_open_gates(state)
    open_count = len(self.open_gates)
    on_board = len([m for m in state.monsters if isinstance(m.place, places.CityPlace)])
    in_outskirts = len([m for m in state.monsters if isinstance(m.place, places.Outskirts)])
    self.spawn_count, self.outskirts_count, cup_count, self.num_clears = self.spawn_counts(
        self.initial_count(state), on_board, in_outskirts,
        state.monster_limit(), state.outskirts_limit(),
    )
    self.min_count = self.spawn_count // open_count
    self.max_count = (self.spawn_count + open_count - 1) // open_count
    self.character = state.characters[state.first_player]
    monster_indexes = [
        idx for idx, monster in enumerate(state.monsters) if monster.place == state.monster_cup]
    # TODO: if there are no monsters left, the ancient one awakens.
    self.to_spawn = random.sample(
        monster_indexes, self.spawn_count + self.outskirts_count + cup_count
    )

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
    city_choices = [val for key, val in choice.items() if key != "Outskirts"]
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


class SpawnGateMonster(MonsterSpawnChoice):

  def __init__(self, location_name):
    super(SpawnGateMonster, self).__init__()
    self.location_name = location_name

  def compute_open_gates(self, state):
    self.open_gates = [self.location_name]

  def initial_count(self, state):
    return 2 if len(state.characters) > 4 else 1


class MonsterSurge(MonsterSpawnChoice):

  def __init__(self, location_name):
    super(MonsterSurge, self).__init__()
    self.location_name = location_name  # May be None for certain mythos cards.

  def compute_open_gates(self, state):
    self.open_gates = [
        name for name, place in state.places.items() if getattr(place, "gate", None) is not None
    ]

  def initial_count(self, state):
    return max(len(self.open_gates), len(state.characters))


class SpawnClue(Event):

  def __init__(self, location_name):
    self.location_name = location_name
    self.spawned = None
    self.eligible = None
    self.choice = None

  def resolve(self, state):
    if self.spawned is not None:
      return True

    if self.choice is not None:
      assert self.choice.is_resolved()
      self.eligible[self.choice.choice_index].clues += 1
      self.spawned = True
      return True

    if state.places[self.location_name].gate is not None:
      self.spawned = False
      return True

    self.eligible = [
        char for char in state.characters if char.place == state.places[self.location_name]]

    if len(self.eligible) == 0:
      state.places[self.location_name].clues += 1
      self.spawned = True
      return True
    if len(self.eligible) == 1:
      self.eligible[0].clues += 1
      self.spawned = True
      return True
    self.choice = MultipleChoice(
        state.characters[state.first_player],
        f"Choose an investigator to receive the clue token at {self.location_name}",
        [char.name for char in self.eligible],
    )
    state.event_stack.append(self.choice)
    return False

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
      receiving_player = self.eligible[self.choice.choice_index]
    return f"{receiving_player.name} received a clue."


class MoveMonsters(Event):

  def __init__(self, white_dimensions, black_dimensions):
    self.white_dimensions = white_dimensions
    self.black_dimensions = black_dimensions
    self.moves = None

  def resolve(self, state):
    if self.moves is None:
      self.moves = []
      for monster in state.monsters:
        if not isinstance(monster.place, places.CityPlace):
          continue
        if monster.dimension not in self.white_dimensions | self.black_dimensions:
          continue

        move_color = "white" if monster.dimension in self.white_dimensions else "black"
        num_moves = 1
        if monster.movement == "stationary":
          num_moves = 0
        elif monster.movement == "fast":
          num_moves = 2
        for _ in range(num_moves):
          self.moves.append(MoveMonster(monster, move_color))

    # self.moves has been set.
    for move in self.moves:
      if not move.is_resolved():
        state.event_stack.append(move)
        return False
    return True

  def is_resolved(self):
    return self.moves is not None and all([move.is_resolved() for move in self.moves])

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

  def resolve(self, state):
    self.source = self.monster.place

    if self.monster.place is None or not hasattr(self.monster.place, "movement"):
      self.destination = False
      return True

    if self.color not in self.monster.place.movement:
      self.destination = False
      return True

    self.destination = self.monster.place.movement[self.color]
    self.monster.place = self.destination
    # TODO: other movement types (flying, unique, stalker, aquatic)
    return True

  def is_resolved(self):
    return self.destination is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.destination:
      return ""
    return f"{self.monster.name} moved from {self.source.name} to {self.destination.name}"


class ReturnToCup(Event):

  def __init__(self, names=None, places=None):
    assert names or places
    assert not (names and places)
    self.names = set(names if names else [])
    self.places = set(places if places else [])
    self.returned = None

  def resolve(self, state):
    if self.returned is not None:
      return True

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
    return True

  def is_resolved(self):
    return self.returned is not None

  def start_str(self):
    if self.names is not None:
      return "All " + ", ".join(self.names) + " will be returned to the cup."
    return "All monsters in " + ", ".join(self.places) + " will be returned to the cup."

  def finish_str(self):
    return f"{self.returned} monsters returned to the cup"

class CloseLocation(Event):

  def __init__(self, location_name, for_turns=float('inf'), evict=True):
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
      self.evict = False # So we don't keep looping
      return False

    self.resolved = True
    return True

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
    state.environment = self.env
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.env.name} is the new environment"
