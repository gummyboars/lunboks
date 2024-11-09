from eldritch import events
from eldritch.cards import Card

__all__ = ["Item", "Weapon", "OneshotWeapon", "Tome"]


class Item(Card):
  ITEM_TYPES = ("weapon", "tome", None)

  def __init__(
    self, name, idx, deck, active_bonuses, passive_bonuses, hands, price, item_type=None
  ):
    assert item_type in self.ITEM_TYPES
    super().__init__(name, idx, deck, active_bonuses, passive_bonuses)
    self.hands = hands
    self.price = price
    self.item_type = item_type

  def hands_used(self):
    return self.hands if self.active else 0

  def get_max_token_event(self, token_type, owner):
    return events.DiscardSpecific(owner, [self])


class Weapon(Item):
  def __init__(self, name, idx, deck, active_bonuses, passive_bonuses, hands, price):
    super().__init__(name, idx, deck, active_bonuses, passive_bonuses, hands, price, "weapon")


class OneshotWeapon(Weapon):
  def get_trigger(self, event, owner, state):
    if not isinstance(event, events.Check) or event.check_type != "combat":
      return None
    if event.character != owner or not self.active:
      return None
    return events.DiscardSpecific(event.character, [self])


class Tome(Item):
  def __init__(self, name, idx, deck, price, movement_cost):
    super().__init__(name, idx, deck, {}, {}, None, price, "tome")
    self.movement_cost = movement_cost

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.CityMovement) or event.character != owner or event.is_done():
      return None
    if self.exhausted:
      return None
    if event.character.movement_points < self.movement_cost:
      return None
    return events.ReadTome(
      [
        events.ExhaustAsset(owner, self),
        events.ChangeMovementPoints(owner, -self.movement_cost),
        self.read_event(owner),
      ],
      owner,
    )

  def get_usable_trigger(self, event, owner, state):
    if not isinstance(event, events.WagonMove) or event.character != owner:
      return None
    if self.exhausted:
      return None
    if event.character.movement_points < self.movement_cost:
      return None
    return events.ReadTome(
      [
        events.ExhaustAsset(owner, self),
        events.ChangeMovementPoints(owner, -self.movement_cost),
        self.read_event(owner),
      ],
      owner,
    )

  def read_event(self, owner):  # pylint: disable=unused-argument
    return events.Nothing()
