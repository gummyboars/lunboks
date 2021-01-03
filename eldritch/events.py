import abc
import operator
from random import SystemRandom
random = SystemRandom()


class Event(metaclass=abc.ABCMeta):
  """The event types are as follows:

  DiceRoll: One or more dice are rolled. The results are saved in the roll attribute.
  Movement: The character will be moved along a route, using movement points as they do so.
  GainOrLoss: The character's sanity, stamina, money, or clues will be changed. The resulting change
    will be stored in the final_adjustments attribute.
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
  def string(self):
    raise NotImplementedError


class Nothing(Event):

  def __init__(self):
    self.done = False

  def resolve(self, state):
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def string(self):
    return "Nothing happens"


class DiceRoll(Event):

  def __init__(self, character, count):
    self.character = character
    self.count = count
    self.roll = None

  def resolve(self, state):
    self.roll = [random.randint(1, 6) for _ in range(self.count)]
    return True

  def is_resolved(self):
    return self.roll is not None

  def string(self):
    if not self.roll:
      return "%s rolled no dice" % self.character.name
    return "%s rolled %s" % (self.character.name, " ".join([str(x) for x in self.roll]))


class Movement(Event):

  def __init__(self, character, route):
    self.character = character
    self.route = route
    self.previous_move = None
    self.done = False

  def resolve(self, state):  # TODO: does every step need to be a separate event?
    if len(self.route) == 0:  # This should never happen.
      self.done = True
      return True
    if len(self.route) > 1:
      self.previous_move = Movement(self.character, self.route[:-1])
      self.route = self.route[-1:]
      state.event_stack.append(self.previous_move)
      return False
    self.character.place = state.places[self.route[0]]
    self.character.movement_points -= 1
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def string(self):
    return "%s moved to %s" % (self.character.name, self.route[0])


class GainOrLoss(Event):

  def __init__(self, character, adjustments, negative=False):
    assert not adjustments.keys() - {"stamina", "sanity", "money", "clues"}
    self.character = character
    self.adjustments = adjustments
    self.negative = negative
    self.final_adjustments = None

  def resolve(self, state):
    for adjustment in self.adjustments.values():
      if isinstance(adjustment, DiceRoll) and not adjustment.is_resolved():
        state.event_stack.append(adjustment)
        return False

    self.final_adjustments = {}
    for attr, adjustment in self.adjustments.items():
      if isinstance(adjustment, DiceRoll):
        adj = sum(adjustment.roll)
      else:
        adj = adjustment
      if self.negative:
        adj = -adj
      old_val = getattr(self.character, attr)
      new_val = old_val + adj
      if new_val < 0:
        new_val = 0
      if attr == "stamina" and new_val > getattr(self.character, "max_stamina"):
        new_val = getattr(self.character, "max_stamina")
      if attr == "sanity" and new_val > getattr(self.character, "max_sanity"):
        new_val = getattr(self.character, "max_sanity")
      self.final_adjustments[attr] = new_val - old_val
      # TODO: this should be a call to the character, both to allow them to override the value
      # change via special abilities, and to allow them to go insane.
      setattr(self.character, attr, new_val)
    return True

  def is_resolved(self):
    return self.final_adjustments is not None

  def string(self):
    gains = ", ".join([
      "%s %s" % (count, attr) for attr, count in self.final_adjustments.items() if count > 0])
    losses = ", ".join([
      "%s %s" % (-count, attr) for attr, count in self.final_adjustments.items() if count < 0])
    result = "gained %s" % gains if gains else ""
    result += " and " if (gains and losses) else ""
    result += "lost %s" % losses if losses else ""
    return self.character.name + " " + result


def Gain(character, adjustments):
  return GainOrLoss(character, adjustments, negative=False)


def Loss(character, adjustments):
  return GainOrLoss(character, adjustments, negative=True)


class StatusChange(Event):

  def __init__(self, character, status, positive=True):
    assert status in {"retainer", "lodge_membership", "delayed", "arrested", "bless_curse"}
    self.character = character
    self.status = status
    self.positive = positive
    self.status_change = None

  def resolve(self, state):
    if self.status in {"retainer", "lodge_membership", "delayed", "arrested"}:
      old_status = getattr(self.character, self.status)
      setattr(self.character, self.status, self.positive)
      self.status_change = int(getattr(self.character, self.status)) - int(old_status)
      return True
    if self.status == "bless_curse":
      old_val = self.character.bless_curse
      new_val = old_val + (1 if self.positive else -1)
      if abs(new_val) > 1:
        new_val = new_val / abs(new_val)
      self.character.bless_curse = new_val
      self.status_change = new_val - old_val
      return True
    raise RuntimeError("unhandled status type %s" % self.status)

  def is_resolved(self):
    return self.status_change is not None

  def string(self):
    status_map = {
        "retainer": (" lost their retainer", " received a retainer"),
        "lodge_membership": (
          " lost their Lodge membership", " became a member of the Silver Twilight Lodge"),
        "delayed": (" is no longer delayed", " was delayed"),
        "arrested": (" is no longer arrested", " was arrested"),
    }
    if self.status_change:
      if self.status in status_map:
        return self.character.name + status_map[self.status][self.status_change]
      if self.character.bless_curse:
        return self.character.name + " became " + (
            "blessed" if self.character.bless_curse > 0 else "cursed")
      return self.character.name + " lost their " + (
          "blessing" if self.status_change == -1 else "curse")
    return "Nothing happens"


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

  def string(self):
    return self.character.name + " moved to " + self.character.place.name


class Draw(Event):

  def __init__(self, character, deck, count):  # TODO: draw_count, keep_count?
    assert deck in {"common", "unique", "spells", "skills"}
    self.character = character
    self.deck = deck
    self.count = count
    self.done = False

  def resolve(self, state):
    deck = getattr(state, self.deck)
    for _ in range(self.count):
      if not deck:
        break
      self.character.possessions.append(deck.popleft())
    self.done = True
    return True

  def is_resolved(self):
    return self.done

  def string(self):
    raise NotImplementedError


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

  def string(self):
    if self.received:
      return self.character.name + " drew a " + self.item_name + " from the " + self.deck + " deck"
    return "There were no " + self.item_name + "s left in the " + self.deck + " deck"


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

  def string(self):
    if not self.successes:
      return self.character.name + " does not have " + self.oper_desc + str(self.threshold) + " " + self.attribute
    return ""


class Check(Event):

  def __init__(self, character, check_type, modifier):
    # TODO: assert on check type
    self.character = character
    self.check_type = check_type
    self.modifier = modifier
    self.dice_result = None
    self.successes = None

  def resolve(self, state):
    # TODO: the check may have an opponent? like undead monsters?
    if self.dice_result is None:
      num_dice = getattr(self.character, self.check_type) + self.modifier
      self.dice_result = DiceRoll(self.character, num_dice)
      state.event_stack.append(self.dice_result)
      return False
    self.successes = self.character.count_successes(self.dice_result.roll, self.check_type)
    return True

  def is_resolved(self):
    return self.successes is not None

  def string(self):
    check_str = self.check_type + " " + ("-" if self.modifier < 0 else "+") + str(self.modifier) + " check"
    if not self.successes:
      return self.character.name + " failed a " + check_str
    return self.character.name + " had " + str(self.successes) + " successes on a " + check_str


class Conditional(Event):

  def __init__(self, character, condition, success_result=None, fail_result=None, success_map=None):
    # Must specify either the success map or both results.
    assert success_map or (success_result and fail_result)
    # Cannot specify both at the same time.
    assert not success_map and (success_result or fail_result)
    assert hasattr(condition, "successes")
    self.success_map = {}
    if success_map:
      assert min(success_map.keys()) == 0
      self.success_map = success_map
    else:
      self.success_map[0] = fail_result
      self.success_map[1] = success_result
    self.character = character
    self.condition = condition
    self.result = None

  def resolve(self, state):
    if not self.condition.is_resolved():
      state.event_stack.append(self.condition)
      return False

    if self.result is not None:
      if not self.result.is_resolved():  # NOTE: this should never happen
        state.event_stack.append(self.result)
        return False
      return True

    for min_successes in reversed(sorted(self.success_map)):
      if self.condition.successes >= min_successes:
        self.result = self.success_map[min_successes]
        state.event_stack.append(self.result)
        break
    else:
      raise RuntimeError("success map without result for %s: %s" % (successes, self.success_map))
    return False

  def is_resolved(self):
    return self.result is not None and self.result.is_resolved()

  def string(self):
    return ""


class Sequence(Event):

  def __init__(self, events):
    self.events = events

  def resolve(self, state):
    for event in self.events:
      if not event.is_resolved():
        state.event_stack.append(event)
        return False
    return True

  def is_resolved(self):
    return all([event.is_resolved() for event in self.events])

  def string(self):
    return ""
