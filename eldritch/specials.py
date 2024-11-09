from typing import List

from eldritch import events
from eldritch import values
from eldritch.abilities.seaside import TeamPlayerBonus
from eldritch.cards import Card, Asset, CHECK_TYPES
from eldritch.items.deputy import PatrolWagon, DeputysRevolver


class Deputy(Card):
  def __init__(self):
    super().__init__("Deputy", None, "specials", {}, {})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.RefreshAssets) and event.character == owner:
      return events.Gain(owner, {"dollars": 1})
    if isinstance(event, events.KeepDrawn) and self.name in event.kept:
      seq = [
        events.DrawSpecific(owner, "tradables", "Deputy's Revolver"),
        events.DrawSpecific(owner, "tradables", "Patrol Wagon"),
      ]
      return events.Sequence(seq, owner)
    return None


class SelfDiscardingCard(Card):
  def __init__(self, name, idx, active_bonuses=None, passive_bonuses=None):
    active_bonuses = active_bonuses or {}
    passive_bonuses = passive_bonuses or {}
    super().__init__(
      name, idx, "specials", active_bonuses=active_bonuses, passive_bonuses=passive_bonuses
    )
    self.tokens["must_roll"] = 0
    self.upkeep_bad_rolls = [1]

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and event.character == owner and self.name in event.kept:
      selves = [p for p in owner.possessions if p.name == self.name]
      kept, *duplicates = sorted(selves, key=lambda x: x.tokens["must_roll"])
      if duplicates:
        return events.Sequence(
          [events.DiscardSpecific(owner, duplicates), events.RemoveToken(kept, "must_roll", owner)],
          owner,
        )

    if isinstance(event, events.RefreshAssets) and event.character == owner:
      if self.tokens["must_roll"]:
        return events.RollToMaintain(owner, self)
      return events.AddToken(self, "must_roll", owner)
    return None

  def upkeep_penalty(self, character):
    return events.DiscardSpecific(character, [self])


class BlessingOrCurse(SelfDiscardingCard):
  def __init__(self, name, idx):
    assert name in ["Blessing", "Curse"]
    super().__init__(name, idx)
    self.opposite = "Curse" if name == "Blessing" else "Blessing"

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and event.character == owner and self.name in event.kept:
      opposites = [p for p in owner.possessions if p.name == self.opposite]
      if opposites:
        return events.DiscardSpecific(owner, [self, *opposites])
    return super().get_trigger(event, owner, state)

  def __repr__(self):
    return f"<{self.name} - {self.tokens}>"


def Blessing(idx):
  return BlessingOrCurse("Blessing", idx)


def Curse(idx):
  return BlessingOrCurse("Curse", idx)


class Retainer(SelfDiscardingCard):
  def __init__(self, idx):
    super().__init__("Retainer", idx)

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.RefreshAssets) and event.character == owner:
      roll = super().get_trigger(event, owner, state)
      gain = events.Gain(owner, {"dollars": 2})
      if roll is not None:
        return events.Sequence([gain, roll], owner)
      return gain
    return None


class BankLoan(SelfDiscardingCard):
  def __init__(self, idx):
    super().__init__("Bank Loan", idx)
    self.upkeep_bad_rolls = [1, 2, 3]

  def upkeep_penalty(self, character):
    default = events.Sequence(
      [
        events.LoseItems(character, values.ItemCount(character)),
        events.DiscardSpecific(character, [self]),
        events.DrawSpecific(character, "specials", "Bad Credit"),
      ],
      character,
    )
    interest = events.SpendChoice(
      character,
      "Pay interest on loan",
      choices=["Pay", "Default"],
      prereqs=[
        values.AttributePrerequisite(character, "dollars", 1, "at least"),
        values.AttributePrerequisite(character, "dollars", 0, "exactly"),
      ],
      spends=[values.ExactSpendPrerequisite({"dollars": 1}), None],
    )
    return events.Sequence(
      [
        interest,
        events.Conditional(character, interest, "choice_index", {0: events.Nothing(), 1: default}),
      ],
      character,
    )

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.TakeBankLoan):
      return events.Gain(owner, {"dollars": 10}, self)
    return super().get_trigger(event, owner, state)

  def get_usable_interrupt(self, event, owner, state):
    if isinstance(event, events.SliderInput) and event.character == owner and not event.is_done():
      # TODO: Usable "anytime"
      return events.BinarySpend(
        owner, "dollars", 10, "Pay off loan?", "Yes", "No", events.DiscardSpecific(owner, [self])
      )
    return None

  def get_interrupt(self, event, owner, state):
    if (
      isinstance(event, events.KeepDrawn)
      and event.character == owner
      and event.drawn is not None
      and self in event.drawn
      and not (
        state.get_override(self, "can_get_bank_loan")
        or owner.get_override(self, "can_get_bank_loan")
      )
    ):
      return events.CancelEvent(event)
    return None


class BadCredit(Asset):
  def __init__(self, idx):
    super().__init__("Bad Credit", idx)

  def get_override(self, other, attribute):
    if attribute == "can_get_bank_loan":
      return False
    return None


class LodgeMembership(Card):
  def __init__(self, idx):
    super().__init__("Lodge Membership", idx, "specials", {}, {})

  def get_interrupt(self, event, owner, state):
    if (
      isinstance(event, events.KeepDrawn)
      and len([c for c in event.draw.drawn if isinstance(c, LodgeMembership)]) > 0
      and event.character == owner
      and event.character.lodge_membership
    ):
      return events.CancelEvent(event)
    return None


class BonusToAllChecks(Card):
  def __init__(self, name, idx):
    super().__init__(name, idx, "specials", {}, {f"{ability}_check": 1 for ability in CHECK_TYPES})

  def get_interrupt(self, event, owner, state):
    if isinstance(event, events.Mythos) and event.is_done():
      return events.DiscardSpecific(owner, [self])
    return None


def VoiceBonus(idx):
  return BonusToAllChecks("Voice Bonus", idx)


class StatDecrease(Card):
  def __init__(self, name, idx, stat):
    assert stat in {"sanity", "stamina"}
    super().__init__(name, idx, "specials", {}, {f"max_{stat}": -1})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and self.name in event.kept:
      return events.CapStatsAtMax(owner)
    return None


def StaminaDecrease(idx):
  return StatDecrease("Stamina Decrease", idx, "stamina")


def SanityDecrease(idx):
  return StatDecrease("Sanity Decrease", idx, "sanity")


def CreateTradables():
  return [DeputysRevolver(), PatrolWagon()]


def CreateSpecials() -> List[Asset]:
  cards = [
    Blessing,
    Curse,
    Retainer,
    BankLoan,
    BadCredit,
    LodgeMembership,
    StaminaDecrease,
    SanityDecrease,
    VoiceBonus,
  ]
  return [Deputy(), TeamPlayerBonus(0)] + [card(i) for i in range(12) for card in cards]
