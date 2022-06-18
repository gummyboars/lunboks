import operator
from eldritch.assets import Card
from eldritch import events
from eldritch import values
from .base import Weapon


class DeputysRevolver(Weapon):

  def __init__(self):
    super().__init__("Deputy's Revolver", None, "tradables", {"physical": 3}, {}, 1, 0)
    self.losable = False


class PatrolWagon(Card):

  def __init__(self):
    super().__init__("Patrol Wagon", None, "tradables", {}, {})

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.CityMovement) or event.character != owner:
      return None
    if event.is_done() or event.moved:
      return None
    choice = events.PlaceChoice(owner, "Move using Patrol Wagon?", none_choice="Cancel")
    # TODO: add an annotation to the PlaceChoice (e.g. "Move").
    was_cancelled = values.Calculation(choice, None, operator.methodcaller("is_cancelled"))
    patrol = events.ForceMovement(owner, choice)
    cancel = events.CancelEvent(event)
    move = events.WagonMove([patrol, cancel], owner)
    cond = events.Conditional(owner, was_cancelled, None, {0: move, 1: events.Nothing()})
    return events.Sequence([choice, cond], owner)

  def get_trigger(self, event, owner, state):
    if not isinstance(event, (events.Combat, events.Return)) or event.character != owner:
      return None
    die = events.DiceRoll(owner, 1)
    discard = events.DiscardSpecific(owner, [self], to_box=True)
    cond = events.Conditional(owner, values.Die(die), None, {0: discard, 2: events.Nothing()})
    return events.Sequence([die, cond], owner)
