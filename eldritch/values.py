from __future__ import annotations

import abc
import collections
import math
import operator
from typing import TYPE_CHECKING

from eldritch import places

if TYPE_CHECKING:
  from eldritch.characters.core import BaseCharacter
  from eldritch.eldritch import GameState


OPER_MAP = {"at least": operator.ge, "at most": operator.le, "exactly": operator.eq}


def ceildiv(lhs, rhs):
  return math.ceil(lhs / rhs)


class Value(metaclass=abc.ABCMeta):
  def __init__(self, error_fmt=None):
    if not error_fmt:
      error_fmt = "You do not meet the prerequisites for choosing {choice}"
    self.error_fmt = error_fmt

  @abc.abstractmethod
  def value(self, state):
    raise NotImplementedError

  def error_str(self, state, choice):  # pylint: disable=unused-argument
    return self.error_fmt.format(choice=choice)


class Calculation(Value):
  def __init__(
    self, left, left_attr=None, operand=None, right=None, right_attr=None, error_fmt=None
  ):
    super().__init__(error_fmt=error_fmt)
    assert left_attr is not None or operand is not None
    self.left = left
    self.left_attr = left_attr
    self.operand = operand
    self.right = right
    self.right_attr = right_attr

  def value(self, state):
    left = self.left
    if self.left_attr is not None:
      left = getattr(left, self.left_attr)
    elif isinstance(left, Value):
      left = left.value(state)

    if self.operand is None:
      return left

    if self.right is None:
      return self.operand(left)

    right = self.right
    if self.right_attr is not None:
      right = getattr(right, self.right_attr)
    elif isinstance(right, Value):
      right = right.value(state)

    return self.operand(left, right)


class OtherWorldName(Value):
  def __init__(self, character):
    super().__init__()
    self.character = character

  def value(self, state):
    if self.character.place is None:
      return None
    if not isinstance(self.character.place, places.OtherWorld):
      return None
    return self.character.place.info.name


def Die(die_roll):
  return Calculation(die_roll, "sum")


class BadDice(Value):
  def __init__(self, roll):
    super().__init__()
    self.roll = roll

  def value(self, state):
    if self.roll.bad is None:
      return 0
    return len([roll for roll in self.roll.roll if roll in self.roll.bad])


class AttributePrerequisite(Calculation):
  def __init__(self, character, attribute, threshold, operand):
    error_fmt = f"You do not have {operand} {threshold} {attribute}"
    super().__init__(character, attribute, OPER_MAP[operand], threshold, error_fmt=error_fmt)


class AttributeNotMaxedPrerequisite(Value):
  def __init__(self, character, attribute):
    assert attribute in {"sanity", "stamina"}
    super().__init__(error_fmt=f"Your {attribute} is already at its max")
    self.character = character
    self.attribute = attribute

  def value(self, state):
    char_max = getattr(self.character, "max_" + self.attribute)(state)
    current = getattr(self.character, self.attribute)
    return int(current < char_max)


class ItemDeckCount(Value):
  def __init__(self, character, decks, error_fmt=None):
    if not error_fmt:
      error_fmt = f"You do not have at least one {' or '.join(decks)} card"
    super().__init__(error_fmt=error_fmt)
    self.character = character
    self.decks = decks

  def value(self, state):
    return sum(getattr(item, "deck", None) in self.decks for item in self.character.possessions)


class ItemCount(ItemDeckCount):
  def __init__(self, character):
    error_fmt = "You do not have at least one item"
    super().__init__(character, {"common", "unique", "spells", "tradables"}, error_fmt=error_fmt)


class ItemNameCount(Value):
  def __init__(self, character, item_name):
    super().__init__(error_fmt=f"You do not have a {item_name}")
    self.character = character
    self.item_name = item_name

  def value(self, state):
    return sum(item.name == self.item_name for item in self.character.possessions)


class NoItemName(Value):
  def __init__(self, character, item_name):
    super().__init__(error_fmt=f"You have a {item_name}")
    self.character = character
    self.item_name = item_name

  def value(self, state):
    return sum(item.name == self.item_name for item in self.character.possessions) == 0


