import abc
import collections
import operator
from random import SystemRandom
random = SystemRandom()

import eldritch.places as places


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
  AttributePrerequisite: Evaluates whether a character meets a specific prerequisite and stores
    either 0 or 1 in the successes attribute.
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


class EndTurn(Event):

  def __init__(self, character, phase):
    self.character = character
    self.phase = phase
    self.done = False

  def resolve(self, state):
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class EndUpkeep(EndTurn):

  def __init__(self, character):
    super(EndUpkeep, self).__init__(character, "upkeep")


class EndMovement(EndTurn):

  def __init__(self, character):
    super(EndMovement, self).__init__(character, "movement")


class DiceRoll(Event):

  def __init__(self, character, count):
    self.character = character
    self.count = count
    self.roll = None
    self.sum = None

  def resolve(self, state):
    self.roll = [random.randint(1, 6) for _ in range(self.count)]
    self.sum = sum(self.roll)
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

  def resolve(self, state):
    if self.character.movement_points <= 0:
      self.done = True
      return True
    assert self.dest in self.character.place.connections
    self.character.place = self.dest
    self.character.movement_points -= 1
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{self.character.name} moved to {self.dest.name}"


def Movement(character, route):
  return Sequence([MoveOne(character, dest) for dest in route], character)


class GainOrLoss(Event):

  def __init__(self, character, gains, losses):
    assert not gains.keys() - {"stamina", "sanity", "dollars", "clues"}
    assert not losses.keys() - {"stamina", "sanity", "dollars", "clues"}
    assert not gains.keys() & losses.keys()
    self.character = character
    self.gains = collections.defaultdict(int)
    self.gains.update(gains)
    self.losses = collections.defaultdict(int)
    self.losses.update(losses)
    self.final_adjustments = None

  def resolve(self, state):
    self.final_adjustments = {}
    for attr, adjustment in self.adjustments.items():
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

  @property
  def adjustments(self):
    computed = collections.defaultdict(int)
    for attr, gain in self.gains.items():
      if isinstance(gain, DiceRoll):
        assert gain.is_resolved()
        adj = sum(gain.roll)
      elif isinstance(gain, MultipleChoice):
        assert gain.is_resolved() and isinstance(gain.choice, int)
        adj = gain.choice
      else:
        adj = gain
      computed[attr] += adj
    for attr, loss in self.losses.items():
      if isinstance(loss, DiceRoll):
        assert loss.is_resolved()
        adj = sum(loss.roll)
      elif isinstance(loss, MultipleChoice):
        assert loss.is_resolved() and isinstance(loss.choice, int)
        adj = loss.choice
      else:
        adj = loss
      computed[attr] -= adj
    return computed

  def is_resolved(self):
    return self.final_adjustments is not None

  def start_str(self):
    return ""

  def finish_str(self):
    gains = ", ".join([
      "%s %s" % (count, attr) for attr, count in self.final_adjustments.items() if count > 0])
    losses = ", ".join([
      "%s %s" % (-count, attr) for attr, count in self.final_adjustments.items() if count < 0])
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
    assert isinstance(amount, (int, MultipleChoice, DiceRoll))
    if isinstance(amount, MultipleChoice):
      assert all([isinstance(choice, int) for choice in amount.choices])
    self.character = character
    self.attr1 = attr1
    self.attr2 = attr2
    self.amount = amount
    self.choice = None
    self.gain = None

  def resolve(self, state):
    if isinstance(self.amount, (MultipleChoice, DiceRoll)):
      assert self.amount.is_resolved()

    if self.gain is not None:
      assert self.gain.is_resolved()
      return True

    if isinstance(self.amount, MultipleChoice):
      amount = self.amount.choice
    elif isinstance(self.amount, DiceRoll):
      amount = sum(self.amount.roll)
    else:
      amount = self.amount

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
    assert attribute in source_event.adjustments
    assert source_event.adjustments[attribute] < 0
    self.prevention_source = prevention_source
    self.source_event = source_event
    self.attribute = attribute
    self.amount = amount
    self.amount_prevented = None
    self.done = False

  def resolve(self, state):
    if self.source_event.adjustments[self.attribute] >= 0:
      self.amount_prevented = 0
      return True
    self.amount_prevented = min(self.amount, -self.source_event.adjustments[self.attribute])
    self.source_event.gains[self.attribute] += self.amount_prevented
    return True

  def is_resolved(self):
    return self.amount_prevented is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.amount_prevented:
      return ""
    return f"{self.prevention_source.name} prevented {self.amount_prevented} {self.attribute} loss"


