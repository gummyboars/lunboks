#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

import eldritch.characters as characters
from eldritch.events import *
import eldritch.gates as gates
from eldritch.mythos import *
import eldritch.places as places
from eldritch.test_events import EventTest


class OpenGateTest(EventTest):

  def setUp(self):
    super(OpenGateTest, self).setUp()
    self.state.gates.clear()
    self.info = places.OtherWorldInfo("Pluto", {"blue", "yellow"})
    self.gate = gates.Gate(self.info, -2)
    self.state.gates.append(self.gate)
    self.square = self.state.places["Square"]
    self.woods = self.state.places["Woods"]

  def testOpenGate(self):
    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    self.assertIsNone(self.woods.gate)
    self.assertEqual(len(self.square.monsters), 0)

    self.state.event_stack.append(OpenGate("Square"))
    self.resolve_until_done()

    self.assertEqual(len(self.state.gates), 0)
    self.assertEqual(self.square.gate, self.gate)
    self.assertIsNone(self.woods.gate)
    self.assertEqual(len(self.square.monsters), 1)
    self.assertEqual(len(self.woods.monsters), 0)

  def testOpenGateSealed(self):
    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    self.assertEqual(len(self.square.monsters), 0)
    self.square.sealed = True

    self.state.event_stack.append(OpenGate("Square"))
    self.resolve_until_done()

    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    self.assertEqual(len(self.square.monsters), 0)
    self.assertTrue(self.square.sealed)


class SpawnClueTest(EventTest):

  def setUp(self):
    super(SpawnClueTest, self).setUp()
    self.square = self.state.places["Square"]

  def testSpawnClue(self):
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.square.clues, 0)

    self.state.event_stack.append(SpawnClue("Square"))
    self.resolve_until_done()

    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.square.clues, 1)

  def testSpawnClueOnCharacter(self):
    self.char.place = self.square
    self.assertEqual(self.char.clues, 0)

    self.state.event_stack.append(SpawnClue("Square"))
    self.resolve_until_done()

    self.assertEqual(self.char.clues, 1)
    self.assertEqual(self.square.clues, 0)

  def testSpawnClueOnTwoCharacters(self):
    self.char.place = self.square
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.square
    buddy.clues = 2
    self.state.characters.append(buddy)

    self.state.event_stack.append(SpawnClue("Square"))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy", "Buddy"])
    choice.resolve(self.state, "Buddy")
    self.resolve_until_done()

    self.assertEqual(self.char.clues, 0)
    self.assertEqual(buddy.clues, 3)
    self.assertEqual(self.square.clues, 0)
