import abc
import collections
from typing import TYPE_CHECKING, Optional

from eldritch import events
from eldritch import values

if TYPE_CHECKING:
  from eldritch.eldritch import GameState


CHECK_TYPES = {"speed", "sneak", "fight", "will", "lore", "luck"}
SUB_CHECKS = {"evade": "sneak", "combat": "fight", "horror": "will", "spell": "lore"}
COMBAT_SUBTYPES = {"physical", "magical"}
MAX_TYPES = {"max_sanity", "max_stamina"}


class Asset(metaclass=abc.ABCMeta):
  # pylint: disable=unused-argument

  JSON_ATTRS = {"name", "handle", "active", "exhausted", "hands", "in_use", "max_tokens", "tokens"}

  def __init__(self, name, idx=None):
    self._name = name
    self._idx = idx
    self._exhausted = False
    self.tokens = {}
    self.max_tokens = {}

  @property
  def name(self):
    return self._name

  @property
  def handle(self):
    if self._idx is None:
      return self._name
    return f"{self._name}{self._idx}"

  @property
  def exhausted(self):
    return self._exhausted

  def get_bonus(self, check_type, attributes, owner, state: Optional["GameState"]):
    return 0

  @property
  def bonuses(self):
    bonuses = {
      check: self.get_bonus(check, None, None, None) for check in CHECK_TYPES | SUB_CHECKS.keys()
    }
    bonuses["combat"] = sum(
      self.get_bonus(check, None, None, None) for check in {"combat"} | COMBAT_SUBTYPES
    )
    return bonuses

  def get_modifier(self, other, attribute):
    return None

  def get_override(self, other, attribute):
    return None

  def get_interrupt(self, event, owner, state):
    return None

  def get_usable_interrupt(self, event, owner, state):
    return None

  def get_trigger(self, event, owner, state):
    return None

  def get_usable_trigger(self, event, owner, state):
    return None

  def get_spend_amount(self, event, owner, state):
    return None

  def get_spend_event(self, owner):
    return events.Nothing()

  def get_max_token_event(self, token_type, owner):
    return events.Nothing()

  def get_zero_tokens_event(self, token_type, owner):
    return events.Nothing()

  def json_repr(self):
    return {attr: getattr(self, attr, None) for attr in self.JSON_ATTRS}

  @classmethod
  def parse_json(cls, data):
    pass  # TODO


class Card(Asset):
  DECKS = {"common", "unique", "spells", "skills", "allies", "tradables", "specials"}
  VALID_BONUS_TYPES = CHECK_TYPES | SUB_CHECKS.keys() | COMBAT_SUBTYPES | MAX_TYPES
  VALID_BONUS_TYPES |= {f"{ct}_check" for ct in CHECK_TYPES | SUB_CHECKS.keys()}

  def __init__(self, name, idx, deck, active_bonuses, passive_bonuses):
    assert deck in self.DECKS
    assert not (active_bonuses.keys() | passive_bonuses.keys()) - self.VALID_BONUS_TYPES
    super().__init__(name, idx)
    self.deck = deck
    self.active_bonuses = collections.defaultdict(int)
    self.active_bonuses.update(active_bonuses)
    self.passive_bonuses = collections.defaultdict(int)
    self.passive_bonuses.update(passive_bonuses)
    self._active = False
    self.losable = True

  @property
  def active(self):
    return self._active

  def get_bonus(self, check_type, attributes, owner, state: Optional["GameState"]):
    bonus = self.passive_bonuses[check_type]
    if self.active:
      bonus += self.active_bonuses[check_type]
    return bonus


class FortuneTeller(Card):
  def __init__(self):
    super().__init__("Fortune Teller", None, "allies", {}, {"luck": 2})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and self.name in event.kept:
      return events.Gain(owner, {"clues": 2})
    return None


class TravelingSalesman(Card):
  def __init__(self):
    super().__init__("Traveling Salesman", None, "allies", {}, {"sneak": 1, "will": 1})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and self.name in event.kept:
      return events.Draw(owner, "common", 1)
    return None


class PoliceDetective(Card):
  def __init__(self):
    super().__init__("Police Detective", None, "allies", {}, {"fight": 1, "lore": 1})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and self.name in event.kept:
      return events.Draw(owner, "spells", 1)
    return None


