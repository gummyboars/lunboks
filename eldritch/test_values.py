#!/usr/bin/env python3

import collections
import operator
import os
import sys
import unittest

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch.values import *
from eldritch import places


# pylint: disable=attribute-defined-outside-init
class Dummy:
  def __init__(self, **kwargs):
    for name, value in kwargs.items():
      setattr(self, name, value)


class DummyChar(Dummy):
  def __init__(self, **kwargs):
    self.possessions = []
    self.override = None
    super().__init__(**kwargs)

  def get_override(self, other, attribute):  # pylint: disable=unused-argument
    return self.override


class DummyMonster(Dummy):
  def has_attribute(self, attribute, state, char):  # pylint: disable=unused-argument
    if char.get_override(self, attribute) is not None:
      return char.get_override(self, attribute)
    return getattr(self, attribute)


class DummyPlace(Dummy):
  def __init__(self, **kwargs):
    self.sealed = False
    self.gate = None
    super().__init__(**kwargs)

  def is_unstable(self, state):  # pylint: disable=unused-argument
    return not self.sealed


class DummyState(Dummy):
  def __init__(self, **kwargs):
    self.common = []
    super().__init__(**kwargs)


class CalculationTest(unittest.TestCase):
  def testDelayedAttribute(self):
    obj = Dummy()
    calc = Calculation(obj, "attr")
    with self.assertRaises(AttributeError):
      calc.value(None)
    obj.attr = "hello"
    self.assertEqual(calc.value(None), "hello")

  def testBasicMathTest(self):
    calc = Calculation(3, None, operator.mul, 4)
    self.assertEqual(calc.value(None), 12)

  def testMathOnAttributeTest(self):
    obj = Dummy()
    calc = Calculation(obj, "attr", operator.mul, 4)
    with self.assertRaises(AttributeError):
      calc.value(None)
    obj.attr = 3
    self.assertEqual(calc.value(None), 12)

  def testUnaryOperator(self):
    obj = Dummy()
    calc = Calculation(obj, "val", operator.neg)
    with self.assertRaises(AttributeError):
      calc.value(None)
    obj.val = 3
    self.assertEqual(calc.value(None), -3)

  def testChainedValues(self):
    dice = Dummy()
    prevention = Dummy()
    reduction = Dummy()
    initial = Calculation(dice, "roll", operator.sub, prevention, "amount")
    final = Calculation(initial, None, operator.sub, reduction, "value")
    with self.assertRaises(AttributeError):
      final.value(None)
    dice.roll = 6
    prevention.amount = 1
    reduction.value = 2
    self.assertEqual(final.value(None), 3)

  def testBoolToInt(self):
    char = Dummy()
    prereq = Calculation(char, "clues", operator.gt, 2)
    success = Calculation(prereq, None, int)
    with self.assertRaises(AttributeError):
      success.value(None)
    char.clues = 2
    self.assertEqual(success.value(None), 0)
    char.clues = 3
    self.assertEqual(success.value(None), 1)


class ItemCountTest(unittest.TestCase):
  def testNamedItemCount(self):
    char = DummyChar()
    char.possessions.extend([Dummy(name="Food"), Dummy(name="Water")])
    count = ItemNameCount(char, "Food")
    self.assertEqual(count.value(None), 1)
    char.possessions.append(Dummy(name="Food"))
    self.assertEqual(count.value(None), 2)
    char.possessions.clear()
    self.assertEqual(count.value(None), 0)

  def testNoItemName(self):
    char = DummyChar()
    char.possessions.extend([Dummy(name="Food"), Dummy(name="Water")])
    none = NoItemName(char, "Gold")
    self.assertTrue(none.value(None))
    char.possessions.append(Dummy(name="Gold"))
    self.assertFalse(none.value(None))

  def testItemDeckCount(self):
    char = DummyChar()
    count = ItemCount(char)
    char.possessions.append(Dummy(name="Revolver", deck="tradables"))
    char.possessions.append(Dummy(name="Deputy", deck="specials"))
    self.assertEqual(count.value(None), 1)
    char.possessions.append(Dummy(name="Food", deck="common"))
    self.assertEqual(count.value(None), 2)
    char.possessions = char.possessions[2:]
    char.possessions.append(Dummy(name="Wagon", deck="tradables"))
    self.assertEqual(count.value(None), 2)
    char.possessions.clear()
    self.assertEqual(count.value(None), 0)


