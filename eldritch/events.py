import abc
import collections
import math
import operator
from random import SystemRandom
from typing import (
    Collection, List, Dict, Optional, Union, NoReturn, TYPE_CHECKING,
)

from eldritch import assets
from eldritch import places
from eldritch import values

from game import InvalidMove, InvalidInput

if TYPE_CHECKING:
  from eldritch.eldritch import GameState
  from eldritch import items

random = SystemRandom()


# TODO: pull this from Card class without creating an import loop
DECKS = {"common", "unique", "spells", "skills", "allies", "tradables", "specials"}


class EventLog:

  def __init__(self, text, flatten):
    self.text: str = text
    self.flatten: bool = flatten
    self.sub_events: List[EventLog] = []

  def __str__(self):
    results = self.format()
    return "\n".join(results)

  def format(self, indent=0):
    results = [indent * "  " + self.text]
    for sub_event in self.sub_events:
      results.extend(sub_event.format(indent+1))
    return results

  def json_repr(self):
    return {"text": self.text, "sub_events": self.sub_events}


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

  def __init__(self):
    self.cancelled = False

  @abc.abstractmethod
  def resolve(self, state: "GameState") -> NoReturn:
    # resolve should return True if the event was resolved, False otherwise.
    # For example, an event that requires a check to be made should add that check to the end
    # of the event stack, and then return False. It will be called again when the check is
    # finished with the results of the check accessible.
    raise NotImplementedError

  @abc.abstractmethod
  def is_resolved(self) -> bool:
    raise NotImplementedError

  def is_cancelled(self) -> bool:
    return self.cancelled

  def is_done(self) -> bool:
    return self.is_cancelled() or self.is_resolved()

  def flatten(self) -> bool:
    return False

  def animated(self) -> bool:
    return False

  @abc.abstractmethod
  def log(self, state) -> str:
    raise NotImplementedError


class ChoiceEvent(Event):
  def __init__(self):
    super().__init__()
    self._choices = None

  @property
  def choices(self):
    return self._choices

  @abc.abstractmethod
  def resolve(
      self, state: "GameState", choice=None
  ) -> NoReturn:  # pylint: disable=arguments-differ
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
    super().__init__()
    self.done = False

  def resolve(self, state):
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    return ""


class Unimplemented(Nothing):
  pass


class Animate(Nothing):

  def animated(self):
    return True


class Sequence(Event):

  def __init__(self, events, character=None):
    super().__init__()
    self.events: List[Event] = events
    if not self.events:
      self.events = [Nothing()]
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

  def flatten(self):
    return True

  def log(self, state):
    return ""


class CancelEvent(Event):

  def __init__(self, to_cancel):  # TODO: cancel message?
    super().__init__()
    self.to_cancel = to_cancel

  def resolve(self, state):
    self.to_cancel.cancelled = True

  def is_resolved(self):
    return self.to_cancel.is_cancelled()

  def log(self, state):
    return ""


class Turn(Event, metaclass=abc.ABCMeta):

  def check_lose_turn(self) -> bool:
    char = getattr(self, "character", None)
    if not char:
      return False
    if not (char.lose_turn_until is None and char.arrested_until is None):
      self.cancelled = True
      return True
    return False


class Upkeep(Turn):

  def __init__(self, character):
    super().__init__()
    self.character = character
    self.focus_given = False
    self.reappear: Optional[Event] = None
    self.refresh: Optional[RefreshAssets] = None
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
    if self.sliders is None:
      self.sliders = SliderInput(self.character)
      state.event_stack.append(self.sliders)
      return
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and not self.focus_given:
      return f"[{self.character.name}]'s upkeep was skipped"
    return f"[{self.character.name}]'s upkeep"


class SliderInput(Event):

  def __init__(self, character, free=False):
    super().__init__()
    self.character = character
    self.pending = self.character.sliders()
    assert len(self.pending) >= 3
    self.free = free
    self.done = False

  def resolve(self, state, name, value):  # pylint: disable=arguments-differ
    if not isinstance(name, str):
      raise InvalidInput(f"Invalid slider name {name}")
    if name not in self.pending.keys() | {"done", "reset"}:
      raise InvalidInput(f"Unknown slider {name}")
    if name == "done":
      if not self.free:
        if self.character.focus_cost(self.pending) > self.character.slider_focus_available():
          raise InvalidMove("You do not have enough focus/slider shifts.")
        self.character.spend_slider_focus(self.character.focus_cost(self.pending))
      for slider_name, slider_value in self.pending.items():
        setattr(self.character, slider_name + "_slider", slider_value)
      self.done = True
      return
    if name == "reset":
      self.pending = self.character.sliders()
      return

    if not isinstance(value, int):
      raise InvalidMove(f"Invalid slider stop {value}")
    if value < 0:
      raise InvalidMove(f"Slider stop {value} must be >= 0")
    if value >= len(getattr(self.character, "_" + name)):
      raise InvalidMove(f"Slider stop {value} is too large")
    pending = self.pending.copy()
    pending[name] = value
    if not self.free:
      if self.character.focus_cost(pending) > self.character.slider_focus_available():
        raise InvalidMove("You do not have enough focus/slider shifts.")
    self.pending = pending

  def prompt(self):
    if self.free:
      return f"[{self.character.name}] to set sliders anywhere"
    remaining_focus = (
        self.character.slider_focus_available() - self.character.focus_cost(self.pending)
    )
    return f"[{self.character.name}] to set sliders ({remaining_focus} shifts remaining)"

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled:
      return f"[{self.character.name}] did not get to set sliders"
    if self.done:
      return f"[{self.character.name}] set sliders"
    return f"[{self.character.name}] must set sliders"


class MoveSliders(Event):
  def __init__(self, character, slider_dests: dict):
    super().__init__()
    self.character = character
    self.slider_dests = slider_dests
    self.done = False

  def resolve(self, state):
    for slider, val in self.slider_dests.items():
      setattr(self.character, slider, val)
    self.done = True

  def is_resolved(self) -> bool:
    return self.done

  def log(self, state):
    if self.cancelled:
      return f"Force movement of {self.character.name}'s sliders was cancelled"
    if self.done:
      return f"[{self.character.name}] sliders set to: {self.slider_dests}"
    return f"[{self.character.name}] sliders will be moved"

  def animated(self) -> bool:
    return True


class Movement(Turn):

  def __init__(self, character):
    super().__init__()
    self.character = character
    self.move: Optional[Event] = None
    self.delayed = False
    self.done = False

  def resolve(self, state):
    self.character.avoid_monsters = []
    if self.check_lose_turn():
      return
    if self.character.delayed_until is not None:
      if self.character.delayed_until <= state.turn_number:
        self.character.delayed_until = None
      else:
        self.cancelled = True
        self.delayed = True
        return

    if self.move is None:
      if isinstance(self.character.place, places.OtherWorld):
        if self.character.place.order == 1:
          world_name = self.character.place.info.name + "2"
          self.move = ForceMovement(self.character, world_name)
        else:
          self.move = Return(self.character, self.character.place.info.name)
      elif isinstance(self.character.place, places.CityPlace):
        self.character.movement_points = self.character.movement_speed()
        self.move = CityMovement(self.character)
      else:
        self.move = Nothing()
      state.event_stack.append(self.move)
      return

    assert self.move.is_done()
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled:
      suffix = " (delayed)" if self.delayed else ""
      return f"[{self.character.name}]'s movement was skipped{suffix}"
    return f"[{self.character.name}]'s movement"


class CityMovement(ChoiceEvent):

  def __init__(self, character):
    super().__init__()
    self.character = character
    self.routes = {}
    self.moved = False
    self.none_choice = "done"
    self.done = False

  def resolve(self, state, choice=None):
    if choice == self.none_choice:
      self.done = True
      return
    if choice not in self.routes:
      raise InvalidMove("That is not a valid destination.")
    self.moved = True
    state.event_stack.append(
        Sequence([MoveOne(self.character, dest) for dest in self.routes[choice]], self.character))

  def is_resolved(self):
    return self.done

  def flatten(self):
    return True

  def log(self, state):
    return ""
    # if not self.done:
    #   return f"[{self.character.name}] to move"
    # if self.moved:
    #   return f"[{self.character.name}] moved"
    # return f"[{self.character.name}] did not move"

  def prompt(self):
    return f"[{self.character.name}] to move ({self.character.movement_points} move remaining)"

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


class WagonMove(Sequence):
  pass


class EncounterPhase(Turn):

  def __init__(self, character):
    super().__init__()
    self.character = character
    self.action: Optional[Event] = None
    self.done = False

  def resolve(self, state):
    if self.check_lose_turn():
      return
    if self.action is None:
      if not isinstance(self.character.place, places.Location):
        self.action = Nothing()
        self.action.done = True
        self.done = True
        return
      if self.character.place.gate and self.character.explored:
        self.action = GateCloseAttempt(self.character, self.character.place.name)
      elif self.character.place.gate:
        self.action = Travel(self.character)
      elif self.character.place.fixed_encounters:
        choices = [self.character.place.neighborhood.name + " Card"]
        prereqs = [None]
        spends = [None]
        results = {0: Encounter(self.character)}
        for idx, fixed in enumerate(self.character.place.fixed_encounters):
          choices.append(fixed.name)
          prereqs.append(fixed.prereq(self.character))
          spends.append(fixed.spend(self.character))
          results[idx+1] = fixed.encounter(self.character, state)
        choice = CardSpendChoice(self.character, "Encounter?", choices, prereqs, spends=spends)
        cond = Conditional(self.character, choice, "choice_index", results)
        self.action = Sequence([choice, cond], self.character)
      else:
        self.action = Encounter(self.character)
      state.event_stack.append(self.action)
      return

    assert self.action.is_done()
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and self.action is None:
      return f"[{self.character.name}]'s encounter phase was skipped"
    return f"[{self.character.name}]'s encounter phase"


class OtherWorldPhase(Turn):

  def __init__(self, character):
    super().__init__()
    self.character = character
    self.action: Optional[Event] = None
    self.done = False

  def resolve(self, state):
    if self.check_lose_turn():
      return
    if self.action is None:
      if not isinstance(self.character.place, places.OtherWorld):
        self.action = Nothing()
        self.action.done = True
        self.done = True
        return
      self.action = GateEncounter(self.character)
      state.event_stack.append(self.action)
      return

    assert self.action.is_done()
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and self.action is None:
      return f"[{self.character.name}]'s other world phase was skipped"
    return f"[{self.character.name}]'s other world phase"


class Mythos(Turn):

  def __init__(self, _):
    super().__init__()
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

  def log(self, state):
    first_player = state.characters[state.first_player]
    return f"[{first_player.name}]'s mythos phase"


class InvestigatorAttack(Turn):

  def __init__(self, character):
    super().__init__()
    self.character = character
    self.choice: Event = CombatChoice(character, "Choose weapons to fight the ancient one")
    self.check: Optional[Check] = None
    self.damage: Optional[Event] = None

  def resolve(self, state):
    if not self.choice.is_done():
      self.choice.monster = state.ancient_one
      state.event_stack.append(self.choice)
      return

    if self.check is None:
      attrs = state.ancient_one.attributes(state, self.character)
      self.check = Check(
          self.character, "combat", state.ancient_one.combat_rating(state, self.character),
          attributes=attrs, name=state.ancient_one.name,
      )
    if not self.check.is_done():
      state.event_stack.append(self.check)
      return

    if self.check.success and self.damage is None:
      self.damage = DamageAncientOne(self.character, self.check.successes)
      state.event_stack.append(self.damage)

  def is_resolved(self):
    if self.check is None:
      return False
    if self.check.is_done() and not self.check.success:
      return True
    return self.damage is not None and self.damage.is_done()

  def log(self, state):
    return f"[{self.character.name}]'s attack"


class DamageAncientOne(Event):

  def __init__(self, character, successes):
    super().__init__()
    self.character = character
    self.successes = successes
    self.done = False

  def resolve(self, state):
    state.ancient_one.health -= self.successes
    state.ancient_one.health = max(0, state.ancient_one.health)
    if state.ancient_one.health <= 0:
      state.game_stage = "victory"
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    return (
        f"[{self.character.name}] had {self.successes} successes against [{state.ancient_one.name}]"
    )

  def animated(self):
    return True


class AncientAttack(Turn):

  def __init__(self, _):
    super().__init__()
    self.attack: Optional[Event] = None
    self.escalated = False
    self.done = False

  def resolve(self, state):
    if self.attack is None:
      self.attack = state.ancient_one.attack(state)
      state.event_stack.append(self.attack)
      return

    if not self.escalated:
      state.ancient_one.escalate(state)
      self.escalated = True

    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    return f"[{state.ancient_one.name}]'s attack"

  def animated(self):
    return True


class DiceRoll(Event):

  def __init__(self, character, count, *, name=None, bad=None):
    super().__init__()
    self.character = character
    self.count = count
    self.name = name
    self.bad = bad
    self.roll = None
    self.sum = None
    self.successes = None

  def resolve(self, state):
    if isinstance(self.count, values.Value):
      self.count = self.count.value(state)
    self.roll = [random.randint(1, 6) for _ in range(self.count)]
    self.sum = sum(self.roll)
    # Some encounters have: "Roll a die for each X. On a success..."
    self.successes = self.character.count_successes(self.roll, None)

  def is_resolved(self):
    return self.roll is not None

  def log(self, state):
    if self.roll is None:
      if self.cancelled:
        return f"[{self.character.name}] did not roll dice"
      count = values.Calculation(self.count, None, max, 0).value(state)
      return f"[{self.character.name}] rolls {count} dice"
    if not self.roll:
      return f"[{self.character.name}] rolled no dice"
    return f"[{self.character.name}] rolled {' '.join(str(x) for x in self.roll)}"

  def animated(self):
    return True


class BonusDiceRoll(DiceRoll):
  pass


class MoveOne(Event):

  def __init__(self, character, dest):
    super().__init__()
    self.character = character
    self.dest = dest
    self.done = False
    self.moved = None

  def resolve(self, state):
    if self.character.movement_points <= 0:
      self.cancelled = True
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

  def log(self, state):
    if self.cancelled and not self.moved:
      return f"[{self.character.name}] could not move to [{self.dest}]"
    if self.moved is None:
      return f"[{self.character.name}] moving from [{self.character.place.name}] to [{self.dest}]"
    if self.moved:
      return f"[{self.character.name}] moved to [{self.dest}]"
    return (
        f"[{self.character.name}] could not move from "
        f"[{self.character.place.name}] to [{self.dest}]"
    )

  def animated(self):
    return True


class GainOrLoss(Event):

  def __init__(self, character, gains, losses, source=None):
    assert not gains.keys() - {"stamina", "sanity", "dollars", "clues"}
    assert not losses.keys() - {"stamina", "sanity", "dollars", "clues"}
    assert not gains.keys() & losses.keys()
    assert all(isinstance(val, (int, values.Value)) or math.isinf(val) for val in gains.values())
    assert all(isinstance(val, (int, values.Value)) or math.isinf(val) for val in losses.values())
    super().__init__()
    self.character = character
    self.gains = gains
    self.losses = losses
    self.source = source
    self.final_adjustments = None

  def __repr__(self):
    repr_str = str(type(self))[:-1] + " {}: {}/{}{}>"
    return repr_str.format(
        self.character.name, self.gains, self.losses, " cancelled" if self.cancelled else ""
    )

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

  def log(self, state):
    # The whole thing was cancelled.
    if self.cancelled and not self.final_adjustments:
      gains = "/".join(self.gains.keys())
      losses = "/".join(self.losses.keys())
      if self.gains and self.losses:
        return f"[{self.character.name}] did not gain {gains} or lose {losses}"
      if self.gains:
        return f"[{self.character.name}] did not gain {gains}"
      if self.losses:
        return f"[{self.character.name}] did not lose {losses}"
      return f"nothing changed for [{self.character.name}]"

    # Has not yet finished.
    if self.final_adjustments is None:
      gains = ", ".join(
          str(gain.value(state) if isinstance(gain, values.Value) else gain) + f" {attr}"
          for attr, gain in self.gains.items()
      )
      losses = ", ".join(
          str(loss.value(state) if isinstance(loss, values.Value) else loss) + f" {attr}"
          for attr, loss in self.losses.items()
      )
      if self.gains and self.losses:
        return f"[{self.character.name}] will gain {gains} and lose {losses}"
      if self.gains:
        return f"[{self.character.name}] will gain {gains}"
      if self.losses:
        return f"[{self.character.name}] will lose {losses}"
      return f"nothing will change for [{self.character.name}]"

    # Finished.
    gains = ", ".join([
        f"{count} {attr}" for attr, count in self.final_adjustments.items() if count > 0])
    losses = ", ".join([
        f"{-count} {attr}" for attr, count in self.final_adjustments.items() if count < 0])
    if gains and losses:
      return f"[{self.character.name}] gained {gains} and lost {losses}"
    if gains:
      return f"[{self.character.name}] gained {gains}"
    if losses:
      return f"[{self.character.name}] lost {losses}"
    return f"nothing changed for [{self.character.name}]"

  def animated(self):
    return True