class Thief(Card):
  def __init__(self):
    super().__init__("Thief", None, "allies", {}, {"sneak": 2})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and self.name in event.kept:
      return events.Draw(owner, "unique", 1)
    return None


class StatIncreaser(Card):
  def __init__(self, name, stat):
    assert stat in MAX_TYPES
    super().__init__(name, None, "allies", {}, {stat: 1})
    self.stat = stat[4:]

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and self.name in event.kept:
      return events.Gain(owner, {self.stat: 1})
    if isinstance(event, events.DiscardNamed) and event.discarded == self:
      return events.CapStatsAtMax(owner)
    if isinstance(event, events.DiscardSpecific) and self in event.discarded:
      return events.CapStatsAtMax(owner)
    return None

  def get_usable_interrupt(self, event, owner, state):
    if not self.is_usable(event, owner, state):
      return None
    restore = events.Gain(owner, {self.stat: float("inf")})
    discard = events.DiscardSpecific(owner, [self])
    return events.Sequence([restore, discard], owner)

  def is_usable(self, event, owner, state):  # pylint: disable=unused-argument
    """
    when can you discard this?
    - after items have refreshed so that you can use some spell during upkeep
    - when adjusting sliders
    - during city movement
    - between fighting different monsters - or any fight/evade/combat choice
    - other world movement
    - before returning to arkham from another world
    - before you draw a card: encounter/gate/mythos
    """
    return False


class ArmWrestler(StatIncreaser):
  def __init__(self):
    super().__init__("Arm Wrestler", "max_stamina")


class Dog(StatIncreaser):
  def __init__(self):
    super().__init__("Dog", "max_sanity")


class BraveGuy(Card):
  def __init__(self):
    super().__init__("Brave Guy", None, "allies", {}, {"speed": 2})

  def get_override(self, other, attribute):
    if attribute == "nightmarish":
      return False
    return None


class PoliceInspector(Card):
  def __init__(self):
    super().__init__("Police Inspector", None, "allies", {}, {"will": 2})

  def get_override(self, other, attribute):
    if attribute == "endless":
      return False
    return None


class VisitingPainter(Card):
  def __init__(self):
    super().__init__("Visiting Painter", None, "allies", {}, {"speed": 1, "luck": 1})

  def get_override(self, other, attribute):
    if attribute == "physical resistance":
      return False
    return None


class OldProfessor(Card):
  def __init__(self):
    super().__init__("Old Professor", None, "allies", {}, {"lore": 2})

  def get_override(self, other, attribute):
    if attribute == "magical resistance":
      return False
    return None


class ToughGuy(Card):
  def __init__(self):
    super().__init__("Tough Guy", None, "allies", {}, {"fight": 2})

  def get_override(self, other, attribute):
    if attribute == "overwhelming":
      return False
    return None


class Deputy(Card):
  def __init__(self):
    super().__init__("Deputy", None, "specials", {}, {})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.RefreshAssets) and event.character == owner:
      return events.Gain(owner, {"dollars": 1})
    if isinstance(event, events.KeepDrawn) and self.name in event.kept:
      return events.Sequence(
        [
          events.DrawSpecific(owner, "tradables", "Deputy's Revolver"),
          events.DrawSpecific(owner, "tradables", "Patrol Wagon"),
        ],
        owner,
      )
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
    if isinstance(event, events.KeepDrawn) and self.name in event.kept:
      selves = [p for p in event.character.possessions if p.name == self.name]
      kept, *duplicates = sorted(selves, key=lambda x: x.tokens["must_roll"])
      if duplicates:
        return events.Sequence(
          [
            events.DiscardSpecific(event.character, duplicates),
            events.RemoveToken(kept, "must_roll", owner),
          ],
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
    if isinstance(event, events.KeepDrawn) and self.name in event.kept:
      if self.opposite in [p.name for p in event.character.possessions]:
        return events.Sequence(
          [
            events.DiscardNamed(event.character, self.name),
            events.DiscardNamed(event.character, self.opposite),
          ],
          event.character,
        )
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


def CreateAllies():
  return [
    ally()
    for ally in [
      FortuneTeller,
      TravelingSalesman,
      PoliceDetective,
      Thief,
      BraveGuy,
      PoliceInspector,
      ArmWrestler,
      VisitingPainter,
      ToughGuy,
      OldProfessor,
      Dog,
    ]
  ]
