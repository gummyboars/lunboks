from eldritch.assets import Asset, Card
import eldritch.events as events


class Item(Card):

  ITEM_TYPES = {"weapon", "tome", None}

  def __init__(self, name, deck, active_bonuses, passive_bonuses, hands, price, item_type=None):
    assert item_type in self.ITEM_TYPES
    super(Item, self).__init__(name, deck, active_bonuses, passive_bonuses)
    self.hands = hands
    self.price = price
    self.item_type = item_type


class Weapon(Item):

  BONUS_TYPES = {"physical", "magical", None}

  def __init__(self, name, deck, active_bonuses, passive_bonuses, hands, price, bonus_type):
    assert bonus_type in self.BONUS_TYPES
    super(Weapon, self).__init__(name, deck, active_bonuses, passive_bonuses, hands, price, "weapon")
    self.bonus_type = bonus_type


class OneshotWeapon(Weapon):
  
  def get_trigger(self, event, owner, state):
    if not isinstance(event, events.Check) or event.check_type != "combat":
      return None
    if event.character != owner or not self.active:
      return None
    return events.DiscardSpecific(event.character, self)


class Food(Item):

  def __init__(self):
    super(Food, self).__init__("Food", "common", {}, {}, None, 1)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.GainOrLoss) or owner != event.character:
      return None
    if "stamina" not in event.adjustments or event.adjustments["stamina"] >= 0:
      return None

    discard = events.DiscardSpecific(event.character, self)
    prevent = events.LossPrevention(self, event, "stamina", 1)
    return events.Sequence([discard, prevent])


class Bullwhip(Weapon):

  def __init__(self):
    super(Bullwhip, self).__init__("Bullwhip", "common", {"combat": 1}, {}, 1, 2, "physical")

  def get_usable_trigger(self, event, owner, state):
    if not isinstance(event, events.Check) or owner != event.character:
      return None
    if event.check_type != "combat":
      return None
    return None  # FIXME: create an event here


def Revolver38():
  return Weapon(".38 Revolver", "common", {"combat": 3}, {}, 1, 4, "physical")
def Cross():  # TODO: bonus against undead.
  return Weapon("Cross", "unique", {}, {"horror": 1}, 1, 3, "magical")
def Dynamite():
  return OneshotWeapon("Dynamite", "common", {"combat": 8}, {}, 2, 4, "physical")
def HolyWater():
  return OneshotWeapon("Holy Water", "unique", {"combat": 6}, {}, 2, 4, "magical")
def TommyGun():
  return Weapon("Tommy Gun", "common", {"combat": 6}, {}, 2, 7, "physical")