def Gain(character, gains, source=None):
  return GainOrLoss(character, gains, {}, source=source)


def Loss(character, losses, source=None):
  return GainOrLoss(character, {}, losses, source=source)


class SplitGain(Event):

  def __init__(self, character, attr1, attr2, amount):
    assert isinstance(amount, (int, values.Value))
    super().__init__()
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

  def flatten(self):
    return True

  def log(self, state):
    return ""


class GainOrLossPrevention(Event):

  def __init__(self, prevention_source, source_event, attribute, amount, gain_or_loss):
    assert isinstance(source_event, GainOrLoss)
    assert isinstance(amount, (int, values.Value)) or math.isinf(amount)
    assert gain_or_loss in {"gains", "losses"}
    assert attribute in getattr(source_event, gain_or_loss)
    super().__init__()
    self.prevention_source = prevention_source
    self.source_event: GainOrLoss = source_event
    self.attribute = attribute
    self.amount = amount
    self.gain_or_loss = gain_or_loss
    self.prevented = None

  def resolve(self, state):
    gains_or_losses = getattr(self.source_event, self.gain_or_loss)
    reduced_loss = values.Calculation(
        gains_or_losses[self.attribute], None, operator.sub, self.amount)
    gains_or_losses[self.attribute] = reduced_loss
    self.prevented = self.amount
    if isinstance(self.amount, values.Value):
      self.prevented = self.amount.value(state)

  def is_resolved(self):
    return self.prevented is not None

  def log(self, state):
    action = {"gains": "gain", "losses": "loss"}[self.gain_or_loss]
    if self.prevented is None:
      amount = self.amount.value(state) if isinstance(self.amount, values.Value) else self.amount
      return f"[{self.prevention_source.name}] will prevent {amount} {self.attribute} {action}"
    if not self.prevented:
      return ""
    return f"[{self.prevention_source.name}] prevented {self.prevented} {self.attribute} {action}"


def LossPrevention(prevention_source, source_event, attribute, amount):
  return GainOrLossPrevention(prevention_source, source_event, attribute, amount, "losses")


def GainPrevention(prevention_source, source_event, attribute, amount):
  return GainOrLossPrevention(prevention_source, source_event, attribute, amount, "gains")


class CapStatsAtMax(Event):

  def __init__(self, character):
    super().__init__()
    self.character = character
    self.done = False

  def resolve(self, state):
    self.character.sanity = min(self.character.sanity, self.character.max_sanity(state))
    self.character.stamina = min(self.character.stamina, self.character.max_stamina(state))
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    return ""

  def animated(self):
    return True


class CollectClues(GainOrLoss):

  def __init__(self, character, place):
    super().__init__(character, {"clues": values.Calculation(place, "clues")}, {})
    self.place = place

  def resolve(self, state):
    super().resolve(state)
    self.place.clues -= (self.picked_up or 0)

  @property
  def picked_up(self):
    if self.final_adjustments is None:
      return None
    return self.final_adjustments.get("clues", 0)

  def log(self, state):
    if self.cancelled:
      return f"[{self.character.name}] did not pick up clues at [{self.place.name}]"
    if self.is_resolved():
      if self.picked_up:
        return f"[{self.character.name}] picked up {self.picked_up} clues"
      return f"no clues for [{self.character.name}] at [{self.place.name}]"
    return f"[{self.character.name}] will pick up {self.place.clues} clues at [{self.place.name}]"


class StackClearMixin:

  def clear_stack(self, state):
    saved_interrupts = state.interrupt_stack[-1]
    saved_triggers = state.trigger_stack[-1]
    saved_log = state.log_stack[-1]
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
    state.log_stack.append(saved_log)
    state.event_stack.append(self)
    assert len(state.event_stack) == len(state.trigger_stack)
    assert len(state.event_stack) == len(state.interrupt_stack)
    assert len(state.event_stack) == len(state.log_stack)


class InsaneOrUnconscious(StackClearMixin, Event):

  def __init__(self, character, attribute, desc):
    assert attribute in {"sanity", "stamina"}
    super().__init__()
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
      lose_count = values.Calculation(values.ItemCount(self.character), None, operator.floordiv, 2)
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

  def log(self, state):
    if self.cancelled and not self.stack_cleared:
      neg_desc = self.desc.replace("went", "go").replace("passed", "pass")
      return f"[{self.character.name}] did not {neg_desc}"
    if isinstance(self.force_move, ForceMovement):
      return (
          f"[{self.character.name}] {self.desc} "
          f"and woke up in the [{self.force_move.location_name}]"
      )
    return f"[{self.character.name}] {self.desc}"

  def animated(self):
    return True


def Insane(character):
  return InsaneOrUnconscious(character, "sanity", "went insane")


def Unconscious(character):
  return InsaneOrUnconscious(character, "stamina", "passed out")


class Devoured(StackClearMixin, Event):

  def __init__(self, character):
    super().__init__()
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
      if state.game_stage == "awakened":
        if all(char.gone for char in state.characters):
          state.game_stage = "defeat"

  def is_resolved(self):
    return self.stack_cleared

  def log(self, state):
    if self.cancelled and not self.stack_cleared:
      return f"[{self.character.name}] was not devoured"
    return f"[{self.character.name}] was devoured"

  def animated(self):
    return True


class DelayOrLoseTurn(Event):

  def __init__(self, character, status, which="next"):
    assert status in {"delayed", "lose_turn", "arrested"}
    assert which in {"this", "next"}
    super().__init__()
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

  def log(self, state):
    if self.cancelled and self.until is None:
      if self.attr == "delayed_until":
        return f"[{self.character.name}] was not delayed"
      return f"[{self.character.name}] did not lose their turn"
    if self.until is None:
      if self.attr == "delayed_until":
        return f"[{self.character.name}] will be delayed"
      if self.num_turns == 1:
        return f"[{self.character.name}] will lose the remainder of their turn"
      return f"[{self.character.name}] will lose a turn"

    if self.attr == "delayed_until":
      return f"[{self.character.name}] was delayed"
    if self.num_turns == 1:
      return f"[{self.character.name}] lost the remainder of their turn"
    return f"[{self.character.name}] lost their next turn"

  def animated(self):
    return True


def Delayed(character):
  return DelayOrLoseTurn(character, "delayed")


def LoseTurn(character):
  return DelayOrLoseTurn(character, "lose_turn")


class ClearStatus(Event):
  def __init__(self, character, status):
    assert status in {"delayed", "lose_turn", "arrested"}
    super().__init__()
    self.character = character
    self.status = status
    self.done = False

  def resolve(self, state):
    setattr(self.character, self.status + "_until", None)
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.done:
      return f"[{self.character.name}] had their {self.status} cleared"
    if self.cancelled:
      return f"[{self.character.name}] had their {self.status} clearing cancelled"
    return f"[{self.character.name}] will have their {self.status} cleared"

  def animated(self):
    return True


class LostInTimeAndSpace(Sequence):

  def __init__(self, character):
    super().__init__([ForceMovement(character, "Lost"), LoseTurn(character)], character)


class BlessCurse(Sequence):
  # TODO: make a subclass of conditional?
  def __init__(self, character, positive):
    if positive:
      card = "Blessing"
    else:
      card = "Curse"
    draw = DrawNamed(character, "specials", card)
    super().__init__([
        draw,
        KeepDrawn(character, draw)], character
    )


class Bless(BlessCurse):
  def __init__(self, character):
    super().__init__(character, True)


class Curse(BlessCurse):
  def __init__(self, character):
    super().__init__(character, False)


def MembershipChange(character, positive):
  if positive:
    return DrawSpecific(character, "specials", "Lodge Membership")
  return DiscardNamed(character, "Lodge Membership")


class StatusChange(Event):

  def __init__(self, character, status, positive=True):
    assert status in {"retainer", "bank_loan"}
    super().__init__()
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

  def log(self, state):  # TODO: rewrite
    if not self.change:
      return "nothing changed"
    status_map = {
        "retainer_start": {-1: " lost their retainer", 1: " received a retainer"},
        "bank_loan_start": {-1: " lost their bank loan??", 1: " received a bank loan"},
    }
    return self.character.name + status_map[self.attr][self.change]


class TakeBankLoan(Sequence):
  def __init__(self, character):
    draw = DrawNamed(character, "specials", "Bank Loan")
    super().__init__(
        [draw, KeepDrawn(character, draw)],
        character
    )


class ForceMovement(Event):

  def __init__(self, character, location_name):
    super().__init__()
    self.character = character
    self.location_name: Union[MapChoice, DrawMythosCard, str] = location_name
    self.done = False

  def resolve(self, state):
    if (isinstance(self.location_name, str)
            and getattr(state.places[self.location_name], "closed", False)):
      destinations = {
          place.name
          for place in state.places[self.location_name].connections
          if not place.closed
      }.difference({self.character.place.name})

      self.location_name = PlaceChoice(
          self.character,
          prompt=f"[{self.location_name}] is closed, choose another destination",
          choices=list(destinations),
      )
      state.event_stack.append(self.location_name)
      return
    if isinstance(self.location_name, MapChoice):
      assert self.location_name.is_done()
      if self.location_name.choice is None:
        # No need to reset explored, since the character did not move.
        self.cancelled = True
        return
      self.location_name = self.location_name.choice
    elif isinstance(self.location_name, DrawMythosCard):
      assert self.location_name.is_done()
      if self.location_name.card is None or self.location_name.card.gate_location is None:
        self.cancelled = True
        return
      self.location_name = self.location_name.card.gate_location
    self.character.place = state.places[self.location_name]
    self.character.explored = False
    self.character.avoid_monsters = []
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    name = self.location_name
    if isinstance(self.location_name, MapChoice):
      name = self.location_name.choice or "nowhere"
    if self.cancelled and not self.done:
      return f"[{self.character.name}] did not move to [{name}]"
    if not self.done:
      return f"[{self.character.name}] will move to [{name}]"
    return f"[{self.character.name}] moved to [{name}]"

  def animated(self):
    return True


class LookAtItems(Event):

  def __init__(self, character, deck, draw_count, prompt="Choose a card", target_type=None):
    assert deck in DECKS
    super().__init__()
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
        if self.target_type is None or getattr(top, "item_type", None) == self.target_type:
          self.drawn.append(top)
        else:
          deck.append(top)

        if i >= decksize:
          break
      deck.extend(self.drawn)

  def is_resolved(self):
    return self.drawn is not None

  def log(self, state):
    if self.cancelled and self.drawn is None:
      return f"[{self.character.name}] did not draw cards from the {self.deck} deck"
    if self.drawn is None:
      if self.target_type is None:
        return f"[{self.character.name}] draws {self.draw_count} cards from the {self.deck} deck"
      return (f"[{self.character.name}] draws {self.draw_count} {self.target_type} "
              + f"cards from the {self.deck} deck")
    return f"[{self.character.name}] drew " + ", ".join(f"[{c.name}]" for c in self.drawn)


class DrawItems(LookAtItems):
  pass


class KeepDrawn(Event):
  def __init__(self, character, draw, prompt="Choose a card", keep_count=1, sort_uniq=False):
    super().__init__()
    self.character = character
    self.draw: Union[DrawItems, DrawNamed] = draw
    self.keep_count = keep_count
    self.drawn = None
    self.kept = []
    self.choice: Optional[ChoiceEvent] = None
    self.prompt = prompt
    self.sort_uniq = sort_uniq

  def resolve(self, state):
    if self.draw.is_cancelled():
      self.cancelled = True
      return

    if self.drawn is None:
      assert self.draw.is_resolved()
      self.drawn = self.draw.drawn

    # Remove cards the character cannot keep:
    self.drawn = [card for card in self.drawn if self.character.get_override(card, "can_keep")]

    if self.choice is not None:
      assert self.choice.is_done()
      if self.choice.is_cancelled():
        self.cancelled = True
        return
      kept_card = self.drawn.pop(self.choice.choice_index)
      self.kept.append(kept_card.name)
      getattr(state, self.draw.deck).remove(kept_card)
      self.character.possessions.append(kept_card)

    remaining_keeps = self.keep_count - len(self.kept)
    if remaining_keeps == 0 or not self.drawn:
      return

    if remaining_keeps < len(self.drawn):
      self.choice = CardChoice(
          self.character, self.prompt, [card.name for card in self.drawn], sort_uniq=self.sort_uniq,
      )
      state.event_stack.append(self.choice)
      return

    self.kept += [card.name for card in self.drawn]
    for card in self.drawn:
      getattr(state, self.draw.deck).remove(card)
    self.character.possessions.extend(self.drawn)

  def is_resolved(self):
    if self.drawn is None:
      return False
    return len(self.kept) >= self.keep_count or not self.drawn

  def log(self, state):
    if self.cancelled and self.drawn is None:
      return f"[{self.character.name}] did not get to keep any cards"
    if not self.is_resolved():
      return f"[{self.character.name}] chooses {self.keep_count} cards to keep"
    return f"[{self.character.name}] kept " + ", ".join("[" + name + "]" for name in self.kept)

  def animated(self):
    return True


def Draw(character, deck, draw_count, prompt="Choose a card", keep_count=1, target_type=None):
  cards = DrawItems(character, deck, draw_count, target_type=target_type)
  if keep_count == "all":
    keep_count = draw_count
  keep = KeepDrawn(character, cards, prompt, keep_count, sort_uniq=math.isinf(draw_count))
  return Sequence([cards, keep], character)


def DrawSpecific(character, deck, item_name):
  draw = DrawNamed(character, deck, item_name)
  return Sequence([draw, KeepDrawn(character, draw)], character)


def GainAllyOrReward(character, ally: str, reward: Event):
  has_ally = values.ContainsPrerequisite("allies", ally)
  gain_ally = DrawSpecific(character, "allies", ally)
  return PassFail(character, has_ally, gain_ally, reward)


class ChangeCount(Event):

  def __init__(self, event, attribute, delta):
    super().__init__()
    self.event = event
    self.attribute = attribute
    self.delta = delta
    self.done = False

  def resolve(self, state):
    setattr(self.event, self.attribute, getattr(self.event, self.attribute) + self.delta)
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    return f"{self.delta} extra"  # TODO: add a source? card type? more descriptive in general?


class SellChosen(Event):

  def __init__(self, character, choice, discount_type="fixed", discount=0):
    assert discount_type in {"fixed", "rate"}
    super().__init__()
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

  def log(self, state):
    if self.cancelled and not self.sold:
      return f"[{self.character.name}] could not sell anything"
    if not self.choice.chosen:
      return f"[{self.character.name}] sold nothing"
    if self.sold:
      return f"[{self.character.name}] sold {', '.join(self.sold)} for {sum(self.prices)}"
    return f"[{self.character.name}] selling" + ",".join(f" [{i.name}]" for i in self.choice.chosen)

  def discounted_price(self, card):
    if self.discount_type == "fixed":
      return card.price - self.discount
    # self.discount_type == "rate"
    return card.price - int(self.discount * card.price)  # Discounts round up

  def animated(self):
    return True


def Sell(char, decks, sell_count=1, discount_type="fixed", discount=0, prompt="Sell item?"):
  items_to_sell = ItemCountChoice(char, prompt, sell_count, min_count=0, decks=decks)
  sell = SellChosen(char, items_to_sell, discount_type=discount_type, discount=discount)
  return Sequence([items_to_sell, sell], char)


class PurchaseDrawn(Event):
  def __init__(
      self, character, draw, discount_type="fixed", discount=0, keep_count=1, prompt="Buy items?",
      sort_uniq=False, must_buy=False,
  ):
    # TODO: draw could be something other than DrawItems (Northside 5)
    assert discount_type in {"fixed", "rate"}
    super().__init__()
    self.character = character
    self.prompt = prompt
    self.sort_uniq = sort_uniq
    self.keep_count = keep_count
    self.discount_type = discount_type
    self.discount = discount
    self.must_buy = must_buy
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
    prereqs = len(choices) * [None]
    if self.must_buy:
      # TODO: consider other items/abilities that can be used as money
      prereqs[-1] = values.Calculation(
          self.character, "dollars", operator.lt, min(prices),
          error_fmt="You must purchase at least one if able",
      )

    self.choice = CardSpendChoice(
        self.character, self.prompt, choices, prereqs, spends=spends, sort_uniq=self.sort_uniq,
    )
    state.event_stack.append(self.choice)

  def is_resolved(self):
    return self.resolved

  def log(self, state):
    if self.cancelled and self.drawn is None:
      return f"[{self.character.name}] did not get to buy any cards"
    if not self.resolved:
      return f"[{self.character.name}] chooses among cards to buy"
    if not self.kept:
      return f"[{self.character.name}] bought nothing"
    return f"[{self.character.name}] bought " + ", ".join(self.kept)

  def discounted_price(self, card):
    if self.discount_type == "fixed":
      return max(card.price - self.discount, 0)
    # self.discount_type == "rate"
    return card.price - int(self.discount * card.price)  # Discounts round up

  def animated(self):
    return True


