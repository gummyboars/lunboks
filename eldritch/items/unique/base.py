import operator
import typing

from eldritch import events, values
from eldritch.items.core import Item, Weapon, OneshotWeapon, Tome

if typing.TYPE_CHECKING:
  from eldritch.eldritch import GameState


__all__ = [
  "CreateUnique",
  "EnchantedKnife",
  "EnchantedBlade",
  "HolyWater",
  "MagicLamp",
  "MagicPowder",
  "SwordOfGlory",
  "AncientTablet",
  "EnchantedJewelry",
  "GateBox",
  "HealingStone",
  "BlueWatcher",
  "SunkenCityRuby",
  "ObsidianStatue",
  "OuterGodlyFlute",
  "SilverKey",
  "PallidMask",
  "DragonsEye",
  "AlienStatue",
  "ElderSign",
  "WardingStatue",
  "TibetanTome",
  "MysticismTome",
  "BlackMagicTome",
  "BlackBook",
  "BookOfTheDead",
  "YellowPlay",
]


def CreateUnique():
  counts = {
    AncientTablet: 1,
    BlueWatcher: 1,
    EnchantedJewelry: 1,
    # TODO: Have inclusion of elder signs be a configurable option?
    ElderSign: 1,  # 4
    OuterGodlyFlute: 1,
    GateBox: 1,
    HealingStone: 1,
    ObsidianStatue: 1,
    PallidMask: 1,
    DragonsEye: 1,
    AlienStatue: 1,
    SunkenCityRuby: 1,
    SilverKey: 1,
    HolyWater: 4,
    EnchantedBlade: 2,
    EnchantedKnife: 2,
    MagicLamp: 1,
    MagicPowder: 2,
    SwordOfGlory: 1,
    WardingStatue: 1,
    TibetanTome: 1,
    MysticismTome: 2,
    BlackMagicTome: 2,
    BlackBook: 2,
    BookOfTheDead: 1,
    YellowPlay: 2,
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
    return events.Sequence(
      [
        events.DiscardSpecific(event.character, [self]),
        events.Loss(event.character, {"sanity": 1}),
      ],
      event.character,
    )


def SwordOfGlory(idx):
  return Weapon("Sword of Glory", idx, "unique", {"magical": 6}, {}, 2, 8)


def PallidMask(idx):
  return Item("Pallid Mask", idx, "unique", {}, {"evade": 2}, None, 4)


class DragonsEye(Item):
  def __init__(self, idx):
    super().__init__("Dragon's Eye", idx, "unique", {}, {}, None, 6)

  def get_usable_interrupt(self, event, owner, state):
    if len(state.event_stack) < 3 or not isinstance(event, events.CardChoice):
      return None
    if event.is_done() or event.prompt() != "Choose an Encounter":  # TODO: hacky/fragile
      return None
    if event.character != owner or self.exhausted:
      return None
    parent = state.event_stack[-3]
    if not isinstance(parent, (events.Encounter, events.GateEncounter)):
      return None
    return events.Sequence(
      [
        events.ExhaustAsset(owner, self),
        events.MulliganEncounter(owner, parent),
        events.Loss(owner, {"sanity": 1}),
      ],
      owner,
    )


class AlienStatue(Item):
  def __init__(self, idx):
    super().__init__("Alien Statue", idx, "unique", {}, {}, None, 5)
    self.movement_cost = 2

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.CityMovement) or event.character != owner or event.is_done():
      return None
    if self.exhausted:
      return None
    if event.character.movement_points < self.movement_cost:
      return None
    return self.event(owner)

  def get_usable_trigger(self, event, owner, state):
    if not isinstance(event, events.WagonMove) or event.character != owner:
      return None
    if self.exhausted:
      return None
    if event.character.movement_points < self.movement_cost:
      return None
    return self.event(owner)

  def event(self, owner):
    spell = events.Draw(owner, "spells", 1)
    clues = events.Gain(owner, {"clues": 3})
    prompt = "Draw 1 spell or gain 3 clues?"
    gain_choice = events.CardChoice(owner, prompt, ["spells", "3 clues"])
    gain_cond = events.Conditional(owner, gain_choice, "choice_index", {0: spell, 1: clues})
    gain = events.Sequence([gain_choice, gain_cond], owner)
    loss = events.Loss(owner, {"stamina": 2})
    die = events.DiceRoll(owner, 1)
    cond = events.Conditional(owner, die, "successes", {0: loss, 1: gain})
    spend = values.ExactSpendPrerequisite({"sanity": 1})
    use_choice = events.CardSpendChoice(
      owner, f"Use [{self.name}]?", [self.handle, "Cancel"], spends=[spend, None]
    )
    use = events.Sequence(
      [
        events.ExhaustAsset(owner, self),
        events.ChangeMovementPoints(owner, -self.movement_cost),
        die,
        cond,
      ],
      owner,
    )
    use_cond = events.Conditional(owner, use_choice, "choice_index", {0: use, 1: events.Nothing()})
    return events.Sequence([use_choice, use_cond], owner)


