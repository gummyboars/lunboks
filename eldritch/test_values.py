#!/usr/bin/env python3

import operator
import os
import sys
import unittest

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch.values import *


class Dummy(object):

  def __init__(self, **kwargs):
    for name, value in kwargs.items():
      setattr(self, name, value)


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
    calc = Calculation(obj, "x", operator.mul, 4)
    with self.assertRaises(AttributeError):
      calc.value(None)
    obj.x = 3
    self.assertEqual(calc.value(None), 12)

  def testUnaryOperator(self):
    obj = Dummy()
    calc = Calculation(obj, "x", operator.neg)
    with self.assertRaises(AttributeError):
      calc.value(None)
    obj.x = 3
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


class PrerequisiteTest(unittest.TestCase):

  def testAttributePrereq(self):
    char = Dummy(clues=0, dollars=0)
    prereq = AttributePrerequisite(char, "clues", 2, "at least")
    self.assertEqual(prereq.value(None), 0)
    char.clues = 2
    self.assertEqual(prereq.value(None), 1)

  def testItemPrereq(self):
    char = Dummy(possessions=[])
    prereq = ItemPrerequisite(char, "bar")
    self.assertEqual(prereq.value(None), 0)
    char.possessions.append(Dummy(name="foo"))
    self.assertEqual(prereq.value(None), 0)
    char.possessions.extend([Dummy(name="bar"), Dummy(name="bar")])
    self.assertEqual(prereq.value(None), 1)

  def testContainsPrereq(self):
    state = Dummy(common=[])
    prereq = ContainsPrerequisite("common", "bar")
    self.assertEqual(prereq.value(state), 0)
    state.common.extend([Dummy(name="foo"), Dummy(name="bar"), Dummy(name="bar")])
    self.assertEqual(prereq.value(state), 2)


if __name__ == '__main__':
  unittest.main()
