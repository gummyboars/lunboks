import abc
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
  return ItemDeckCount(character, {"common", "unique", "spells"})


class ContainsPrerequisite(Value):

  def __init__(self, deck, card_name):
    self.deck = deck
    self.card_name = card_name

  def value(self, state):
    return sum([card.name == self.card_name for card in getattr(state, self.deck)])