class AncientTablet(Item):
  def __init__(self, idx):
    super().__init__("Ancient Tablet", idx, "unique", {}, {}, None, 8)

  def get_usable_interrupt(self, event, owner, state):
    movement_cost = 3
    if not isinstance(event, events.CityMovement) or event.character != owner or event.is_done():
      return None

    if self.exhausted:
      return None

    if owner.movement_points < movement_cost:
      return None

    rolls = events.DiceRoll(owner, 2, name=self.handle)
    two_success = events.Draw(owner, "spells", 2, keep_count=2)
    one_success = events.Sequence(
      [events.Draw(owner, "spells", 1), events.Gain(owner, {"clues": 2})], owner
    )
    no_success = events.Gain(owner, {"clues": 4})

    return events.Sequence(
      [
        events.DiscardSpecific(owner, [self]),
        events.ChangeMovementPoints(owner, -movement_cost),
        rolls,
        events.Conditional(
          owner, rolls, "successes", {0: no_success, 1: one_success, 2: two_success}
        ),
      ],
      owner,
    )


class BlueWatcher(Item):
  def __init__(self, idx):
    super().__init__("Blue Watcher", idx, "unique", {}, {}, None, 4)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, (events.SpendChoice, events.DiceRoll, events.CombatChoice)):
      return None
    if event.is_done():
      return None
    if owner != event.character:
      return None
    if len(state.event_stack) > 1 and isinstance(state.event_stack[-2], events.InvestigatorAttack):
      return None
    if isinstance(event, events.CombatChoice):
      if event.combat_round is None:
        return None
      return events.Sequence(
        [
          events.PassCombatRound(
            event.combat_round,
            log_message=(
              "{char_name} passed a combat round against"
              " {monster_name} using Blue Watcher of the Pyramid"
            ),
          ),
          events.DiscardSpecific(owner, [self]),
          events.Loss(owner, {"stamina": 2}),
        ],
        owner,
      )
    if len(state.event_stack) < 3:
      return None
    # GateCloseAttempt -> Check -> DiceRoll/SpendChoice
    if not isinstance(state.event_stack[-3], events.GateCloseAttempt):
      return None
    if state.event_stack[-2] != state.event_stack[-3].check:
      return None
    if isinstance(event, events.SpendChoice):
      return events.Sequence(
        [
          events.PassCheck(owner, state.event_stack[-2], self),
          events.DiscardSpecific(owner, [self]),
          events.CancelEvent(event),
          events.Loss(owner, {"stamina": 2}),
        ],
        owner,
      )
    if isinstance(event, events.DiceRoll) and event == state.event_stack[-2].dice:
      return events.Sequence(
        [
          events.PassCheck(owner, state.event_stack[-2], self),
          events.DiscardSpecific(owner, [self]),
          events.CancelEvent(event),
          events.Loss(owner, {"stamina": 2}),
        ],
        owner,
      )
    return None


