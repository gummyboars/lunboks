from eldritch import events, values
from .base import Item, Weapon, OneshotWeapon

__all__ = [
    "CreateUnique", "EnchantedKnife", "EnchantedBlade", "HolyWater", "MagicLamp", "MagicPowder",
    "SwordOfGlory",
    "AncientTablet", "EnchantedJewelry", "GateBox", "HealingStone", "BlueWatcher", "SunkenCityRuby",
    "ObsidianStatue", "OuterGodlyFlute"
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


class AncientTablet(Item):
  def __init__(self, idx):
    super().__init__("Ancient Tablet", idx, "unique", {}, {}, None, 8)

  def get_usable_interrupt(self, event, owner, state):
    movement_cost = 3
    if not isinstance(event, events.CityMovement) or event.character != owner or event.is_done():
      return None

    if self.exhausted:
      return None

    print(owner.movement_points)
    if owner.movement_points < movement_cost:
      return None

    rolls = events.DiceRoll(owner, 2)
    two_success = events.Draw(owner, "spells", 2, keep_count=2)
    one_success = events.Sequence(
        [events.Draw(owner, "spells", 1), events.Gain(owner, {"clues": 2})],
        owner
    )
    no_success = events.Gain(owner, {"clues": 4})

    return events.Sequence([
        events.DiscardSpecific(owner, [self]),
        events.ChangeMovementPoints(owner, -movement_cost),
        rolls,
        events.Conditional(
            owner, rolls, "successes", {0: no_success, 1: one_success, 2: two_success}
        )
    ], owner)


class BlueWatcher(Item):
  def __init__(self, idx):
    super().__init__("Blue Watcher", idx, "unique", {}, {}, None, 4)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, (events.Check, events.CombatRound)):
      return None
    if not owner == event.character:
      return None
    if owner.stamina < 2:
      return None
    if isinstance(event, events.CombatRound):
      return events.Sequence([
          events.PassCombatRound(
              event,
              log_message="{char_name} passed a combat round against {monster_name} using Blue Watcher of the Pyramid"
          ),
          events.DiscardSpecific(owner, [self])
      ], owner)
    # TODO: Pass combat check or gate close check
    if (event.check_type == "combat"
        or (event.check_type in ("fight", "lore")
            and isinstance(state.event_stack[-2], events.GateCloseAttempt))):
      return events.Sequence(
          [events.DiscardSpecific(owner, [self]), events.PassCheck(owner, event)],
          owner
      )
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


class GateBox(Item):
  def __init__(self, idx):
    super().__init__("Gate Box", idx, "unique", {}, {}, None, 4)

  def get_interrupt(self, event, owner, state):
    if (not isinstance(event, events.GateChoice)
        or not event.character == owner
        or len(state.event_stack) < 2
        or not isinstance(state.event_stack[-2], events.Return)
        or event.gate_name is None):
      return None
    print("Gate boxing")
    gate_choice = events.GateChoice(
        owner, "Gate box allows you to choose any open gate", None, event.none_choice, event.annotation
    )
    state.event_stack[-2].return_choice = gate_choice
    return events.Sequence([
        events.CancelEvent(event),
        gate_choice
    ],
        owner)


class HealingStone(Item):
  def __init__(self, idx):
    super().__init__("Healing Stone", idx, "unique", {}, {}, None, 8)

  # Copied get_usable{_trigger,_interrupt,} from Physician ability
  def get_usable_trigger(self, event, owner, state):
    if not isinstance(event, events.UpkeepActions):
      return None
    return self.get_usable(event, owner, state)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, (events.UpkeepActions, events.SliderInput)):
      return None
    return self.get_usable(event, owner, state)

  def get_usable(self, event, owner, state):
    if self.exhausted:
      return None
    if event.character != owner:
      return None
    # End copy-paste

    available = [attr for attr in ["stamina", "sanity"] if getattr(owner, attr) < getattr(owner, f"max_{attr}")(state)]
    if not available:
      return None
    elif len(available) == 1:
      gain = events.Gain(owner, {available[0]: 1})
    else:
      gain = events.BinaryChoice(
          owner,
          "Gain 1 Stamina or 1 Sanity?",
          "1 Stamina",
          "1 Sanity",
          events.Gain(owner, {"stamina": 1}),
          events.Gain(owner, {"sanity": 1}),
      )
    # While the text doesn't explicitly say to exhaust, if you don't,
    # you can keep gaining forever!
    return events.Sequence([events.ExhaustAsset(owner, self), gain], owner)

  def get_trigger(self, event, owner, state):
    # The original card did not specify "Discard Healing Stone if the Ancient One awakens."
    if isinstance(event, events.Awaken):
      return events.DiscardSpecific(owner, [self])
    return super().get_trigger(event, owner, state)


class ObsidianStatue(Item):
  def __init__(self, idx):
    super().__init__("Obsidian Statue", idx, "unique", {}, {}, None, 4)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.GainOrLoss) or not event.character == owner:
      return None

    types = [loss_type for loss_type in ("sanity", "stamina") if loss_type in event.losses]
    seq = [events.DiscardSpecific(owner, [self])]
    if len(types) == 0:
      return None
    elif len(types) == 1:
      loss_type = types[0]
      seq.append(events.LossPrevention(self, event, loss_type, float("inf")))
    else:
      seq.append(
          events.BinaryChoice(
              owner,
              "Prevent Sanity or Stamina loss?",
              "Sanity",
              "Stamina",
              events.LossPrevention(self, event, "sanity", float("inf")),
              events.LossPrevention(self, event, "stamina", float("inf")),
          )
      )
    return events.Sequence(seq, owner)


class OuterGodlyFlute(Item):
  def __init__(self, idx):
    super().__init__("Flute", idx, "unique", {}, {}, None, 8)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.CombatRound):
      return None
    if owner.stamina < 3 or owner.sanity < 3:
      print("Can't use")
      return None

    seq = [
        events.DiscardSpecific(owner, [self]),
        events.PassCombatRound(event)
    ]
    for monster in state.monsters:
      if monster.place == owner.place and monster != event.monster:
        seq.append(events.TakeTrophy(owner, monster))
    seq.append(events.Loss(owner, {"stamina": 3, "sanity": 3}))
    return events.Sequence(
        seq, owner
    )


class SunkenCityRuby(Item):
  def __init__(self, idx):
    super().__init__("Ruby", idx, "unique", {}, {}, None, 8)

  def get_interrupt(self, event, owner, state):
    if isinstance(event, events.CityMovement) and event.character == owner:
      return events.ChangeMovementPoints(owner, 3)
    return None