class PrerequisiteTest(unittest.TestCase):
  def testAttributePrereq(self):
    char = DummyChar(clues=0, dollars=0)
    prereq = AttributePrerequisite(char, "clues", 2, "at least")
    self.assertEqual(prereq.value(None), 0)
    char.clues = 2
    self.assertEqual(prereq.value(None), 1)

  def testAttributeNotMaxedPrereq(self):
    char = DummyChar(sanity=5, max_sanity=lambda state: 5)
    prereq = AttributeNotMaxedPrerequisite(char, "sanity")
    self.assertEqual(prereq.value(None), 0)
    char.sanity = 3
    self.assertEqual(prereq.value(None), 1)

  def testItemPrereq(self):
    char = DummyChar()
    prereq = ItemPrerequisite(char, "bar")
    self.assertEqual(prereq.value(None), 0)
    char.possessions.append(Dummy(name="foo"))
    self.assertEqual(prereq.value(None), 0)
    char.possessions.extend([Dummy(name="bar"), Dummy(name="bar")])
    self.assertEqual(prereq.value(None), 1)

  def testContainsPrereq(self):
    state = DummyState()
    prereq = ContainsPrerequisite("common", "bar")
    self.assertEqual(prereq.value(state), 0)
    state.common.extend([Dummy(name="foo"), Dummy(name="bar"), Dummy(name="bar")])
    self.assertEqual(prereq.value(state), 2)

  def testMonsterPrereq(self):
    state = DummyState()
    char = DummyChar()
    monster = DummyMonster(ambush=True)
    prereq = NoAmbushPrerequisite(monster, char)
    self.assertEqual(prereq.value(state), 0)
    char.override = True
    self.assertEqual(prereq.value(state), 0)
    char.override = False
    self.assertEqual(prereq.value(state), 1)


class StabilityTest(unittest.TestCase):
  def testStability(self):
    place = DummyPlace()
    state = DummyState()
    stable = PlaceStable(place)
    unstable = PlaceUnstable(place)
    self.assertEqual(stable.value(state), 0)
    self.assertEqual(unstable.value(state), 1)
    place.sealed = True
    self.assertEqual(stable.value(state), 1)
    self.assertEqual(unstable.value(state), 0)


class OnGateTest(unittest.TestCase):
  def testOnGate(self):
    place = DummyPlace(gate=Dummy(name="Abyss"))
    state = DummyState()
    char = DummyChar(place=place)
    on_gate = OnGate(char)
    self.assertEqual(on_gate.value(state), 1)
    place.gate = None
    self.assertEqual(on_gate.value(state), 0)


class OpenGatesTest(unittest.TestCase):
  def testOpenGates(self):
    state = DummyState()
    place1 = DummyPlace(name="one", gate="hello")
    place2 = DummyPlace(name="two", gate="goodbye")
    place3 = DummyPlace(name="three")
    state.places = {"one": place1, "two": place2, "three": place3}
    gates = OpenGates()
    count = OpenGateCount()
    self.assertCountEqual(gates.value(state), ["one", "two"])
    self.assertEqual(count.value(state), 2)
    place2.gate = None
    place1.gate = None
    self.assertCountEqual(gates.value(state), [])
    self.assertEqual(count.value(state), 0)


class MonstersOnBoardTest(unittest.TestCase):
  def testOpenGates(self):
    state = DummyState()
    outskirts = places.Outskirts()
    sky = places.Sky()
    street = places.CityPlace("", "")
    cultist = DummyMonster(handle="cultist")
    maniac = DummyMonster(handle="maniac")
    state.monsters = [cultist, maniac]
    cultist.place = None
    maniac.place = street

    board = MonstersOnBoard()
    count = BoardMonsterCount()
    self.assertCountEqual(board.value(state), ["maniac"])
    self.assertEqual(count.value(state), 1)
    cultist.place = outskirts
    maniac.place = sky
    self.assertCountEqual(board.value(state), ["cultist", "maniac"])
    self.assertEqual(count.value(state), 2)


