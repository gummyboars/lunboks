import abc
import collections
import operator


class Value(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def value(self, state):
    raise NotImplementedError


class Calculation(Value):

  def __init__(self, left, left_attr=None, operand=None, right=None, right_attr=None):
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


def Die(die_roll):
  return Calculation(die_roll, "sum")


def AttributePrerequisite(character, attribute, threshold, operand):
  oper = {"at least": operator.ge, "at most": operator.le, "exactly": operator.eq}[operand]
  return Calculation(character, attribute, oper, threshold)


class AttributeNotMaxedPrerequisite(Value):

  def __init__(self, character, attribute):
    assert attribute in {"sanity", "stamina"}
    self.character = character
    self.attribute = attribute

  def value(self, state):
    char_max = getattr(self.character, "max_" + self.attribute)(state)
    current = getattr(self.character, self.attribute)
    return int(current < char_max)


class ItemDeckCount(Value):

  def __init__(self, character, decks):
    self.character = character
    self.decks = decks

  def value(self, state):
    return sum([getattr(item, "deck", None) in self.decks for item in self.character.possessions])


class ItemNameCount(Value):

  def __init__(self, character, item_name):
    self.character = character
    self.item_name = item_name

  def value(self, state):
    return sum([item.name == self.item_name for item in self.character.possessions])


def ItemPrerequisite(character, item_name, threshold=1, operand="at least"):
  oper = {"at least": operator.ge, "at most": operator.le, "exactly": operator.eq}[operand]
  return Calculation(
      Calculation(ItemNameCount(character, item_name), None, oper, threshold), None, int)


def ItemDeckPrerequisite(character, deck, threshold=1, operand="at least"):
  oper = {"at least": operator.ge, "at most": operator.le, "exactly": operator.eq}[operand]
  return Calculation(
      Calculation(ItemDeckCount(character, {deck}), None, oper, threshold), None, int)


def ItemCountPrerequisite(character, threshold=1, operand="at least"):
  oper = {"at least": operator.ge, "at most": operator.le, "exactly": operator.eq}[operand]
  return Calculation(
      ItemDeckCount(character, {"common", "unique", "spells"}), None, oper, threshold
  )


class ContainsPrerequisite(Value):

  def __init__(self, deck, card_name):
    self.deck = deck
    self.card_name = card_name

  def value(self, state):
    return sum([card.name == self.card_name for card in getattr(state, self.deck)])


class MonsterAttributePrerequisite(Value):

  def __init__(self, monster, attribute, character):
    self.monster = monster
    self.attribute = attribute
    self.character = character

  def value(self, state):
    return int(self.monster.has_attribute(self.attribute, state, self.character))


def NoAmbushPrerequisite(monster, character):
  return Calculation(
      1, None, operator.sub, MonsterAttributePrerequisite(monster, "ambush", character))


class SpendValue(Value):

  SPEND_TYPES = {
      "stamina": "stamina", "sanity": "sanity", "dollars": "dollars", "clues": "clues",
      "monsters": "monsters", "gates": "gates",
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
  def spend_types(self):
    raise NotImplementedError

  @abc.abstractmethod
  def annotation(self, state):
    raise NotImplementedError


class ExactSpendPrerequisite(SpendValue):
  """MultiSpendPrerequisite represents spending an exact amount of multiple different types."""

  def __init__(self, spend_amounts):
    assert not spend_amounts.keys() - self.SPEND_TYPES.keys()
    assert all(isinstance(val, int) for val in spend_amounts.values())
    super().__init__()
    self.spend_amounts = spend_amounts

  def value(self, state):
    spent_map = {key: sum(spend_count.values()) for key, spend_count in self.spend_map.items()}
    for spend_type in spent_map.keys() | self.spend_amounts.keys():
      if spent_map.get(spend_type, 0) != self.spend_amounts.get(spend_type, 0):
        return 0
    return 1

  def spend_types(self):
    return set(self.spend_amounts.keys())

  def annotation(self, state):
    parts = []
    for spend_type in sorted(self.spend_amounts):
      parts.append(str(self.spend_amounts[spend_type]) + " " + self.SPEND_TYPES[spend_type])
    return ", ".join(parts)


class RangeSpendPrerequisite(SpendValue):
  """SpendPrerequisite represents spending between spend_amount and spend_max of spend_type."""

  def __init__(self, spend_type, spend_min, spend_max):
    assert spend_type in self.SPEND_TYPES
    super().__init__()
    self.spend_type = spend_type
    self.spend_min = spend_min
    self.spend_max = spend_max

  def value(self, state):
    spend_min = self.spend_min.value(state) if isinstance(self.spend_min, Value) else self.spend_min
    spend_max = self.spend_max.value(state) if isinstance(self.spend_max, Value) else self.spend_max
    if sum(sum(spend_count.values()) for spend_count in self.spend_map.values()) != self.spent():
      return 0
    return int(self.spent() >= spend_min and self.spent() <= spend_max)

  def spend_types(self):
    return {self.spend_type}

  def annotation(self, state):
    spend_min = self.spend_min.value(state) if isinstance(self.spend_min, Value) else self.spend_min
    spend_max = self.spend_max.value(state) if isinstance(self.spend_max, Value) else self.spend_max
    return f"{spend_min}-{spend_max} self.SPEND_TYPES[self.spend_type]"

  def spent(self):
    return sum(self.spend_map[self.spend_type].values())


class ToughnessSpendBase(SpendValue, metaclass=abc.ABCMeta):

  def __init__(self, toughness):
    assert toughness > 0
    super().__init__()
    self.toughness = toughness

  def value(self, state):
    for spend_type in self.spend_map.keys() - self.spend_types():
      if sum(self.spend_map[spend_type].values()) != 0:  # Cannot spend anything else.
        return 0

    total_spent = 0
    min_spent = None
    for toughness in self.spend_map["toughness"].values():
      if min_spent is None or toughness < min_spent:
        min_spent = toughness
      total_spent += toughness
    for count in self.spend_map["gates"].values():  # TODO: can the count ever be not 1?
      if count == 0:
        continue
      if min_spent is None or min_spent > 5:
        min_spent = 5
      total_spent += count * 5

    if min_spent is None:
      return 0
    if total_spent < self.toughness:
      return 0
    if total_spent - self.toughness >= min_spent:  # Not allowed to overspend too much.
      return 0
    return 1

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
    self.spend_choice = spend_choice
    self.spend_type = spend_type

  def value(self, state):
    assert self.spend_choice.is_done()
    if self.spend_choice.is_cancelled():
      return 0
    return sum(self.spend_choice.spend_map[self.spend_type].values())
