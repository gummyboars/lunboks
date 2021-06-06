from eldritch.assets import Asset, Card
from eldritch import events
from eldritch import places


class Item(Card):

  ITEM_TYPES = {"weapon", "tome", None}

  def __init__(self, name, deck, active_bonuses, passive_bonuses, hands, price, item_type=None):
    assert item_type in self.ITEM_TYPES
    super(Item, self).__init__(name, deck, active_bonuses, passive_bonuses)
    self.hands = hands
    self.price = price
    self.item_type = item_type

  def hands_used(self):
    return self.hands if self.active else 0


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
    return events.Sequence([discard, prevent], owner)

class Whiskey(Item):

  def __init__(self):
    super(Whiskey, self).__init__("Whiskey", "common", {}, {}, None, 1)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.GainOrLoss) or owner != event.character:
      return None
    if "sanity" not in event.adjustments or event.adjustments["sanity"] >= 0:
      return None

    discard = events.DiscardSpecific(event.character, self)
    prevent = events.LossPrevention(self, event, "sanity", 1)
    return events.Sequence([discard, prevent], owner)


class ResearchMaterials(Item):

  def __init__(self):
    super(ResearchMaterials, self).__init__("Research Materials", "common", {}, {}, None, 1)

  def get_usable_trigger(self, event, owner, state):
    return None  # TODO


class Bullwhip(Weapon):

  def __init__(self):
    super(Bullwhip, self).__init__("Bullwhip", "common", {"combat": 1}, {}, 1, 2, "physical")

  def get_usable_trigger(self, event, owner, state):
    if not isinstance(event, events.Check) or owner != event.character:
      return None
    if event.check_type != "combat":
      return None
    return None  # TODO: create an event here


def Revolver38():
  return Weapon(".38 Revolver", "common", {"combat": 3}, {}, 1, 4, "physical")
def Cross():  # TODO: bonus against undead.
  return Weapon("Cross", "common", {}, {"horror": 1}, 1, 3, "magical")
def Dynamite():
  return OneshotWeapon("Dynamite", "common", {"combat": 8}, {}, 2, 4, "physical")
def HolyWater():
  return OneshotWeapon("Holy Water", "unique", {"combat": 6}, {}, 2, 4, "magical")
def TommyGun():
  return Weapon("Tommy Gun", "common", {"combat": 6}, {}, 2, 7, "physical")


class Spell(Item):

  def __init__(self, name, active_bonuses, hands, difficulty, sanity_cost):
    super(Spell, self).__init__(name, "spells", active_bonuses, {}, hands, None)
    self.difficulty = difficulty
    self.sanity_cost = sanity_cost
    self.in_use = False
    self.deactivatable = False

  def get_difficulty(self, state):
    return self.difficulty

  def get_required_successes(self, state):
    return 1

  def hands_used(self):
    return self.hands if self.in_use else 0

  def activate(self, owner, state):
    return events.Nothing()


class CombatSpell(Spell):

  def is_combat(self, event, owner):
    if getattr(event, "character", None) != owner:
      return False
    if isinstance(event, events.CombatChoice) and not event.is_resolved():
      return True
    # May cast even before making the decision to fight or evade. TODO: this is hacky.
    if isinstance(event, events.MultipleChoice) and event.prompt().endswith("or flee from it?") and not event.is_resolved():
      return True
    return False

  def get_usable_interrupt(self, event, owner, state):
    if not self.is_combat(event, owner):
      return None
    if self.in_use:
      if self.deactivatable:
        return events.DeactivateSpell(owner, self)
      return None
    if self.exhausted or owner.sanity < self.sanity_cost:
      return None
    if owner.hands_available() < self.hands:
      return None
    return events.CastSpell(owner, self)

  def get_trigger(self, event, owner, state):
    if not self.in_use:
      return None
    if isinstance(event, (events.CombatRound, events.EvadeRound)) and event.character == owner:
      return events.MarkDeactivatable(owner, self)
    return None

  def activate(self, owner, state):
    return events.ActivateItem(owner, self)


def Wither():
  return CombatSpell("Wither", {"combat": 3}, 1, 0, 0)
def Shrivelling():
  return CombatSpell("Shrivelling", {"combat": 6}, 1, -1, 1)
def DreadCurse():
  return CombatSpell("Dread Curse", {"combat": 9}, 2, -2, 2)


class Voice(Spell):

  def __init__(self):
    super(Voice, self).__init__(
        "Voice", {"speed": 1, "sneak": 1, "fight": 1, "will": 1, "lore": 1, "luck": 1}, 0, -1, 1)

  def get_usable_trigger(self, event, owner, state):
    return None
    # TODO: an actual event for upkeep
    # if self.exhausted or owner.sanity < self.sanity_cost:
    #   return None
    # if state.turn_phase != "upkeep" or state.characters[state.turn_idx] != owner:
    #   return None
    # return events.CastSpell(owner, self)

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.Mythos) and self.active:
      return events.DeactivateSpell(owner, self)
    return None


class FindGate(Spell):

  def __init__(self):
    super(FindGate, self).__init__("Find Gate", {}, 0, -1, 1)

  def movement_in_other_world(self, owner, state):
    if state.turn_phase != "movement" or state.characters[state.turn_idx] != owner:
      return False
    if not isinstance(owner.place, places.OtherWorld):
      return False
    return True

  def get_usable_interrupt(self, event, owner, state):
    if self.exhausted or owner.sanity < self.sanity_cost:
      return None
    if not self.movement_in_other_world(owner, state):
      return None
    if not isinstance(event, events.ForceMovement):
      return None
    return events.CastSpell(owner, self)

  def get_usable_trigger(self, event, owner, state):
    if self.exhausted or owner.sanity < self.sanity_cost:
      return None
    if not self.movement_in_other_world(owner, state):
      return None
    # Note: you can travel into another world during the movement phase by failing a combat check
    # against certain types of monsters.
    if not isinstance(event, events.Travel):
      return None
    return events.CastSpell(owner, self)

  def activate(self, owner, state):
    return events.Return(owner, owner.place.info.name)  # TODO: cancel the ForceMovement if any.


def CreateCommon():
  common = []
  for item in [Revolver38, Dynamite, TommyGun, Food, ResearchMaterials, Bullwhip, Cross]:
    common.extend([item(), item()])
  return common


def CreateUnique():
  counts = {
      HolyWater: 4,
  }
  uniques = []
  for item, count in counts.items():
    uniques.extend([item() for _ in range(count)])
  return uniques


def CreateSpells():
  counts = {
      DreadCurse: 4,
      FindGate: 4,
      Shrivelling: 5,
      Voice: 3,
      Wither: 6,
  }
  spells = []
  for item, count in counts.items():
    spells.extend([item() for _ in range(count)])
  return spells