class EnteredGateTest(unittest.TestCase):
  def testEnteredGate(self):
    state = DummyState()
    place1 = DummyPlace(name="one", gate=Dummy(handle="Gate A0"))
    place2 = DummyPlace(name="two", gate=Dummy(handle="Gate A1"))
    place3 = Dummy(name="three")  # Streets have no gate
    state.places = {"three": place3, "one": place1, "two": place2}

    char = DummyChar(entered_gate="Gate A0")
    entered_gate = EnteredGate(char)
    self.assertEqual(entered_gate.value(state), "one")
    char.entered_gate = "Gate A1"
    self.assertEqual(entered_gate.value(state), "two")
    char.entered_gate = None
    self.assertIsNone(entered_gate.value(state))


class UnsuccessfulDiceTest(unittest.TestCase):
  def testUnsuccessfulDice(self):
    char = Dummy(is_success=lambda roll, _: roll >= 5)
    check = Dummy(character=char, roll=[1, 6, 3, 4, 5, 2], check_type="combat")
    state = DummyState()
    bad_dice = UnsuccessfulDice(check)
    self.assertEqual(bad_dice.value(state), [0, 2, 3, 5])
    check.character.is_success = lambda roll, _: roll >= 4  # pylint: disable=no-member
    self.assertEqual(bad_dice.value(state), [0, 2, 5])


class BadDiceTest(unittest.TestCase):
  def testBadDice(self):
    state = DummyState()
    roll = Dummy(roll=[1, 2, 3, 4], bad=[1, 2])
    bad_dice = BadDice(roll)
    self.assertEqual(bad_dice.value(state), 2)
    roll.bad = [4, 5, 6]
    self.assertEqual(bad_dice.value(state), 1)

  def testBadDiceWithNone(self):
    state = DummyState()
    roll = Dummy(roll=[1, 2, 3, 4], bad=None)
    bad_dice = BadDice(roll)
    self.assertEqual(bad_dice.value(state), 0)


