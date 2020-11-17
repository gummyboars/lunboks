#!/usr/bin/env python3

import collections
import json
import unittest
from unittest import mock

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
    self.assertIsInstance(c.player_data[0].cards, collections.defaultdict)
    self.assertIsInstance(c.player_data[0].trade_ratios, collections.defaultdict)
    # TODO: add some more assertions here

  def testDumpAndLoad(self):
    c = catan.CatanState()
    c.init_normal()
    data = c.json_str()
    d = catan.CatanState.parse_json(data)

    for loc_attr in ["tiles", "ports", "port_corners", "pieces", "roads"]:
      keys = getattr(c, loc_attr).keys()
      self.assertCountEqual(keys, getattr(d, loc_attr).keys())
      for key in keys:
        old_item = getattr(c, loc_attr)[key]
        new_item = getattr(d, loc_attr)[key]
        # Direct comparison for primitives.
        if not hasattr(old_item, "__dict__"):
          self.assertEqual(old_item, new_item, "%s [%s] old == new" % (loc_attr, key))
          continue
        # Attribute-by-attribute comparison for objects.
        self.assertCountEqual(old_item.__dict__.keys(), new_item.__dict__.keys())
        for attr in old_item.__dict__:
          self.assertEqual(
              getattr(old_item, attr), getattr(new_item, attr),
              "%s [%s]: %s old == new" % (loc_attr, key, attr))


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
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc1"], 2)
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc2"], 4)
    self.assertEqual(self.c.player_data[1].trade_ratios["rsrc1"], 4)


class TestDistributeResources(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_piece(catan.Piece(3, 3, "city", 0))
    self.c.pieces[(3, 5)].piece_type = "city"
    for rsrc in ["rsrc3", "rsrc4", "rsrc5"]:
      self.c.player_data[0].cards[rsrc] = 8
      self.c.player_data[1].cards[rsrc] = 9
    self.c.player_data[0].cards["rsrc1"] = 0
    self.c.player_data[1].cards["rsrc1"] = 0

  def testTooManyResources(self):
    self.c.distribute_resources(5)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], 8)
    self.assertEqual(self.c.player_data[1].cards["rsrc4"], 9)

    self.c.distribute_resources(6)
    self.assertEqual(self.c.player_data[0].cards["rsrc5"], 8)
    self.assertEqual(self.c.player_data[1].cards["rsrc5"], 9)

  def testTooManyResourcesOnlyOnePlayer(self):
    self.c.distribute_resources(9)
    self.assertEqual(self.c.player_data[0].cards["rsrc3"], 10)
    self.assertEqual(self.c.player_data[1].cards["rsrc3"], 9)
    self.assertEqual(self.c.player_data[1].cards["rsrc1"], 2)