class OverridePrerequisite(Value):
  def __init__(self, character: BaseCharacter, attribute: str, other=None, error_fmt=None):
    if error_fmt is None:
      error_fmt = f"'{attribute}' is overridden"
    super().__init__(error_fmt=error_fmt)
    self.character: BaseCharacter = character
    self.attribute: str = attribute
    self.other = other

  def value(self, state: GameState):
    state_override = state.get_override(self.other, self.attribute)
    char_override = self.character.get_override(self.other, self.attribute)
    return all(override for override in [state_override, char_override] if override is not None)


class ItemPrerequisite(Calculation):
  def __init__(self, character, item_name, threshold=1, operand="at least"):
    name_count = ItemNameCount(character, item_name)
    name_thresh = Calculation(name_count, None, OPER_MAP[operand], threshold)
    error_fmt = f"You do not have {operand} {threshold} {item_name}"
    super().__init__(name_thresh, None, int, error_fmt=error_fmt)


class ItemDeckPrerequisite(Calculation):
  def __init__(self, character, deck, threshold=1, operand="at least"):
    deck_count = ItemDeckCount(character, {deck})
    deck_thresh = Calculation(deck_count, None, OPER_MAP[operand], threshold)
    error_fmt = f"You do not have {operand} {threshold} {deck} cards"
    super().__init__(deck_thresh, None, int, error_fmt=error_fmt)


class ItemCountPrerequisite(Calculation):
  def __init__(self, character, threshold=1, operand="at least"):
    item_count = ItemCount(character)
    error_fmt = f"You do not have {operand} {threshold} items"
    super().__init__(item_count, None, OPER_MAP[operand], threshold, error_fmt=error_fmt)


class ContainsPrerequisite(Value):
  def __init__(self, deck, card_name, error_fmt=None):
    super().__init__(error_fmt=error_fmt)
    self.deck = deck
    self.card_name = card_name

  def value(self, state):
    return sum(card.name == self.card_name for card in getattr(state, self.deck))


class MonsterAttributePrerequisite(Value):
  def __init__(self, monster, attribute, character, error_fmt=None):
    super().__init__(error_fmt=error_fmt)
    self.monster = monster
    self.attribute = attribute
    self.character = character

  def value(self, state):
    return int(self.monster.has_attribute(self.attribute, state, self.character))


class NoAmbushPrerequisite(Calculation):
  def __init__(self, monster, character):
    error_fmt = "You cannot flee from a monster with Ambush"
    ambush = MonsterAttributePrerequisite(monster, "ambush", character)
    super().__init__(1, None, operator.sub, ambush, error_fmt=error_fmt)


class PlaceStable(Value):
  def __init__(self, place):
    super().__init__()
    self.place = place

  def value(self, state):
    return int(not self.place.is_unstable(state))


class PlaceUnstable(Value):
  def __init__(self, place):
    super().__init__()
    self.place = place

  def value(self, state):
    return int(self.place.is_unstable(state))


class InCity(Value):
  def __init__(self, character):
    super().__init__()
    self.character = character

  def value(self, state):
    return int(isinstance(self.character.place, places.CityPlace))


class OnGate(Value):
  def __init__(self, character):
    super().__init__()
    self.character = character

  def value(self, state):
    return int(getattr(self.character.place, "gate", None) is not None)


class UnsuccessfulDice(Value):
  def __init__(self, check):
    super().__init__()
    self.check = check

  def value(self, state):
    if not self.check.roll:
      return []
    return [
      idx
      for idx, roll in enumerate(self.check.roll)
      if not self.check.character.is_success(roll, self.check.check_type)
    ]


class OpenGates(Value):
  def value(self, state):
    return [place.name for place in state.places.values() if getattr(place, "gate", None)]


def OpenGateCount():
  return Calculation(OpenGates(), None, len)


class MonstersOnBoard(Value):
  def value(self, state):
    return [
      mon.handle
      for mon in state.monsters
      if isinstance(mon.place, (places.CityPlace, places.Outskirts))
    ]


def BoardMonsterCount():
  return Calculation(MonstersOnBoard(), None, len)


class EnteredGate(Value):
  def __init__(self, character):
    super().__init__()
    self.character = character

  def value(self, state):
    if self.character.entered_gate is None:
      return None
    for name, place in state.places.items():
      if getattr(place, "gate", None) and place.gate.handle == self.character.entered_gate:
        return name
    return None