class SpendTest(unittest.TestCase):
  def testFixedValuePrerequisite(self):
    state = DummyState()
    spend = ExactSpendPrerequisite({"dollars": 1})
    spend.spend_event = Dummy(spend_map=collections.defaultdict(dict))
    # Prerequisite starts unsatisfied.
    self.assertEqual(spend.remaining_spend(state), {"dollars": 1})
    self.assertEqual(spend.remaining_max(state), {"dollars": 1})
    # Spend one dollar, the prereq is satisfied.
    spend.spend_event.spend_map["dollars"]["dollars"] = 1
    self.assertEqual(spend.remaining_spend(state), {})
    # If for some reason you decided to spend clues and then changed your mind, still satisfied.
    spend.spend_event.spend_map["clues"]["clues"] = 0
    self.assertEqual(spend.remaining_spend(state), {})
    # Spend an extra dollar, now no longer satisfied.
    spend.spend_event.spend_map["dollars"]["dollars"] = 2
    self.assertEqual(spend.remaining_spend(state), {"dollars": -1})
    self.assertEqual(spend.remaining_max(state), {"dollars": -1})

  def testSpendZeroPrerequisite(self):
    state = DummyState()
    spend = SpendNothing()
    spend.spend_event = Dummy(spend_map=collections.defaultdict(dict))
    # This can happen when trying to buy an item that has been discounted to zero dollars.
    self.assertEqual(spend.remaining_spend(state), {})
    self.assertEqual(spend.remaining_max(state), {})
    spend.spend_event.spend_map["dollars"]["dollars"] = 1
    self.assertEqual(spend.remaining_spend(state), {"dollars": -1})
    self.assertEqual(spend.remaining_max(state), {"dollars": -1})
    # Should be satisfied both when not present and when present but 0.
    spend.spend_event.spend_map["dollars"]["dollars"] = 0
    self.assertEqual(spend.remaining_spend(state), {})
    self.assertEqual(spend.remaining_max(state), {})

  def testRangePrerequisite(self):
    state = DummyState()
    spend = RangeSpendPrerequisite("dollars", 1, 6)
    spend.spend_event = Dummy(spend_map=collections.defaultdict(dict))
    self.assertEqual(spend.remaining_spend(state), {"dollars": 1})
    self.assertEqual(spend.remaining_max(state), {"dollars": 6})

    spend.spend_event.spend_map["dollars"]["dollars"] = 1
    self.assertEqual(spend.remaining_spend(state), {})
    self.assertEqual(spend.remaining_max(state), {"dollars": 5})
    spend.spend_event.spend_map["dollars"]["dollars"] = 6
    self.assertEqual(spend.remaining_spend(state), {})
    self.assertEqual(spend.remaining_max(state), {})
    spend.spend_event.spend_map["dollars"]["dollars"] = 7
    self.assertEqual(spend.remaining_spend(state), {"dollars": -1})
    self.assertEqual(spend.remaining_max(state), {"dollars": -1})

  def testDynamicRange(self):
    state = DummyState()
    char = DummyChar(sanity=3)
    spend = RangeSpendPrerequisite("sanity", 1, Calculation(char, "sanity"))
    spend.spend_event = Dummy(spend_map=collections.defaultdict(dict))

    self.assertEqual(spend.remaining_spend(state), {"sanity": 1})
    self.assertEqual(spend.remaining_max(state), {"sanity": 3})
    spend.spend_event.spend_map["sanity"]["sanity"] = 1
    self.assertEqual(spend.remaining_spend(state), {})
    self.assertEqual(spend.remaining_max(state), {"sanity": 2})
    spend.spend_event.spend_map["sanity"]["sanity"] = 3
    self.assertEqual(spend.remaining_spend(state), {})
    self.assertEqual(spend.remaining_max(state), {})
    char.sanity = 2
    self.assertEqual(spend.remaining_spend(state), {"sanity": -1})
    self.assertEqual(spend.remaining_max(state), {"sanity": -1})

  def testSpendMultipleTypes(self):
    state = DummyState()
    spend = ExactSpendPrerequisite({"clues": 2})
    spend.spend_event = Dummy(spend_map=collections.defaultdict(dict))
    self.assertEqual(spend.remaining_spend(state), {"clues": 2})

    spend.spend_event.spend_map["clues"]["clues"] = 1
    self.assertEqual(spend.remaining_spend(state), {"clues": 1})
    spend.spend_event.spend_map["clues"]["Research Materials0"] = 1
    self.assertEqual(spend.remaining_spend(state), {})
    spend.spend_event.spend_map["clues"]["clues"] = 2
    self.assertEqual(spend.remaining_spend(state), {"clues": -1})

  def testMultiPrerequisite(self):
    state = DummyState()
    spend = ExactSpendPrerequisite({"dollars": 1, "clues": 2})
    spend.spend_event = Dummy(spend_map=collections.defaultdict(dict))
    self.assertEqual(spend.remaining_spend(state), {"dollars": 1, "clues": 2})
    self.assertEqual(spend.remaining_spend(state), {"dollars": 1, "clues": 2})

    spend.spend_event.spend_map["dollars"]["dollars"] = 1
    self.assertEqual(spend.remaining_spend(state), {"clues": 2})
    spend.spend_event.spend_map["clues"]["clues"] = 2
    self.assertEqual(spend.remaining_spend(state), {})
    spend.spend_event.spend_map["clues"]["Research Materials0"] = 1
    self.assertEqual(spend.remaining_spend(state), {"clues": -1})
    spend.spend_event.spend_map["clues"]["clues"] = 1
    self.assertEqual(spend.remaining_spend(state), {})
    spend.spend_event.spend_map["stamina"]["stamina"] = 1
    self.assertEqual(spend.remaining_spend(state), {"stamina": -1})

  def testFlexMultiPrerequisite(self):
    state = DummyState()
    char = DummyChar(sanity=3, stamina=3, dollars=2)
    spend = FlexibleRangeSpendPrerequisite(["dollars", "stamina", "sanity"], 1, 3, char)
    spend.spend_event = Dummy(spend_map=collections.defaultdict(dict))
    self.assertEqual(spend.remaining_spend(state), {"dollars": 1, "stamina": 1, "sanity": 1})
    self.assertEqual(spend.remaining_max(state), {"dollars": 2, "stamina": 1, "sanity": 0})

    spend.spend_event.spend_map["dollars"]["dollars"] = 1
    self.assertDictEqual(spend.remaining_spend(state), {})
    self.assertDictEqual(spend.remaining_max(state), {"dollars": 1, "stamina": 1, "sanity": 0})

    spend.spend_event.spend_map["stamina"]["stamina"] = 1
    self.assertDictEqual(spend.remaining_spend(state), {})
    self.assertDictEqual(spend.remaining_max(state), {"dollars": 1, "stamina": 0, "sanity": 0})

    spend.spend_event.spend_map["stamina"]["stamina"] = 2
    self.assertDictEqual(spend.remaining_spend(state), {})
    self.assertDictEqual(spend.remaining_max(state), {})

    spend.spend_event.spend_map["stamina"]["stamina"] = 1
    spend.spend_event.spend_map["sanity"]["sanity"] = 1
    self.assertDictEqual(spend.remaining_spend(state), {})
    self.assertDictEqual(spend.remaining_max(state), {})

    spend.spend_event.spend_map["dollars"]["dollars"] = 0
    spend.spend_event.spend_map["stamina"]["stamina"] = 1
    spend.spend_event.spend_map["sanity"]["sanity"] = 1
    char.dollars = 0
    char.stamina = 2
    self.assertDictEqual(spend.remaining_spend(state), {})
    self.assertDictEqual(spend.remaining_max(state), {"dollars": 0, "stamina": 0, "sanity": 1})


