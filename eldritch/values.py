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
    char_max = getattr(self.character, "max_" + self.attribute)
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

  SPEND_TYPES = {"stamina", "sanity", "dollars", "clues", "toughness", "gates"}

  def __init__(self):
    self.spend_map = collections.defaultdict(dict)

  @property
  @abc.abstractmethod
  def spend_types(self):
    raise NotImplementedError


class SpendPrerequisite(SpendValue):
  """SpendPrerequisite represents spending between spend_amount and spend_max of spend_type."""

  def __init__(self, spend_type, spend_min, spend_max=None):
    assert spend_type in self.SPEND_TYPES
    # TODO: focus and movement points, maybe?
    super().__init__()
    self.spend_type = spend_type
    self.spend_min = spend_min
    self.spend_max = spend_max or spend_min

  def value(self, state):
    spend_min = self.spend_min.value(state) if isinstance(self.spend_min, Value) else self.spend_min
    spend_max = self.spend_max.value(state) if isinstance(self.spend_max, Value) else self.spend_max
    if sum(sum(spend.values()) for spend in self.spend_map.values()) != self.spent:
      return 0
    return int(self.spent >= spend_min and self.spent <= spend_max)

  @property
  def spend_types(self):
    return {self.spend_type}

  @property
  def spent(self):
    return sum(self.spend_map[self.spend_type].values())


class MultiSpendPrerequisite(SpendValue):
  """MultiSpendPrerequisite represents spending an exact amount of multiple different types."""

  def __init__(self, spend_amounts):
    assert not spend_amounts.keys() - self.SPEND_TYPES
    assert all(isinstance(val, int) for val in spend_amounts.values())
    super().__init__()
    self.spend_amounts = spend_amounts

  def value(self, state):
    spent_map = {key: sum(val.values()) for key, val in self.spend_map.items() if sum(val.values())}
    if spent_map.keys() ^ self.spend_amounts.keys():
      return 0
    return int(all(spent_map[key] == self.spend_amounts[key] for key in self.spend_amounts))

  @property
  def spend_types(self):
    return set(self.spend_amounts.keys())


class SpendCount(Value):

  def __init__(self, spend_choice, spend_type):
    self.spend_choice = spend_choice
    self.spend_type = spend_type

  def value(self, state):
    assert self.spend_choice.is_done()
    if self.spend_choice.is_cancelled():
      return 0
    return sum(self.spend_choice.spend_map[self.spend_type].values())