class InsaneOrUnconscious(Event):

  def __init__(self, character, attribute, desc, place):
    self.character = character
    self.attribute = attribute
    self.desc = desc
    self.place = place
    self.stack_cleared = False
    self.force_move = ForceMovement(character, place)

  def resolve(self, state):
    if self.force_move.is_resolved():
      return True

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
    self.stack_cleared = True

    # TODO: lose half the items and clues.
    self.character.lost_turn = True
    state.event_stack.append(self.force_move)
    return False

  def is_resolved(self):
    return self.force_move.is_resolved()

  def start_str(self):
    return f"{self.character.name} {self.desc}"

  def finish_str(self):
    return f"{self.character.name} woke up in the {self.place}"


def Insane(character, asylum):
  return InsaneOrUnconscious(character, "sanity", "went insane", "Asylum")


def Unconscious(character, hospital):
  return InsaneOrUnconscious(character, "stamina", "got knocked unconscious", "Hospital")


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
    self.character.place = state.places[self.location_name]
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def start_str(self):
    return ""

  def finish_str(self):
    return self.character.name + " moved to " + self.character.place.name


class Draw(Event):

  def __init__(self, character, deck, draw_count, prompt="Choose a card"):
    assert deck in {"common", "unique", "spells", "skills", "allies"}
    self.character = character
    self.deck = deck
    self.prompt = prompt
    self.draw_count = draw_count
    self.keep_count = 1  # TODO: allow the player to keep more than one?
    self.drawn = None
    self.choice = None
    self.kept = None

  def resolve(self, state):
    if self.kept is not None:
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
        getattr(state, self.deck).append(card)
      return True

    if self.drawn is None:
      self.drawn = []
      deck = getattr(state, self.deck)
      for _ in range(self.draw_count):
        if not deck:
          break
        self.drawn.append(deck.popleft())
      # TODO: is there a scenario when the player can go insane/unconscious before they
      # successfully pick a card?

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
    return f"{self.character.name} draws {self.draw_count} cards from the {self.deck} deck"

  def finish_str(self):
    return f"{self.character.name} keeps " + ", ".join(self.kept)


class Encounter(Event):

  def __init__(self, character, location):
    self.character = character
    self.location = location
    self.draw = DrawEncounter(character, location, 1)
    self.encounter = None

  def resolve(self, state):
    if not self.draw.is_resolved():
      state.event_stack.append(self.draw)
      return False

    if self.encounter and self.encounter.is_resolved():
      return True

    if len(self.draw.cards) == 1:
      self.encounter = self.draw.cards[0].encounter_event(self.character, self.location.name)
      state.event_stack.append(self.encounter)
      return False

    encounters = [
        card.encounter_event(self.character, self.location.name) for card in self.draw.cards]
    choice = CardChoice(self.character, "Choose an Encounter", [card.name for card in draw.cards])
    cond = Conditional(
        self.character, choice, "choice_index", {idx: enc for idx, enc in enumerate(encounters)})
    self.encounter = Sequence([choice, cond], character)
    state.stack.append(self.encounter)
    return False

  def is_resolved(self):
    return self.encounter and self.encounter.is_resolved()

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class DrawEncounter(Event):

  def __init__(self, character, location, count):
    assert count > 0
    self.character = character
    self.location = location
    self.count = count
    self.cards = []

  def resolve(self, state):
    encounters = self.location.neighborhood.encounters
    assert len(encounters) >= self.count
    self.cards.extend(random.sample(encounters, self.count))
    return True

  def is_resolved(self):
    return len(self.cards) == self.count

  def start_str(self):
    return f"{self.character.name} draws {self.count} encounter cards"

  def finish_str(self):
    return f"{self.character.name} drew " + ", ".join([card.name for card in self.cards])


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


# TODO: also add a discard by name
class DiscardSpecific(Event):

  def __init__(self, character, item):
    if isinstance(item, str):
      try:
        item = next(i for i in character.possessions if i.name == item)
      except StopIteration:
        raise AssertionError("Character does not have any {}".format(item))
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


class AttributePrerequisite(Event):

  def __init__(self, character, attribute, threshold, operand):
    oper_map = {
        "at least": operator.ge,
        "less than": operator.lt,
        "exactly": operator.eq,
    }
    assert operand in oper_map
    self.character = character
    self.attribute = attribute
    self.threshold = threshold
    self.oper_desc = operand
    self.operand = oper_map[operand]
    self.successes = None

  def resolve(self, state):
    self.successes = int(self.operand(getattr(self.character, self.attribute), self.threshold))
    return True

  def is_resolved(self):
    return self.successes is not None

  def start_str(self):
    return ""

  def finish_str(self):
    if not self.successes:
      return self.character.name + " does not have " + self.oper_desc + " " + str(self.threshold) + " " + self.attribute
    return ""