class SpendToughnessTest(unittest.TestCase):
  def testToughnessExactSpending(self):
    state = DummyState()
    spend = ToughnessSpend(5)
    spend.spend_event = Dummy(spend_map=collections.defaultdict(dict))
    self.assertEqual(spend.remaining_spend(state), {"toughness": 5})

    spend.spend_event.spend_map["toughness"]["Some monster"] = 4
    self.assertEqual(spend.remaining_spend(state), {"toughness": 1})
    # Exact spend
    spend.spend_event.spend_map["toughness"]["Other monster"] = 1
    self.assertEqual(spend.remaining_spend(state), {})
    # Unrelated spending at zero should have no effect.
    spend.spend_event.spend_map["clues"]["clues"] = 0
    self.assertEqual(spend.remaining_spend(state), {})
    # Cannot spend anything else
    spend.spend_event.spend_map["gates"]["some gate"] = 1
    self.assertEqual(spend.remaining_spend(state), {"gates": -1})
    # A gate does not count as 5 toughness for TougnessSpend.
    spend.spend_event.spend_map["toughness"].clear()
    self.assertEqual(spend.remaining_spend(state), {"gates": -1, "toughness": 5})
    self.assertEqual(spend.remaining_max(state), {"gates": -1, "toughness": 5})

  def testToughnessOverspend(self):
    state = DummyState()
    spend = ToughnessSpend(5)
    spend.spend_event = Dummy(spend_map=collections.defaultdict(dict))
    self.assertEqual(spend.remaining_spend(state), {"toughness": 5})

    spend.spend_event.spend_map["toughness"]["Some monster"] = 4
    self.assertEqual(spend.remaining_spend(state), {"toughness": 1})
    # Spent 6, but minimum spend is two, so overspend is okay.
    spend.spend_event.spend_map["toughness"]["Other monster"] = 2
    self.assertEqual(spend.remaining_spend(state), {})
    # Not okay: overspent by two, with one monster worth 2
    spend.spend_event.spend_map["toughness"]["Some monster"] = 3
    spend.spend_event.spend_map["toughness"]["Third monster"] = 2
    self.assertEqual(spend.remaining_spend(state), {"toughness": -2})

  def testToughnessOrGateSpending(self):
    state = DummyState()
    spend = ToughnessOrGatesSpend(10)
    spend.spend_event = Dummy(spend_map=collections.defaultdict(dict))
    self.assertEqual(spend.remaining_spend(state), {"toughness": 10})
    self.assertEqual(spend.remaining_max(state), {"toughness": 10})

    spend.spend_event.spend_map["toughness"]["Some monster"] = 4
    spend.spend_event.spend_map["gates"]["Some gate"] = 1
    self.assertEqual(spend.remaining_spend(state), {"toughness": 1})
    # Exact spend
    spend.spend_event.spend_map["toughness"]["Other monster"] = 1
    self.assertEqual(spend.remaining_spend(state), {})
    # Unrelated spending at zero should have no effect.
    spend.spend_event.spend_map["clues"]["clues"] = 0
    self.assertEqual(spend.remaining_spend(state), {})
    # Can use only monsters
    spend.spend_event.spend_map["gates"].clear()
    spend.spend_event.spend_map["toughness"]["big monster"] = 5
    self.assertEqual(spend.remaining_spend(state), {})
    # Can use only gates
    spend.spend_event.spend_map["toughness"].clear()
    spend.spend_event.spend_map["gates"] = {"Some gate": 1, "Other gate": 1}
    self.assertEqual(spend.remaining_spend(state), {})

  def testToughnessOrGateOverspend(self):
    state = DummyState()
    spend = ToughnessOrGatesSpend(10)
    spend.spend_event = Dummy(spend_map=collections.defaultdict(dict))
    self.assertEqual(spend.remaining_spend(state), {"toughness": 10})

    spend.spend_event.spend_map["toughness"]["Some monster"] = 4
    spend.spend_event.spend_map["gates"]["Some gate"] = 1
    self.assertEqual(spend.remaining_spend(state), {"toughness": 1})
    # Spent 11, but minimum spend is two, so overspend is okay.
    spend.spend_event.spend_map["toughness"]["Other monster"] = 2
    self.assertEqual(spend.remaining_spend(state), {})
    # Not okay: overspent by two, with one monster worth 2
    spend.spend_event.spend_map["toughness"]["Some monster"] = 3
    spend.spend_event.spend_map["toughness"]["Third monster"] = 2
    self.assertEqual(spend.remaining_spend(state), {"toughness": -2})
    # Use two gates
    spend.spend_event.spend_map["toughness"].clear()
    spend.spend_event.spend_map["gates"]["Other gate"] = 1
    self.assertEqual(spend.remaining_spend(state), {})
    # Not okay: overspend one gate.
    spend.spend_event.spend_map["gates"]["Third gate"] = 1
    self.assertEqual(spend.remaining_spend(state), {"toughness": -5})


