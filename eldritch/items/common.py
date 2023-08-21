from eldritch import events
from eldritch import values
from .base import Item, Weapon, OneshotWeapon, Tome

__all__ = [
    "CreateCommon",
    "Automatic45", "Axe", "Bullwhip", "CavalrySaber", "Cross", "Derringer18", "Dynamite",
    "Knife", "Revolver38", "Rifle", "Shotgun", "TommyGun", "AncientTome", "DarkCloak",
    "Food", "Lantern", "ResearchMaterials", "Whiskey", "OldJournal",
    "Map", "Motorcycle", "CigaretteCase"
]


def CreateCommon():
  common = []
  for item in [
      AncientTome, Automatic45, DarkCloak, Derringer18, Revolver38, Dynamite, Rifle, Shotgun,
      TommyGun, Food, ResearchMaterials, Bullwhip, Cross, CavalrySaber, Knife, Whiskey, Axe,
      Lantern, OldJournal
  ]:
    common.extend([item(0), item(1)])
  return common


# Weapons


def Automatic45(idx):
  return Weapon(".45 Automatic", idx, "common", {"physical": 4}, {}, 1, 5)


class Axe(Weapon):

  def __init__(self, idx):
    super().__init__("Axe", idx, "common", {"physical": 2}, {}, 1, 3)
    self._two_handed = False

  def get_bonus(self, check_type, attributes):
    bonus = super().get_bonus(check_type, attributes)
    if check_type == "physical" and self._two_handed:
      bonus += 1
    return bonus

  def deactivate(self):
    self._two_handed = False

  def hands_used(self):
    return sum([self._active, self._two_handed])

  def json_repr(self):
    data = super().json_repr()
    if self.active:
      data["hands"] = self.hands_used()
    return data


class Bullwhip(Weapon):

  def __init__(self, idx):
    super().__init__("Bullwhip", idx, "common", {"physical": 1}, {}, 1, 2)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.SpendChoice) or event.is_done() or event.character != owner:
      return None
    if len(state.event_stack) < 2 or not isinstance(state.event_stack[-2], events.Check):
      return None
    if self.exhausted or state.event_stack[-2].check_type != "combat":
      return None
    choice = events.MultipleChoice(owner, "Choose a die to reroll", state.event_stack[-2].roll[:])
    chosen = values.Calculation(choice, "choice_index")
    return events.Sequence([
        events.ExhaustAsset(owner, self), choice,
        events.RerollSpecific(owner, state.event_stack[-2], chosen),
    ], owner)


def CavalrySaber(idx):
  return Weapon("Cavalry Saber", idx, "common", {"physical": 2}, {}, 1, 3)


class Cross(Weapon):

  def __init__(self, idx):
    super().__init__("Cross", idx, "common", {}, {"horror": 1}, 1, 3)

  def get_bonus(self, check_type, attributes):
    bonus = super().get_bonus(check_type, attributes)
    if self.active and check_type == "magical" and attributes and "undead" in attributes:
      bonus += 3
    return bonus


class Derringer18(Weapon):

  def __init__(self, idx):
    super().__init__(".18 Derringer", idx, "common", {"physical": 2}, {}, 1, 3)
    self.losable = False


def Dynamite(idx):
  return OneshotWeapon("Dynamite", idx, "common", {"physical": 8}, {}, 2, 4)


def Knife(idx):
  return Weapon("Knife", idx, "common", {"physical": 1}, {}, 1, 2)


def Revolver38(idx):
  return Weapon(".38 Revolver", idx, "common", {"physical": 3}, {}, 1, 4)


def Rifle(idx):
  return Weapon("Rifle", idx, "common", {"physical": 5}, {}, 2, 6)


def Shotgun(idx):  # NOTE: shotgun's special ability is hard-coded into character's count_successes
  return Weapon("Shotgun", idx, "common", {"physical": 4}, {}, 2, 6)


def TommyGun(idx):
  return Weapon("Tommy Gun", idx, "common", {"physical": 6}, {}, 2, 7)