class SpendValue(metaclass=abc.ABCMeta):
  SPEND_TYPES = {  # noqa: RUF012
    "stamina": "stamina",
    "sanity": "sanity",
    "dollars": "dollars",
    "clues": "clues",
    "monsters": "monsters",
    "gates": "gates",
  }
  # TODO: focus and movement points, maybe?

  def __init__(self):
    self.spend_event = None

  @property
  def spend_map(self):
    if self.spend_event is None:
      return collections.defaultdict(dict)
    return self.spend_event.spend_map

  @abc.abstractmethod
  def remaining_spend(self, state):
    spent_map = {key: sum(spend_count.values()) for key, spend_count in self.spend_map.items()}
    return {
      spend_type: -spend_count
      for spend_type, spend_count in spent_map.items()
      if spend_type not in self.spend_types() and spend_count
    }

  def remaining_max(self, state):
    return self.remaining_spend(state)

  @abc.abstractmethod
  def spend_types(self):
    raise NotImplementedError

  @abc.abstractmethod
  def annotation(self, state):
    raise NotImplementedError


class SpendNothing(SpendValue):
  def remaining_spend(self, state):  # pylint: disable=useless-super-delegation
    return super().remaining_spend(state)

  def spend_types(self):
    return set()

  def annotation(self, state):
    return ""


class ExactSpendPrerequisite(SpendValue):
  """MultiSpendPrerequisite represents spending an exact amount of multiple different types."""

  def __init__(self, spend_amounts):
    assert not spend_amounts.keys() - self.SPEND_TYPES.keys()
    assert all(isinstance(val, int) for val in spend_amounts.values())
    super().__init__()
    self.spend_amounts = spend_amounts

  def remaining_spend(self, state):
    spent_map = {key: sum(spend_count.values()) for key, spend_count in self.spend_map.items()}
    remaining = {}
    for spend_type in spent_map.keys() | self.spend_amounts.keys():
      diff = self.spend_amounts.get(spend_type, 0) - spent_map.get(spend_type, 0)
      if diff:
        remaining[spend_type] = diff
    return remaining

  def spend_types(self):
    return set(self.spend_amounts.keys())

  def annotation(self, state):
    parts = []
    for spend_type in sorted(self.spend_amounts):
      parts.append(f"{self.spend_amounts[spend_type]} {self.SPEND_TYPES[spend_type]}")  # noqa: PERF401
    return ", ".join(parts)


class RangeSpendPrerequisite(SpendValue):
  """SpendPrerequisite represents spending between spend_amount and spend_max of spend_type."""

  def __init__(self, spend_type, spend_min, spend_max):
    assert spend_type in self.SPEND_TYPES
    super().__init__()
    self.spend_type = spend_type
    self.spend_min = spend_min
    self.spend_max = spend_max

  def remaining_spend(self, state):
    remaining = super().remaining_spend(state)

    spend_min = self.spend_min.value(state) if isinstance(self.spend_min, Value) else self.spend_min
    spend_max = self.spend_max.value(state) if isinstance(self.spend_max, Value) else self.spend_max
    spent = sum(self.spend_map[self.spend_type].values())
    if spent < spend_min:
      remaining[self.spend_type] = spend_min - spent
    elif spent > spend_max:
      remaining[self.spend_type] = spend_max - spent
    return remaining

  def remaining_max(self, state):
    remaining = super().remaining_spend(state)
    spend_max = self.spend_max.value(state) if isinstance(self.spend_max, Value) else self.spend_max
    spent = sum(self.spend_map[self.spend_type].values())
    if spent != spend_max:
      remaining[self.spend_type] = spend_max - spent
    return remaining

  def spend_types(self):
    return {self.spend_type}

  def annotation(self, state):
    spend_min = self.spend_min.value(state) if isinstance(self.spend_min, Value) else self.spend_min
    spend_max = self.spend_max.value(state) if isinstance(self.spend_max, Value) else self.spend_max
    return f"{spend_min}-{spend_max} {self.SPEND_TYPES[self.spend_type]}"