class SpendCountTest(unittest.TestCase):
  def testSpendCountValue(self):
    spend_choice = Dummy()
    spend_choice.spend_map = collections.defaultdict(dict)
    spend_choice.is_done = lambda: True
    spend_choice.is_cancelled = lambda: False
    state = DummyState()

    stam = SpendCount(spend_choice, "stamina")
    san = SpendCount(spend_choice, "sanity")

    spend_choice.spend_map["stamina"] = {"stamina": 3, "Some Item": 1}
    spend_choice.spend_map["sanity"] = {"Some Item": 2}

    self.assertEqual(stam.value(state), 4)
    self.assertEqual(san.value(state), 2)

  def testSpendCountCancelled(self):
    spend_choice = Dummy(spend_map=collections.defaultdict(dict))
    spend_choice.is_done = lambda: True
    spend_choice.is_cancelled = lambda: True
    state = DummyState()

    stam = SpendCount(spend_choice, "stamina")
    san = SpendCount(spend_choice, "sanity")

    spend_choice.spend_map["stamina"] = {"stamina": 3, "Some Item": 1}
    spend_choice.spend_map["sanity"] = {"Some Item": 2}

    self.assertEqual(stam.value(state), 0)
    self.assertEqual(san.value(state), 0)


if __name__ == "__main__":
  unittest.main()