class ElderSign(Item):
  def __init__(self, idx):
    super().__init__("Elder Sign", idx, "unique", {}, {}, None, 5)

  def get_usable_interrupt(self, event, owner, state: "GameState"):
    if (
      isinstance(event, events.MultipleChoice)
      and event.prompt() == "Close the gate?"
      and event.character == owner
      and state.get_override(self, "can_seal")
      and len(state.event_stack) > 1
    ):
      close = state.event_stack[-2]
      return events.Sequence(
        [
          events.DiscardSpecific(owner, [self], to_box=True),
          events.CancelEvent(event),
          events.CancelEvent(close),
          events.CloseGate(owner, close.location_name, True, True, force_seal=True),
          events.RemoveDoom(owner),
          events.Loss(owner, {"sanity": 1, "stamina": 1}, source=self),
        ],
        character=owner,
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

    if owner != event.character:
      return None

    loss = event.losses.get("stamina", 0)
    if isinstance(loss, values.Value):
      loss = loss.value(state)

    if loss <= 0:
      return None

    reduction = events.LossPrevention(self, event, "stamina", 1)
    return events.Sequence([reduction, events.AddToken(self, "stamina", owner, n_tokens=1)], owner)


class GateBox(Item):
  def __init__(self, idx):
    super().__init__("Gate Box", idx, "unique", {}, {}, None, 4)
    # This item is hard-coded into ReturnGateChoice to make trading work nicely.


class HealingStone(Item):
  def __init__(self, idx):
    super().__init__("Healing Stone", idx, "unique", {}, {}, None, 8)

  def get_usable_interrupt(self, event, owner, state):
    if event.is_done() or not isinstance(event, events.SliderInput):
      return None
    if self.exhausted:
      return None
    if event.character != owner:
      return None

    available = [
      attr
      for attr in ["stamina", "sanity"]
      if getattr(owner, attr) < getattr(owner, f"max_{attr}")(state)
      and state.get_override(owner, f"can_gain_{attr}")
    ]
    if not available:
      return None
    if len(available) == 1:
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
    if not isinstance(event, events.GainOrLoss) or event.character != owner:
      return None

    types = [
      loss_type
      for loss_type in ("sanity", "stamina")
      if loss_type in event.losses
      and values.Calculation(event.losses[loss_type], operand=operator.gt, right=0).value(state)
    ]
    seq = [events.DiscardSpecific(owner, [self])]
    if len(types) == 0:
      return None
    if len(types) == 1:
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
    if not isinstance(event, events.CombatChoice) or event.character != owner or event.is_done():
      return None
    if len(state.event_stack) < 2 or not isinstance(state.event_stack[-2], events.CombatRound):
      return None
    if owner.stamina < 3 or owner.sanity < 3:
      return None
    # In some instances, the character may be fighting a monster that is not in a location (for
    # example, Mythos65). In these cases, the flute is not usable.
    if event.monster.place != owner.place:
      return None

    combat_round = state.event_stack[-2]

    seq = [events.DiscardSpecific(owner, [self]), events.PassCombatRound(combat_round)]
    for monster in state.monsters:
      if monster.place == owner.place and monster != event.monster:
        seq.append(events.TakeTrophy(owner, monster))  # noqa: PERF401
    seq.append(events.Loss(owner, {"stamina": 3, "sanity": 3}))
    return events.Sequence(seq, owner)


class SilverKey(Item):
  def __init__(self, idx):
    super().__init__("Silver Key", idx, "unique", {}, {}, None, 4)
    self.tokens["stamina"] = 0
    self.max_tokens["stamina"] = 3

  def get_usable_interrupt(self, event, owner, state):
    evade = None
    if not isinstance(event, (events.FightOrEvadeChoice, events.DiceRoll)):
      return None
    if event.character != owner or event.is_done():
      return None
    cancel, token = events.CancelEvent(event), events.AddToken(self, "stamina", owner)
    if isinstance(event, events.FightOrEvadeChoice) and {"Flee", "Evade"} | set(event.choices):
      if len(state.event_stack) < 3:
        return None
      if isinstance(state.event_stack[-3], (events.EvadeOrCombat, events.Combat)):
        evade = state.event_stack[-3].evade
        if isinstance(evade, events.EvadeRound):
          return events.Sequence([cancel, events.PassEvadeRound(evade), token], owner)
      return None
    # Event is a DiceRoll
    if len(state.event_stack) < 2 or not isinstance(state.event_stack[-2], events.Check):
      return None
    check = state.event_stack[-2]
    if check.check_type != "evade" or check.dice != event:
      return None
    return events.Sequence([cancel, events.PassCheck(owner, check, self), token], owner)


class SunkenCityRuby(Item):
  def __init__(self, idx):
    super().__init__("Ruby", idx, "unique", {}, {}, None, 8)

  def get_interrupt(self, event, owner, state):
    if isinstance(event, events.CityMovement) and event.character == owner:
      return events.ChangeMovementPoints(owner, 3)
    return None


class WardingStatue(Item):
  def __init__(self, idx):
    super().__init__("Warding Statue", idx, "unique", {}, {}, None, 6)

  def get_usable_interrupt(self, event, owner, state):
    discard = events.DiscardSpecific(owner, [self])
    if isinstance(event, events.AncientAttack):
      return events.Sequence([discard, events.CancelEvent(event)], owner)
    if (
      isinstance(event, events.GainOrLoss)
      and len(state.event_stack) > 1
      and isinstance(state.event_stack[-2], events.CombatRound)
      and state.event_stack[-2].damage == event
    ):
      return events.Sequence(
        [discard, events.LossPrevention(self, event, "stamina", float("inf"))], owner
      )
    return None


# Tomes


class TibetanTome(Tome):
  def __init__(self, idx):
    super().__init__("Tibetan Tome", idx, "unique", 3, 2)
    self.max_tokens["stamina"] = 2
    self.tokens["stamina"] = 0

  def read_event(self, owner):
    check = events.Check(owner, "lore", -1, name=self.handle)
    success = events.Sequence(
      [
        events.AddToken(self, "stamina", owner),
        events.Draw(owner, "spells", 1),
        events.Loss(owner, {"sanity": 1}, source=self),
      ],
      owner,
    )
    return events.PassFail(owner, check, success, events.Nothing())


class MysticismTome(Tome):
  def __init__(self, idx):
    super().__init__("Mysticism Tome", idx, "unique", 5, 2)

  def read_event(self, owner):
    check = events.Check(owner, "lore", -2, name=self.handle)
    success = events.Sequence(
      [events.DiscardSpecific(owner, [self]), events.Draw(owner, "skills", 1)], owner
    )
    return events.PassFail(owner, check, success, events.Nothing())


class BlackMagicTome(Tome):
  def __init__(self, idx):
    super().__init__("Black Magic Tome", idx, "unique", 3, 2)

  def read_event(self, owner):
    check = events.Check(owner, "lore", -2, name=self.handle)
    success = events.Sequence(
      [
        events.DiscardSpecific(owner, [self]),
        events.Draw(owner, "spells", 1),
        events.GainOrLoss(owner, gains={"clues": 1}, losses={"sanity": 2}, source=self),
      ],
      owner,
    )
    return events.PassFail(owner, check, success, events.Nothing())


class BlackBook(Tome):
  def __init__(self, idx):
    super().__init__("Black Book", idx, "unique", 3, 1)

  def read_event(self, owner):
    check = events.Check(owner, "lore", -1, name=self.handle)
    success = events.Sequence(
      [
        events.DiscardSpecific(owner, [self]),
        events.Draw(owner, "spells", 1),
        events.Loss(owner, losses={"sanity": 1}, source=self),
      ],
      owner,
    )
    return events.PassFail(owner, check, success, events.Nothing())


class BookOfTheDead(Tome):
  def __init__(self, idx):
    super().__init__("Book of the Dead", idx, "unique", 6, 2)

  def read_event(self, owner):
    check = events.Check(owner, "lore", -2, name=self.handle)
    success = events.Sequence(
      [events.Draw(owner, "spells", 1), events.Loss(owner, losses={"sanity": 2}, source=self)],
      owner,
    )
    return events.PassFail(owner, check, success, events.Nothing())


class YellowPlay(Tome):
  def __init__(self, idx):
    super().__init__("Yellow Play", idx, "unique", 2, 2)

  def read_event(self, owner):
    check = events.Check(owner, "lore", -2, name=self.handle)
    success = events.Sequence(
      [
        events.DiscardSpecific(owner, [self]),
        events.GainOrLoss(owner, gains={"clues": 4}, losses={"sanity": 1}, source=self),
      ],
      owner,
    )
    return events.PassFail(owner, check, success, events.Nothing())