class FlexibleRangeSpendPrerequisite(SpendValue):
  def __init__(
    self,
    spend_types: list,
    spend_min: float,
    spend_max: float,
    character: BaseCharacter | None = None,
  ):
    assert all(spend_type in self.SPEND_TYPES for spend_type in spend_types)
    super().__init__()
    self._spend_types = spend_types
    self.spend_min = spend_min
    self.spend_max = spend_max
    self.character = character

  def remaining_spend(self, state):
    remaining = super().remaining_spend(state)

    spend_min = self.spend_min.value(state) if isinstance(self.spend_min, Value) else self.spend_min
    spend_max = self.spend_max.value(state) if isinstance(self.spend_max, Value) else self.spend_max
    spent = sum(
      value for spend_type in self._spend_types for value in self.spend_map[spend_type].values()
    )

    for spend_type in self._spend_types:
      if spent < spend_min:
        remaining[spend_type] = spend_min - spent
      elif spent > spend_max:
        remaining[spend_type] = spend_max - spent
    return remaining

  def remaining_max(self, state):
    remaining = super().remaining_spend(state)
    spend_max = self.spend_max.value(state) if isinstance(self.spend_max, Value) else self.spend_max
    spent = sum(
      value for spend_type in self._spend_types for value in self.spend_map[spend_type].values()
    )
    if spent != spend_max:
      for spend_type in self._spend_types:
        min_remaining = 1 if spend_type in ("sanity", "stamina") else 0
        available = getattr(self.character, spend_type, 0)
        already_spent = self.spend_map[spend_type].get(spend_type, 0)
        spendable = max(available - min_remaining - already_spent, 0)
        if spendable > spend_max - spent:
          remaining[spend_type] = spend_max - spent
          spent = spend_max
        else:
          spent += spendable
          remaining[spend_type] = spendable

    return remaining

  def spend_types(self):
    return set(self._spend_types)

  def annotation(self, state):
    spend_min = self.spend_min.value(state) if isinstance(self.spend_min, Value) else self.spend_min
    spend_max = self.spend_max.value(state) if isinstance(self.spend_max, Value) else self.spend_max
    spend_types = ", ".join(self.SPEND_TYPES[spend_type] for spend_type in self._spend_types)
    return f"{spend_min}-{spend_max} ({spend_types})"


class ToughnessSpendBase(SpendValue, metaclass=abc.ABCMeta):
  def __init__(self, toughness):
    assert toughness > 0
    super().__init__()
    self.toughness = toughness

  def remaining_spend(self, state):
    remaining = super().remaining_spend(state)
    total_spent = 0
    min_spent = None
    for toughness in self.spend_map["toughness"].values():
      if min_spent is None or toughness < min_spent:
        min_spent = toughness
      total_spent += toughness
    if "gates" in self.spend_types():
      for count in self.spend_map["gates"].values():  # TODO: can the count ever be not 1?
        if count == 0:
          continue
        if min_spent is None or min_spent > 5:
          min_spent = 5
        total_spent += count * 5

    if min_spent is None:
      remaining["toughness"] = self.toughness
    elif total_spent < self.toughness:  # noqa: SIM114
      remaining["toughness"] = self.toughness - total_spent
    elif total_spent - self.toughness >= min_spent:  # Not allowed to overspend too much.
      remaining["toughness"] = self.toughness - total_spent
    return remaining

  def annotation(self, state):
    return f"{self.toughness} toughness"


class ToughnessSpend(ToughnessSpendBase):
  """ToughnessSpend represents spending toughness, disallowing excessive overspend."""

  def spend_types(self):
    return {"toughness"}


class ToughnessOrGatesSpend(ToughnessSpendBase):
  """ToughnessOrGatesSpend represents spending increments of five toughness or one gate trophy."""

  def __init__(self, toughness):
    assert toughness % 5 == 0
    super().__init__(toughness)

  def spend_types(self):
    return {"toughness", "gates"}


class SpendCount(Value):
  def __init__(self, spend_choice, spend_type):
    super().__init__()
    self.spend_choice = spend_choice
    self.spend_type = spend_type

  def value(self, state):
    assert self.spend_choice.is_done()
    if self.spend_choice.is_cancelled():
      return 0
    return sum(self.spend_choice.spend_map[self.spend_type].values())