class Check(Event):

  def __init__(self, character, check_type, modifier):
    # TODO: assert on check type
    self.character = character
    self.check_type = check_type
    self.modifier = modifier
    self.dice = None
    self.roll = None
    self.successes = None

  def resolve(self, state):
    # TODO: the check may have an opponent? like undead monsters?
    if self.dice is None:
      num_dice = getattr(self.character, self.check_type) + self.modifier
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
    assert hasattr(condition, attribute)
    assert all([isinstance(key, int) for key in result_map])
    assert min(result_map.keys()) == 0
    self.character = character
    self.condition = condition
    self.attribute = attribute
    self.result_map = result_map
    self.result = None

  def resolve(self, state):
    assert self.condition.is_resolved()
    if self.result is not None:
      if not self.result.is_resolved():  # NOTE: this should never happen
        state.event_stack.append(self.result)
        return False
      return True

    for min_result in reversed(sorted(self.result_map)):
      if getattr(self.condition, self.attribute) >= min_result:
        self.result = self.result_map[min_result]
        state.event_stack.append(self.result)
        return False
    raise RuntimeError(
        "result map without result for %s: %s" %
        (getattr(self.condition, self.attribute), self.result_map)
    )

  def is_resolved(self):
    return self.result is not None and self.result.is_resolved()

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


def PassFail(character, condition, pass_result, fail_result):
  outcome = Conditional(character, condition, "successes", {0: fail_result, 1: pass_result})
  return Sequence([condition, outcome], character)


class Sequence(Event):

  def __init__(self, events, character=None):
    self.events = events
    self.character = character

  def resolve(self, state):
    for event in self.events:
      if not event.is_resolved():
        state.event_stack.append(event)
        return False
    return True

  def is_resolved(self):
    return all([event.is_resolved() for event in self.events])

  def start_str(self):
    return ""

  def finish_str(self):
    return ""