def Purchase(char, deck, draw_count, discount_type="fixed", discount=0, keep_count=1,
             target_type=None, prompt="Buy items?", must_buy=False):
  items_to_buy = DrawItems(char, deck, draw_count, target_type=target_type)
  buy = PurchaseDrawn(
      char, items_to_buy, discount_type=discount_type, discount=discount, keep_count=keep_count,
      prompt=prompt, sort_uniq=math.isinf(draw_count), must_buy=must_buy,
  )
  return Sequence([items_to_buy, buy], char)


def MoveAndEncounter(character, choice):
  was_cancelled = values.Calculation(choice, None, operator.methodcaller("is_cancelled"))
  move_enc = Sequence([ForceMovement(character, choice), TravelOrEncounter(character)], character)
  return Conditional(character, was_cancelled, "", {0: move_enc, 1: Nothing()})


def TravelOrEncounter(character, count=1):
  on_gate = values.OnGate(character)
  return Conditional(character, on_gate, "", {0: Encounter(character, count), 1: Travel(character)})


class Encounter(Event):

  def __init__(self, character, count=1):
    super().__init__()
    self.character = character
    self.loc_name: Optional[str] = None
    self.draw: Optional[DrawEncounter] = None
    self.encounter: Optional[Event] = None
    self.count = count

  def resolve(self, state):
    if not isinstance(self.character.place, places.Location):
      self.cancelled = True
      return

    if self.draw is None:
      neighborhood = self.character.place.neighborhood
      self.draw = DrawEncounter(self.character, neighborhood, self.count)

    if not self.draw.is_done():
      state.event_stack.append(self.draw)
      return

    if self.draw.is_cancelled() or not self.draw.cards:
      self.cancelled = True
      return

    if self.encounter and self.encounter.is_done():
      return

    self.loc_name = self.character.place.name
    if self.character.lodge_membership and self.loc_name == "Lodge":
      self.loc_name = "Sanctum"

    encounters = [card.encounter_event(self.character, self.loc_name) for card in self.draw.cards]
    if any(isinstance(enc, Unimplemented) for enc in encounters):
      # TODO: Implement all the encounters, but this is a stopgap to let us play
      self.draw = None
      state.event_stack.append(Nothing())
      return

    if len(self.draw.cards) == 1 and state.test_mode:  # TODO: test this
      self.encounter = self.draw.cards[0].encounter_event(self.character, self.loc_name)
      state.event_stack.append(self.encounter)
      return

    choice = CardChoice(
        self.character, "Choose an Encounter", [card.name for card in self.draw.cards],
    )
    cond = Conditional(self.character, choice, "choice_index", dict(enumerate(encounters)))
    self.encounter = Sequence([choice, cond], self.character)
    state.event_stack.append(self.encounter)

  def is_resolved(self):
    return self.encounter and self.encounter.is_done()

  def log(self, state):
    if self.cancelled and self.draw is None:
      return f"[{self.character.name}] did not have an encounter"
    if self.draw is None:
      return f"[{self.character.name}] has an encounter"
    return f"[{self.character.name}] had an encounter at [{self.loc_name}]"


class DrawEncounter(Event):

  def __init__(self, character, neighborhood, count):
    assert count > 0
    super().__init__()
    self.character = character
    self.neighborhood = neighborhood
    self.count = count
    self.cards = None

  def resolve(self, state):
    self.cards = self.neighborhood.encounters[:self.count]
    random.shuffle(self.neighborhood.encounters)

  def is_resolved(self):
    return self.cards is not None

  def log(self, state):
    if self.cancelled and not self.cards:
      return f"[{self.character.name}] did not draw encounter cards"
    if not self.cards:
      return f"[{self.character.name}] draws {self.count} encounter cards"
    return f"[{self.character.name}] drew " + ", ".join([card.name for card in self.cards])


class GateEncounter(Event):

  def __init__(self, character):
    super().__init__()
    self.character = character
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

    if not hasattr(self.character.place, "colors"):
      # Character is not in another world.
      self.cancelled = True
      return
    colors = self.character.place.colors
    world_name = self.character.place.info.name

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
      self.draw = DrawGateCard(self.character, colors)
      state.event_stack.append(self.draw)
      return

    encounters = [card.encounter_event(self.character, world_name) for card in self.cards]
    if any(isinstance(enc, Unimplemented) for enc in encounters):
      self.draw = None
      state.gate_cards.extend(self.cards)
      self.cards = []
      state.event_stack.append(Nothing())
      return

    if len(self.cards) == 1 and state.test_mode:  # TODO: test this
      self.encounter = self.cards[0].encounter_event(self.character, world_name)
      state.event_stack.append(self.encounter)
      return

    choice = CardChoice(self.character, "Choose an Encounter", [card.name for card in self.cards])
    cond = Conditional(self.character, choice, "choice_index", dict(enumerate(encounters)))
    self.encounter = Sequence([choice, cond], self.character)
    state.event_stack.append(self.encounter)

  def is_resolved(self):
    return self.encounter is not None and self.encounter.is_done() and not self.cards

  def log(self, state):
    if self.cancelled and not self.cards:
      return f"[{self.character.name}] did not have an other world encounter"
    if self.encounter is None:
      return f"[{self.character.name}] has an other world encounter"
    return f"[{self.character.name}] had an other world encounter"


class DrawGateCard(Event):

  def __init__(self, character, colors):
    super().__init__()
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

  def log(self, state):
    if self.cancelled and self.card is None:
      return f"[{self.character.name}] did not draw a gate card"
    if self.card is None:
      return f"[{self.character.name}] must draw a " + " or ".join(self.colors) + " gate card"
    if self.shuffled:
      return f"[{self.character.name}] shuffled the deck and then drew [{self.card.name}]"
    return f"[{self.character.name}] drew [{self.card.name}]"


class DrawNamed(Event):

  def __init__(self, character, deck, item_name):
    assert deck in DECKS
    super().__init__()
    self.character = character
    self.deck = deck
    self.item_name = item_name
    self.drawn = None

  def resolve(self, state):
    deck = getattr(state, self.deck)
    for item in deck:
      if item.name == self.item_name:
        self.drawn = [item]
        break
    else:
      self.drawn = []
    if self.deck not in {"specials", "tradables"}:
      random.shuffle(getattr(state, self.deck))

  def is_resolved(self):
    return self.drawn is not None

  def log(self, state):
    if self.cancelled and self.drawn is None:
      return f"[{self.character.name}] could not draw a [{self.item_name}]"
    if self.drawn is None:
      return f"[{self.character.name}] searches the {self.deck} deck for a [{self.item_name}]"
    if self.drawn:
      return f"[{self.character.name}] drew a [{self.item_name}] from the {self.deck} deck"
    return f"There were no [{self.item_name}]s left in the {self.deck} deck"


class ExhaustAsset(Event):

  def __init__(self, character, item):
    assert item in character.possessions
    super().__init__()
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

  def log(self, state):
    if self.cancelled and self.exhausted is None:
      return f"[{self.character.name}] could not exhaust their [{self.item.name}]"
    if self.exhausted is None:
      return f"[{self.character.name}] exhausts their [{self.item.name}]"
    if not self.exhausted:
      return f"[{self.character.name}] did not exhaust their [{self.item.name}]"
    return f"[{self.character.name}] exhausted their [{self.item.name}]"

  def animated(self):
    return True


class RefreshAsset(Event):

  def __init__(self, character, item):
    assert item in character.possessions
    super().__init__()
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

  def log(self, state):
    if self.cancelled and self.refreshed is None:
      return f"[{self.character.name}] could not refresh their [{self.item.name}]"
    if self.refreshed is None:
      return f"[{self.character.name}] refreshes their [{self.item.name}]"
    if not self.refreshed:
      return f"[{self.character.name}] did not refresh their [{self.item.name}]"
    return f"[{self.character.name}] refreshed their [{self.item.name}]"

  def animated(self):
    return True


class RefreshAssets(Event):

  def __init__(self, character):
    super().__init__()
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

  def flatten(self):
    return True

  def log(self, state):
    return ""


class ActivateItem(Event):

  def __init__(self, character, item):
    assert item in character.possessions
    super().__init__()
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

  def log(self, state):
    if self.cancelled and self.activated is None:
      return f"[{self.character.name}] could not use their [{self.item.name}]"
    if self.activated is None:
      return f"[{self.character.name}] is using their [{self.item.name}]"
    if not self.activated:
      return f"[{self.character.name}] did not use their [{self.item.name}]"
    return f"[{self.character.name}] used their [{self.item.name}]"

  def animated(self):
    return True


class ActivateChosenItems(Event):

  def __init__(self, character, item_choice):
    super().__init__()
    self.character = character
    self.item_choice = item_choice
    self.activations: Optional[List[Event]] = None
    self.idx = 0
    self.fix_axe = None

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
    # HACK: allocate an extra hand to an axe if we have an extra hand. Note that you cannot have
    # two extra hands to allocate to axes, since an axe by definition takes at least one hand.
    if self.character.hands_available() > 0:
      axes = [item for item in self.item_choice.chosen if item.name == "Axe"]
      if axes:
        axes[0]._two_handed = True  # pylint: disable=protected-access
    self.fix_axe = True

  def is_resolved(self):
    return self.activations is not None and self.idx == len(self.activations) and self.fix_axe

  def flatten(self):
    return True

  def log(self, state):
    return ""


class DeactivateItem(Event):

  def __init__(self, character, item, discarded=False):
    if not discarded:
      assert item in character.possessions
    super().__init__()
    self.character = character
    self.item = item
    self.deactivated = None
    self.discarded = discarded

  def resolve(self, state):
    if self.item not in self.character.possessions and not self.discarded:
      self.deactivated = False
      return
    self.item._active = False  # pylint: disable=protected-access
    if hasattr(self.item, "deactivate"):
      self.item.deactivate()
    self.deactivated = True

  def is_resolved(self):
    return self.deactivated is not None

  def log(self, state):
    if self.cancelled and self.deactivated is None:
      return f"[{self.character.name}] could not stop using their [{self.item.name}]"
    if self.deactivated is None:
      return f"[{self.character.name}] will stop using their [{self.item.name}]"
    if not self.deactivated:
      return f"[{self.character.name}] did not stop using their [{self.item.name}]"
    return f"[{self.character.name}] stopped using their [{self.item.name}]"

  def animated(self):
    return True


class DeactivateItems(Event):

  def __init__(self, character):
    super().__init__()
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

  def flatten(self):
    return True

  def log(self, state):
    return ""


