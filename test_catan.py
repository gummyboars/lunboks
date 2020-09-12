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
    self.assertIsInstance(c.player_data, list)
    self.assertEqual(len(c.player_data), 1)
    self.assertIsInstance(c.player_data[0]["cards"], collections.defaultdict)
    self.assertIsInstance(c.player_data[0]["trade_ratios"], collections.defaultdict)
    # TODO: add some more assertions here


class BaseInputHandlerTest(unittest.TestCase):

  def setUp(self):
    with open("test.json") as json_file:
      json_data = json_file.read()
    self.c = catan.CatanState.parse_json(json_data)


class TestLoadTestData(BaseInputHandlerTest):

  def testSessions(self):
    self.assertIn("Player1", self.c.player_sessions)
    self.assertEqual(self.c.player_sessions["Player1"], 0)

  def testTradeRatios(self):
    self.assertEqual(self.c.player_data[0]["trade_ratios"]["rsrc1"], 2)
    self.assertEqual(self.c.player_data[0]["trade_ratios"]["rsrc2"], 4)
    self.assertEqual(self.c.player_data[1]["trade_ratios"]["rsrc1"], 4)


class TestHandleSettleInput(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_road(Road([3, 3, 4, 4], "road", 0))
    self.c.add_road(Road([5, 4, 6, 5], "road", 0))
    self.c.add_road(Road([5, 4, 6, 3], "road", 0))

  def testSettle(self):
    resources = ["rsrc1", "rsrc2", "rsrc3", "rsrc4"]
    counts = [self.c.player_data[0]["cards"][x] for x in resources]
    self.c.handle("Player1", {"type": "settle", "location": [3, 3]})
    for rsrc, orig_count in zip(resources, counts):
      self.assertEqual(self.c.player_data[0]["cards"][rsrc], orig_count - 1)

  def testMustSettleNextToRoad(self):
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle("Player1", {"type": "settle", "location": [2, 3]})

  def testMustSettleNextToOwnRoad(self):
    self.c.add_road(Road([4, 6, 5, 6], "road", "blue"))
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle("Player1", {"type": "settle", "location": [5, 6]})

  def testCannotSettleTooClose(self):
    self.c.add_road(Road([4, 6, 5, 6], "road", "red"))
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.c.handle("Player1", {"type": "settle", "location": [6, 3]})
    # Validate both distance from own settlements and from opponents'.
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.c.handle("Player1", {"type": "settle", "location": [4, 6]})

  def testCannotSettleSettledLocation(self):
    self.c.add_road(Road([3, 5, 4, 4], "road", "red"))
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle("Player1", {"type": "settle", "location": [5, 4]})
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle("Player1", {"type": "settle", "location": [3, 5]})
    # Also validate you cannot build on top of a city.
    self.c.handle_city([3, 5], 1)
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle("Player1", {"type": "settle", "location": [3, 5]})

  def testMustSettleValidLocation(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple of size 2"):
      self.c.handle("Player1", {"type": "settle", "location": [2]})


class TestHandleRoadInput(BaseInputHandlerTest):

  def testRoadsMustConnect(self):
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle("Player1", {"type": "road", "location": [2, 3, 3, 3]})

  def testRoadsMustConnectToSelf(self):
    # Validate that roads must connect to your own roads, not opponents'.
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle("Player1", {"type": "road", "location": [4, 6, 5, 6]})

  def testBuildRoad(self):
    count2 = self.c.player_data[0]["cards"]["rsrc2"]
    count4 = self.c.player_data[0]["cards"]["rsrc4"]
    self.c.handle("Player1", {"type": "road", "location": [3, 3, 4, 4]})
    # Validate that resources were taken away.
    self.assertEqual(self.c.player_data[0]["cards"]["rsrc2"], count2 - 1)
    self.assertEqual(self.c.player_data[0]["cards"]["rsrc4"], count4 - 1)
    # Test both connection to a road and connection to a settlement.
    self.c.handle("Player1", {"type": "road", "location": [5, 4, 6, 3]})
    self.assertEqual(self.c.player_data[0]["cards"]["rsrc2"], count2 - 2)
    self.assertEqual(self.c.player_data[0]["cards"]["rsrc4"], count4 - 2)

  def testCannotBuildWithoutResources(self):
    self.c.player_data[0]["cards"]["rsrc2"] = 0
    with self.assertRaisesRegex(InvalidMove, "need an extra 1 {rsrc2}"):
      self.c.handle("Player1", {"type": "road", "location": [3, 3, 4, 4]})

  def testRoadLocationMustBeAnEdge(self):
    with self.assertRaisesRegex(InvalidMove, "not a valid edge"):
      self.c.handle("Player1", {"type": "road", "location": [2, 3, 4, 4]})

  def testRoadLocationMustBeValid(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple"):
      self.c.handle("Player1", {"type": "road", "location": [1, 3, 4]})
    with self.assertRaisesRegex(AssertionError, "must be left"):
      self.c.handle("Player1", {"type": "road", "location": [4, 4, 3, 3]})

  def testCannotBuildOnWater(self):
    self.c.add_road(Road([5, 4, 6, 5], "road", "red"))
    with self.assertRaisesRegex(InvalidMove, "must be land"):
      self.c.handle("Player1", {"type": "road", "location": [6, 5, 7, 5]})


class TestCalculateRobPlayers(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_player("Player3")
    self.c.turn_idx = 2
    self.c.dice_roll = (6, 1)
    self.c.turn_phase = "robber"
    moved_piece = self.c.pieces.pop((3, 5))
    moved_piece.location = catan.CornerLocation(4, 6)
    self.c.add_piece(moved_piece)

  def testRobNoAdjacentPieces(self):
    p1_old_count = sum(self.c.player_data[0]["cards"][x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1]["cards"][x] for x in catan.RESOURCES)
    self.c.handle("Player3", {"type": "robber", "location": [2, 3]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0]["cards"][x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1]["cards"][x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count)

  def testRobTwoAdjacentPlayers(self):
    p1_old_count = sum(self.c.player_data[0]["cards"][x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1]["cards"][x] for x in catan.RESOURCES)
    self.c.handle("Player3", {"type": "robber", "location": [4, 4]})
    self.assertEqual(self.c.turn_phase, "rob")
    p1_new_count = sum(self.c.player_data[0]["cards"][x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1]["cards"][x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count)

    self.c.handle("Player3", {"type": "rob", "player": 1})
    p1_new_count = sum(self.c.player_data[0]["cards"][x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1]["cards"][x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2]["cards"][x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count - 1)
    self.assertEqual(p3_new_count, 1)

  def testRobSingleAdjacentPlayer(self):
    p1_old_count = sum(self.c.player_data[0]["cards"][x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1]["cards"][x] for x in catan.RESOURCES)
    self.c.handle("Player3", {"type": "robber", "location": [4, 2]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0]["cards"][x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1]["cards"][x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2]["cards"][x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count - 1)
    self.assertEqual(p2_new_count, p2_old_count)
    self.assertEqual(p3_new_count, 1)

  def testRobSingleAdjacentPlayerWithoutCards(self):
    self.c.player_data[0]["cards"].clear()
    self.c.handle("Player3", {"type": "robber", "location": [4, 2]})
    self.assertEqual(self.c.turn_phase, "main")
    p3_new_count = sum(self.c.player_data[2]["cards"][x] for x in catan.RESOURCES)
    self.assertEqual(p3_new_count, 0)

  def testRobTwoAdjacentPlayersOneWithoutCards(self):
    p2_old_count = sum(self.c.player_data[1]["cards"][x] for x in catan.RESOURCES)
    self.c.player_data[0]["cards"].clear()
    self.c.handle("Player3", {"type": "robber", "location": [4, 4]})
    self.assertEqual(self.c.turn_phase, "main")
    p2_new_count = sum(self.c.player_data[1]["cards"][x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2]["cards"][x] for x in catan.RESOURCES)
    self.assertEqual(p2_new_count, p2_old_count - 1)
    self.assertEqual(p3_new_count, 1)


if __name__ == '__main__':
  unittest.main()
