#!/usr/bin/env python3

import collections
import unittest

import catan

InvalidMove = catan.InvalidMove
Road = catan.Road


class TestInitBoard(unittest.TestCase):

  def testBeginner(self):
    state = catan.CatanState()
    state.init_beginner()

    self.assertEqual(len(state.tiles), 4 + 5 + 6 + 7 + 6 + 5 + 4, "number of tiles")
    for loc, tile in state.tiles.items():
      self.assertEqual(loc, tile.location.json_repr(), "tiles mapped to location")


class TestLoadState(unittest.TestCase):

  def testLoadState(self):
    with open("beginner.json") as json_file:
      json_data = json_file.read()
    c = catan.CatanState.parse_json(json_data)
    self.assertIsInstance(c.cards, collections.defaultdict)
    self.assertIsInstance(c.cards["red"], collections.defaultdict)
    self.assertIsInstance(c.trade_ratios, collections.defaultdict)
    self.assertIsInstance(c.trade_ratios["red"], collections.defaultdict)
    # TODO: add some more assertions here


class BaseInputHandlerTest(unittest.TestCase):

  def setUp(self):
    with open("test.json") as json_file:
      json_data = json_file.read()
    self.c = catan.CatanState.parse_json(json_data)


class TestLoadTestData(BaseInputHandlerTest):

  def testTradeRatios(self):
    self.assertEqual(self.c.trade_ratios["red"]["rsrc1"], 2)
    self.assertEqual(self.c.trade_ratios["red"]["rsrc2"], 4)
    self.assertEqual(self.c.trade_ratios["blue"]["rsrc1"], 4)


class TestHandleSettleInput(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_road(Road([3, 3, 4, 4], "road", "red"))
    self.c.add_road(Road([5, 4, 6, 5], "road", "red"))
    self.c.add_road(Road([5, 4, 6, 3], "road", "red"))

  def testSettle(self):
    resources = ["rsrc1", "rsrc2", "rsrc3", "rsrc4"]
    counts = [self.c.cards["red"][x] for x in resources]
    self.c.handle({"type": "settle", "location": [3, 3]}, "Player1")
    for rsrc, orig_count in zip(resources, counts):
      self.assertEqual(self.c.cards["red"][rsrc], orig_count - 1)

  def testMustSettleNextToRoad(self):
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle({"type": "settle", "location": [2, 3]}, "Player1")

  def testMustSettleNextToOwnRoad(self):
    self.c.add_road(Road([4, 6, 5, 6], "road", "blue"))
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle({"type": "settle", "location": [5, 6]}, "Player1")

  def testCannotSettleTooClose(self):
    self.c.add_road(Road([4, 6, 5, 6], "road", "red"))
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.c.handle({"type": "settle", "location": [6, 3]}, "Player1")
    # Validate both distance from own settlements and from opponents'.
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.c.handle({"type": "settle", "location": [4, 6]}, "Player1")

  def testCannotSettleSettledLocation(self):
    self.c.add_road(Road([3, 5, 4, 4], "road", "red"))
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle({"type": "settle", "location": [5, 4]}, "Player1")
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle({"type": "settle", "location": [3, 5]}, "Player1")
    # Also validate you cannot build on top of a city.
    self.c.handle_city([3, 5], "blue")
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle({"type": "settle", "location": [3, 5]}, "Player1")

  def testMustSettleValidLocation(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple of size 2"):
      self.c.handle({"type": "settle", "location": [2]}, "Player1")


class TestHandleRoadInput(BaseInputHandlerTest):

  def testRoadsMustConnect(self):
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle({"type": "road", "location": [2, 3, 3, 3]}, "Player1")

  def testRoadsMustConnectToSelf(self):
    # Validate that roads must connect to your own roads, not opponents'.
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle({"type": "road", "location": [4, 6, 5, 6]}, "Player1")

  def testBuildRoad(self):
    count2 = self.c.cards["red"]["rsrc2"]
    count4 = self.c.cards["red"]["rsrc4"]
    self.c.handle({"type": "road", "location": [3, 3, 4, 4]}, "Player1")
    # Validate that resources were taken away.
    self.assertEqual(self.c.cards["red"]["rsrc2"], count2 - 1)
    self.assertEqual(self.c.cards["red"]["rsrc4"], count4 - 1)
    # Test both connection to a road and connection to a settlement.
    self.c.handle({"type": "road", "location": [5, 4, 6, 3]}, "Player1")
    self.assertEqual(self.c.cards["red"]["rsrc2"], count2 - 2)
    self.assertEqual(self.c.cards["red"]["rsrc4"], count4 - 2)

  def testCannotBuildWithoutResources(self):
    self.c.cards["red"]["rsrc2"] = 0
    with self.assertRaisesRegex(InvalidMove, "need an extra 1 {rsrc2}"):
      self.c.handle({"type": "road", "location": [3, 3, 4, 4]}, "Player1")

  def testRoadLocationMustBeAnEdge(self):
    with self.assertRaisesRegex(InvalidMove, "not a valid edge"):
      self.c.handle({"type": "road", "location": [2, 3, 4, 4]}, "Player1")

  def testRoadLocationMustBeValid(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple"):
      self.c.handle({"type": "road", "location": [1, 3, 4]}, "Player1")
    with self.assertRaisesRegex(AssertionError, "must be left"):
      self.c.handle({"type": "road", "location": [4, 4, 3, 3]}, "Player1")

  def testCannotBuildOnWater(self):
    self.c.add_road(Road([5, 4, 6, 5], "road", "red"))
    with self.assertRaisesRegex(InvalidMove, "must be land"):
      self.c.handle({"type": "road", "location": [6, 5, 7, 5]}, "Player1")


if __name__ == '__main__':
  unittest.main()