class CastSpell(Event):

  def __init__(self, character, spell, choice=None):
    assert spell in character.possessions
    super().__init__()
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
      cost = self.spell.sanity_cost(state)
      spend = values.ExactSpendPrerequisite(
          {"sanity": cost}
      )
      self.choice = CardSpendChoice(
          self.character, f"Cast [{self.spell.name}]",
          [self.spell.name, "Cancel"], spends=[spend, None],
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
      self.check = Check(
          self.character, "spell", self.spell.get_difficulty(state), name=self.spell.name,
          difficulty=self.spell.get_required_successes(state),
      )
      self.spell.check = self.check
      state.event_stack.append(self.check)
      return
    assert self.check.is_done()

    if not self.exhaust.is_done():
      state.event_stack.append(self.exhaust)
      return

    if not self.check.success:
      self.success = False
      self.fail_message = f"({self.check.successes} < {self.check.difficulty})"
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

  def log(self, state):
    if self.cancelled and (self.check is None or self.success is None):
      return f"[{self.character.name}] did not cast [{self.spell.name}]"
    if self.success is None:
      return f"[{self.character.name}] is casting [{self.spell.name}]"
    if self.success:
      return f"[{self.character.name}] successfully cast [{self.spell.name}]"
    return f"[{self.character.name}] failed to cast [{self.spell.name}] {self.fail_message}"

  def animated(self):
    return True


class MarkDeactivatable(Event):

  def __init__(self, character, spell):
    assert spell in character.possessions
    super().__init__()
    self.character = character
    self.spell = spell
    self.done = False

  def resolve(self, state):
    self.spell.deactivatable = True
    self.done = True

  def is_resolved(self):
    return self.done

  def flatten(self):
    return True

  def log(self, state):
    return ""


class DeactivateSpell(Event):

  def __init__(self, character, spell):
    assert spell in character.possessions
    super().__init__()
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

  def log(self, state):
    if self.cancelled and not self.done:
      return f"[{self.character.name}] could not stop using their [{self.spell.name}]"
    if not self.done:
      return f"[{self.character.name}] will stop using their [{self.spell.name}]"
    return f"[{self.character.name}] stopped using their [{self.spell.name}]"

  def animated(self):
    return True


class DeactivateCombatSpells(Event):

  def __init__(self, character):
    super().__init__()
    self.character = character
    self.deactivations: Optional[List[Event]] = None
    self.idx = 0

  def resolve(self, state):
    if self.deactivations is None:
      self.deactivations = [
          DeactivateSpell(self.character, spell) for spell in self.character.possessions
          if getattr(spell, "deck", None) == "spells" and spell.in_use and spell.combat
      ]
    while self.idx < len(self.deactivations):
      if not self.deactivations[self.idx].is_done():
        state.event_stack.append(self.deactivations[self.idx])
        return
      self.idx += 1

  def is_resolved(self):
    return self.deactivations is not None and all(event.is_done() for event in self.deactivations)

  def flatten(self):
    return True

  def log(self, state):
    return ""


def LoseItems(character, count, prompt=None, decks=None, item_type=None):
  prompt = prompt or "Choose items to lose"
  choice = ItemLossChoice(character, prompt, count, decks=decks, item_type=item_type)
  loss = DiscardSpecific(character, choice)
  return Sequence([choice, loss], character)


class DiscardSpecific(Event):

  def __init__(
          self,
          character,
          items_to_discard: "Union[ItemChoice, values.Value, List[assets.Card]]",
          to_box=False):
    super().__init__()
    self.character = character
    self.items = items_to_discard
    self.to_box = to_box
    self.discarded = None
    self.done = False
    self._verb = "discard"
    self._verb_past = "discarded"

  def resolve(self, state):
    if isinstance(self.items, ItemChoice):
      assert self.items.is_done()
      if self.items.is_cancelled():
        self.cancelled = True
        return
      self.items = self.items.chosen

    if isinstance(self.items, values.Value):
      self.items = self.items.value(state)

    if self.discarded is None:
      self.discarded = []
      for item in self.items:
        for attr in item.tokens:
          item.tokens[attr] = 0
        if item not in self.character.possessions:
          continue
        self.character.possessions.remove(item)
        item._exhausted = False  # pylint: disable=protected-access
        if not self.to_box:
          getattr(state, item.deck).append(item)
        self.discarded.append(item)
      state.event_stack.append(
          Sequence(
              [DeactivateItem(self.character, item, discarded=True) for item in self.discarded],
              self.character
          )
      )
      return
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and self.discarded is None:
      return f"[{self.character.name}] could not {self._verb} the items"
    if self.discarded is None:
      if isinstance(self.items, ItemChoice):
        text = f"[{self.character.name}] will {self._verb} the chosen items"
      else:
        text = (
            f"[{self.character.name}] will {self._verb} "
            + ", ".join(item.name for item in self.items)
        )
      if not self.to_box:
        return text
      return text + " to the box"
    if not self.discarded:
      text = f"[{self.character.name}] did not have items to {self._verb}"
    else:
      text = f"[{self.character.name}] {self._verb_past} "
      text += ", ".join(item.name for item in self.discarded)
    if not self.to_box:
      return text
    return text + " to the box"

  def animated(self):
    return True


class RollToMaintain(Event):
  def __init__(self, character, item: "assets.SelfDiscardingCard"):
    super().__init__()
    self.character = character
    self.item = item
    self.roll = None
    self.penalty = None
    self.done = False

  def resolve(self, state) -> None:
    if self.roll is None:
      self.roll = DiceRoll(self.character, 1, name=self.item.name, bad=self.item.upkeep_bad_rolls)
      state.event_stack.append(self.roll)
      return

    if self.roll.sum in self.item.upkeep_bad_rolls and self.penalty is None:
      # TODO: allow the item to determine its own bad stuff
      self.penalty = self.item.upkeep_penalty(self.character)
      state.event_stack.append(self.penalty)
      return

    self.done = True

  def is_resolved(self) -> bool:
    return self.done

  def log(self, state):
    if self.cancelled and self.roll is None:
      return f"[{self.character.name}] did not roll for [{self.item.name}]"
    if self.cancelled:
      return f"[{self.character.name}] could not pay the penalty for [{self.item.name}]"
    if self.done:
      if self.penalty is not None:
        return f"[{self.character.name}] rolled poorly and paid the penalty for [{self.item.name}]"
      return f"[{self.character.name}] keeps the [{self.item.name}]"
    return f"[{self.character.name}] to roll for their [{self.item.name}]"


class DiscardNamed(Event):

  def __init__(self, character, item_name):
    super().__init__()
    self.character = character
    self.item_name = item_name
    self.discarded = None
    self.done = False

  def resolve(self, state):
    if self.discarded is None:
      for item in self.character.possessions:
        if item.name == self.item_name:
          self.character.possessions.remove(item)
          item._exhausted = False  # pylint: disable=protected-access
          for attr in item.tokens:
            item.tokens[attr] = 0
          deck = getattr(state, item.deck)
          deck.append(item)
          self.discarded = item
          state.event_stack.append(DeactivateItem(self.character, item, discarded=True))
          return
      self.discarded = False
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and self.discarded is None:
      return f"[{self.character.name}] could not discard their [{self.item_name}]"
    if self.discarded is None:
      return f"[{self.character.name}] will discard a [{self.item_name}]"
    if not self.discarded:
      return f"[{self.character.name}] did not have a [{self.item_name}] to discard"
    return f"[{self.character.name}] discarded their [{self.item_name}]"

  def animated(self):
    return True


class ReturnMonsterFromBoard(Event):  # TODO: merge the three return monster to cup events

  def __init__(self, character, monster, to_box=False):
    super().__init__()
    self.character = character
    self.monster = monster
    self.to_box = to_box
    self.returned = False

  def resolve(self, state):
    self.monster.place = None if self.to_box else state.monster_cup
    self.returned = True

  def is_resolved(self):
    return self.returned

  def log(self, state):
    if self.cancelled and not self.returned:
      return f"[{self.monster.name}] was not returned to the {'box' if self.to_box else 'cup'}"
    if not self.returned:
      return f"[{self.monster.name}] is returned to the {'box' if self.to_box else 'cup'}"
    return f"[{self.monster.name}] was returned to the {'box' if self.to_box else 'cup'}"

  def animated(self):
    return True


class ReturnMonsterToCup(Event):

  def __init__(self, character, handle):
    super().__init__()
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

  def log(self, state):
    name = self.handle.rstrip("0123456789")
    if self.cancelled and self.returned is None:
      return f"[{self.character.name}] could not return [{name}] to the cup"
    if self.returned is None:
      return f"[{self.character.name}] returns [{name}] to the cup"
    return (
        f"[{self.character.name}] returned " +
        ", ".join(f"[{name}]" for name in self.returned) +
        " to the cup"
    )

  def animated(self):
    return True


class ReturnGateToStack(Event):

  def __init__(self, character, handle):
    super().__init__()
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

  def log(self, state):
    name = self.handle.rstrip("0123456789")
    if self.cancelled and self.returned is None:
      return f"[{self.character.name}] could not return [{name}]"
    if self.returned is None:
      return f"[{self.character.name}] returns [{name}]"
    return f"[{self.character.name}] returned " + ", ".join(f"[{name}]" for name in self.returned)

  def animated(self):
    return True


class Check(Event):

  def __init__(self, character, check_type, modifier, *, difficulty=1, name=None,
               attributes=None, source=None):
    # TODO: assert on check type
    assert difficulty > 0
    super().__init__()
    self.character = character
    self.check_type = check_type
    self.modifier = modifier
    self.difficulty = difficulty
    self.attributes = attributes
    self.name = name
    self.source = source
    self.dice: Optional[Event] = None
    self.pass_check: Optional[Event] = None
    self.roll = None
    self.successes = None
    self.spend: Optional[SpendChoice] = None
    self.bonus_dice: Optional[Event] = None
    self.done = False

  def resolve(self, state):
    if self.pass_check is not None:
      self.successes = self.difficulty
      self.done = True
      return
    if self.dice is None:
      if self.check_type == "combat":
        num_dice = self.character.combat(state, self.attributes) + self.modifier
      else:
        num_dice = getattr(self.character, self.check_type)(state) + self.modifier
      self.dice = DiceRoll(self.character, num_dice, name=self.name)
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
      if not self.character.get_override(self.source, "can_spend_clues"):
        self.done = True
        return
      spend = values.ExactSpendPrerequisite({"clues": 1})
      prompt = f"[{self.character.name}] has {self.successes} successes on a {self.check_str()}"
      if self.successes is None:
        prompt = f"[{self.character.name}] makes a {self.check_str()}"
      self.spend = SpendChoice(
          self.character, prompt,
          ["Spend", "Pass" if self.success else "Fail"], spends=[spend, None],
      )
      state.event_stack.append(self.spend)
      return

    if self.spend.is_cancelled() or self.spend.choice_index:
      self.done = True
      return

    # self.spend finished, and self.bonus_dice is None
    self.spend = None
    self.bonus_dice = BonusDiceRoll(self.character, 1, name=self.name)
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
    if self.spend is not None:
      self.spend.choices[1] = "Pass" if self.success else "Fail"
      prompt = f"[{self.character.name}] has {self.successes} successes on a {self.check_str()}"
      self.spend._prompt = prompt  # pylint: disable=protected-access

  @property
  def success(self):
    if self.successes is None:
      return None
    return self.successes >= self.difficulty

  def is_resolved(self):
    return self.done

  def check_str(self):
    if self.difficulty == 1:
      return f"{self.check_type} {self.modifier:+d} check"
    return f"{self.check_type} {self.modifier:+d} [{self.difficulty}] check"

  def log(self, state):
    if self.pass_check:
      return f"[{self.character.name}] passed a {self.check_str()}"
    if self.cancelled and self.roll is None:
      return f"[{self.character.name}] did not make a {self.check_str()}"
    if self.roll is None:
      return f"[{self.character.name}] makes a {self.check_str()}"
    if not self.successes:
      return f"[{self.character.name}] failed a {self.check_str()}"
    return f"[{self.character.name}] passed a {self.check_str()} with {self.successes} successes"

  def animated(self):
    return True


class AddExtraDie(Event):

  def __init__(self, character, event):
    assert isinstance(event, BonusDiceRoll)
    super().__init__()
    self.character = character
    self.dice: BonusDiceRoll = event
    self.done = False

  def resolve(self, state):
    assert not self.dice.is_done()
    self.dice.count += 1
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    return f"[{self.character.name}] gets an extra die from their skill"


class RerollCheck(Event):

  def __init__(self, character, check):
    assert isinstance(check, Check)
    super().__init__()
    self.character = character
    self.check: Check = check
    self.dice: Optional[DiceRoll] = None
    self.done = False

  def resolve(self, state):
    if self.dice is None:
      self.dice = DiceRoll(self.character, len(self.check.roll), name=self.check.name)
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

  def log(self, state):
    if self.cancelled and not self.done:
      return f"[{self.character.name}] could not reroll a {self.check.check_type} check"
    if not self.done:
      return f"[{self.character.name}] rerolls a {self.check.check_type} check"
    return f"[{self.character.name}] rerolled a {self.check.check_type} check"


class RerollSpecific(Event):

  def __init__(self, character, check, reroll_indexes):
    super().__init__()
    self.character = character
    self.check: Check = check
    self.reroll_indexes = reroll_indexes
    self.dice: Optional[DiceRoll] = None
    self.done = False

  def resolve(self, state):
    if isinstance(self.reroll_indexes, values.Value):
      self.reroll_indexes = self.reroll_indexes.value(state)
    if isinstance(self.reroll_indexes, int):
      self.reroll_indexes = [self.reroll_indexes]

    if not self.reroll_indexes:
      self.cancelled = True
      return

    if self.dice is None:
      self.dice = DiceRoll(self.character, len(self.reroll_indexes), name=self.check.name)
      state.event_stack.append(self.dice)
      return

    if self.dice.is_cancelled():
      self.cancelled = True
      return

    for idx, orig_idx in enumerate(self.reroll_indexes):
      self.check.roll[orig_idx] = self.dice.roll[idx]
    self.check.count_successes()
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    ctype = f"{self.check.check_type} check"
    if self.cancelled and not self.done:
      return f"[{self.character.name}] did not reroll dice for their {ctype}"
    if not self.done:
      return f"[{self.character.name}] rerolls some of the dice on their {ctype}"
    return f"[{self.character.name}] rerolled {len(self.reroll_indexes)} dice on their {ctype}"


class RerollSpecificDice(Event):
  """More general than, but logging not as nice as, RerollSpecific"""
  def __init__(
      self, character, dice_roll: DiceRoll, reroll_indexes: Union[List[int], int, values.Value]
  ):
    super().__init__()
    self.character = character
    self.dice_roll = dice_roll
    self.reroll_indexes = reroll_indexes
    self.dice = None
    self.done = False


  def resolve(self, state):
    if isinstance(self.reroll_indexes, values.Value):
      self.reroll_indexes = self.reroll_indexes.value(state)
    if isinstance(self.reroll_indexes, int):
      self.reroll_indexes = [self.reroll_indexes]

    if not self.reroll_indexes:
      self.cancelled = True
      return

    if self.dice is None:
      self.dice = DiceRoll(self.character, len(self.reroll_indexes), name=self.dice_roll.name)
      state.event_stack.append(self.dice)
      return

    if self.dice.is_cancelled():
      self.cancelled = True
      return

    for idx, orig_idx in enumerate(self.reroll_indexes):
      self.dice_roll.roll[orig_idx] = self.dice.roll[idx]
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    ctype = f"{self.dice_roll.name} roll"
    if self.cancelled and not self.done:
      return f"[{self.character.name}] did not reroll dice for their {ctype}"
    if not self.done:
      return f"[{self.character.name}] rerolls some of the dice on their {ctype}"
    return f"[{self.character.name}] rerolled {len(self.reroll_indexes)} dice on their {ctype}"



class Conditional(Event):

  def __init__(self, character, condition, attribute, result_map):
    assert isinstance(condition, values.Value) or hasattr(condition, attribute)
    assert all(isinstance(key, int) for key in result_map)
    assert min(result_map.keys()) == 0
    super().__init__()
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

  def flatten(self):
    return True

  def log(self, state):
    return ""


def PassFail(character, condition, pass_result: Event, fail_result: Event):
  outcome = Conditional(character, condition, "success", {0: fail_result, 1: pass_result})
  if isinstance(condition, values.Value):
    return outcome
  return Sequence([condition, outcome], character)


def PassOrLoseDice(
    char,
    stat: str,
    modifier: int,
    attribute: Union[Collection, str],
    n_dice: int = 1,
    adjustment: int = 0,
) -> Event:
  check = Check(char, stat, modifier)
  die = DiceRoll(char, n_dice, bad=[])
  amt = values.Calculation(die, "sum", operand=operator.add, right=adjustment)
  if isinstance(attribute, str):
    attribute = [attribute]
  loss = Loss(char, {attr: amt for attr in attribute})

  seq = Sequence([die, loss], char)
  return PassFail(char, check, Nothing(), seq)


class Arrested(Event):

  def __init__(self, character):
    super().__init__()
    self.character = character
    self.jail = None
    self.done = False

  def resolve(self, state):
    if self.jail is None:
      self.jail = Sequence([
          ForceMovement(self.character, "Police"),
          Loss(self.character,
               {"dollars": values.Calculation(self.character, "dollars", operator.floordiv, 2)}
               )
      ], self.character)
      state.event_stack.append(self.jail)
      return
    self.character.arrested_until = state.turn_number + 2
    self.done = True

  def is_resolved(self) -> bool:
    return self.done

  def log(self, state):
    if self.done:
      return f"[{self.character.name}] was arrested and lost their next turn"
    if self.cancelled:
      return f"[{self.character.name}]'s arrest was cancelled"
    return f"[{self.character.name}] to be arrested"


class MultipleChoice(ChoiceEvent):

  def __init__(self, character, prompt, choices, prereqs=None, annotations=None):
    if prereqs is None:
      prereqs = [None] * len(choices)
    assert len(choices) == len(prereqs)
    assert all(prereq is None or isinstance(prereq, values.Value) for prereq in prereqs)
    super().__init__()
    self.character = character
    self._prompt = prompt
    self._choices = choices
    self.prereqs: List[Optional[values.Value]] = prereqs
    self._annotations = annotations
    self.invalid_choices = {}
    self.choice = None

  def compute_choices(self, state):
    # Any unsatisfied prerequisite means that choice is invalid.
    self.invalid_choices.clear()
    for idx, choice in enumerate(self.choices):
      if self.prereqs[idx] is not None and self.prereqs[idx].value(state) < 1:
        self.invalid_choices[idx] = self.prereqs[idx].error_str(state, choice)

  def resolve(self, state, choice=None):
    assert not self.is_resolved()
    self.validate_choice(choice)
    self.choice = choice

  def validate_choice(self, choice):
    if choice not in self.choices:
      raise InvalidMove(f"{choice} is not a valid choice.")
    prereq_err = self.invalid_choices.get(self.choices.index(choice))
    if prereq_err:
      raise InvalidMove(prereq_err)

  def is_resolved(self):
    return self.choice is not None

  def log(self, state):
    if self.cancelled and self.choice is None:
      return f"[{self.character.name}] did not get to choose"
    if self.choice is None:
      return f"[{self.character.name}] must choose one of" + ",".join(f" {c}" for c in self.choices)
    return f"[{self.character.name}] chose {str(self.choice)}"

  def prompt(self):
    return self._prompt

  def annotations(self, state):
    return self._annotations

  @property
  def choice_index(self):
    if self.choice is None:
      return None
    return self.choices.index(self.choice)


class FightOrEvadeChoice(MultipleChoice):

  def __init__(self, character, prompt, evade_choice, monster, prereqs=None, annotations=None):
    super().__init__(character, prompt, ["Fight", evade_choice], prereqs, annotations)
    self.monster = monster


class MonsterChoice(ChoiceEvent):

  def __init__(self, character, prompt, monsters, annotations, none_choice=None):
    assert monsters
    assert len(monsters) == len(annotations)
    super().__init__()
    self.character = character
    self._prompt = prompt
    self.monsters = monsters
    self.none_choice = none_choice
    self._annotations = annotations
    self.invalid_choices = {}
    self.choice = None

  def compute_choices(self, state):
    self.invalid_choices = {idx: True for idx, val in enumerate(self._annotations) if val}
    valid_choices = [idx for idx in range(len(self.monsters)) if idx not in self.invalid_choices]
    if len(valid_choices) == 1 and not state.usables:  # Do not auto-choose if player can interrupt.
      self.choice = self.monsters[valid_choices[0]]

  def resolve(self, state, choice=None):
    assert not self.is_resolved()
    if self.none_choice is not None and choice == self.none_choice:
      self.choice = choice
      return
    chosen_monsters = [pair for pair in enumerate(self.monsters) if pair[1].handle == choice]
    if len(chosen_monsters) != 1:
      raise InvalidMove(f"Unknown monster {choice}")
    idx, monster = chosen_monsters[0]
    if idx in self.invalid_choices:
      raise InvalidMove(f"You have already dealt with that [{monster.name}]")
    self.choice = monster

  def is_resolved(self):
    return self.choice is not None

  def log(self, state):
    if self.cancelled and self.choice is None:
      return f"[{self.character.name}] did not get to choose a monster"
    if self.choice is None:
      return f"[{self.character.name}] must choose a monster"
    if isinstance(self.choice, str):
      return f"[{self.character.name}] chose [{self.choice}]"
    return f"[{self.character.name}] chose [{self.choice.name}]"

  def prompt(self):
    return self._prompt

  def annotations(self, state):
    return self._annotations


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
    if spend_seq:
      state.event_stack.append(Sequence(spend_seq, self.character))

  def spent_handles(self):
    # Items that have multiple spend types should only be counted once.
    handles = set()
    for spend_count in self.spend_map.values():
      handles |= spend_count.keys()
    return handles

  def spend_handle(self, handle, spend_map):
    name = handle.rstrip("0123456789")
    invalid_spends = spend_map.keys() - self.spendable
    if invalid_spends:
      raise InvalidMove(f"Cannot spend {', '.join(invalid_spends)} from [{name}]")
    if handle in self.spent_handles():
      raise InvalidMove(f"[{name}] has already been spent")
    for key, val in spend_map.items():
      self.spend_map[key][handle] = val

  def unspend_handle(self, handle):
    for spend_count in self.spend_map.values():
      if handle in spend_count:
        del spend_count[handle]

  def spend(self, spend_type):
    if spend_type not in self.spendable & {"stamina", "sanity", "dollars", "clues"}:
      raise InvalidMove(f"Cannot spend {spend_type}")
    already_spent = self.spend_map[spend_type].get(spend_type, 0)
    if getattr(self.character, spend_type) - already_spent <= 0:
      raise InvalidMove(f"Cannot spend more {spend_type} than you have")
    self.spend_map[spend_type][spend_type] = already_spent + 1

  def unspend(self, spend_type):
    if spend_type not in self.spend_map.keys() & {"stamina", "sanity", "dollars", "clues"}:
      raise InvalidMove(f"Cannot unspend {spend_type}")
    already_spent = self.spend_map[spend_type].get(spend_type, 0)
    if already_spent <= 0:
      raise InvalidMove(f"Cannot unspend {spend_type} that you have not spent")
    self.spend_map[spend_type][spend_type] -= 1


class SpendItemChoiceMixin(SpendMixin):

  def __init__(self, *args, **kwargs):
    spend = kwargs.pop("spend")
    super().__init__(*args, **kwargs)
    assert isinstance(spend, values.SpendValue)
    self.spend_prereq = spend
    self.spendable = spend.spend_types()
    self.remaining_spend = True
    self.remaining_max = True
    spend.spend_event = self

  def compute_choices(self, state):
    super().compute_choices(state)
    self.remaining_spend = self.spend_prereq.remaining_spend(state) or False
    self.remaining_max = self.spend_prereq.remaining_max(state) or False

  def resolve(self, state, choice=None):
    if choice == "done" and not self.chosen:
      self.cancelled = True
      return
    super().resolve(state, choice)

  def validate_choice(self, state, chosen, final):
    if len(chosen) > 0:
      remaining = self.spend_prereq.remaining_spend(state)
      if remaining:
        if len(remaining) == 1:
          spend, count = next(iter(remaining.items()))
          if count < 0:
            raise InvalidMove(f"You have overspent {-count} {spend}")
          raise InvalidMove(f"You must spend an additional {count} {spend}")
        remaining_str = ", ".join(f"{value} {key}" for key, value in remaining.items())
        raise InvalidMove(f"You must change your spending by {remaining_str}")
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
    self.remaining_max = [value is not None for value in spends]
    for spend in spends:
      spend = spend or values.SpendNothing()
      assert isinstance(spend, values.SpendValue)
      self.spends.append(spend)
      spend.spend_event = self
      self.spendable |= spend.spend_types()

  def compute_choices(self, state):
    super().compute_choices(state)
    self.remaining_spend = [spend.remaining_spend(state) or False for spend in self.spends]
    self.remaining_max = [spend.remaining_max(state) or False for spend in self.spends]

  def resolve(self, state, choice=None):
    if choice not in self.choices:
      raise InvalidMove(f"Invalid choice {choice}")
    choice_idx = self.choices.index(choice)
    remaining_spend: dict = self.remaining_spend[choice_idx]
    if remaining_spend:
      if len(remaining_spend) == 1:
        spend, count = next(iter(remaining_spend.items()))
        if count < 0:
          raise InvalidMove(f"You have overspent {-count} {spend}")
        raise InvalidMove(f"You must spend an additional {count} {spend}")
      remaining_str = ", ".join(f"{value} {key}" for key, value in remaining_spend.items())
      raise InvalidMove(f"You must change your spending by {remaining_str}")
    super().resolve(state, choice)

  def annotations(self, state):
    return [spend.annotation(state) for spend in self.spends]


class SpendChoice(SpendMultiChoiceMixin, MultipleChoice):
  pass


class ChangeMovementPoints(Event):

  def __init__(self, character, count):
    super().__init__()
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

  def log(self, state):
    if self.cancelled and self.change is None:
      return f"[{self.character.name}] did not gain or lose movement points"
    if self.change is None:
      text = f"gains {self.count}" if self.count > 0 else f"loses {-self.count}"
    else:
      text = f"gained {self.count}" if self.count > 0 else f"lost {-self.count}"
    return f"[{self.character.name}] {text} movement points"


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

  def __init__(self, character, prompt, decks=None, item_type=None):
    super().__init__()
    self.character = character
    self._prompt = prompt
    self._choices = None
    self.chosen = []
    if decks is None:
      decks = {"common", "unique", "spells", "tradables"}
    assert not decks - DECKS, f"invalid decks {decks}"
    self.decks = decks
    assert item_type in {None, "weapon", "tome"}
    self.item_type = item_type
    self.done = False

  def resolve(self, state, choice=None):
    if not isinstance(choice, str):
      raise InvalidInput(f"Invalid input {choice}")
    if choice == "done":
      self.validate_choice(state, self.chosen, final=True)
      self.done = True
      return

    # If the character is trying to deselect an item, remove it from the list.
    chosen_copy = [pos for pos in self.chosen if pos.handle != choice]
    if len(chosen_copy) >= len(self.chosen):  # Otherwise, add it to the list.
      chosen_copy += [pos for pos in self.character.possessions if pos.handle == choice]
      if len(chosen_copy) <= len(self.chosen):
        raise InvalidMove(f"Unknown card {choice}")

    self.validate_choice(state, chosen_copy, final=False)
    self.chosen = chosen_copy

  def validate_choice(self, state, chosen, final):  # pylint: disable=unused-argument
    invalid_cards = [pos.handle for pos in chosen if pos.handle not in self.choices]
    if invalid_cards:
      raise InvalidMove(f"Invalid choices: [{'], ['.join(invalid_cards)}]")

  def compute_choices(self, state):
    self._choices = [
        pos.handle for pos in self.character.possessions
        if (getattr(pos, "deck", None) in self.decks) and self._matches_type(pos)
    ]

  def _matches_type(self, pos):
    if self.item_type is None:
      return True
    return getattr(pos, "item_type", None) == self.item_type

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled:
      return f"[{self.character.name}] did not choose anything"
    if not self.done:
      return f"[{self.character.name}] must {self.prompt()}"
    return f"[{self.character.name}] chose {', '.join('['+item.name+']' for item in self.chosen)}"

  def prompt(self):
    return self._prompt

  @property
  def choice_count(self):
    return len(self.chosen) if self.chosen else 0

  @property
  def select_type(self):
    return "check"


class CombatChoice(ItemChoice):

  def __init__(self, character, prompt, monster=None, combat_round=None):
    super().__init__(character, prompt, decks=None, item_type="weapon")
    self.monster = monster
    self.combat_round = combat_round
    self.activate = None

  def resolve(self, state, choice=None):
    super().resolve(state, choice)
    if not self.is_resolved():
      return
    self.activate = ActivateChosenItems(self.character, self)
    state.event_stack.append(self.activate)

  def validate_choice(self, state, chosen, final):
    super().validate_choice(state, chosen, final)
    for pos in chosen:
      if getattr(pos, "hands", None) is None:
        raise InvalidMove("You must choose a weapon")
      if getattr(pos, "deck", None) == "spells":
        raise InvalidMove("That spell cannot be cast during combat")
    hands_used = sum(pos.hands for pos in chosen)
    if hands_used > self.character.hands_available():
      raise InvalidMove("You do not have enough hands")

  def hands_used(self):
    return sum(pos.hands for pos in self.chosen)

  @property
  def select_type(self):
    return "hands"


class ItemCountChoice(ItemChoice):

  def __init__(
      self, character, prompt, count, min_count=None, decks=None, item_type=None, select_type=None,
  ):
    super().__init__(character, prompt, decks=decks, item_type=item_type)
    self.count = count
    self.min_count = count if min_count is None else min_count
    self._select_type = select_type or "check"

  def validate_choice(self, state, chosen, final):
    super().validate_choice(state, chosen, final)
    min_count = self.min_count
    if isinstance(self.min_count, values.Value):
      min_count = self.min_count.value(state)
    max_count = self.count
    if isinstance(self.count, values.Value):
      max_count = self.count.value(state)
    if len(chosen) > max_count:
      raise InvalidMove(f"Too many cards (max {max_count})")
    if final:
      if len(chosen) < min_count:
        if math.isinf(min_count):
          raise InvalidMove("Not enough cards")
        raise InvalidMove(f"Not enough cards (min {min_count})")

  @property
  def select_type(self):
    return self._select_type


class ItemLossChoice(ItemChoice):

  def __init__(self, character, prompt, count, decks=None, item_type=None):
    super().__init__(character, prompt, decks=decks, item_type=item_type)
    self.count = count

  def validate_choice(self, state, chosen, final=False):
    super().validate_choice(state, chosen, final)
    count = self.count.value(state) if isinstance(self.count, values.Value) else self.count
    if len(chosen) > count:
      raise InvalidMove(f"Too many cards (max {count})")
    if not final:
      return

    if len(chosen) == count:
      return
    # If the user has not chosen as many items as they need to lose, go through all of their items
    # and validate that every viable option is either (a) not losable or (b) already chosen.
    any_losable = False
    for pos in self.character.possessions:
      if pos in chosen or pos.handle not in self.choices:
        continue
      if getattr(pos, "losable", True):
        any_losable = True
    if any_losable:
      if math.isinf(count):
        raise InvalidMove("Not enough cards")
      raise InvalidMove(f"Not enough cards (min {count})")

  @property
  def select_type(self):
    return "x"


class WeaponOrSpellLossChoice(ItemLossChoice):

  def __init__(self, character, prompt, count):
    super().__init__(character, prompt, count)

  def compute_choices(self, state):
    self._choices = [
        pos.handle for pos in self.character.possessions
        if getattr(pos, "deck", None) == "spells" or getattr(pos, "item_type", None) == "weapon"
    ]
    if not self.choices:
      self.cancelled = True


class SinglePhysicalWeaponChoice(SpendItemChoiceMixin, ItemCountChoice):

  def __init__(self, character, prompt, spend):
    super().__init__(character, prompt, 1, min_count=0, item_type="weapon", spend=spend)

  def compute_choices(self, state):
    super().compute_choices(state)
    self._choices = [
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

  def __init__(self, character, prompt, none_choice=None, annotation=None):
    super().__init__()
    self.character = character
    self._prompt = prompt
    self._choices = None
    self.none_choice = none_choice
    self.annotation = annotation
    self.choice = None

  @abc.abstractmethod
  def compute_choices(self, state):
    raise NotImplementedError

  def resolve(self, state, choice=None):
    if choice is not None and choice == self.none_choice:
      self.cancelled = True
      return
    if choice not in self.choices:
      raise InvalidMove(f"Invalid choice {choice}")
    self.choice = choice

  def is_resolved(self):
    return self.choice is not None

  def prompt(self):
    return self._prompt

  def annotations(self, state):
    if self.annotation and self.choices is not None:
      return [self.annotation for _ in self.choices]
    return None


class PlaceChoice(MapChoice):

  VALID_FILTERS = {"streets", "locations", "open", "closed"}

  def __init__(
      self, character, prompt, choices=None, choice_filters=None, none_choice=None, annotation=None,
  ):
    assert choice_filters is None or choices is None
    super().__init__(character, prompt, none_choice=none_choice, annotation=annotation)
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
      self._choices = self.fixed_choices
      return
    self._choices = []
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
    if not self.choices:
      self.cancelled = True

  def log(self, state):
    if self.cancelled:
      return f"[{self.character.name}] did not choose anything"
    if self.choice is not None:
      return f"[{self.character.name}] chose [{self.choice}]"
    if self.fixed_choices:
      return f"[{self.character.name}] must choose one of " + ", ".join(self.fixed_choices)
    if len(self.choice_filters & {"streets", "locations"}) > 1:
      return f"[{self.character.name}] may choose any street or location"
    if "streets" in self.choice_filters:
      return f"[{self.character.name}] may choose any street"
    return f"[{self.character.name}] may choose any location"


class GateChoice(MapChoice):

  def __init__(self, character, prompt, gate_name=None, none_choice=None, annotation=None):
    super().__init__(character, prompt, none_choice=none_choice, annotation=annotation)
    self.gate_name = gate_name
    self.overridden = False

  def compute_choices(self, state):
    if isinstance(self.gate_name, values.Value):
      self.gate_name = self.gate_name.value(state)
      if self.gate_name is None:
        self.cancelled = True
        return

    self._choices = []
    for name, place in state.places.items():
      if not isinstance(place, (places.Location, places.Street)):
        continue
      if getattr(place, "gate", None) is not None:
        if place.gate.name == self.gate_name or self.gate_name is None:
          self.choices.append(name)
    if not self.choices:
      self.cancelled = True
      return
    if len(self.choices) == 1 and self.none_choice is None and not state.usables:
      self.choice = self.choices[0]

  def log(self, state):
    if self.cancelled:
      return f"[{self.character.name}] did not choose a gate"
    if self.choice is not None:
      return f"[{self.character.name}] chose the gate at [{self.choice}]"
    if self.gate_name is not None:
      return f"[{self.character.name}] must choose a gate to [{self.gate_name}]"
    return f"[{self.character.name}] must choose a gate"


class OverrideGateChoice(Event):
  def __init__(self, character, original_choice: GateChoice, **changes):
    super().__init__()
    self.character = character
    self.original_choice = original_choice
    self.changes = changes
    assert len(changes)
    assert {"_prompt", "gate_name", "none_choice", "annotation"}.issuperset(changes.keys())
    self.done = False

  def resolve(self, state):
    for key, value in self.changes.items():
      setattr(self.original_choice, key, value)
    self.original_choice.overridden = True
    self.done = True

  def is_resolved(self) -> bool:
    return self.done

  def log(self, state) -> str:
    changes = [f"{key} to {repr(value)}" for key, value in self.changes.items()]
    if self.done:
      return "Gate choice updated " + ", ".join(changes)
    return "Gate choice to update " + ", ".join(changes)


class NearestGateChoice(MapChoice):

  def __init__(self, character, prompt, annotation, none_choice=None):
    super().__init__(character, prompt, none_choice=none_choice, annotation=annotation)

  def compute_choices(self, state):
    if not isinstance(self.character.place, places.CityPlace):
      self.cancelled = True
      return

    self._choices = []
    nearest = None
    distances = {self.character.place.name: 0}
    queue = [self.character.place]
    while queue:
      place = queue.pop(0)
      distance = distances[place.name]
      if nearest is not None and distance > nearest:
        break
      if getattr(place, "gate", None) is not None:
        nearest = distance
        self.choices.append(place.name)
        continue
      for nearby in place.connections:
        if nearby.name not in distances:
          distances[nearby.name] = distance + 1
          queue.append(nearby)

    if not self.choices:
      self.cancelled = True
      return
    if len(self.choices) == 1 and self.none_choice is None and not state.usables:
      self.choice = self.choices[0]

  def log(self, state):
    if self.cancelled and self.choice is None:
      return "There were no open gates"
    if self.choice is None:
      return f"[{self.character.name}] must choose the nearest gate"
    return f"[{self.character.name}] chose the gate at [{self.choice}]"


class NearestLowestSneakChoice(MapChoice, metaclass=abc.ABCMeta):

  def __init__(self, character, monster):
    super().__init__(character, f"Choose where the [{monster.name}] should move")
    self.monster = monster

  def compute_choices(self, state):
    if any(char.place == self.monster.place for char in state.characters):
      self.cancelled = True
      return

    candidates = collections.defaultdict(list)
    distances = {self.monster.place.name: 0}
    queue = [self.monster.place]
    while queue:
      place = queue.pop(0)
      if self.is_valid(place):
        if any(char.place == place for char in state.characters):
          candidates[distances[place.name]].append(place)
      if place.name == "Sky":
        connections = [p for p in state.places.values() if isinstance(p, places.Street)]
      else:
        connections = place.connections
      for conn in connections:
        if conn.name in distances:
          continue
        distances[conn.name] = distances[place.name] + 1
        queue.append(conn)
    if not candidates:
      self.cancelled = True
      return
    min_distance = min(candidates.keys())
    if min_distance > self.max_distance():
      self.cancelled = True
      return
    char_list = [char for char in state.characters if char.place in candidates[min_distance]]
    char_list.sort(key=lambda char: char.sneak(state))

    choices = {char.place for char in char_list if char.sneak(state) == char_list[0].sneak(state)}
    self._choices = [choice.name for choice in choices]
    if len(self._choices) == 1 and not state.usables:
      self.choice = self._choices[0]
      return

  @abc.abstractmethod
  def is_valid(self, place):
    raise NotImplementedError

  def max_distance(self):
    return float("inf")

  def log(self, state):
    if self.cancelled and self.choice is None:
      return f"There was nowhere for the [{self.monster.name}] to move"
    if self.choice is None:
      return f"[{self.character.name}] must choose where the [{self.monster.name}] moves"
    return f"[{self.character.name}] chose [{self.choice}]"


class FlyingLowestSneakChoice(NearestLowestSneakChoice):

  def is_valid(self, place):
    return isinstance(place, places.Street)

  def max_distance(self):
    return 1


class HoundLowestSneakChoice(NearestLowestSneakChoice):

  def is_valid(self, place):
    return isinstance(place, places.Location) and place.name not in ["Hospital", "Asylum"]


class MonsterOnBoardChoice(ChoiceEvent):

  def __init__(self, character, prompt):
    super().__init__()
    self.character = character
    self._prompt = prompt
    self._choices = []
    self.chosen = None

  def compute_choices(self, state):
    # TODO: other ways of narrowing choices (e.g. streets only)
    self._choices = [
        mon.handle for mon in state.monsters
        if isinstance(mon.place, (places.CityPlace, places.Outskirts))
    ]
    if not self.choices:
      self.cancelled = True

  def resolve(self, state, choice=None):
    if choice not in self.choices:
      raise InvalidMove(f"Invalid choice {choice}")
    chosen = [mon for mon in state.monsters if mon.handle == choice]
    if len(chosen) != 1:
      raise InvalidMove("You must choose exactly one monster")
    self.chosen = chosen[0]

  def is_resolved(self):
    return self.chosen is not None

  def log(self, state):
    if self.cancelled and self.chosen is None:
      return "There were no monsters on the board"
    if self.chosen is None:
      return f"[{self.character.name}] must choose a monster on the board"
    return f"[{self.character.name}] chose [{self.chosen.name}] at [{self.chosen.place.name}]"

  def prompt(self):
    return self._prompt


class EvadeOrFightAll(Event):

  def __init__(self, character, monsters, auto_evade=False):
    assert monsters
    super().__init__()
    self.character = character
    self.monsters = monsters
    self.done = [False] * len(monsters)
    self.choice: Optional[MonsterChoice] = None
    self.combat: Optional[EvadeOrCombat] = None
    self.auto_evade = auto_evade
    self.place = None

  def resolve(self, state):
    # Keep track of the character's location. If it changes, then the EvadeOrFightAll ends.
    # See the Dream Flier or Dimensional Shambler for an example of how this could happen.
    # Doubles as an initialization flag used to filter monsters from character.avoid_monsters.
    if self.place is None:
      self.place = self.character.place
      for idx, monster in enumerate(self.monsters):
        if monster in self.character.avoid_monsters:
          self.done[idx] = True
    if self.place != self.character.place:
      self.cancelled = True
      return

    # If we finished a combat, record that this monster is handled and give another choice.
    if self.combat is not None:
      assert self.combat.is_done()
      idx = self.monsters.index(self.combat.monster)
      self.done[idx] = True
      for idx, monster in enumerate(self.monsters):
        # Maybe an item defeated these monsters
        if monster.place != self.character.place:
          self.done[idx] = True
      self.combat = None
    if all(self.done):
      return

    if self.choice is not None and not self.choice.is_resolved():  # Maybe it got cancelled somehow?
      self.choice = None

    # Give the user a choice of monsters.
    if self.choice is None:
      # This will ignore any monsters that have been taken as trophies.
      present_monsters = [pair for pair in enumerate(self.monsters) if pair[1].place == self.place]
      # Annotate all monsters already fought or evaded with "Done".
      shown_monsters = [monster for _, monster in present_monsters]
      annotations = ["Done" if self.done[idx] else None for idx, _ in present_monsters]
      prompt = "Choose a monster to fight or evade"
      none_choice = "Ignore All" if self.auto_evade else None
      self.choice = MonsterChoice(self.character, prompt, shown_monsters, annotations, none_choice)
      state.event_stack.append(self.choice)
      return

    # If the user has chosen the option to evade all remaining monsters, we are done.
    if self.auto_evade and self.choice.choice == "Ignore All":
      self.done = [True] * len(self.done)
      return

    # When the user chooses a monster, put a EvadeOrCombat on the stack for that monster.
    # Also be sure to reset the choice so that they can choose again next iteration.
    self.combat = EvadeOrCombat(self.character, self.choice.choice, auto_evade=self.auto_evade)
    self.choice = None
    state.event_stack.append(self.combat)

  def is_resolved(self):
    return all(self.done)

  def log(self, state):
    if not self.is_done():
      if self.auto_evade:
        return f"[{self.character.name}] may choose to fight monsters"
      return f"[{self.character.name}] must evade or fight monsters"
    if getattr(self.choice, "choice", None) == "Ignore All":
      return f"[{self.character.name}] chose not to fight monsters"
    return f"[{self.character.name}] evaded or fought monsters"


class EvadeOrCombat(Event):

  def __init__(self, character, monster, auto_evade=False):
    super().__init__()
    self.character = character
    self.monster = monster
    self.combat: Optional[Combat] = None
    self.evade: Optional[EvadeRound] = None
    self.choice: Optional[Event] = None
    self.auto_evade = auto_evade

  def resolve(self, state):
    if isinstance(self.monster, DrawMonstersFromCup):
      if self.monster.is_cancelled() or len(self.monster.monsters) != 1:
        self.cancelled = True
        return
      self.monster = state.monsters[self.monster.monsters[0]]

    if self.choice is None:
      self.combat = Combat(self.character, self.monster)
      self.evade = EvadeRound(self.character, self.monster) if not self.auto_evade else Nothing()
      evade_text = "Evade" if not self.auto_evade else "Ignore"
      prompt = f"Fight the [{self.monster.name}] or {evade_text.lower()} it?"
      choice = FightOrEvadeChoice(self.character, prompt, evade_text, self.monster)
      cond = Conditional(self.character, choice, "choice_index", {0: self.combat, 1: self.evade})
      self.choice = Sequence([choice, cond], self.character)

    if not self.choice.is_done():
      state.event_stack.append(self.choice)
      return
    if self.evade.is_resolved() and (self.auto_evade or getattr(self.evade, "evaded", False)):
      return
    if not self.combat.is_done():
      state.event_stack.append(self.combat)
      return

  def is_resolved(self):
    if self.choice is None:
      return False
    if self.evade.is_resolved() and (self.auto_evade or getattr(self.evade, "evaded", False)):
      return True
    return self.combat.is_done()

  def log(self, state):
    if self.cancelled and self.choice is None:
      return f"[{self.character.name}] did not fight or evade the monster"
    if not self.is_done():
      evade_text = "evade" if not self.auto_evade else "ignore"
      return f"[{self.character.name}] must either fight or {evade_text} the monster"
    if self.evade.is_resolved() and getattr(self.evade, "evaded", self.auto_evade):
      evade_text = "evaded" if not self.auto_evade else "ignored"
      return f"[{self.character.name}] {evade_text} the [{self.monster.name}]"
    return f"[{self.character.name}] fought the [{self.monster.name}]"


class Combat(Event):

  def __init__(self, character, monster):
    super().__init__()
    self.character = character
    self.monster = monster
    self.horror: Optional[Event] = None
    self.sanity_loss: Optional[Event] = None
    self.choice: Optional[Sequence] = None
    self.evade: Optional[EvadeRound] = None
    self.combat: Optional[CombatRound] = None
    self.done = False

  def resolve(self, state):
    # Horror check
    if self.monster.difficulty("horror", state, self.character) is not None and self.horror is None:
      self.horror = Check(
          self.character, "horror", self.monster.difficulty("horror", state, self.character),
          name=self.monster.visual_name,
      )
      self.sanity_loss = Loss(
          self.character, {"sanity": self.monster.damage("horror", state, self.character)})
    if self.horror is not None:
      if not self.horror.is_done():
        state.event_stack.append(self.horror)
        return
      if not self.sanity_loss.is_done():
        # Failed horror check
        if not self.horror.success:
          state.event_stack.append(self.sanity_loss)
          return
        # Nightmarish for successful horror check
        nightmarish = self.monster.has_attribute("nightmarish", state, self.character)
        if self.horror.success and nightmarish:
          self.sanity_loss = Loss(
              self.character, {"sanity": self.monster.bypass_damage("horror", state)})
          state.event_stack.append(self.sanity_loss)
          return

    # Combat or flee choice.
    self.combat = CombatRound(self.character, self.monster)
    self.evade = EvadeRound(self.character, self.monster)
    no_ambush = values.NoAmbushPrerequisite(self.monster, self.character)
    prompt = f"Fight the [{self.monster.name}] or flee from it?"
    choice = FightOrEvadeChoice(self.character, prompt, "Flee", self.monster, [None, no_ambush])
    cond = Conditional(self.character, choice, "choice_index", {0: self.combat, 1: self.evade})
    self.choice = Sequence([choice, cond], self.character)
    state.event_stack.append(self.choice)

  def is_resolved(self):
    if self.evade is None or self.combat is None:
      return False
    return self.evade.evaded or self.combat.defeated

  def log(self, state):
    if self.cancelled and self.horror is None and self.combat is None:
      return f"[{self.character.name}] did not enter combat with a [{self.monster.name}]"
    if self.is_done():
      return f"[{self.character.name}] fought a [{self.monster.name}]"
    return f"[{self.character.name}] is fighting a [{self.monster.name}]"


class EvadeRound(Event):

  def __init__(self, character, monster):
    super().__init__()
    self.character = character
    self.monster = monster
    self.check: Optional[Check] = None
    self.damage: Optional[Event] = None
    self.pass_evade: Optional[PassEvadeRound] = None
    self.evaded = None

  def resolve(self, state):
    if self.evaded is not None:
      return
    if self.check is None:
      self.check = Check(
          self.character, "evade", self.monster.difficulty("evade", state, self.character),
          name=self.monster.visual_name,
      )
    if not self.check.is_done():
      state.event_stack.append(self.check)
      return
    if self.check.success:
      self.pass_evade = PassEvadeRound(self)
      state.event_stack.append(self.pass_evade)
      return

    self.evaded = False
    for event in reversed(state.event_stack):  # Cancel any movement.
      if isinstance(event, (MoveOne, WagonMove)):
        event.cancelled = True
      if isinstance(event, CityMovement):
        event.done = True  # TODO: should this be cancelled instead?
        break
    self.damage = Loss(
        self.character, {"stamina": self.monster.damage("combat", state, self.character)})
    state.event_stack.append(self.damage)

  def is_resolved(self):
    return self.evaded or (self.damage is not None and self.damage.is_done())

  def log(self, state):
    if self.cancelled and self.evaded is None:
      return f"[{self.character.name}] did not flee from a [{self.monster.name}]"
    if self.evaded is None:
      return f"[{self.character.name}] is attempting to flee from a [{self.monster.name}]"
    if self.evaded:
      return f"[{self.character.name}] evaded a [{self.monster.name}]"
    return (f"[{self.character.name}] did not evade the [{self.monster.name}]"
            + " and lost any remaining movement")


class PassEvadeRound(Event):
  def __init__(
      self, evade_round, log_message="[{char_name}] passed an evade round against [{monster_name}]"
  ):
    super().__init__()
    self.character = evade_round.character
    self.evade_round = evade_round
    self.log_message = log_message.format(
        char_name=self.character.name,
        monster_name=getattr(evade_round.monster, "name", "No Monster")
    )
    self.done = False

  def resolve(self, state):
    if self.evade_round.pass_evade is None:
      # can happen if passing the evade is the result of a spell, e.g. Mists of ©
      self.evade_round.pass_evade = self
    if self.evade_round.monster:
      self.evade_round.character.avoid_monsters.append(self.evade_round.monster)
    if (
        self.evade_round.check
        and self.evade_round.check.spend
        and not self.evade_round.check.spend.is_done()
    ):
      self.evade_round.check.spend.cancelled = True
    if self.evade_round.check and not self.evade_round.check.is_done():
      self.evade_round.check.cancelled = True
    self.evade_round.evaded = True
    self.done = True

  def is_resolved(self) -> bool:
    return self.done

  def log(self, state):
    return self.log_message


class CombatRound(Event):

  def __init__(self, character, monster, deactivate=False):
    super().__init__()
    self.character = character
    self.monster = monster
    self.movement_cancelled = False
    self.choice: Event = CombatChoice(
        character, f"Choose weapons to fight the [{monster.name}]", self.monster, combat_round=self,
    )
    self.check: Optional[Check] = None
    self.defeated = None
    self.damage: Optional[Event] = None
    self.pass_combat: Optional[Event] = None
    self.deactivate = deactivate
    self.done = False

  def resolve(self, state):
    if not self.movement_cancelled:  # Cancel any movement.
      for event in reversed(state.event_stack):
        if isinstance(event, (MoveOne, WagonMove)):
          event.cancelled = True
        if isinstance(event, CityMovement):
          self.character.movement_points = 0
          event.done = True  # TODO: should this be cancelled instead?
          break
      self.movement_cancelled = True

    if not self.choice.is_done():
      state.event_stack.append(self.choice)
      return

    if self.check is None:
      attrs = self.monster.attributes(state, self.character)
      self.check = Check(
          self.character, "combat", self.monster.difficulty("combat", state, self.character),
          attributes=attrs, name=self.monster.visual_name,
          difficulty=self.monster.toughness(state, self.character),
      )
    if not self.check.is_done():
      state.event_stack.append(self.check)
      return

    if self.deactivate and not isinstance(self.deactivate, Event):
      self.deactivate = Sequence(
          [DeactivateItems(self.character), DeactivateCombatSpells(self.character)],
          self.character
      )
      state.event_stack.append(self.deactivate)
      return

    if self.defeated is None:
      self.defeated = bool(self.check.success)

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

  def log(self, state):
    if self.cancelled and self.defeated is None:
      return f"[{self.character.name}] did not fight a [{self.monster.name}]"
    if not self.is_resolved():
      return f"[{self.character.name}] is fighting a [{self.monster.name}]"
    if self.defeated:
      return f"[{self.character.name}] defeated a [{self.monster.name}]"
    return f"[{self.character.name}] did not defeat the [{self.monster.name}]"


class PassCheck(Event):
  def __init__(self, character, check, item):
    self.character = character
    self.check = check
    self.item = item
    self.done = False
    super().__init__()

  def resolve(self, state):
    self.check.pass_check = self
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.done:
      return f"[{self.character.name}] force-passed a {self.check.check_type} check"
    if self.cancelled:
      return f"[{self.character.name}] force-passing a {self.check.check_type} check cancelled"
    return f"[{self.character.name}] to force-pass a {self.check.check_type} check"


class PassCombatRound(Event):
  def __init__(
      self,
      combat_round,
      log_message="[{char_name}] passed a combat round against [{monster_name}]"
  ):
    super().__init__()
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

  @property
  def monster(self):
    return self.combat_round.monster

  def resolve(self, state):
    if self.combat_round.pass_combat is None:
      # Can happen if passing combat is the effect of a spell, e.g. Bind Monster
      self.combat_round.pass_combat = self
    self.combat_round.defeated = True
    self.combat_round.done = True
    if self.combat_round.choice is not None and not self.combat_round.choice.is_resolved():
      self.combat_round.choice.cancelled = True
    char = self.combat_round.character
    monster = self.combat_round.monster
    if self.take_trophy is None and monster is not None:
      self.take_trophy = TakeTrophy(char, monster)
      state.event_stack.append(self.take_trophy)
      return

    if (monster is not None
        and monster.has_attribute("overwhelming", state, char)
            and self.damage is None):
      self.damage = Loss(
          char, {"stamina": monster.bypass_damage("combat", state)})
      state.event_stack.append(self.damage)
      return

    self.done = True

  def is_resolved(self) -> bool:
    return self.done

  def log(self, state):
    return self.log_message


class ForceTakeTrophy(Event):

  def __init__(self, character, monster):
    super().__init__()
    self.character = character
    self.monster = monster
    self.done = False

  def resolve(self, state):
    if isinstance(self.monster, MonsterOnBoardChoice):
      if self.monster.is_cancelled():
        self.cancelled = True
        return
      self.monster = self.monster.chosen
    if isinstance(self.monster, DrawMonstersFromCup):
      if self.monster.is_cancelled() or len(self.monster.monsters) != 1:
        self.cancelled = True
        return
      self.monster = state.monsters[self.monster.monsters[0]]

    self.monster.place = None
    self.character.trophies.append(self.monster)
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and not self.done:
      return f"[{self.character.name}] did not take a monster trophy"
    if not self.done:
      return f"[{self.character.name}] takes a monster trophy"
    return f"[{self.character.name}] took a [{self.monster.name}] as a trophy"

  def animated(self):
    return True


class TakeTrophy(ForceTakeTrophy):
  def log(self, state):
    if self.done:
      return (f"[{self.character.name}] took a [{self.monster.name}] as"
              " a trophy after defeating it in combat")
    return super().log(state)


class RespawnTrophies(Event):
  def __init__(self, monster_name, location_name):
    super().__init__()
    self.monster_name = monster_name
    self.location_name = location_name
    self.respawned_monsters = None

  def resolve(self, state):
    monsters = [
        monster
        for char in state.characters
        for monster in char.trophies
        if monster.name == self.monster_name
    ]

    place = state.places[self.location_name]
    for monster in monsters:
      monster.place = place
      for char in state.characters:
        if monster in char.trophies:
          char.trophies.remove(monster)
          break
    self.respawned_monsters = monsters

  def is_resolved(self):
    return self.respawned_monsters is not None

  def log(self, state):
    if self.cancelled and self.respawned_monsters is None:
      return f"Respawning of [{self.monster_name}]s at [{self.location_name}] cancelled"
    if self.respawned_monsters is None:
      return f"[{self.monster_name}]s taken as trophies will respawn at [{self.location_name}]"
    if self.respawned_monsters:
      return f"{len(self.respawned_monsters)} [{self.monster_name}](s) respawned at " \
             f"[{self.location_name}]"
    return f"No [{self.monster_name}]s to respawn at [{self.location_name}]"


class TakeGateTrophy(Event):
  def __init__(self, character, gate):
    super().__init__()
    self.character = character
    self.gate = gate
    self.done = False

  def resolve(self, state):
    if isinstance(self.gate, GateChoice):
      if self.gate.is_cancelled():
        self.cancelled = True
        return
      self.gate = state.places[self.gate.choice].gate
    if self.gate == "draw":
      if state.gates:
        self.gate = state.gates.popleft()
      else:
        # According to my reading, No Gate Markers only awakens the ancient one when a gate opens
        self.cancelled = True
        return

    for place in state.places:
      if getattr(state.places[place], "gate", None) is self.gate:
        state.places[place].gate = None

    if self.gate:
      self.character.trophies.append(self.gate)
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and not self.done:
      return f"{self.character.name} did not take a gate trophy"
    if self.done and self.gate is None:
      return f"{self.character.name} tried to draw a gate, but there were none"
    if not self.done:
      return f"{self.character.name} takes a gate trophy"
    return f"{self.character.name} took a {self.gate.name} gate trophy"

  def animated(self):
    return True


class MonsterAppears(Conditional):

  def __init__(self, character):
    draw = DrawMonstersFromCup(1, character, to_board=False)
    appears = Sequence([draw, EvadeOrCombat(character, draw)], character)
    unstable = values.PlaceUnstable(character.place)
    super().__init__(character, unstable, "", {0: Nothing(), 1: appears})

  def flatten(self):
    return False

  def log(self, state):
    if self.cancelled and self.result is None:
      return "a monster did not appear"
    if self.result is None:
      return "a monster appears"
    if isinstance(self.result, Nothing):
      return "a monster did not appear"
    return "a monster appeared"


class Travel(Event):

  def __init__(self, character, destination=None):
    super().__init__()
    self.character = character
    self.destination: Optional[Union[MapChoice, str]] = destination
    self.done = False

  def resolve(self, state):
    if isinstance(self.destination, MapChoice):
      if self.destination.is_cancelled():
        self.cancelled = True
        return
      if getattr(state.places[self.destination.choice], "gate", None) is None:
        self.cancelled = True
        return
      self.destination = state.places[self.destination.choice].gate.name
    if self.destination is None:
      if getattr(self.character.place, "gate", None) is None:
        self.cancelled = True
        return
      self.destination = self.character.place.gate.name
    self.character.place = state.places[self.destination + "1"]
    self.character.explored = False  # just in case
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and not self.done:
      return f"[{self.character.name}] did not move to another world"
    if not self.done:
      return f"[{self.character.name}] moves to another world"
    return f"[{self.character.name}] moved to [{self.destination}]"

  def animated(self):
    return True


class Return(Event):

  def __init__(self, character, world_name, get_lost=True):
    super().__init__()
    self.character = character
    self.world_name = world_name
    self.return_choice: Optional[ChoiceEvent] = None
    self.get_lost = get_lost
    self.lost: Optional[Event] = None
    self.returned = None

  def resolve(self, state):
    if self.return_choice is None:
      self.return_choice = GateChoice(
          self.character, "Choose a gate to return to", self.world_name, annotation="Return")
      state.event_stack.append(self.return_choice)
      return
    assert self.return_choice.is_done()

    if not self.return_choice.is_resolved():  # Unable to return
      if self.get_lost and self.lost is None:
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

  def log(self, state):
    if self.cancelled and self.returned is None:
      return f"[{self.character.name}] did not return"
    if self.returned is None:
      return f"[{self.character.name}] returns"
    if self.lost is not None:
      return f"[{self.character.name}] was unable to return"
    if not self.returned:
      return f"[{self.character.name}] did not return"
    return f"[{self.character.name}] returned to [{state.places[self.return_choice.choice].name}]"

  def animated(self):
    return True


class PullThroughGate(Sequence):

  def __init__(self, chars):  # TODO: characters should not be delayed if the travel is cancelled?
    assert chars
    self.chars = chars
    seq = []
    for char in chars:
      seq.extend([Travel(char), Delayed(char)])
    super().__init__(seq)


class GateCloseAttempt(Event):

  def __init__(self, character, location_name):
    super().__init__()
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
      self.check = Check(
          self.character, attribute, difficulty,
          name=state.places[self.location_name].gate.json_repr()["name"],
          source=self,
      )
      state.event_stack.append(self.check)
      return

    assert self.check.is_done()
    if not self.check.success:
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

  def log(self, state):
    if self.cancelled and self.closed is None:
      return f"[{self.character.name}] could not close the gate at [{self.location_name}]"
    if self.closed is None:
      return f"[{self.character.name}] can close the gate at [{self.location_name}]"
    if self.choice.is_cancelled() or self.choice.choice == "Don't close":
      return f"[{self.character.name}] chose not to close the gate at [{self.location_name}]"
    if not self.closed:
      return f"[{self.character.name}] failed to close the gate at [{self.location_name}]"
    return f"[{self.character.name}] closed the gate at [{self.location_name}]"


class CloseGate(Event):

  def __init__(self, character, location_name, can_take, can_seal):
    super().__init__()
    self.character = character
    self.location_name: Union[MapChoice, str] = location_name
    self.gate = None
    self.can_take = can_take
    self.take_gate = None
    self.closed_until = None
    self.can_seal = can_seal
    self.return_monsters = None
    self.seal_choice: Optional[ChoiceEvent] = None
    self.sealed = None

  def resolve(self, state: "eldritch.GameState"):
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
      state.places[self.location_name].gate = None

      if self.can_take:
        if self.take_gate is None:
          self.take_gate = TakeGateTrophy(self.character, self.gate)
          state.event_stack.append(self.take_gate)
          return
      else:
        state.gates.append(self.gate)

    if self.closed_until is None:
      closed_until = state.places[self.location_name].closed_until or -1
      if closed_until > state.turn_number:
        self.closed_until = CloseLocation(self.location_name, closed_until - state.turn_number - 1)
        state.event_stack.append(
            self.closed_until
        )
        return
      self.closed_until = False

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

    if not (self.can_seal and state.get_override(self, "can_seal")):
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

  def log(self, state):
    if self.cancelled and self.gate is None:
      return f"[{self.character.name}] did not close a gate"
    if self.gate is None:
      return f"[{self.character.name}] is closing a gate"
    verb = "closed and sealed" if self.sealed else "closed"
    return f"[{self.character.name}] {verb} the gate at [{self.location_name}]"

  def animated(self):
    return True


class RemoveAllSeals(Event):

  def __init__(self):
    super().__init__()
    self.done = False

  def resolve(self, state):
    for place in state.places.values():
      if getattr(place, "sealed", False):
        place.sealed = False
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    return "All locations were unsealed."

  def animated(self):
    return True


class DrawMythosCard(Event):

  def __init__(self, character, require_gate=False):
    super().__init__()
    self.character = character
    self.require_gate = require_gate
    self.shuffled = False
    self.card = None

  def resolve(self, state):
    while True:
      card = state.mythos.popleft()
      state.mythos.append(card)
      if card.name == "ShuffleMythos":
        random.shuffle(state.mythos)
        self.shuffled = True
        continue
      if self.require_gate and card.gate_location is None:
        continue
      break
    self.card = card

  def is_resolved(self):
    return self.card is not None

  def log(self, state):
    if self.cancelled and self.card is None:
      return f"[{self.character.name}] did not draw a mythos card"
    if self.card is None:
      return f"[{self.character.name}] draws a mythos card"
    if self.shuffled:
      return f"[{self.character.name}] shuffled the deck and then drew [{self.card.name}]"
    return f"[{self.character.name}] drew [{self.card.name}]"


class OpenGate(Event):

  def __init__(self, location_name):
    super().__init__()
    self.location_name = location_name
    self.opened = None
    self.draw_monsters: Optional[Event] = None
    self.spawn: Optional[Event] = None
    self.add_doom: Optional[Event] = None

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

    if self.opened is None:
      self.opened = state.places[self.location_name].gate is None
      if self.opened:
        if not state.gates:
          state.event_stack.append(Awaken())
          return
        # TODO: should drawing a gate be its own event?
        state.places[self.location_name].gate = state.gates.popleft()
        state.places[self.location_name].clues = 0
        self.add_doom = AddDoom()
        state.event_stack.append(self.add_doom)
        return

    if self.draw_monsters is None:
      if not self.opened:  # Monster surge
        open_gates = [place for place in state.places.values() if getattr(place, "gate", None)]
        count = max(len(open_gates), len(state.characters))
      else:  # Regular gate opening
        count = 2 if len(state.characters) > 4 else 1
      self.draw_monsters = DrawMonstersFromCup(count)
      state.event_stack.append(self.draw_monsters)
      return

    spawn_gates = [self.location_name]
    if not self.opened:  # Monster surge
      spawn_gates = [
          name for name, place in state.places.items()
          if getattr(place, "gate", None) and place.is_unstable(state)
      ]
    self.spawn = MonsterSpawnChoice(self.draw_monsters, self.location_name, spawn_gates)
    state.event_stack.append(self.spawn)

  def is_resolved(self):
    if self.draw_monsters is None:
      return self.opened is False
    return self.spawn is not None and self.spawn.is_done()

  def log(self, state):
    location_name = self.location_name
    if isinstance(self.location_name, DrawMythosCard):
      location_name = getattr(self.location_name.card, "gate_location", None)

    if self.cancelled and self.opened is None:
      if location_name is not None:
        return f"Gate did not open at [{location_name}]"
      return "Gate did not open"
    if self.opened is None:
      if location_name is not None:
        return f"Gate will open at [{location_name}]"
      return "Gate will not open"
    if self.opened:
      return f"A gate appeared at [{self.location_name}]."
    if self.spawn:
      return f"A monster surge occurred at [{self.location_name}]."
    return f"A gate did not appear at [{self.location_name}]."

  def animated(self):
    return True


class AddToken(Event):
  def __init__(self, asset, token_type, character=None, n_tokens=1):
    assert token_type in asset.tokens
    self.asset = asset
    self.token_type = token_type
    self.character = character
    self.added = False
    self.resolved_max = False
    self.resolved_zero = False
    self.done = False
    self.n_tokens = n_tokens
    super().__init__()

  def is_resolved(self):
    return self.done

  def resolve(self, state):
    token_type = self.token_type
    asset = self.asset

    if not self.added:
      asset.tokens[self.token_type] = max(asset.tokens[self.token_type] + self.n_tokens, 0)
      self.added = True

    if ((not self.resolved_max)
            and (asset.tokens[token_type] >= asset.max_tokens.get(token_type, float("inf")))):
      state.event_stack.append(self.asset.get_max_token_event(token_type, self.character))
      self.resolved_max = True
      return
    if (not self.resolved_zero) and (asset.tokens[token_type] == 0):
      state.event_stack.append(self.asset.get_zero_tokens_event(token_type, self.character))
      self.resolved_zero = True
      return

    self.done = True

  def log(self, state):
    verb = "added" if self.n_tokens > 0 else "removed"
    if not self.added:
      return f"{self.n_tokens} {self.token_type.title()} tokens to be {verb} to [{self.asset.name}]"
    if self.resolved_max:
      return f"[{self.asset.name}] has reached its maximum of {self.token_type.title()} tokens"
    if self.resolved_zero:
      return f"[{self.asset.name}] has reached zero {self.token_type.title()} tokens"
    if self.done and not self.cancelled:
      return f"{self.n_tokens} {self.token_type.title()} token(s) {verb} to [{self.asset.name}]"
    return (f"{self.n_tokens} {self.token_type.title()} token(s) prevented"
            f" from being {verb} to [{self.asset.name}]")

  def animated(self):
    return True


class AddTokenMap(Sequence):
  def __init__(self, asset, token_map, character=None):
    super().__init__(None, character)
    self.asset = asset
    self.token_map = token_map

  def resolve(self, state):
    if isinstance(self.token_map, values.Value):
      self.token_map = {k: v for m in self.token_map.value(state).values() for k, v in m.items()}

    if len(self.events) == 1 and isinstance(self.events[0], Nothing):
      self.events = [
          AddToken(self.asset, token_type, self.character, n_tokens)
          for token_type, n_tokens in self.token_map.items()
      ]
    super().resolve(state)


def RemoveToken(asset, token_type, character=None, n_tokens=1):
  return AddToken(asset, token_type, character, -n_tokens)


class AllyToBox(Event):
  def __init__(self):
    super().__init__()
    self.ally = None
    self.done = False

  def is_resolved(self):
    return self.done

  def resolve(self, state):
    if state.allies:
      self.ally = state.allies.popleft()
      state.boxed_allies.append(self.ally)
    self.done = True

  def log(self, state):
    if self.cancelled:
      return "No ally was boxed"
    if self.ally:
      return f"[{self.ally.name}] was returned to the box"
    if self.done:
      return "No allies remaining to be returned to the box"
    return "Returning an ally to the box"

  def animated(self):
    return True


class AddDoom(Event):
  def __init__(self, character=None, count=1):
    super().__init__()
    self.count = count
    self.done = False
    self.character = character

  def resolve(self, state):
    state.ancient_one.doom += self.count
    state.ancient_one.doom = min(state.ancient_one.doom, state.ancient_one.max_doom)
    if state.game_stage == "awakened":
      state.ancient_one.health += len(state.characters) * self.count
      max_health = state.ancient_one.max_doom * len(state.characters)
      state.ancient_one.health = min(state.ancient_one.health, max_health)
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and not self.done:
      return "Doom token was not added"
    if not self.done:
      return f"{self.count} doom tokens will be added"
    return f"{self.count} doom tokens were added"

  def animated(self):
    return True


class RemoveDoom(Event):
  def __init__(self, character=None):
    super().__init__()
    self.done = False
    self.character = character

  def resolve(self, state):
    if not self.done:
      state.ancient_one.doom = max(0, state.ancient_one.doom - 1)
      if state.game_stage == "awakened":
        state.ancient_one.health = max(0, state.ancient_one.health - len(state.characters))
        if state.ancient_one.health <= 0:
          state.game_stage = "victory"
      self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and not self.done:
      return "Doom token was not removed"
    if not self.done:
      return "Doom token will be removed"
    return "Doom token was removed"

  def animated(self):
    return True


class DrawMonstersFromCup(Event):

  def __init__(self, count=1, character=None, to_board=True):
    super().__init__()
    self.character = character
    self.count = count
    self.awaken: Optional[Event] = None
    self.monsters = None
    self.to_board = to_board

  def resolve(self, state):
    monster_indexes = [
        idx for idx, monster in enumerate(state.monsters)
        if monster.place == state.monster_cup and (
            not self.to_board or state.get_override(monster, "can_draw_to_board"))
    ]
    if len(monster_indexes) < self.count:
      self.awaken = Awaken()
      state.event_stack.append(self.awaken)
      return
    self.monsters = random.sample(monster_indexes, self.count)
    assert len(self.monsters) == self.count, f"Should be {self.count}, drew {len(self.monsters)}"

  def is_resolved(self):
    if self.awaken is not None:
      return self.awaken.is_done()
    return self.monsters is not None

  def log(self, state):
    if self.awaken is not None:
      return f"there were not enough monsters in the cup ({self.count})"
    if self.cancelled:
      return "monsters were not drawn from the cup"
    if self.monsters is None:
      return f"{self.count} monsters will be drawn from the cup"
    return (
        ", ".join(f"[{state.monsters[idx].name}]" for idx in self.monsters) +
        " were drawn from the cup"
    )


class MonsterSpawnChoice(ChoiceEvent):

  def __init__(self, draw_monsters, location_name, open_gates):
    super().__init__()
    self.draw_monsters = draw_monsters
    self.location_name = location_name
    self.open_gates = open_gates
    self.max_count = None
    self.min_count = None
    self.spawn_count = None
    self.outskirts_count = None
    self.steps_remaining = None
    self.terrors = []
    self.character = None
    self.to_spawn = None
    self.pending = collections.defaultdict(list)

  @staticmethod
  def spawn_counts(to_spawn, on_board, in_outskirts, monster_limit, outskirts_limit):
    available_board_count = max(monster_limit - on_board, 0)
    if to_spawn <= available_board_count:
      return to_spawn, 0, 0

    to_outskirts = to_spawn - available_board_count
    available_outskirts_count = max(outskirts_limit - in_outskirts, 0)
    if to_outskirts <= available_outskirts_count:
      return available_board_count, to_outskirts, 0

    remaining = to_outskirts - available_outskirts_count
    in_outskirts = outskirts_limit
    steps_remaining = 0
    if outskirts_limit == 0:
      steps_remaining = -1
    while remaining > 0:
      if in_outskirts == 0:
        steps_remaining += 1
      in_outskirts += 1
      remaining -= 1
      if in_outskirts > outskirts_limit:
        in_outskirts = 0

    return available_board_count, available_outskirts_count+1, steps_remaining

  def compute_choices(self, state):
    if self.draw_monsters.is_cancelled() or len(self.draw_monsters.monsters) < 1:
      self.cancelled = True
      return
    open_count = len(self.open_gates)
    if not open_count:
      self.cancelled = True
      return
    if self.location_name is not None:
      assert getattr(state.places[self.location_name], "gate", None) is not None
    if self.to_spawn is None:
      self.to_spawn = self.draw_monsters.monsters[:]

    on_board = len([m for m in state.monsters if isinstance(m.place, places.CityPlace)])
    in_outskirts = len([m for m in state.monsters if isinstance(m.place, places.Outskirts)])
    self.spawn_count, self.outskirts_count, self.steps_remaining = self.spawn_counts(
        len(self.to_spawn), on_board, in_outskirts, state.monster_limit(), state.outskirts_limit(),
    )
    self.min_count = self.spawn_count // open_count
    self.max_count = (self.spawn_count + open_count - 1) // open_count
    self.character = state.characters[state.first_player]

    # Don't ask the user for a choice in the case of one gate with no outskirts, or all outskirts.
    if self.steps_remaining == 0:
      if len(self.open_gates) == 1 and self.outskirts_count == 0:
        self.pending[self.open_gates[0]] = self.to_spawn
        self.confirm(state)
      elif self.spawn_count == 0:
        self.pending["Outskirts"] = self.to_spawn
        self.confirm(state)

  def resolve(self, state, choice=None):
    if choice == "confirm":
      self.confirm(state)
      return

    if choice == "reset":
      self.pending.clear()
      return

    if not isinstance(choice, dict):
      raise InvalidInput(f"{choice} must be a map")
    if len(choice) != 1:
      raise InvalidInput(f"{choice} must be a map with one entry")
    place = list(choice.keys())[0]
    monster_idx = list(choice.values())[0]
    if not isinstance(monster_idx, int):
      raise InvalidInput(f"{choice} must be a map of string -> monster id (integer)")
    if monster_idx not in self.to_spawn:
      raise InvalidMove(f"Invalid monster id: {monster_idx}")
    if place not in set(self.open_gates) | {"Outskirts", "cup"}:
      raise InvalidMove(f"Invalid monster placement: {place}")

    for monster_list in self.pending.values():
      if monster_idx in monster_list:
        monster_list.remove(monster_idx)
        break
    if place != "cup":
      self.pending[place].append(monster_idx)

  def confirm(self, state):
    choice = self.pending
    # Type validation.
    if not isinstance(choice, dict):
      raise InvalidInput(f"{choice} must be a map")
    if not all(isinstance(val, list) for val in choice.values()):
      raise InvalidInput(f"{choice} must be a map of string -> list of monster ids (integers)")
    bad_indexes = [str(idx) for idx in sum(choice.values(), []) if not isinstance(idx, int)]
    if bad_indexes:
      raise InvalidInput(f"{choice} must be a map of string -> list of monster ids (integers)")

    # Gate/outskirts placement validation.
    invalid_places = set(choice.keys()) - set(self.open_gates) - {"Outskirts"}
    if invalid_places:
      raise InvalidMove(f"Invalid monster placement: {', '.join(invalid_places)}")

    # Validate that monster indexes have no duplicates and are a subset of the spawn indexes.
    monster_indexes = sum(choice.values(), [])
    duplicate_ids = collections.Counter(monster_indexes) - collections.Counter(set(monster_indexes))
    if duplicate_ids:
      raise InvalidMove(f"Duplicate ids: {', '.join(str(idx) for idx in duplicate_ids.keys())}")
    unknown_monsters = [str(idx) for idx in set(monster_indexes) - set(self.to_spawn)]
    if unknown_monsters:
      raise InvalidMove(f"Invalid monster ids: {', '.join(unknown_monsters)}")

    # Validate the total number of monsters should equal the board count + the outskirts count.
    cerr = f"Place {self.spawn_count} monsters on gates and {self.outskirts_count} in the outskirts"
    if len(monster_indexes) != self.spawn_count + self.outskirts_count:
      raise InvalidMove(cerr)
    # Validate that the monsters are correctly distributed between the board and the outskirts.
    outskirts_count = len(choice.get("Outskirts") or [])
    if outskirts_count != self.outskirts_count:
      raise InvalidMove(cerr)

    # We have already validated that the board has received the correct number of monsters. Now,
    # we must validate that they are distributed evenly amongst the gates.
    city_choices = [choice.get(key, []) for key in self.open_gates]
    if self.max_count > 0:
      if max(len(indexes) for indexes in city_choices) != self.max_count:
        raise InvalidMove(f"You may place a maximum of {self.max_count} monsters in a single area")
      if min(len(indexes) for indexes in city_choices) != self.min_count:
        raise InvalidMove(f"Each area must have a minimum of {self.min_count} monsters on it")
      if self.location_name:
        if len(choice.get(self.location_name, [])) != self.max_count:
          raise InvalidMove(f"You must place {self.max_count} monsters on [{self.location_name}]")

    # Validation complete. Distribute the monsters.
    to_remove = set()
    for location_name, monster_indexes in choice.items():
      for monster_idx in monster_indexes:
        state.monsters[monster_idx].place = state.places[location_name]
      to_remove |= set(monster_indexes)

    # Clear the outskirts if necessary.
    in_outskirts = len([m for m in state.monsters if isinstance(m.place, places.Outskirts)])
    if in_outskirts > state.outskirts_limit():
      for monster in state.monsters:
        if monster.place == state.places["Outskirts"]:
          monster.place = state.monster_cup
      # If the outskirts were cleared, increase the terror level.
      self.terrors.append(IncreaseTerror())
      state.event_stack.append(self.terrors[-1])

    # Update the list of monsters to be spawned and clear the pending list.
    self.to_spawn = list(set(self.to_spawn) - to_remove)
    self.pending.clear()

  def is_resolved(self):
    if self.to_spawn is None:
      return False
    if self.terrors and not self.terrors[-1].is_done():
      return False
    return not self.to_spawn

  def prompt(self):
    return ""

  def log(self, state):
    first_player = state.characters[state.first_player]
    if self.to_spawn != []:
      return f"[{first_player.name}] to distribute monsters to the board"
    text = f"[{first_player.name}] sent some monsters to the board and the rest to the outskirts."
    if self.terrors:
      text += f" The outskirts cleared {len(self.terrors)} times."
    return text


class IncreaseTerror(Event):
  def __init__(self, count=1):
    super().__init__()
    self.count = count
    self.added = 0
    self.done = False

  def resolve(self, state):
    close = None
    if self.added < self.count:
      self.added += 1
      if state.terror >= 10:
        state.event_stack.append(AddDoom())
        return
      state.terror += 1
      ally_to_box = AllyToBox()
      if state.terror == 3:
        close = CloseLocation("Store")
      elif state.terror == 6:
        close = CloseLocation("Shop")
      elif state.terror == 9:
        close = CloseLocation("Shoppe")
      if close:
        state.event_stack.append(Sequence([ally_to_box, close]))
      else:
        state.event_stack.append(ally_to_box)
      return

    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and not self.done:
      if self.added:
        return f"Terror track advanced by {self.added} before being cancelled"
      return "Terror track was not advanced"
    if not self.done:
      return f"Terror track will advance by up to {self.count}"
    return f"Terror track advanced by {self.added} of {self.count}"

  def animated(self):
    return True


class AddGlobalEffect(Event):
  def __init__(self, effect, source_deck=None, active_until=None):
    assert source_deck in {"mythos", None}  # TODO: add more as necessary
    super().__init__()
    self.effect = effect
    self.source_deck = source_deck
    self.done = False
    self.active_until = active_until

  def resolve(self, state):
    if self.source_deck is not None:
      source_deck = getattr(state, self.source_deck)
      if source_deck and self.effect in source_deck:
        source_deck.remove(self.effect)
    state.other_globals.append(self.effect)
    if self.active_until is not None:
      self.effect.active_until = self.active_until
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled:
      return f"Didn't add [{self.effect.name}] to play"
    if self.done:
      return f"[{self.effect.name}] enters play"
    return f"[{self.effect.name}] to be entered into play"

  def animated(self):
    return True


class RemoveGlobalEffect(Event):
  def __init__(self, effect, source_deck=None):
    super().__init__()
    self.effect = effect
    self.source_deck = source_deck
    self.done = False

  def resolve(self, state):
    state.other_globals.remove(self.effect)
    if self.source_deck is not None:
      source_deck = getattr(state, self.source_deck)
      if source_deck and self.effect not in source_deck:
        source_deck.append(self.effect)
    self.effect.active_until = None

    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled:
      return f"Didn't remove [{self.effect.name}] from play"
    if self.done:
      return f"[{self.effect.name}] removed from play"
    return f"[{self.effect.name}] to be removed from play"

  def animated(self):
    return True


class SpawnClue(Event):

  def __init__(self, location_name):
    super().__init__()
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
        f"Choose an investigator to receive the clue token at [{self.location_name}]",
        [char.name for char in self.eligible],
    )
    state.event_stack.append(self.choice)

  def is_resolved(self):
    return self.spawned is not None

  def log(self, state):
    if self.spawned is None and not self.cancelled:
      return f"A clue appears at [{self.location_name}]"
    if not self.spawned:
      return f"A Clue does not appear at [{self.location_name}]"
    if not self.eligible:
      return f"A clue appeared at [{self.location_name}]."
    if len(self.eligible) == 1:
      receiving_player = self.eligible[0]
    else:
      receiving_player = self.eligible[self.choice.choice_index or 0]
    return f"[{receiving_player.name}] received a clue."

  def animated(self):
    return True


class MoveMonsters(Event):

  def __init__(self, white_dimensions, black_dimensions):
    super().__init__()
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

  def log(self, state):
    movement = ", ".join(self.white_dimensions) + " move on white; "
    return movement + ", ".join(self.black_dimensions) + " move on black"


class MoveMonster(Event):

  def __init__(self, monster, color):
    super().__init__()
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

    movement = self.monster.movement(state)

    if movement == "stationary":
      self.destination = False
      return

    if movement == "unique":
      if self.move_event is None:
        self.move_event = self.monster.move_event(state)
        state.event_stack.append(self.move_event)
        return
      assert self.move_event.is_done()
      if isinstance(self.move_event, MapChoice) and not self.move_event.is_cancelled():
        self.destination = state.places[self.move_event.choice]
        self.monster.place = self.destination
      else:
        self.destination = False
      return

    local_chars = [char for char in state.characters if char.place == self.monster.place]
    if local_chars:
      self.destination = False
      return

    if movement == "flying":
      if self.move_event is None:
        self.move_event = FlyingLowestSneakChoice(
            state.characters[state.first_player], self.monster,
        )
        state.event_stack.append(self.move_event)
        return
      assert self.move_event.is_done()
      if not self.move_event.is_cancelled():
        self.destination = state.places[self.move_event.choice]
        self.monster.place = self.destination
      else:
        if self.monster.place.name == "Sky":
          self.destination = False
        else:
          self.destination = state.places["Sky"]
          self.monster.place = self.destination
      return

    # TODO: other movement types (stalker, aquatic)

    self.destination = False
    if self.color in getattr(self.monster.place, "movement", {}):
      self.destination = self.monster.place.movement[self.color]
      self.monster.place = self.destination

    # Hack: second move for fast monsters. Mark this event as not resolved, then append a Nothing()
    # to the stack so that we attempt to resolve movement again. Use move_event to track this.
    # We do it this way so that both of the monster's moves are animated.
    if movement == "fast" and self.move_event is None:
      if [char for char in state.characters if char.place == self.monster.place]:
        return
      self.destination = None
      self.move_event = Animate()
      state.event_stack.append(self.move_event)
      return

  def is_resolved(self):
    return self.destination is not None

  def log(self, state):
    if self.cancelled and self.destination is None:
      return f"[{self.monster.name}] did not move"
    if self.destination is None:
      return f"[{self.monster.name}] moves"
    if not self.destination:
      return f"[{self.monster.name}] did not move"
    return f"[{self.monster.name}] moved from [{self.source.name}] to [{self.destination.name}]"

  def animated(self):
    return True


class ReturnToCup(Event):

  def __init__(self, names=None, from_places=None):
    assert names or from_places
    assert not (names and from_places)
    super().__init__()
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

  def log(self, state):
    if self.cancelled and self.returned is None:
      return "monsters were not returned to the cup"
    if self.returned is None:
      if self.names:
        return "All " + ", ".join(self.names) + " will be returned to the cup."
      return "All monsters in " + ", ".join(self.places) + " will be returned to the cup."
    return f"{self.returned} monsters returned to the cup"

  def animated(self):
    return True


class CloseLocation(Event):

  def __init__(self, location_name, for_turns=float("inf"), evict=True):
    super().__init__()
    self.location_name = location_name
    self.for_turns = for_turns
    self.evict = evict
    self.resolved = False

  def resolve(self, state):
    until = state.turn_number + self.for_turns + 1
    place = state.places[self.location_name]
    if place.closed:
      place.closed_until = max(place.closed_until, until)
    else:
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

  def log(self, state):
    if self.cancelled and not self.resolved:
      return f"[{self.location_name}] was not closed"
    suffix = f"for {self.for_turns} turns" if not math.isinf(self.for_turns) else "permanently"
    if not self.resolved:
      return f"[{self.location_name}] is closing {suffix}"
    return f"[{self.location_name}] was closed {suffix}"

  def animated(self):
    return True


class ActivateEnvironment(Event):

  def __init__(self, environment):
    super().__init__()
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

  def log(self, state):
    if self.cancelled and not self.done:
      return f"[{self.env.name}] did not become the new environment"
    if not self.done:
      return f"[{self.env.name}] becomes the new environment"
    return f"[{self.env.name}] became the new environment"

  def animated(self):
    return True


class StartRumor(Event):

  def __init__(self, rumor):
    super().__init__()
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

  def log(self, state):
    if self.cancelled and not self.started:
      return f"Rumor [{self.rumor.name}] did not enter play"
    if self.started is None:
      return f"Rumor [{self.rumor.name}] begins"
    if not self.started:
      return f"Rumor [{self.rumor.name}] did not enter play because a rumor is already in play"
    return f"Rumor [{self.rumor.name}] began"

  def animated(self):
    return True


class ProgressRumor(Event):

  def __init__(self, rumor, amount=1):
    super().__init__()
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

  def log(self, state):
    if self.cancelled and self.increase is None:
      return "The rumor did not advance"
    if self.increase is None:
      return f"The rumor will advance by {self.amount}"
    return f"The rumor advanced by {self.increase}"

  def animated(self):
    return True


class EndRumor(Event):

  def __init__(self, rumor, failed, add_global=False):
    super().__init__()
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

  def log(self, state):
    if self.cancelled and not self.done:
      return "The rumor did not end"
    if self.failed:
      return "The rumor has failed"
    return "The rumor has passed"

  def animated(self):
    return True


class AncientOneAttack(Sequence):
  pass


class Awaken(Event):

  def __init__(self):
    super().__init__()
    self.stack_cleared = False
    self.awaken_done = False
    self.doom_maxed = False
    self.moved_chars = False
    self.done = False

  def resolve(self, state):
    if not self.stack_cleared:
      saved_interrupts = state.interrupt_stack[-1]
      saved_triggers = state.trigger_stack[-1]
      saved_log = state.log_stack[-1]
      state.event_stack.clear()
      state.interrupt_stack.clear()
      state.trigger_stack.clear()
      state.log_stack.clear()
      state.event_stack.append(self)
      state.interrupt_stack.append(saved_interrupts)
      state.trigger_stack.append(saved_triggers)
      state.log_stack.append(saved_log)
      state.game_stage = "awakened"
      state.turn_phase = "ancient"
      state.environment = None
      state.rumor = None
      self.stack_cleared = True
    if not self.awaken_done:
      state.ancient_one.health = len(state.characters) * state.ancient_one.max_doom
      state.ancient_one.awaken(state)
      self.awaken_done = True
    if not self.doom_maxed:
      state.event_stack.append(AddDoom(count=float("inf")))
      self.doom_maxed = True
      return
    if not self.moved_chars:
      # TODO: we can devour lost characters here instead of in global triggers
      for char in state.characters:
        if char.place != state.places["Lost"]:
          char.place = state.places["Battle"]
      self.moved_chars = True
    self.done = True

  def is_resolved(self):
    return self.done

  def log(self, state):
    if self.cancelled and not self.done:
      return f"[{state.ancient_one.name}] did not awaken"
    if not self.done:
      return f"[{state.ancient_one.name}] awakens"
    return f"[{state.ancient_one.name}] awakened"

  def animated(self):
    return True
