#!/usr/bin/env python3

import collections
import json
import threading
import unittest
from unittest import mock

import catan
import game
import server

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
    g = catan.CatanGame.parse_json(json_data)
    c = g.game
    self.assertIsInstance(c.player_data, list)
    self.assertEqual(len(c.player_data), 1)
    self.assertIsInstance(c.player_data[0].cards, collections.defaultdict)
    self.assertIsInstance(c.player_data[0].trade_ratios, collections.defaultdict)
    # TODO: add some more assertions here

  def testLoadSeafarerState(self):
    with open("ship_test.json") as json_file:
      json_data = json_file.read()
    g = catan.CatanGame.parse_json(json_data)
    c = g.game
    self.assertIsInstance(c, catan.Seafarers)
    self.assertTrue(hasattr(c, "built_this_turn"))
    self.assertTrue(hasattr(c, "ships_moved"))
    self.assertEqual(c.built_this_turn, [(1, 4, 2, 5)])
    self.assertEqual(c.ships_moved, 1)

  def testDumpAndLoad(self):
    c = catan.CatanState()
    c.init_normal()
    g = catan.CatanGame()
    g.game = c
    data = g.json_str()
    d = catan.CatanGame.parse_json(data).game

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

  TEST_FILE = "test.json"
  EXTRA_RULESETS = []

  def setUp(self):
    with open(self.TEST_FILE) as json_file:
      json_data = json.loads(json_file.read())
    if self.EXTRA_RULESETS:
      json_data["rulesets"].extend(self.EXTRA_RULESETS)
    self.g = catan.CatanGame.parse_json(json.dumps(json_data))
    self.c = self.g.game

  def breakpoint(self):
    t = threading.Thread(target=server.ws_main, args=(server.GLOBAL_LOOP,))
    t.start()
    server.GAMES['test'] = game.GameHandler('test', catan.CatanGame)
    server.GAMES['test'].game = self.g
    server.main()
    t.join()


class TestLoadTestData(BaseInputHandlerTest):

  def testSessions(self):
    self.assertIn("Player1", self.g.player_sessions)
    self.assertEqual(self.g.player_sessions["Player1"], 0)

  def testTradeRatios(self):
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc1"], 2)
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc2"], 4)
    self.assertEqual(self.c.player_data[1].trade_ratios["rsrc1"], 4)


class DebugRulesOffTest(BaseInputHandlerTest):

  def testDebugDisabledNormalGame(self):
    self.assertListEqual(self.g.post_urls(), [])

    handler = mock.MagicMock()
    with mock.patch.object(self.c, "distribute_resources") as dist:
      self.g.handle_post(handler, "/roll_dice", {"count": ["5"]}, None)
      self.assertTrue(handler.send_error.called)
      self.assertFalse(dist.called)

class DebugRulesOnTest(BaseInputHandlerTest):

  EXTRA_RULESETS = ["debug"]

  def testDebugEnabledRollDice(self):
    self.assertCountEqual(self.g.post_urls(), ["/roll_dice", "/force_dice"])
    handler = mock.MagicMock()
    with mock.patch.object(self.c, "distribute_resources") as dist:
      self.g.handle_post(handler, "/roll_dice", {"count": ["5"]}, None)
      self.assertFalse(handler.send_error.called)
      self.assertEqual(dist.call_count, 5)

  def testDebugEnabledForceDice(self):
    handler = mock.MagicMock()
    self.g.handle_post(handler, "/force_dice", {"value": ["5"]}, None)
    self.assertFalse(handler.send_error.called)

    self.c.turn_phase = "dice"
    self.c.handle_roll_dice()
    self.assertTupleEqual(self.c.dice_roll, (2, 3))
    for _ in range(4):  # 1 in 1.68 million chance of failing.
      self.c.turn_phase = "dice"
      self.c.handle_roll_dice()
      if self.c.dice_roll != (2, 3):
        break
    else:
      self.fail("Dice roll did not reset")


class TestGetEdgeType(BaseInputHandlerTest):

  TEST_FILE = "sea_test.json"

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_road(Road([1, 4, 2, 5], "road", 0))
    self.c.add_road(Road([1, 6, 2, 5], "ship", 0))
    self.c.add_road(Road([2, 5, 3, 5], "ship", 0))
    self.c.add_tile(catan.Tile(-2, 3, "rsrc5", True, 4))

  def testEdgeTypeUnoccupied(self):
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(0, 4, 1, 4)), "road")
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(5, 6, 6, 5)), "coastup")
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(1, 4, 2, 3)), "coastdown")
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(3, 5, 4, 4)), "ship")
    self.assertIsNone(self.c._get_edge_type(catan.EdgeLocation(0, 8, 1, 8)))

  def testEdgeTypeOccupied(self):
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(1, 4, 2, 5)), "road")
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(2, 5, 3, 5)), "ship")
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(1, 6, 2, 5)), "ship")


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