class TestHandleSettleInput(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_road(Road([3, 3, 4, 4], "road", 0))
    self.c.add_road(Road([5, 4, 6, 5], "road", 0))
    self.c.add_road(Road([5, 4, 6, 3], "road", 0))

  def testSettle(self):
    resources = ["rsrc1", "rsrc2", "rsrc3", "rsrc4"]
    counts = [self.c.player_data[0].cards[x] for x in resources]
    self.c.handle("Player1", {"type": "settle", "location": [3, 3]})
    for rsrc, orig_count in zip(resources, counts):
      self.assertEqual(self.c.player_data[0].cards[rsrc], orig_count - 1)

  def testMustSettleNextToRoad(self):
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle("Player1", {"type": "settle", "location": [2, 3]})

  def testMustSettleNextToOwnRoad(self):
    self.c.add_road(Road([4, 6, 5, 6], "road", 1))
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle("Player1", {"type": "settle", "location": [5, 6]})

  def testCannotSettleTooClose(self):
    self.c.add_road(Road([4, 6, 5, 6], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.c.handle("Player1", {"type": "settle", "location": [6, 3]})
    # Validate both distance from own settlements and from opponents'.
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.c.handle("Player1", {"type": "settle", "location": [4, 6]})

  def testCannotSettleSettledLocation(self):
    self.c.add_road(Road([3, 5, 4, 4], "road", 0))
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

  def testCannotBuildTooManySettlements(self):
    self.c.add_piece(catan.Piece(1, 4, "settlement", 0))
    self.c.add_piece(catan.Piece(1, 6, "settlement", 0))
    self.c.add_piece(catan.Piece(5, 6, "settlement", 0))
    self.c.add_piece(catan.Piece(5, 2, "settlement", 0))
    with self.assertRaisesRegex(InvalidMove, "settlements remaining"):
      self.c.handle("Player1", {"type": "settle", "location": [3, 3]})

    self.c.pieces[(1, 4)].piece_type = "city"
    self.c.pieces[(1, 6)].piece_type = "city"
    self.c.pieces[(5, 6)].piece_type = "city"
    self.c.pieces[(5, 2)].piece_type = "city"
    with self.assertRaisesRegex(InvalidMove, "cities remaining"):
      self.c.handle("Player1", {"type": "city", "location": [5, 4]})


class TestHandleRoadInput(BaseInputHandlerTest):

  def addThirteenRoads(self):
    self.c.add_road(Road([5, 4, 6, 3], "road", 0))
    self.c.add_road(Road([5, 2, 6, 3], "road", 0))
    self.c.add_road(Road([4, 2, 5, 2], "road", 0))
    self.c.add_road(Road([3, 3, 4, 2], "road", 0))
    self.c.add_road(Road([2, 3, 3, 3], "road", 0))
    self.c.add_road(Road([1, 4, 2, 3], "road", 0))
    self.c.add_road(Road([1, 4, 2, 5], "road", 0))
    self.c.add_road(Road([1, 6, 2, 5], "road", 0))
    self.c.add_road(Road([1, 6, 2, 7], "road", 0))
    self.c.add_road(Road([2, 7, 3, 7], "road", 0))
    self.c.add_road(Road([3, 7, 4, 6], "road", 0))
    self.c.add_road(Road([4, 6, 5, 6], "road", 0))
    self.c.add_road(Road([5, 6, 6, 5], "road", 0))

  def testRoadsMustConnect(self):
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle("Player1", {"type": "road", "location": [2, 3, 3, 3]})

  def testRoadsMustConnectToSelf(self):
    # Validate that roads must connect to your own roads, not opponents'.
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle("Player1", {"type": "road", "location": [4, 6, 5, 6]})

  def testBuildRoad(self):
    count2 = self.c.player_data[0].cards["rsrc2"]
    count4 = self.c.player_data[0].cards["rsrc4"]
    self.c.handle("Player1", {"type": "road", "location": [3, 3, 4, 4]})
    # Validate that resources were taken away.
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], count2 - 1)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], count4 - 1)
    # Test both connection to a road and connection to a settlement.
    self.c.handle("Player1", {"type": "road", "location": [5, 4, 6, 3]})
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], count2 - 2)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], count4 - 2)

  def testCannotBuildTooManyRoads(self):
    self.addThirteenRoads()
    self.c.handle("Player1", {"type": "road", "location": [5, 4, 6, 5]})
    with self.assertRaisesRegex(InvalidMove, "no roads remaining"):
      self.c.handle("Player1", {"type": "road", "location": [3, 3, 4, 4]})

  def testCanPlayRoadBuildingWithOneRoadLeft(self):
    self.addThirteenRoads()
    self.c.player_data[0].cards["roadbuilding"] += 1
    self.c.handle("Player1", {"type": "play_dev", "card_type": "roadbuilding"})
    self.c.handle("Player1", {"type": "road", "location": [5, 4, 6, 5]})
    self.assertEqual(self.c.turn_phase, "main")

  def testCannotPlayRoadBuildingAtMaxRoads(self):
    self.addThirteenRoads()
    self.c.handle("Player1", {"type": "road", "location": [5, 4, 6, 5]})
    self.c.player_data[0].cards["roadbuilding"] += 1
    with self.assertRaisesRegex(InvalidMove, "no roads remaining"):
      self.c.handle("Player1", {"type": "play_dev", "card_type": "roadbuilding"})

  def testCannotBuildWithoutResources(self):
    self.c.player_data[0].cards["rsrc2"] = 0
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
    self.c.add_road(Road([5, 4, 6, 5], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "must be land"):
      self.c.handle("Player1", {"type": "road", "location": [6, 5, 7, 5]})

  def testCannotBuildAcrossOpponentSettlement(self):
    self.c.add_road(Road([3, 5, 4, 4], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle("Player1", {"type": "road", "location": [2, 5, 3, 5]})


class TestCalculateRobPlayers(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.started = False  # To allow new players to join.
    self.c.handle_join("Player3", {"name": "Player3"})
    self.c.started = True
    self.c.turn_idx = 2
    self.c.dice_roll = (6, 1)
    self.c.turn_phase = "robber"
    moved_piece = self.c.pieces.pop((3, 5))
    moved_piece.location = catan.CornerLocation(4, 6)
    self.c.add_piece(moved_piece)

  def testRobNoAdjacentPieces(self):
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.handle("Player3", {"type": "robber", "location": [2, 3]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count)

  def testRobTwoAdjacentPlayers(self):
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.handle("Player3", {"type": "robber", "location": [4, 4]})
    self.assertEqual(self.c.turn_phase, "rob")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count)

    self.c.handle("Player3", {"type": "rob", "player": 1})
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count - 1)
    self.assertEqual(p3_new_count, 1)

  def testRobSingleAdjacentPlayer(self):
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.handle("Player3", {"type": "robber", "location": [4, 2]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count - 1)
    self.assertEqual(p2_new_count, p2_old_count)
    self.assertEqual(p3_new_count, 1)

  def testRobSingleAdjacentPlayerWithoutCards(self):
    self.c.player_data[0].cards.clear()
    self.c.handle("Player3", {"type": "robber", "location": [4, 2]})
    self.assertEqual(self.c.turn_phase, "main")
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p3_new_count, 0)

  def testRobTwoAdjacentPlayersOneWithoutCards(self):
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.player_data[0].cards.clear()
    self.c.handle("Player3", {"type": "robber", "location": [4, 4]})
    self.assertEqual(self.c.turn_phase, "main")
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p2_new_count, p2_old_count - 1)
    self.assertEqual(p3_new_count, 1)


class TestLongestRouteCalculation(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)

  def testSingleRoad(self):
    val = self.c._dfs_depth(0, catan.CornerLocation(4, 4), set([]), None)
    self.assertEqual(val, 1)

  def testTwoRoads(self):
    self.c.add_road(Road([5, 4, 6, 5], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(4, 4), set([]), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 5), set([]), None)
    self.assertEqual(val, 2)
    # Starting from the middle should give a length of 1.
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 4), set([]), None)
    self.assertEqual(val, 1)

  def testThreeRoads(self):
    self.c.add_road(Road([5, 4, 6, 5], "road", 0))
    self.c.add_road(Road([5, 4, 6, 3], "road", 0))
    # Starting on any end of the network should still get you 2.
    val = self.c._dfs_depth(0, catan.CornerLocation(4, 4), set([]), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 5), set([]), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 3), set([]), None)
    self.assertEqual(val, 2)
    # Starting from the middle should give a length of 1.
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 4), set([]), None)
    self.assertEqual(val, 1)

  def testRoadInterruption(self):
    self.c.add_road(Road([5, 4, 6, 5], "road", 0))
    self.c.add_road(Road([5, 6, 6, 5], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(4, 4), set([]), None)
    self.assertEqual(val, 3)
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 6), set([]), None)
    self.assertEqual(val, 3)
    # Add a piece for the other player to interrupt the road.
    self.c.add_piece(catan.Piece(6, 5, "settlement", 1))
    val = self.c._dfs_depth(0, catan.CornerLocation(4, 4), set([]), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 6), set([]), None)
    self.assertEqual(val, 1)

  def testSandwichedRoad(self):
    # Test that you can still start a road at someone else's settlement.
    self.c.add_piece(catan.Piece(5, 6, "settlement", 1))
    self.c.add_road(Road([3, 5, 4, 4], "road", 0))
    self.c.add_road(Road([5, 4, 6, 5], "road", 0))
    self.c.add_road(Road([5, 6, 6, 5], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(4, 4), set([]), None)
    self.assertEqual(val, 3)
    val = self.c._dfs_depth(0, catan.CornerLocation(3, 5), set([]), None)
    self.assertEqual(val, 4)
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 6), set([]), None)
    self.assertEqual(val, 4)

  def testCircularRoad(self):
    self.c.add_road(Road([3, 3, 4, 4], "road", 0))
    self.c.add_road(Road([3, 3, 4, 2], "road", 0))
    self.c.add_road(Road([4, 2, 5, 2], "road", 0))
    self.c.add_road(Road([5, 2, 6, 3], "road", 0))
    self.c.add_road(Road([5, 4, 6, 3], "road", 0))

    # Start by testing a simple loop.
    for corner in [(3, 3), (4, 4), (5, 4), (6, 3), (5, 2), (4, 2)]:
      val = self.c._dfs_depth(0, catan.CornerLocation(*corner), set([]), None)
      self.assertEqual(val, 6, "loop length for corner %s" % (corner,))

    # Add two tips onto the end of the loop. Length from either end should be 7.
    self.c.add_road(Road([2, 3, 3, 3], "road", 0))
    self.c.add_road(Road([5, 4, 6, 5], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(2, 3), set([]), None)
    self.assertEqual(val, 7, "enter and loop around")
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 5), set([]), None)
    self.assertEqual(val, 7, "enter and loop around")

    # Make the road longer without using the loop than with the loop.
    self.c.add_road(Road([1, 4, 2, 3], "road", 0))
    self.c.add_road(Road([1, 4, 2, 5], "road", 0))
    self.c.add_road(Road([5, 6, 6, 5], "road", 0))
    self.c.add_road(Road([4, 6, 5, 6], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(4, 6), set([]), None)
    self.assertEqual(val, 10, "take long route around loop")
    val = self.c._dfs_depth(0, catan.CornerLocation(2, 5), set([]), None)
    self.assertEqual(val, 10, "take long route around loop")

  def testPortConnection(self):
    # Start with 2 ships and 4 roads, but no connection between them.
    self.c.add_road(Road([3, 3, 4, 4], "road", 0))
    self.c.add_road(Road([3, 3, 4, 2], "ship", 0))
    self.c.add_road(Road([4, 2, 5, 2], "ship", 0))
    self.c.add_road(Road([5, 2, 6, 3], "road", 0))
    self.c.add_road(Road([5, 4, 6, 3], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(3, 3), set([]), None)
    self.assertEqual(val, 4, "no road -> ship connection")
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 2), set([]), None)
    self.assertEqual(val, 4, "no road -> ship connection")
    val = self.c._dfs_depth(0, catan.CornerLocation(4, 2), set([]), None)
    self.assertEqual(val, 1, "single ship length in either direction")
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 4), set([]), None)
    self.assertEqual(val, 2, "two roads in either direction")

    # Add a connector piece.
    self.c.add_piece(catan.Piece(3, 3, "settlement", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(3, 3), set([]), None)
    self.assertEqual(val, 4, "still cannot go road->ship in the middle")
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 2), set([]), None)
    self.assertEqual(val, 6, "but can go road->ship through a port")

    # Make sure somebody else's settlement doesn't count.
    self.c.pieces[(3, 3)].player = 1
    val = self.c._dfs_depth(0, catan.CornerLocation(3, 3), set([]), None)
    self.assertEqual(val, 4, "cannot go through someone else's port")
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 2), set([]), None)
    self.assertEqual(val, 4, "cannot go through someone else's port")