# Tome

class AncientTome(Tome):

  def __init__(self, idx):
    super().__init__("Ancient Tome", idx, "common", 4, 2)

  def read_event(self, owner):
    check = events.Check(owner, "lore", -1, name=self.name)
    success = events.Sequence(
        [events.Draw(owner, "spells", 1), events.DiscardSpecific(owner, [self])], owner,
    )
    return events.PassFail(owner, check, success, events.Nothing())


class OldJournal(Tome):
  def __init__(self, idx):
    super().__init__("OldJournal", idx, "common", 1, 1)

  def read_event(self, owner):
    check = events.Check(owner, "lore", -1, name=self.name)
    success = events.Sequence(
        [events.Gain(owner, {"clues": 3}), events.DiscardSpecific(owner, [self])], owner
    )
    return events.PassFail(owner, check, success, events.Nothing())

# Other


class CigaretteCase(Item):
  def __init__(self, idx):
    super().__init__("Cigarette Case", idx, "common", {}, {}, None, 1)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.SpendChoice) or event.is_done() or event.character != owner:
      return None
    if len(state.event_stack) < 2 or not isinstance(state.event_stack[-2], events.Check):
      return None
    return events.Sequence([
        events.DiscardSpecific(owner, [self]),
        events.RerollCheck(state.event_stack[-2].character, state.event_stack[-2]),
    ], owner)


def DarkCloak(idx):
  return Item("Dark Cloak", idx, "common", {}, {"evade": 1}, None, 2)


class Food(Item):

  def __init__(self, idx):
    super().__init__("Food", idx, "common", {}, {}, None, 1)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.GainOrLoss) or owner != event.character:
      return None
    if isinstance(event.losses.get("stamina"), values.Value):
      if event.losses["stamina"].value(state) < 1:
        return None
    elif event.losses.get("stamina", 0) < 1:
      return None

    discard = events.DiscardSpecific(event.character, [self])
    prevent = events.LossPrevention(self, event, "stamina", 1)
    return events.Sequence([discard, prevent], owner)


def Lantern(idx):
  return Item("Lantern", idx, "common", {}, {"luck": 1}, None, 3)


class SpeedBoost(Item):
  def __init__(self, name, idx, deck, price, boost_amount: int):
    super().__init__(name, idx, deck, {}, {}, None, price)
    self.boost_amount = boost_amount

  def get_usable_interrupt(self, event, owner, state):
    if isinstance(event, events.CityMovement) and event.character == owner and not self.exhausted:
      return events.Sequence([
          events.ChangeMovementPoints(owner, self.boost_amount),
          events.ExhaustAsset(owner, self)
      ])
    return None


def Map(idx):
  return SpeedBoost("Map", idx, "common", 2, 1)


def Motorcycle(idx):
  return SpeedBoost("Motorcycle", idx, "common", 4, 2)


class ResearchMaterials(Item):

  def __init__(self, idx):
    super().__init__("Research Materials", idx, "common", {}, {}, None, 1)

  def get_spend_amount(self, event, owner, state):
    if not isinstance(event, events.SpendMixin) or event.is_done():
      return None
    if event.character != owner or "clues" not in event.spendable:
      return None
    if self.handle in event.spent_handles():
      return False
    return {"clues": 1}

  def get_spend_event(self, owner):
    return events.DiscardSpecific(owner, [self])


class Whiskey(Item):

  def __init__(self, idx):
    super().__init__("Whiskey", idx, "common", {}, {}, None, 1)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.GainOrLoss) or owner != event.character:
      return None
    if isinstance(event.losses.get("sanity"), values.Value):
      if event.losses["sanity"].value(state) < 1:
        return None
    elif event.losses.get("sanity", 0) < 1:
      return None

    discard = events.DiscardSpecific(event.character, [self])
    prevent = events.LossPrevention(self, event, "sanity", 1)
    return events.Sequence([discard, prevent], owner)