class testRobberMovement(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.turn_phase = "robber"
    self.c.handle_robber((2, 3), 1)
    self.c.turn_phase = "robber"

  def testRobberInvalidMove(self):
    with self.assertRaises(InvalidMove):
      self.c.handle_robber((-1,-1),1)

  def testRobberInvalidMoveRegex(self):
    with self.assertRaisesRegex(InvalidMove, "Robber would be lost in time and space."):
      self.c.handle_robber((-1,-1),1)

  def testRobberStationaryMove(self):
    with self.assertRaises(InvalidMove):
      self.c.handle_robber(self.c.robber.as_tuple(),1)

  def testRobberStationaryMoveRegex(self):
    with self.assertRaisesRegex(InvalidMove, "You must move the robber."):
      self.c.handle_robber(self.c.robber.as_tuple(),1)

  def testRobberLandMove(self):
    with self.assertRaises(InvalidMove):
      self.c.handle_robber((2,1),1)

  def testRobberLandMoveRegex(self):
    with self.assertRaisesRegex(InvalidMove, "Robbers would drown at sea."):
      self.c.handle_robber((2,1),1)

  def testNoRobbingFromTwoPointsRegex(self):
    self.c.rob_at_two = False
    with self.assertRaisesRegex(InvalidMove, "Robbers refuse to rob such poor people."):
      self.c.handle_robber((2,5),0)

  def testRobbingFromMoreThanTwoPoints(self):
    self.c.rob_at_two = False
    self.c.add_piece(catan.Piece(4,2, "city", 1))
    self.c.handle_robber((2,5),0)

  def testRobbingFromTwoPointsMixedPlayerRegex(self):
    self.c.rob_at_two = False
    self.c.add_piece(catan.Piece(4,2, "city", 1))
    self.c.add_player("green", "Player3")
    self.c.add_piece(catan.Piece(1,6, "city", 3))
    with self.assertRaisesRegex(InvalidMove, "Robbers refuse to rob such poor people."):
      self.c.handle_robber((2,5),0)

  def testNoRobbingFromTwoPointsWithHiddenRegex(self):
    self.c.rob_at_two = False
    self.c.player_data[1].cards.update({"library": 1})
    with self.assertRaisesRegex(InvalidMove, "Robbers refuse to rob such poor people."):
      self.c.handle_robber((2,5),0)

  def testRobbingFromSelfAtTwoPoints(self):
    self.c.rob_at_two = False
    self.c.add_piece(catan.Piece(4,2, "city", 1))
    self.c.handle_robber((4,4),0)

class TestHandleSettleInput(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_road(Road([3, 3, 4, 4], "road", 0))
    self.c.add_road(Road([5, 4, 6, 5], "road", 0))
    self.c.add_road(Road([5, 4, 6, 3], "road", 0))

  def testSettle(self):
    resources = ["rsrc1", "rsrc2", "rsrc3", "rsrc4"]
    counts = [self.c.player_data[0].cards[x] for x in resources]
    self.c.handle(0, {"type": "settle", "location": [3, 3]})
    for rsrc, orig_count in zip(resources, counts):
      self.assertEqual(self.c.player_data[0].cards[rsrc], orig_count - 1)

  def testMustSettleNextToRoad(self):
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle(0, {"type": "settle", "location": [2, 3]})

  def testMustSettleNextToOwnRoad(self):
    self.c.add_road(Road([4, 6, 5, 6], "road", 1))
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle(0, {"type": "settle", "location": [5, 6]})

  def testCannotSettleTooClose(self):
    self.c.add_road(Road([4, 6, 5, 6], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.c.handle(0, {"type": "settle", "location": [6, 3]})
    # Validate both distance from own settlements and from opponents'.
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.c.handle(0, {"type": "settle", "location": [4, 6]})

  def testCannotSettleSettledLocation(self):
    self.c.add_road(Road([3, 5, 4, 4], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle(0, {"type": "settle", "location": [5, 4]})
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle(0, {"type": "settle", "location": [3, 5]})
    # Also validate you cannot build on top of a city.
    self.c.handle_city([3, 5], 1)
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle(0, {"type": "settle", "location": [3, 5]})

  def testMustSettleValidLocation(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple of size 2"):
      self.c.handle(0, {"type": "settle", "location": [2]})

  def testCannotBuildTooManySettlements(self):
    self.c.add_piece(catan.Piece(1, 4, "settlement", 0))
    self.c.add_piece(catan.Piece(1, 6, "settlement", 0))
    self.c.add_piece(catan.Piece(5, 6, "settlement", 0))
    self.c.add_piece(catan.Piece(5, 2, "settlement", 0))
    with self.assertRaisesRegex(InvalidMove, "settlements remaining"):
      self.c.handle(0, {"type": "settle", "location": [3, 3]})

    self.c.pieces[(1, 4)].piece_type = "city"
    self.c.pieces[(1, 6)].piece_type = "city"
    self.c.pieces[(5, 6)].piece_type = "city"
    self.c.pieces[(5, 2)].piece_type = "city"
    with self.assertRaisesRegex(InvalidMove, "cities remaining"):
      self.c.handle(0, {"type": "city", "location": [5, 4]})


def AddThirteenRoads(c):
  c.add_road(Road([5, 4, 6, 3], "road", 0))
  c.add_road(Road([5, 2, 6, 3], "road", 0))
  c.add_road(Road([4, 2, 5, 2], "road", 0))
  c.add_road(Road([3, 3, 4, 2], "road", 0))
  c.add_road(Road([2, 3, 3, 3], "road", 0))
  c.add_road(Road([1, 4, 2, 3], "road", 0))
  c.add_road(Road([1, 4, 2, 5], "road", 0))
  c.add_road(Road([1, 6, 2, 5], "road", 0))
  c.add_road(Road([1, 6, 2, 7], "road", 0))
  c.add_road(Road([2, 7, 3, 7], "road", 0))
  c.add_road(Road([3, 7, 4, 6], "road", 0))
  c.add_road(Road([4, 6, 5, 6], "road", 0))
  c.add_road(Road([5, 6, 6, 5], "road", 0))


class TestHandleRoadInput(BaseInputHandlerTest):

  def testRoadsMustConnect(self):
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle(0, {"type": "road", "location": [2, 3, 3, 3]})

  def testRoadsMustConnectToSelf(self):
    # Validate that roads must connect to your own roads, not opponents'.
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle(0, {"type": "road", "location": [4, 6, 5, 6]})

  def testBuildRoad(self):
    count2 = self.c.player_data[0].cards["rsrc2"]
    count4 = self.c.player_data[0].cards["rsrc4"]
    self.c.handle(0, {"type": "road", "location": [3, 3, 4, 4]})
    # Validate that resources were taken away.
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], count2 - 1)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], count4 - 1)
    # Test both connection to a road and connection to a settlement.
    self.c.handle(0, {"type": "road", "location": [5, 4, 6, 3]})
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], count2 - 2)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], count4 - 2)

  def testCannotBuildTooManyRoads(self):
    AddThirteenRoads(self.c)
    self.c.handle(0, {"type": "road", "location": [5, 4, 6, 5]})
    with self.assertRaisesRegex(InvalidMove, "no roads remaining"):
      self.c.handle(0, {"type": "road", "location": [3, 3, 4, 4]})

  def testCanPlayRoadBuildingWithOneRoadLeft(self):
    AddThirteenRoads(self.c)
    self.c.player_data[0].cards["roadbuilding"] += 1
    self.c.handle(0, {"type": "play_dev", "card_type": "roadbuilding"})
    self.c.handle(0, {"type": "road", "location": [5, 4, 6, 5]})
    self.assertEqual(self.c.turn_phase, "main")

  def testCannotPlayRoadBuildingAtMaxRoads(self):
    AddThirteenRoads(self.c)
    self.c.handle(0, {"type": "road", "location": [5, 4, 6, 5]})
    self.c.player_data[0].cards["roadbuilding"] += 1
    with self.assertRaisesRegex(InvalidMove, "no roads remaining"):
      self.c.handle(0, {"type": "play_dev", "card_type": "roadbuilding"})

  def testCannotBuildWithoutResources(self):
    self.c.player_data[0].cards["rsrc2"] = 0
    with self.assertRaisesRegex(InvalidMove, "need an extra 1 {rsrc2}"):
      self.c.handle(0, {"type": "road", "location": [3, 3, 4, 4]})

  def testRoadLocationMustBeAnEdge(self):
    with self.assertRaisesRegex(InvalidMove, "not a valid edge"):
      self.c.handle(0, {"type": "road", "location": [2, 3, 4, 4]})

  def testRoadLocationMustBeValid(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple"):
      self.c.handle(0, {"type": "road", "location": [1, 3, 4]})
    with self.assertRaisesRegex(AssertionError, "must be left"):
      self.c.handle(0, {"type": "road", "location": [4, 4, 3, 3]})

  def testCannotBuildOnWater(self):
    self.c.add_road(Road([5, 4, 6, 3], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "must be land"):
      self.c.handle(0, {"type": "road", "location": [6, 3, 7, 3]})

  def testCannotBuildAcrossOpponentSettlement(self):
    self.c.add_road(Road([3, 5, 4, 4], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle(0, {"type": "road", "location": [2, 5, 3, 5]})


class TestHandleShipInput(BaseInputHandlerTest):

  TEST_FILE = "sea_test.json"

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_tile(catan.Tile(-2, 5, "space", False, None))
    self.c.add_tile(catan.Tile(-2, 3, "rsrc5", True, 4))

  def testShipsMustConnectToNetwork(self):
    with self.assertRaisesRegex(InvalidMove, "Ships.*must be connected.*ship network"):
      self.c.handle(0, {"type": "ship", "location": [4, 4, 5, 4]})

  def testShipsCannotConnectToRoads(self):
    self.c.add_road(Road([1, 4, 2, 5], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "must be connected.*ship network"):
      self.c.handle(0, {"type": "ship", "location": [1, 4, 2, 3]})
    # Verify that you can build a road in that same spot that you can't build a ship.
    self.c.handle(0, {"type": "road", "location": [1, 4, 2, 3]})

  def testBuildShip(self):
    old_counts = {x: self.c.player_data[0].cards[x] for x in catan.RESOURCES}
    self.c.handle(0, {"type": "ship", "location": [2, 5, 3, 5]})
    new_counts = {x: self.c.player_data[0].cards[x] for x in catan.RESOURCES}
    self.assertEqual(new_counts.pop("rsrc1"), old_counts.pop("rsrc1") - 1)
    self.assertEqual(new_counts.pop("rsrc2"), old_counts.pop("rsrc2") - 1)
    # Validate that no other resources were deducted.
    self.assertDictEqual(new_counts, old_counts)

  def testNotEnoughResources(self):
    self.c.player_data[0].cards.update({"rsrc1": 0, "rsrc2": 1, "rsrc4": 1})
    with self.assertRaisesRegex(InvalidMove, "1 {rsrc1}"):
      self.c.handle(0, {"type": "ship", "location": [2, 5, 3, 5]})

  def testCannotBuildOnLand(self):
    self.c.add_road(Road([1, 6, 2, 5], "ship", 0))
    self.c.add_road(Road([0, 6, 1, 6], "ship", 0))
    self.c.add_road(Road([-1, 5, 0, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "must be water"):
      self.c.handle(0, {"type": "ship", "location": [-1, 5, 0, 4]})

  def testCannotBuildOnRoad(self):
    self.c.add_road(Road([1, 6, 2, 5], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "already a road"):
      self.c.handle(0, {"type": "ship", "location": [1, 6, 2, 5]})

  def testCanStillBuildWithTooManyRoads(self):
    roads = [
        [-3, 4, -2, 3], [-2, 3, -1, 3], [-1, 3, 0, 2], [0, 2, 1, 2], [1, 2, 2, 3],
        [-3, 4, -2, 5], [-2, 5, -1, 5], [-1, 5, 0, 4], [-1, 3, 0, 4], [0, 4, 1, 4], [1, 4, 2, 3],
        [-1, 5, 0, 6], [0, 6, 1, 6], [1, 4, 2, 5], [1, 6, 2, 5],
    ]
    for road in roads:
      self.c.add_road(Road(road, "road", 0))
    self.assertEqual(
        len([x for x in self.c.roads.values() if x.player == 0 and x.road_type == "road"]), 15)
    self.c.handle(0, {"type": "ship", "location": [2, 5, 3, 5]})

  def testRoadBuildingCanBuildShips(self):
    self.c.player_data[0].cards.clear()
    self.c.turn_phase = "dev_road"
    self.c.handle(0, {"type": "ship", "location": [2, 5, 3, 5]})
    self.assertEqual(self.c.turn_phase, "dev_road")
    self.assertEqual(self.c.dev_roads_placed, 1)
    self.c.handle(0, {"type": "ship", "location": [3, 5, 4, 4]})
    self.assertEqual(self.c.turn_phase, "main")

  def testRoadBuildingCanBuildMixed(self):
    self.c.player_data[0].cards.clear()
    self.c.turn_phase = "dev_road"
    self.c.handle(0, {"type": "road", "location": [1, 4, 2, 5]})
    self.assertEqual(self.c.turn_phase, "dev_road")
    self.assertEqual(self.c.dev_roads_placed, 1)
    self.c.handle(0, {"type": "ship", "location": [2, 5, 3, 5]})
    self.assertEqual(self.c.turn_phase, "main")

  def testCanBuildShipInPlacePhase(self):
    self.c.game_phase = "place2"
    self.c.turn_phase = "road"
    self.c.add_piece(catan.Piece(3, 7, "settlement", 0))
    self.c.handle(0, {"type": "ship", "location": [3, 7, 4, 6]})
    self.assertEqual(self.c.game_phase, "main")

  def testCannotBuildTooManyShips(self):
    roads = [
        [1, 4, 2, 5], [1, 6, 2, 5], [1, 6, 2, 7], [2, 7, 3, 7], [3, 7, 4, 6], [3, 5, 4, 6],
        [3, 5, 4, 4], [4, 4, 5, 4], [5, 4, 6, 5], [4, 6, 5, 6], [5, 6, 6, 5],
        [3, 3, 4, 4], [3, 3, 4, 2], [5, 4, 6, 3], [5, 2, 6, 3],
    ]
    for road in roads:
      self.c.add_road(Road(road, "ship", 0))
    self.assertEqual(
        len([x for x in self.c.roads.values() if x.player == 0 and x.road_type == "ship"]), 15)
    with self.assertRaisesRegex(InvalidMove, "no ships remaining"):
      self.c.handle(0, {"type": "ship", "location": [4, 2, 5, 2]})


class TestShipOpenClosedCalculation(BaseInputHandlerTest):

  TEST_FILE = "sea_test.json"

  def testBasicMovable(self):
    road1_loc = (2, 5, 3, 5)
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.assertTrue(self.c.roads[road1_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.assertEqual(self.c.roads[road1_loc].source.as_tuple(), (2, 5))

    road2_loc = (3, 5, 4, 6)
    self.c.add_road(Road(road2_loc, "ship", 0))
    self.assertFalse(self.c.roads[road1_loc].movable)  # Original no longer movable
    self.assertFalse(self.c.roads[road1_loc].closed)  # Should still be open
    self.assertEqual(self.c.roads[road1_loc].source.as_tuple(), (2, 5))
    self.assertTrue(self.c.roads[road2_loc].movable)
    self.assertFalse(self.c.roads[road2_loc].closed)
    self.assertEqual(self.c.roads[road2_loc].source.as_tuple(), (2, 5))

  def testBasicOpenClosed(self):
    road1_loc = (1, 6, 2, 5)
    road2_loc = (1, 6, 2, 7)
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.c.add_road(Road(road2_loc, "ship", 0))
    self.assertFalse(self.c.roads[road1_loc].movable)
    self.assertTrue(self.c.roads[road2_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.assertFalse(self.c.roads[road2_loc].closed)
    self.c.add_piece(catan.Piece(2, 7, "settlement", 0))
    self.assertTrue(self.c.roads[road1_loc].closed)
    self.assertTrue(self.c.roads[road2_loc].closed)
    # We don't assert on movable here - once the shipping path is closed, movable is irrelevant.

  def testCanClosePathFromOtherSide(self):
    # Same test as basic open closed, but put the settlement in first. The ship's source
    # will be the far settlement, but this shouldn't stop the DFS from doing its thing.
    road1_loc = (1, 6, 2, 5)
    road2_loc = (1, 6, 2, 7)
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.c.add_piece(catan.Piece(2, 7, "settlement", 0))
    self.assertTrue(self.c.roads[road1_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.c.add_road(Road(road2_loc, "ship", 0))
    self.assertTrue(self.c.roads[road1_loc].closed)
    self.assertTrue(self.c.roads[road2_loc].closed)

  def testBranchingOpenClosedPaths(self):
    self.c.add_piece(catan.Piece(5, 6, "settlement", 0))
    road1_loc = (2, 5, 3, 5)
    road3_loc = (4, 6, 5, 6)
    road2_loc = (3, 5, 4, 6)
    road4_loc = (3, 7, 4, 6)

    # The setup: two settlements build towards eachother (roads 1 and 3), with a branch going
    # towards a third island.
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.c.add_road(Road(road3_loc, "ship", 0))
    self.assertTrue(self.c.roads[road1_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.assertTrue(self.c.roads[road3_loc].movable)
    self.assertFalse(self.c.roads[road3_loc].closed)
    self.c.add_road(Road(road4_loc, "ship", 0))
    self.assertFalse(self.c.roads[road3_loc].movable)
    self.assertFalse(self.c.roads[road3_loc].closed)

    # The connection: the settlements get connected by another ship (road 2).
    self.c.add_road(Road(road2_loc, "ship", 0))
    self.assertTrue(self.c.roads[road1_loc].closed)
    self.assertTrue(self.c.roads[road2_loc].closed)
    self.assertTrue(self.c.roads[road3_loc].closed)
    self.assertFalse(self.c.roads[road4_loc].closed)
    self.assertTrue(self.c.roads[road4_loc].movable)
    self.assertEqual(self.c.roads[road4_loc].source.as_tuple(), (5, 6))

    # The settlement: after settling the third island, all roads should be closed.
    self.c.add_piece(catan.Piece(3, 7, "settlement", 0))
    self.assertTrue(self.c.roads[road4_loc].closed)

  def testCloseMiddleOfPath(self):
    # We build a shipping route past an island, then settle the island, and validate that the
    # ships on the other side of the route are still open and get updated correctly.
    locs = [(1, 4, 2, 5), (1, 4, 2, 3), (2, 3, 3, 3), (3, 3, 4, 4)]
    for loc in locs[:-1]:
      self.c.add_road(Road(loc, "ship", 0))

    for loc in locs[:-1]:
      with self.subTest(loc=loc):
        self.assertEqual(self.c.roads[loc].source.as_tuple(), (2, 5))

    self.c.add_piece(catan.Piece(2, 3, "settlement", 0))
    for loc in locs[:-1]:
      with self.subTest(loc=loc):
        self.assertEqual(self.c.roads[loc].source.as_tuple(), (2, 5))
    self.assertTrue(self.c.roads[locs[-2]].movable)

    self.c.add_road(Road(locs[-1], "ship", 0))
    self.assertFalse(self.c.roads[locs[-2]].movable)
    self.assertTrue(self.c.roads[locs[-1]].movable)
    self.assertFalse(self.c.roads[locs[-2]].closed)
    self.assertFalse(self.c.roads[locs[-1]].closed)

  def testReturnToOrigin(self):
    road_locs = [
        (2, 5, 3, 5), (3, 5, 4, 6), (3, 7, 4, 6), (2, 7, 3, 7), (1, 6, 2, 7), (1, 6, 2, 5),
    ]
    for loc in road_locs:
      self.c.add_road(Road(loc, "ship", 0))
    for loc in road_locs:
      with self.subTest(loc=loc):
        self.assertFalse(self.c.roads[loc].closed)
    # The first and last ships should be movable.
    self.assertTrue(self.c.roads[road_locs[0]].movable)
    self.assertTrue(self.c.roads[road_locs[-1]].movable)
    # The rest should not.
    for loc in road_locs[1:-1]:
      with self.subTest(loc=loc):
        self.assertFalse(self.c.roads[loc].movable)

    # Just for fun, add a settlement at 3, 7 and make sure all roads are now marked as closed.
    self.c.add_piece(catan.Piece(3, 7, "settlement", 0))
    for loc in road_locs:
      with self.subTest(loc=loc):
        self.assertTrue(self.c.roads[loc].closed)

  def testMakeALoop(self):
    first_loc = (2, 5, 3, 5)
    self.c.add_road(Road(first_loc, "ship", 0))
    road_locs = [
        (3, 5, 4, 4), (4, 4, 5, 4), (5, 4, 6, 5), (3, 5, 4, 6), (4, 6, 5, 6), (5, 6, 6, 5),
    ]
    for loc in road_locs:
      self.c.add_road(Road(loc, "ship", 0))
    for loc in [first_loc] + road_locs:
      with self.subTest(loc=loc):
        self.assertFalse(self.c.roads[loc].closed)

    # The first road is not movable, but everything else is.
    self.assertFalse(self.c.roads[first_loc].movable)
    for loc in road_locs:
      with self.subTest(loc=loc):
        self.assertTrue(self.c.roads[loc].movable)

  def testLoopAndReturnToOrigin(self):
    # Okay, smartypants. You want to make a loop on the water and then also return to your
    # starting point. Because you hate me. The two ships connected to the starting point should
    # be movable, as well as all the ships in the loop, including the ship that connects the
    # far loop to the near loop.
    road_locs = [
        (2, 5, 3, 5),
        (3, 5, 4, 4), (4, 4, 5, 4), (5, 4, 6, 5), (3, 5, 4, 6), (4, 6, 5, 6), (5, 6, 6, 5),
        (3, 7, 4, 6), (2, 7, 3, 7), (1, 6, 2, 7), (1, 6, 2, 5),
    ]

    for loc in road_locs[:-1]:
      self.c.add_road(Road(loc, "ship", 0))

    for loc in road_locs[:-1]:
      with self.subTest(loc=loc):
        self.assertFalse(self.c.roads[loc].closed)

    for loc in road_locs[1:7]:
      with self.subTest(loc=loc):
        self.assertTrue(self.c.roads[loc].movable)
    self.assertFalse(self.c.roads[road_locs[0]].movable)
    self.assertFalse(self.c.roads[road_locs[7]].movable)
    self.assertFalse(self.c.roads[road_locs[8]].movable)
    self.assertTrue(self.c.roads[road_locs[-2]].movable)

    # Here we go - add the last road, returning to the starting point.
    self.c.add_road(Road(road_locs[-1], "ship", 0))

    for loc in road_locs:
      with self.subTest(loc=loc):
        self.assertFalse(self.c.roads[loc].closed)

    for loc in road_locs[:7]:
      with self.subTest(loc=loc):
        self.assertTrue(self.c.roads[loc].movable)
    for loc in road_locs[8:-1]:
      with self.subTest(loc=loc):
        self.assertFalse(self.c.roads[loc].movable)
    self.assertTrue(self.c.roads[road_locs[-1]].movable)

    # As a bonus, use the last four ships to make an extra loop.
    bonus_locs = [(3, 3, 4, 4), (2, 3, 3, 3), (1, 4, 2, 3), (1, 4, 2, 5)]
    for loc in bonus_locs:
      self.c.add_road(Road(loc, "ship", 0))

    for loc in road_locs + bonus_locs:
      with self.subTest(loc=loc):
        self.assertFalse(self.c.roads[loc].closed)

    expected_movable = set(road_locs[:7] + [road_locs[-1]] + [bonus_locs[-1]])
    for loc in road_locs + bonus_locs:
      with self.subTest(loc=loc):
        self.assertEqual(self.c.roads[loc].movable, loc in expected_movable)

    # Lastly, add a settlement on the far island. Since every ship in this triple loop is
    # on some path from one settlement to the other, all ships should be marked as closed.
    self.c.add_piece(catan.Piece(6, 5, "settlement", 0))
    for loc in road_locs + bonus_locs:
      with self.subTest(loc=loc):
        self.assertTrue(self.c.roads[loc].closed)

  def testRecomputeMovableAfterShipMoveToDifferentNetwork(self):
    self.c.add_piece(catan.Piece(6, 5, "settlement", 0))
    self.c.add_piece(catan.Piece(2, 7, "settlement", 0))
    roads = [(1, 6, 2, 5), (5, 4, 6, 5), (4, 4, 5, 4)]
    for road in roads:
      self.c.add_road(Road(road, "ship", 0))
    # Start with one ship attached to 2, 5, and two ships connected to 6, 5.
    for road in roads:
      self.assertFalse(self.c.roads[road].closed)
    self.assertTrue(self.c.roads[roads[0]].movable)
    self.assertTrue(self.c.roads[roads[2]].movable)
    self.assertFalse(self.c.roads[roads[1]].movable)
    self.assertEqual(self.c.roads[roads[0]].source.as_tuple(), (2, 5))
    self.assertEqual(self.c.roads[roads[1]].source.as_tuple(), (6, 5))
    self.assertEqual(self.c.roads[roads[2]].source.as_tuple(), (6, 5))

    # Move the outermost ship to attach to 2, 5. Its source should change. Also,
    # the ship that remains attached to 6, 5 should become movable again.
    new_loc = (0, 6, 1, 6)
    self.c.built_this_turn.clear()
    self.c.handle(0, {"type": "move_ship", "from": roads[2], "to": new_loc})
    self.assertEqual(self.c.roads[new_loc].source.as_tuple(), (2, 5))
    self.assertTrue(self.c.roads[new_loc].movable)
    self.assertFalse(self.c.roads[new_loc].closed)
    self.assertFalse(self.c.roads[roads[0]].movable)
    self.assertFalse(self.c.roads[roads[0]].closed)
    self.assertTrue(self.c.roads[roads[1]].movable)
    self.assertFalse(self.c.roads[roads[1]].closed)

    # Move the other ship attached to 6, 5 to close the connection between 2, 5 and 2, 7.
    # These two ships should become closed, the previously moved ship should remain movable.
    last_loc = (1, 6, 2, 7)
    self.c.ships_moved = 0
    self.c.handle(0, {"type": "move_ship", "from": roads[1], "to": last_loc})
    self.assertIn(self.c.roads[last_loc].source.as_tuple(), [(2, 5), (2, 7)])
    self.assertTrue(self.c.roads[last_loc].closed)
    self.assertTrue(self.c.roads[roads[0]].closed)
    self.assertFalse(self.c.roads[new_loc].closed)
    self.assertTrue(self.c.roads[new_loc].movable)


class TestShipMovement(BaseInputHandlerTest):
  
  TEST_FILE = "sea_test.json"

  def setUp(self):
    super(TestShipMovement, self).setUp()
    self.c.add_road(Road([2, 5, 3, 5], "ship", 0))

  def testMoveShip(self):
    self.c.handle(0, {"type": "move_ship", "from": [2, 5, 3, 5], "to": [1, 4, 2, 5]})

  def testInvalidInput(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple of size 4"):
      self.c.handle(0, {"type": "move_ship", "from": [1, 4, 2, 5], "to": [3, 5, 4]})
    with self.assertRaisesRegex(InvalidMove, "should be a tuple of size 4"):
      self.c.handle(0, {"type": "move_ship", "from": [1, 4, 2, 5, 5], "to": [3, 5, 4, 4]})

  def testMustMoveExistingShip(self):
    with self.assertRaisesRegex(InvalidMove, "do not have a ship"):
      self.c.handle(0, {"type": "move_ship", "from": [1, 4, 2, 5], "to": [3, 5, 4, 4]})

  def testNewLocationMustConnectToNetwork(self):
    self.c.add_road(Road([3, 5, 4, 4], "ship", 0))
    # Extra check: the new location is a location that would be connected to the network
    # if the ship were not moving.
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle(0, {"type": "move_ship", "from": [3, 5, 4, 4], "to": [4, 4, 5, 4]})
    # Check that the old ship is still there.
    self.assertIn((3, 5, 4, 4), self.c.roads)

  def testCannotMoveOnTopOfExistingShip(self):
    self.c.add_road(Road([1, 4, 2, 5], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "already a ship"):
      self.c.handle(0, {"type": "move_ship", "from": [2, 5, 3, 5], "to": [1, 4, 2, 5]})

  def testCannotMoveRoads(self):
    self.c.add_road(Road([1, 4, 2, 5], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "only move ships"):
      self.c.handle(0, {"type": "move_ship", "from": [1, 4, 2, 5], "to": [1, 6, 2, 5]})

  def testCannotMoveOtherPlayersShips(self):
    self.c.add_piece(catan.Piece(6, 5, "settlement", 1))
    self.c.add_road(Road([5, 4, 6, 5], "ship", 1))
    with self.assertRaisesRegex(InvalidMove, "only move your"):
      self.c.handle(0, {"type": "move_ship", "from": [5, 4, 6, 5], "to": [1, 4, 2, 5]})

  def testCannotMoveShipOnClosedRoute(self):
    self.c.add_piece(catan.Piece(2, 7, "settlement", 0))
    self.c.add_road(Road([1, 6, 2, 5], "ship", 0))
    self.c.add_road(Road([1, 6, 2, 7], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "that connects two"):
      self.c.handle(0, {"type": "move_ship", "from": [1, 6, 2, 7], "to": [1, 4, 2, 5]})
    # Validate that moving a different ship here will work.
    self.c.handle(0, {"type": "move_ship", "from": [2, 5, 3, 5], "to": [1, 4, 2, 5]})

  def testMustMoveShipAtEndOfRoute(self):
    self.c.add_road(Road([3, 5, 4, 4], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "at the end"):
      self.c.handle(0, {"type": "move_ship", "from": [2, 5, 3, 5], "to": [1, 4, 2, 5]})
    # Validate that moving a ship at the end of the network will work.
    self.c.handle(0, {"type": "move_ship", "from": [3, 5, 4, 4], "to": [1, 4, 2, 5]})

  def testCannotMoveTwoShipsInOneTurn(self):
    self.c.add_road(Road([3, 5, 4, 4], "ship", 0))
    self.c.handle(0, {"type": "move_ship", "from": [3, 5, 4, 4], "to": [1, 4, 2, 5]})
    with self.assertRaisesRegex(InvalidMove, "already moved a ship"):
      self.c.handle(0, {"type": "move_ship", "from": [2, 5, 3, 5], "to": [1, 6, 2, 5]})

  def testCannotMoveShipBuiltThisTurn(self):
    self.c.handle(0, {"type": "ship", "location": [3, 5, 4, 4]})
    with self.assertRaisesRegex(InvalidMove, "built this turn"):
      self.c.handle(0, {"type": "move_ship", "from": [3, 5, 4, 4], "to": [1, 6, 2, 5]})


class TestShipMovement(BaseInputHandlerTest):
  
  TEST_FILE = "ship_test.json"

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_piece(catan.Piece(6, 5, "settlement", 1))
    p0_roads = [
        (1, 4, 2, 3), (2, 3, 3, 3),
    ]
    p1_roads = [
        (5, 6, 6, 5), (5, 4, 6, 5), (5, 4, 6, 3), (5, 2, 6, 3), (6, 5, 7, 5),
    ]
    for road in p0_roads:
      self.c.add_road(Road(road, "ship", 0))
    for road in p1_roads:
      self.c.add_road(Road(road, "ship", 1))

    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertEqual(self.c.player_data[1].longest_route, 4)
    self.assertIsNone(self.c.longest_route_player)
    self.c.add_road(Road((3, 3, 4, 2), "ship", 0))
    self.assertEqual(self.c.player_data[0].longest_route, 5)
    self.assertEqual(self.c.longest_route_player, 0)
    self.c.ships_moved = 0

  def testCanMoveShipToMakeLongerRoute(self):
    self.c.add_road(Road((4, 2, 5, 2), "ship", 1))
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.assertEqual(self.c.longest_route_player, 0)
    self.c.handle_move_ship([6, 5, 7, 5], [4, 6, 5, 6], 1)
    self.assertEqual(self.c.player_data[1].longest_route, 6)
    self.assertEqual(self.c.longest_route_player, 1)

  def testCanLoseLongestRouteByMovingShip(self):
    self.c.handle_move_ship([1, 6, 2, 5], [3, 3, 4, 4], 0)
    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertIsNone(self.c.longest_route_player)

  def testCanLoseLongestRouteToOtherPlayerByMovingShip(self):
    self.c.add_road(Road((4, 2, 5, 2), "ship", 1))
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.assertEqual(self.c.longest_route_player, 0)

    self.c.handle_move_ship([1, 6, 2, 5], [3, 3, 4, 4], 0)
    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertEqual(self.c.longest_route_player, 1)


class TestCalculateRobPlayers(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_player("green", "Player3")  # New player's index is 2.
    self.c.turn_idx = 2
    self.c.dice_roll = (6, 1)
    self.c.turn_phase = "robber"
    moved_piece = self.c.pieces.pop((3, 5))
    moved_piece.location = catan.CornerLocation(4, 6)
    self.c.add_piece(moved_piece)

  def testRobNoAdjacentPieces(self):
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.handle(2, {"type": "robber", "location": [2, 3]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count)

  def testRobTwoAdjacentPlayers(self):
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.handle(2, {"type": "robber", "location": [4, 4]})
    self.assertEqual(self.c.turn_phase, "rob")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count)

    self.c.handle(2, {"type": "rob", "player": 1})
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count - 1)
    self.assertEqual(p3_new_count, 1)

  def testRobSingleAdjacentPlayer(self):
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.handle(2, {"type": "robber", "location": [4, 2]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count - 1)
    self.assertEqual(p2_new_count, p2_old_count)
    self.assertEqual(p3_new_count, 1)

  def testRobSingleAdjacentPlayerWithoutCards(self):
    self.c.player_data[0].cards.clear()
    self.c.handle(2, {"type": "robber", "location": [4, 2]})
    self.assertEqual(self.c.turn_phase, "main")
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p3_new_count, 0)

  def testRobTwoAdjacentPlayersOneWithoutCards(self):
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.player_data[0].cards.clear()
    self.c.handle(2, {"type": "robber", "location": [4, 4]})
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
    self.c = catan.CatanState.parse_json(json.loads(json_data))
    self.c.add_player("blue", "PlayerA")
    self.c.add_player("green", "PlayerB")
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
    self.c.add_player("green", "Player3")
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
    self.c = catan.CatanGame()

  def testConnectAndDisconnect(self):
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.disconnect_user("two")
    self.assertSetEqual(self.c.connected, {"one", "three"})

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
    self.assertCountEqual(self.c.player_sessions.keys(), ["one", "two", "three"])
    for key in ["one", "two", "three"]:
      self.assertIsInstance(self.c.player_sessions[key], catan.CatanPlayer)
    self.assertEqual(self.c.host, "one")
    self.c.disconnect_user("two")
    self.assertCountEqual(self.c.player_sessions.keys(), ["one", "three"])
    self.c.connect_user("four")
    self.c.handle_join("four", {"name": "player4"})
    self.assertCountEqual(self.c.player_sessions.keys(), ["one", "four", "three"])

  def testStartGame(self):
    self.assertIsNone(self.c.game)
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
    self.assertIsNone(self.c.game)

    self.c.handle_start("one", {"scenario": "standard"})
    self.assertIsNotNone(self.c.game)
    self.assertIsNone(self.c.host)
    self.assertGreater(len(self.c.game.tiles.keys()), 0)

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

    self.assertIsNotNone(self.c.game)
    self.assertEqual(len(self.c.game.player_data), 2)
    self.assertCountEqual(self.c.player_sessions.keys(), ["two", "four"])
    self.assertEqual(self.c.game.player_data[self.c.player_sessions["two"]].name, "player2")
    self.assertEqual(self.c.game.player_data[self.c.player_sessions["four"]].name, "player4")
    self.assertEqual(self.c.game.discard_players, [0, 0])
    self.assertEqual(self.c.game.counter_offers, [None, None])


if __name__ == '__main__':
  unittest.main()