class TestLongestRouteAssignment(unittest.TestCase):

  def setUp(self):
    with open("beginner.json") as json_file:
      json_data = json_file.read()
    self.c = catan.CatanState.parse_json(json_data)
    self.c.started = False  # To allow new players to join
    self.c.handle_join("PlayerA", {"name": "PlayerA"})
    self.c.handle_join("PlayerB", {"name": "PlayerB"})
    self.c.started = True
    self.c.add_road(Road([4, 4, 5, 4], "road", 0))
    self.c.add_road(Road([5, 4, 6, 5], "road", 0))
    self.c.add_road(Road([7, 5, 8, 6], "road", 0))
    self.c.add_road(Road([3, 3, 4, 2], "road", 1))
    self.c.add_road(Road([4, 2, 5, 2], "road", 1))
    self.c.add_road(Road([5, 2, 6, 1], "road", 1))
    self.c.add_road(Road([6, 1, 7, 1], "road", 1))
    self.c.add_road(Road([3, 7, 4, 8], "road", 2))
    self.c.add_road(Road([4, 8, 5, 8], "road", 2))
    self.c.add_road(Road([5, 8, 6, 9], "road", 2))
    self.c.add_road(Road([6, 9, 7, 9], "road", 2))

  def testCreateLongestRoad(self):
    self.assertIsNone(self.c.longest_route_player)
    # Add a fifth road to playerA's network, giving them longest road.
    self.c.add_road(Road([7, 1, 8, 2], "road", 1))
    self.assertEqual(self.c.longest_route_player, 1)
    # Connect two segments of first player's roads, giving them longest road.
    self.c.add_road(Road([6, 5, 7, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)

  def testBreakLongestRoad(self):
    self.c.add_road(Road([7, 1, 8, 2], "road", 1))
    self.c.add_road(Road([6, 5, 7, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    # Break first player's longest road with a piece from playerB.
    self.c.add_piece(catan.Piece(5, 4, "settlement", 2))
    # PlayerA should get longest road since first player's is broken.
    self.assertEqual(self.c.longest_route_player, 1)
    self.assertEqual(self.c.player_data[0].longest_route, 4)

  def testBreakLongestRoadNoEligiblePlayers(self):
    self.c.add_road(Road([6, 5, 7, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    self.c.add_piece(catan.Piece(5, 4, "settlement", 2))
    self.assertIsNone(self.c.longest_route_player)

  def testBreakLongestRoadMultipleEligiblePlayers(self):
    self.c.add_road(Road([7, 1, 8, 2], "road", 1))
    self.c.add_road(Road([7, 9, 8, 8], "road", 2))
    self.c.add_road(Road([6, 5, 7, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    self.c.add_piece(catan.Piece(5, 4, "settlement", 2))
    # Now that first player's road is broken, nobody gets longest road because playerA
    # and playerB are tied.
    self.assertIsNone(self.c.longest_route_player)

  def testBreakLongestRoadNextRoadTooShort(self):
    self.c.add_road(Road([6, 5, 7, 5], "road", 0))
    # Break playerB's road of 4 so that this scenario is distinguishable from the one
    # where multiple players are tied for next longest road.
    self.c.add_piece(catan.Piece(5, 8, "settlement", 0))
    self.assertEqual(self.c.player_data[2].longest_route, 2)
    self.assertEqual(self.c.longest_route_player, 0)
    # Break first player's longest road. Their longest road should now be 3.
    self.c.add_piece(catan.Piece(6, 5, "settlement", 2))
    self.assertEqual(self.c.player_data[0].longest_route, 3)
    self.assertEqual(self.c.player_data[1].longest_route, 4)
    self.assertIsNone(self.c.longest_route_player)

  def testBreakLongestRoadStayingTied(self):
    # Give first player a longest road of 6.
    self.c.add_road(Road([2, 5, 3, 5], "road", 0))
    self.c.add_road(Road([1, 4, 2, 5], "road", 0))
    self.c.add_road(Road([1, 4, 2, 3], "road", 0))
    # Give playerA a longest road of 5.
    self.c.add_road(Road([7, 1, 8, 2], "road", 1))
    self.assertEqual(self.c.longest_route_player, 0)
    self.assertEqual(self.c.player_data[0].longest_route, 6)
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    # Break first player's road one road away from the edge, cutting them down to 5.
    self.c.add_piece(catan.Piece(5, 4, "settlement", 2))
    self.assertEqual(self.c.player_data[0].longest_route, 5)
    # They should retain longest route.
    self.assertEqual(self.c.longest_route_player, 0)

  def testBreakRoadButStaysSameLength(self):
    # Give first player a circular road.
    self.c.add_road(Road([3, 5, 4, 6], "road", 0))
    self.c.add_road(Road([4, 6, 5, 6], "road", 0))
    self.c.add_road(Road([5, 6, 6, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    self.assertEqual(self.c.player_data[0].longest_route, 6)
    # Break the circular road in the middle. The road length should stay the same.
    self.c.add_piece(catan.Piece(6, 5, "settlement", 2))
    self.assertEqual(self.c.player_data[0].longest_route, 6)
    self.assertEqual(self.c.longest_route_player, 0)


class TestLargestArmy(BaseInputHandlerTest):

  def testLargestArmy(self):
    self.c._handle_knight(0)
    self.c._handle_knight(0)
    self.assertEqual(self.c.largest_army_player, None)
    self.c._handle_knight(0)
    self.assertEqual(self.c.player_data[0].knights_played, 3)
    self.assertEqual(self.c.largest_army_player, 0)

  def testSurpassLargestArmy(self):
    self.c._handle_knight(0)
    self.c._handle_knight(0)
    self.c._handle_knight(0)
    self.assertEqual(self.c.largest_army_player, 0)
    self.c._handle_knight(1)
    self.c._handle_knight(1)
    self.c._handle_knight(1)
    self.assertEqual(self.c.largest_army_player, 0)
    self.c._handle_knight(1)
    self.assertEqual(self.c.player_data[1].knights_played, 4)
    self.assertEqual(self.c.largest_army_player, 1)


@mock.patch("random.randint", return_value=3.5)
class TestDiscard(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.started = False  # To allow new players to join.
    self.c.handle_join("Player3", {"name": "Player3"})
    self.c.started = True
    for pdata in self.c.player_data:
      pdata.cards.clear()

  def testCalculateDiscardPlayers(self, randint):
    self.c.player_data[0].cards.update({"rsrc1": 4, "rsrc2": 4, "rsrc3": 4, "rsrc5": 4})
    self.c.player_data[1].cards.update({"rsrc1": 4, "rsrc3": 2, "rsrc5": 1, "knight": 5})
    self.c.player_data[2].cards.update({"rsrc1": 2, "rsrc2": 4, "rsrc3": 2, "rsrc5": 1})
    self.c.turn_phase = "dice"
    self.c.handle_roll_dice()
    self.assertEqual(self.c.turn_phase, "discard")
    # Player 0 has 16 cards, and must discard 8.
    # Player 1 does not have to discard because dev cards don't count.
    # Player 2 must discard 9/2 rounded down = 4.
    self.assertListEqual(self.c.discard_players, [8, 0, 4])

    # Player 1 does not need to discard.
    with self.assertRaisesRegex(InvalidMove, "do not need to discard"):
      self.c.handle_discard({"rsrc1": 4}, 1)
    # Player 2 must discard the correct number of cards.
    with self.assertRaisesRegex(InvalidMove, "must discard 4"):
      self.c.handle_discard({"rsrc2": 4, "rsrc5": 1}, 2)
    # Player 0 cannot discard cards they don't have.
    with self.assertRaisesRegex(InvalidMove, "would need"):
      self.c.handle_discard({"rsrc1": 4, "rsrc4": 4}, 0)

    self.assertEqual(self.c.turn_phase, "discard")
    self.c.handle_discard({"rsrc2": 4}, 2)
    self.assertEqual(self.c.turn_phase, "discard")
    self.c.handle_discard({"rsrc1": 4, "rsrc2": 4}, 0)
    self.assertEqual(self.c.turn_phase, "robber")

  def testNobodyDiscards(self, randint):
    self.c.player_data[0].cards.update({"rsrc1": 2, "rsrc2": 2, "rsrc3": 1, "rsrc5": 1})
    self.c.player_data[1].cards.update({"rsrc1": 4, "rsrc3": 2, "rsrc5": 1, "knight": 5})
    self.c.player_data[2].cards.update({"rsrc1": 2, "rsrc2": 0, "rsrc3": 2, "rsrc5": 1})
    self.c.turn_phase = "dice"
    self.c.handle_roll_dice()
    self.assertEqual(self.c.turn_phase, "robber")


class TestBuyDevCard(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.player_data[0].cards.update({"rsrc1": 4, "rsrc3": 4, "rsrc5": 4})
    self.c.player_data[1].cards.update({"rsrc1": 2, "rsrc3": 2, "rsrc5": 1})
    self.c.dev_cards = ["knight", "yearofplenty", "knight"]

  def testBuyNotEnoughResources(self):
    self.c.handle_buy_dev(1)
    with self.assertRaisesRegex(InvalidMove, "need an extra"):
      self.c.handle_buy_dev(1)

  def testBuyNoCardsLeft(self):
    self.c.handle_buy_dev(0)
    self.c.handle_buy_dev(0)
    self.c.handle_buy_dev(0)
    with self.assertRaisesRegex(InvalidMove, "no development cards left"):
      self.c.handle_buy_dev(0)
    self.assertEqual(self.c.player_data[0].cards["knight"], 2)
    self.assertEqual(self.c.player_data[0].cards["yearofplenty"], 1)


class TestUnstartedGame(unittest.TestCase):

  def setUp(self):
    self.c = catan.CatanState()

  def testConnectAndDisconnect(self):
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.disconnect_user("two")
    self.assertDictEqual(self.c.player_sessions, {"one": None, "three": None})

  def testChangeHost(self):
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.assertEqual(self.c.host, "one")
    self.c.disconnect_user("two")
    self.assertEqual(self.c.host, "one")
    self.c.disconnect_user("one")
    self.assertEqual(self.c.host, "three")
    self.c.disconnect_user("three")
    self.assertIsNone(self.c.host)
    self.c.connect_user("four")
    self.assertEqual(self.c.host, "four")

  def testJoinAndLeave(self):
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.handle_join("one", {"name": "player1"})
    self.c.handle_join("two", {"name": "player2"})
    self.c.handle_join("three", {"name": "player3"})
    self.assertDictEqual(self.c.player_sessions, {"one": 0, "two": 1, "three": 2})
    self.assertEqual(self.c.host, "one")
    self.c.disconnect_user("two")
    self.assertDictEqual(self.c.player_sessions, {"one": 0, "three": 2})
    self.c.connect_user("four")
    self.c.handle_join("four", {"name": "player4"})
    self.assertDictEqual(self.c.player_sessions, {"one": 0, "four": 1, "three": 2})
    self.assertEqual(self.c.player_data[1].name, "player4")

  def testStartGame(self):
    self.assertFalse(self.c.started)
    self.assertDictEqual(self.c.tiles, {})
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.connect_user("four")
    with self.assertRaisesRegex(InvalidMove, "at least two players"):
      self.c.handle_start("one", {"scenario": "standard"})

    self.c.handle_join("one", {"name": "player1"})
    self.c.handle_join("two", {"name": "player2"})
    self.c.handle_join("three", {"name": "player3"})
    self.c.handle_join("four", {"name": "player4"})
    with self.assertRaisesRegex(InvalidMove, "not the host"):
      self.c.handle_start("two", {"scenario": "standard"})
    with self.assertRaisesRegex(InvalidMove, "Unknown scenario"):
      self.c.handle_start("one", {"scenario": "nsaoeu"})
    with self.assertRaisesRegex(InvalidMove, "Unknown scenario"):
      self.c.handle_start("one", {})
    self.assertFalse(self.c.started)

    self.c.handle_start("one", {"scenario": "standard"})
    self.assertTrue(self.c.started)
    self.assertIsNone(self.c.host)
    self.assertGreater(len(self.c.tiles.keys()), 0)

    with self.assertRaisesRegex(InvalidMove, "already started"):
      self.c.handle_start("one", {"scenario": "standard"})
    with self.assertRaisesRegex(catan.InvalidPlayer, "already started"):
      self.c.handle_join("one", {"name": "troll"})

  def testDiscardDisconnectedPlayers(self):
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.connect_user("four")
    self.c.connect_user("five")
    self.c.handle_join("one", {"name": "player1"})
    self.c.handle_join("two", {"name": "player2"})
    self.c.handle_join("three", {"name": "player3"})
    self.c.handle_join("four", {"name": "player4"})
    self.c.disconnect_user("one")
    self.c.disconnect_user("three")
    self.c.handle_start(self.c.host, {"scenario": "standard"})

    self.assertTrue(self.c.started)
    self.assertEqual(len(self.c.player_data), 2)
    self.assertDictEqual(self.c.player_sessions, {"two": 0, "four": 1, "five": None})
    self.assertEqual(self.c.discard_players, [0, 0])
    self.assertEqual(self.c.counter_offers, [None, None])


if __name__ == '__main__':
  unittest.main()