class Arrested(Sequence):

  def __init__(self, character):
    super(Arrested, self).__init__([
      ForceMovement(character, "Police"), LoseTurn(character),
      Loss(character, {"dollars": character.dollars // 2}),
    ], character)


class ChoiceEvent(Event):

  @abc.abstractmethod
  def resolve(self, state, choice=None):
    raise NotImplementedError

  @abc.abstractmethod
  def prompt(self):
    raise NotImplementedError


class MultipleChoice(ChoiceEvent):

  def __init__(self, character, prompt, choices):
    self.character = character
    self._prompt = prompt
    self.choices = choices
    self.choice = None

  def resolve(self, state, choice=None):
    assert not self.is_resolved()
    assert choice in self.choices
    self.choice = choice
    return True

  def is_resolved(self):
    return self.choice is not None

  def start_str(self):
    return f"{self.character.name} must choose one of " + ", ".join([str(c) for c in self.choices])

  def finish_str(self):
    return f"{self.character.name} chose {str(self.choice)}"

  def prompt(self):
    return self._prompt

  @property
  def choice_index(self):
    if self.choice is None:
      return None
    return self.choices.index(self.choice)


def BinaryChoice(character, prompt, first_choice, second_choice, first_event, second_event):
  choice = MultipleChoice(character, prompt, [first_choice, second_choice])
  outcome = Conditional(character, choice, "choice_index", {0: first_event, 1: second_event})
  return Sequence([choice, outcome], character)


class ItemChoice(ChoiceEvent):

  def __init__(self, character, prompt):
    self.character = character
    self._prompt = prompt
    self.choices = None

  def resolve(self, state, choice=None):
    if self.is_resolved():
      return True
    assert all([0 <= idx < len(self.character.possessions) for idx in choice])
    self.resolve_internal(choice)

  def resolve_internal(self, choices):
    self.choices = [self.character.possessions[idx] for idx in choices]

  def is_resolved(self):
    return self.choices is not None

  def start_str(self):
    return f"{self.character.name} must " + self.prompt()

  def finish_str(self):
    return f"{self.character.name} chose some stuff"

  def prompt(self):
    return self._prompt


class CombatChoice(ItemChoice):

  def resolve_internal(self, choices):
    for idx in choices:
      assert getattr(self.character.possessions[idx], "hands", None) is not None
    assert sum([self.character.possessions[idx].hands for idx in choices]) <= 2
    super(CombatChoice, self).resolve_internal(choices)
    for pos in self.character.possessions:
      pos._active = False
    for pos in self.choices:
      pos._active = True


class ItemCountChoice(ItemChoice):

  def __init__(self, character, prompt, count):
    super(ItemCountChoice, self).__init__(character, prompt)
    self.count = count

  def resolve_internal(self, choices):
    assert self.count == len(choices)
    super(ItemCountChoice, self).resolve_internal(choices)


class CardChoice(MultipleChoice):
  pass


class EvadeOrFightAll(Sequence):
  
  def __init__(self, character, monsters):
   super(EvadeOrFightAll, self).__init__([
     EvadeOrCombat(character, monster) for monster in monsters], character)


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
    if monster.difficulty("horror") is not None:
      self.horror = Check(character, "horror", monster.difficulty("horror"))
      self.sanity_loss = Loss(character, {"sanity": monster.damage("horror")})
    else:
      self.horror = None
      self.sanity_loss = None
    self.choice = None
    self.evade = None
    self.combat = None
    self.done = False

  def resolve(self, state):
    if self.horror is not None:
      if not self.horror.is_resolved():
        state.event_stack.append(self.horror)
        return False
      if self.horror.successes < 1 and not self.sanity_loss.is_resolved():
        state.event_stack.append(self.sanity_loss)
        return False
    if self.choice is None:
      # TODO: deal with ambush
      self.combat = CombatRound(self.character, self.monster)
      self.evade = EvadeRound(self.character, self.monster)
      prompt = f"Fight the {self.monster.name} or flee from it?"
      self.choice = BinaryChoice(self.character, prompt, "Fight", "Flee", self.combat, self.evade)
      state.event_stack.append(self.choice)
      return False
    assert self.choice.is_resolved()
    if self.evade.evaded:
      return True
    if self.combat.defeated:
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
    self.check = Check(character, "evade", monster.difficulty("evade"))
    self.damage = Loss(character, {"stamina": monster.damage("combat")})
    self.evaded = None

  def resolve(self, state):
    if self.evaded is not None:
      return True
    if not self.check.is_resolved():
      state.event_stack.append(self.check)
      return False
    if self.check.successes >= 1:
      self.evaded = True
      return True
    state.event_stack.append(self.damage)
    return False

  def is_resolved(self):
    return self.evaded or self.damage.is_resolved()

  def start_str(self):
    return f"{self.character.name} attempted to flee from {self.monster.name}"

  def finish_str(self):
    if self.evaded:
      return f"{self.character.name} evaded a {self.monster.name}"
    return f"{self.character.name} did not evade the {self.monster.name}"


class CombatRound(Event):

  def __init__(self, character, monster):
    self.character = character
    self.monster = monster
    self.choice = CombatChoice(character, f"Choose weapons to fight the {monster.name}")
    self.check = Check(character, "combat", monster.difficulty("combat"))
    self.damage = Loss(character, {"stamina": monster.damage("combat")})
    self.defeated = None

  def resolve(self, state):
    if self.defeated is not None:
      return True
    if not self.choice.is_resolved():
      state.event_stack.append(self.choice)
      return False
    if not self.check.is_resolved():
      state.event_stack.append(self.check)
      return False
    if self.check.successes >= self.monster.toughness:
      # TODO: take the monster as a trophy
      self.defeated = True
      return True
    self.defeated = False
    state.event_stack.append(self.damage)
    return False

  def is_resolved(self):
    return self.defeated or self.damage.is_resolved()

  def start_str(self):
    return f"{self.character.name} started a combat round against a {self.monster.name}"

  def finish_str(self):
    if self.defeated:
      return f"{self.character.name} defeated a {self.monster.name}"
    return f"{self.character.name} did not defeat the {self.monster.name}"


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
      return True  # TODO: monster surge

    # TODO: inevstigators getting sucked in.
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


class SpawnGateMonster(Event):

  def __init__(self, location_name):
    self.location_name = location_name
    self.spawned = None

  def resolve(self, state):
    if self.spawned is not None:
      return True

    self.spawned = []
    num_to_spawn = 2 if len(state.characters) > 4 else 1
    monster_cup = [monster for monster in state.monsters if monster.place == state.monster_cup]
    # TODO: if there are no monsters left, the ancient one awakens.
    self.spawned = random.sample(monster_cup, num_to_spawn)
    # TODO: check against the monster limit, send some to the outskirts.
    for monster in self.spawned:
      monster.place = state.places[self.location_name]
    return True

  def is_resolved(self):
    return self.spawned is not None

  def start_str(self):
    return ""

  def finish_str(self):
    return f"{len(self.spawned)} monsters appeared at {self.location_name}."


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
