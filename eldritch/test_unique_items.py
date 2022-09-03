#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch import abilities
from eldritch import assets
from eldritch import characters
from eldritch import encounters
from eldritch import events
from eldritch.events import *
from eldritch import gates
from eldritch import gate_encounters
from eldritch import items
from eldritch import monsters
from eldritch.test_events import EventTest, Canceller

class EnchantedJewelryTest(EventTest):
  def setUp(self):
    super().setUp()
    self.jewelry = items.EnchantedJewelry(0)
    self.char.possessions = [self.jewelry]

  def testSingleStamina(self):
    loss = events.Loss(self.char, {"stamina": 1})
    self.state.event_stack.append(loss)
    self.resolve_to_usable(0, "Enchanted Jewelry0")
    print("appending Enchanted Jewelry")
    self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
    # self.resolve_until_done()
    # self.assertEqual(self.jewelry.tokens["stamina"], 1)
    # self.assertEqual(self.char.stamina, 5)


  def testMultipleStaminaUnused(self):
    loss = events.Loss(self.char, {"stamina": 2})
    self.state.event_stack.append(loss)
    self.resolve_to_usable(0, "Enchanted Jewelry0")
    print("appending Enchanted Jewelry")
    self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
    self.resolve_until_done()
    self.assertEqual(self.jewelry.tokens["stamina"], 1)
    self.assertEqual(self.char.stamina, 4)


  def testMultipleStaminaUsed(self):
      loss = events.Loss(self.char, {"stamina": 2})
      self.state.event_stack.append(loss)
      self.resolve_to_usable(0, "Enchanted Jewelry0")
      print("appending Enchanted Jewelry")
      self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
      self.resolve_to_usable(0, "Enchanted Jewelry0")
      self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
      self.resolve_until_done()
      self.assertEqual(self.jewelry.tokens["stamina"], 2)
      self.assertEqual(self.char.stamina, 5)

  def testSingleStaminaMaxTokens(self):
    self.jewelry.tokens["stamina"] = 2
    loss = events.Loss(self.char, {"stamina": 1})
    self.state.event_stack.append(loss)
    self.resolve_to_usable(0, "Enchanted Jewelry0")
    print("appending Enchanted Jewelry")
    self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertNotIn(self.char.possesssions, self.jewelry)
