from eldritch import events, values
from .base import Item, Weapon, OneshotWeapon

__all__ = [
    "CreateUnique", "EnchantedKnife", "EnchantedBlade", "HolyWater", "MagicLamp", "MagicPowder",
    "SwordOfGlory",
    "AlienStatue", "AncientTablet", "EnchantedJewelry",
]


def CreateUnique():
  counts = {
      HolyWater: 4,
      EnchantedBlade: 2,
      EnchantedKnife: 2,
      MagicLamp: 1,
      MagicPowder: 2,
      SwordOfGlory: 1,
  }
  uniques = []
  for item, count in counts.items():
    uniques.extend([item(idx) for idx in range(count)])
  return uniques


def EnchantedKnife(idx):
  return Weapon("Enchanted Knife", idx, "unique", {"magical": 3}, {}, 1, 5)


def EnchantedBlade(idx):
  return Weapon("Enchanted Blade", idx, "unique", {"magical": 4}, {}, 1, 6)


def HolyWater(idx):
  return OneshotWeapon("Holy Water", idx, "unique", {"magical": 6}, {}, 2, 4)


def MagicLamp(idx):
  return Weapon("Magic Lamp", idx, "unique", {"magical": 5}, {}, 2, 7)


class MagicPowder(Weapon):
  def __init__(self, idx):
    super().__init__("Magic Powder", idx, "unique", {"magical": 9}, {}, 2, 6)

  def get_trigger(self, event, owner, state):
    if not isinstance(event, events.Check) or event.check_type != "combat":
      return None
    if event.character != owner or not self.active:
      return None
    return events.Sequence([
        events.DiscardSpecific(event.character, [self]),
        events.Loss(event.character, {"sanity": 1}),
    ], event.character
    )


def SwordOfGlory(idx):
  return Weapon("Sword of Glory", idx, "unique", {"magical": 6}, {}, 2, 8)


def PallidMask(idx):
  return Item("Pallid Mask", idx, "unique", {}, {"evade": 2}, None, 4)


class AlienStatue(Item):
  def _init__(self, idx):
    super().__init__("Alien Statue", idx, "unique", {}, {}, None, 5)

  def get_usable_interrupt(self, event, owner, state):
    movement_cost = 2
    if not isinstance(event, events.CityMovement) or event.character != owner or event.is_done():
      return None

    if self.exhausted:
      return None

    if event.character.movement_points < movement_cost:
      return None

    success_choice = events.BinaryChoice(
        owner,
        "Gain 1 spell or 2 clues?",
        "Spell?",
        "Clues?",
        events.Draw(owner, "spells", 1),
        events.Gain(owner, {"clues": 2})
    )

    spend = events.Sequence(
        [values.ExactSpendPrerequisite({"sanity": 1, "movement": 2})
         ],
        owner
    )
    spend_choice = events.SpendChoice(
        owner,
        "Spend 2 movement and 1 sanity to roll a die?",
        ["Spend", "Don't"],
        spends=[spend, None],
    )
    return events.Sequence([
        event.ExhaustAsset(owner, self),
        spend_choice,
        events.PassFail(owner, events.DiceRoll(owner, 1),
                        success_choice,
                        events.Loss(owner, {"stamina": 2})),
    ], owner
    )


class AncientTablet(Item):
  def _init__(self, idx):
    super().__init__("Ancient Tablet", idx, "unique", {}, {}, None, 8)

  def get_usable_interrupt(self, event, owner, state):
    movement_cost = 3
    if not isinstance(event, events.CityMovement) or event.character != owner or event.is_done():
      return None

    if self.exhausted:
      return None

    if event.character.movement_points < movement_cost:
      return None

    rolls = events.DiceRoll(owner, 2)
    two_success = events.Draw(owner, "spells", 2, keep_count=2)
    one_success = events.Sequence(
        [events.Draw(owner, "spells", 1), events.Gain(owner, {"clues": 2})],
        owner
    )
    no_success = events.Gain(owner, {"clues": 4})

    return events.Sequence([
        event.DiscardSpecific(owner, [self]),
        event.ChangeMovementPoints(owner, -movement_cost),
        events.Conditional(
            owner, rolls, "successes", {0: no_success, 1: one_success, 2: two_success}
        )
    ], owner)


class BluePyramidWatcher(Item):
  def __init__(self, idx):
    super().__init__("Blue Gate Watcher", idx, "unique", {}, {}, None, 4)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.Check):
      return None
    if not owner == event.character:
      return None
    #TODO: Pass combat check or gate close check
    return None


class DragonsEye(Item):
  def __init__(self, idx):
    super().__init__("Dragon's Eye", idx, "unique", {}, {}, None, 6)

  def get_usable_trigger(self, event, owner, state):
    if not isinstance(event, (events.DrawGateCard, events.DrawEncounter)):
      return None

    if self.exhausted:
      return None

    if not owner == event.character:
      return None

    # TODO: may redraw the current GateCard or EncounterCard
    return None


class EnchantedJewelry(Item):
  def __init__(self, idx):
    super().__init__("Enchanted Jewelry", idx, "unique", {}, {}, None, 3)
    self.tokens["stamina"] = 0
    self.max_tokens["stamina"] = 3

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.GainOrLoss):
      return None

    if not owner == event.character:
      return None

    loss = event.losses.get("stamina", 0)
    if isinstance(loss, values.Value):
      loss = loss.value(state)

    if loss <= 0:
      return None

    reduction = events.LossPrevention(self, event, "stamina", 1)
    return events.Sequence(
        [
            reduction,
            events.AddToken(self, "stamina", event.character, n_tokens=1)
        ],
        owner
    )


class HealingStone(Item):
  def __init__(self, idx):
    super().__init__("Healing Stone", idx, "unique", {}, {}, None, 8)

  def get_usable_interrupt(self, event, owner, state):
    if state.turn_phase == "upkeep" and not self.exhausted:
      choice = events.BinaryChoice(
          owner,
          "Gain 1 Stamina or 1 Sanity?",
          "1 Stamina",
          events.Gain(owner, {"stamina": 1}),
          "1 Sanity",
          events.Gain(owner, {"sanity": 1}),
      )
      # While the text doesn't explicitly say to exhaust, if you don't,
      # you can keep gaining forever!
      return events.Sequence([events.ExhaustAsset(owner, self), choice], owner)
    return super().get_usable_interrupt(event, owner, state)

  def get_trigger(self, event, owner, state):
    # The original card did not specify "Discard Healing Stone if the Ancient One awakens."
    if isinstance(event, events.Awaken):
      return events.DiscardSpecific(owner, [self])
    return super().get_trigger(event, owner, state)


class OuterGodlyFlute(Item):
  def __init__(self, idx):
    super().__init__("Outer Godly Flute", idx, "unique", {}, {}, None, 8)

  def get_usable_trigger(self, event, owner, state):
    if not isinstance(event, events.Combat):
      return None
    seq = [events.Loss(owner, {"stamina": 3, "sanity": 3}), ]
    # TODO: Defeat monsters
    return events.Sequence(
         seq, owner
    )
