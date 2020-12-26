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
    state = catan.BeginnerMap()
    state.add_player("red", "player1")
    state.add_player("blue", "player2")
    state.init({})

    self.assertEqual(len(state.tiles), 4 + 5 + 6 + 7 + 6 + 5 + 4, "number of tiles")
    for loc, tile in state.tiles.items():
      self.assertEqual(loc, tile.location.json_repr(), "tiles mapped to location")

  def testRandomized(self):
    state = catan.RandomMap()
    state.add_player("red", "player1")
    state.add_player("blue", "player2")
    state.init({})
    counts = collections.defaultdict(int)
    for card in state.dev_cards:
      counts[card] += 1
    expected = {
        "knight": 14, "monopoly": 2, "yearofplenty": 2, "roadbuilding": 2,
        "chapel": 1, "university": 1, "palace": 1, "library": 1, "market": 1,
    }
    self.assertDictEqual(counts, expected)

  def testInitNumbers(self):
    state = catan.RandomMap()
    state.add_player("red", "player1")
    state.add_player("blue", "player2")
    state.init({})
    # Put the desert in a few different spots to test that it gets skipped properly.
    for desert_spot in [(7, 1), (4, 2), (1, 7), (10, 2), (7, 3), (10, 4), (7, 5)]:
      # Reset the tile numbers to None
      for tile in state.tiles.values():
        tile.number = None
      desert = [(loc, tile) for loc, tile in state.tiles.items() if tile.tile_type == "norsrc"]
      self.assertEqual(len(desert), 1)
      state.tiles[desert[0][0]].tile_type = state.tiles[desert_spot].tile_type
      state.tiles[desert_spot].tile_type = "norsrc"
      state._init_numbers((7, 1), catan.TILE_NUMBERS)
      nums = [tile.number for tile in state.tiles.values() if tile.is_land]
      self.assertCountEqual(nums, catan.TILE_NUMBERS + [None])  # None for the desert.
      self.assertIsNone(state.tiles[desert_spot].number)

  def testInitLarge(self):

    class LargeMap(catan.ExtraPlayers, catan.RandomMap):
      pass

    state = LargeMap()
    state.add_player("red", "player1")
    state.add_player("blue", "player2")
    state.add_player("green", "player3")
    state.add_player("yellow", "player4")
    state.add_player("brown", "player5")
    state.add_player("cyan", "player6")
    state.init({})
    counts = collections.defaultdict(int)
    for card in state.dev_cards:
      counts[card] += 1
    expected = {
        "knight": 20, "monopoly": 3, "yearofplenty": 3, "roadbuilding": 3,
        "chapel": 1, "university": 1, "palace": 1, "library": 1, "market": 1,
    }
    self.assertDictEqual(counts, expected)


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
    self.assertEqual(c.built_this_turn, [(2, 4, 3, 5)])
    self.assertEqual(c.ships_moved, 1)
    self.assertEqual(len(c.roads), 2)
    self.assertEqual(list(c.roads.values())[0].road_type, "ship")
    self.assertIsInstance(list(c.roads.values())[0].source, catan.CornerLocation)

  def testDumpAndLoad(self):
    # TODO: test with different numbers of users
    scenarios = ["Random Map", "The Four Islands", "Through the Desert"]
    for scenario in scenarios:
      with self.subTest(scenario=scenario):
        g = catan.CatanGame()
        g.connect_user("se0")
        g.connect_user("se1")
        g.connect_user("se2")
        g.handle_join("se0", {"name": "player1"})
        g.handle_join("se1", {"name": "player2"})
        g.handle_join("se2", {"name": "player3"})
        g.handle_start("se0", {"options": {"Scenario": "Through the Desert", "5-6 Players": False}})
        c = g.game
        data = g.json_str()
        d = catan.CatanGame.parse_json(data).game

        self.recursiveAssertEqual(c, d, "")

  def recursiveAssertEqual(self, obja, objb, path):
    if not isinstance(obja, catan.CatanState):  # Dynamically generated classes are not equal.
      self.assertEqual(type(obja), type(objb), path)
    if hasattr(obja, "__dict__"):  # Objects
      self.assertCountEqual(obja.__dict__.keys(), objb.__dict__.keys(), path)
      for key in obja.__dict__:
        self.assertIn(key, objb.__dict__, path + f".{key}")
        self.recursiveAssertEqual(getattr(obja, key), getattr(objb, key), path + f".{key}")
      return
    if isinstance(obja, dict):  # Any subclass of dictionary
      self.assertCountEqual(obja.keys(), objb.keys(), path)
      for key in obja:
        self.assertIn(key, objb, path + f"[{key}]")
        self.recursiveAssertEqual(obja[key], objb[key], path + f"[{key}]")
      return
    if isinstance(obja, str):  # Before iterable - str is iterable and produces more strs.
      self.assertEqual(obja, objb, path)
      return
    try:  # Any iterable
      itera = iter(obja)
      iterb = iter(objb)
      for idx, pair in enumerate(zip(itera, iterb)):
        self.recursiveAssertEqual(pair[0], pair[1], path + f"[{idx}]")
      return
    except TypeError:
      pass
    # Primitives
    self.assertEqual(obja, objb, path)


class BreakpointTest(unittest.TestCase):

  def breakpoint(self):
    t = threading.Thread(target=server.ws_main, args=(server.GLOBAL_LOOP,))
    t.start()
    server.GAMES['test'] = game.GameHandler('test', catan.CatanGame)
    server.GAMES['test'].game = self.g
    server.main()
    t.join()


class CornerComputationTest(unittest.TestCase):

  def testIslandCorners(self):
    self.c = catan.SeafarerIslands()
    self.c.load_file("islands3.json")
    self.c._compute_contiguous_islands()
    self.assertIn((3, 1), self.c.corners_to_islands)
    self.assertIn((5, 5), self.c.corners_to_islands)
    self.assertEqual(self.c.corners_to_islands[(3, 1)], self.c.corners_to_islands[(5, 5)])

    self.assertIn((15, 1), self.c.corners_to_islands)
    self.assertIn((12, 4), self.c.corners_to_islands)
    self.assertEqual(self.c.corners_to_islands[(15, 1)], self.c.corners_to_islands[(12, 4)])

    self.assertNotEqual(self.c.corners_to_islands[(3, 1)], self.c.corners_to_islands[(12, 4)])

  def testShoreCorners(self):
    self.c = catan.SeafarerShores()
    self.c.load_file("shores4.json")
    self.c._compute_contiguous_islands()
    self.assertIn((3, 3), self.c.corners_to_islands)
    self.assertIn((14, 8), self.c.corners_to_islands)
    self.assertEqual(self.c.corners_to_islands[(3, 3)], self.c.corners_to_islands[(14, 8)])

    self.assertIn((18, 4), self.c.corners_to_islands)
    self.assertIn((20, 6), self.c.corners_to_islands)
    self.assertEqual(self.c.corners_to_islands[(18, 4)], self.c.corners_to_islands[(20, 6)])

    self.assertIn((14, 10), self.c.corners_to_islands)
    self.assertIn((18, 12), self.c.corners_to_islands)
    self.assertEqual(self.c.corners_to_islands[(14, 10)], self.c.corners_to_islands[(18, 12)])

    # Assert that the island number for each of these corners is unique.
    islands = [self.c.corners_to_islands[loc] for loc in [(3, 3), (20, 6), (14, 10)]]
    self.assertEqual(len(islands), len(set(islands)))

  def testDesertCorners(self):
    self.c = catan.SeafarerDesert()
    self.c.load_file("desert3.json")
    self.c._compute_contiguous_islands()
    self.assertIn((3, 1), self.c.corners_to_islands)
    self.assertIn((14, 6), self.c.corners_to_islands)
    self.assertEqual(self.c.corners_to_islands[(3, 1)], self.c.corners_to_islands[(14, 6)])

    self.assertIn((15, 1), self.c.corners_to_islands)
    self.assertIn((20, 4), self.c.corners_to_islands)
    self.assertEqual(self.c.corners_to_islands[(15, 1)], self.c.corners_to_islands[(20, 4)])

    self.assertIn((3, 9), self.c.corners_to_islands)

    # Assert that the island number for each of these corners is unique.
    islands = [self.c.corners_to_islands[loc] for loc in [(3, 1), (20, 4), (3, 9)]]
    self.assertEqual(len(islands), len(set(islands)))

    # Desert corner that doesn't touch any other land should not have an island number.
    self.assertNotIn((21, 5), self.c.corners_to_islands)


class PlacementRestrictionsTest(unittest.TestCase):

  def testSaveAndLoad(self):
    self.c = catan.SeafarerDesert()
    self.c.add_player("red", "player1")
    self.c.add_player("blue", "player2")
    self.c.add_player("green", "player3")
    self.c.init({})
    self.assertCountEqual(self.c.placement_islands, [(-1, 3)])
    self.g = catan.CatanGame()
    self.g.update_rulesets_and_choices({"Scenario": "The Four Islands", "5-6 Players": False})
    self.g.game = self.c

    dump = self.g.json_str()
    loaded = catan.CatanGame.parse_json(dump)
    game = loaded.game
    self.assertCountEqual(game.placement_islands, [(-1, 3)])

  def testDesert3Placement(self):
    self.c = catan.SeafarerDesert()
    self.c.add_player("red", "player1")
    self.c.add_player("blue", "player2")
    self.c.add_player("green", "player3")
    self.c.init({})
    self.assertCountEqual(self.c.placement_islands, [(-1, 3)])

    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(0, {"type": "settle", "location": [0, 8]})
    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(0, {"type": "settle", "location": [12, 0]})
    self.c.handle(0, {"type": "settle", "location": [3, 3]})

    # We're going to skip a bunch of placements.
    self.c.game_phase = "place2"
    self.c.turn_phase = "settle"
    self.c.turn_idx = 1

    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(1, {"type": "settle", "location": [9, 9]})
    self.c.handle(1, {"type": "settle", "location": [3, 5]})

  def testDesert4Placement(self):
    self.c = catan.SeafarerDesert()
    self.c.add_player("red", "player1")
    self.c.add_player("blue", "player2")
    self.c.add_player("green", "player3")
    self.c.add_player("violet", "player4")
    self.c.init({})
    self.assertCountEqual(self.c.placement_islands, [(-1, 5)])

    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(0, {"type": "settle", "location": [0, 8]})
    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(0, {"type": "settle", "location": [12, 0]})
    self.c.handle(0, {"type": "settle", "location": [3, 3]})

    # We're going to skip a bunch of placements.
    self.c.game_phase = "place2"
    self.c.turn_phase = "settle"
    self.c.turn_idx = 1

    # It should still validate islands in the second placement round.
    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(1, {"type": "settle", "location": [12, 12]})
    self.c.handle(1, {"type": "settle", "location": [12, 8]})

  def testShores3Placement(self):
    self.c = catan.SeafarerShores()
    self.c.add_player("red", "player1")
    self.c.add_player("blue", "player2")
    self.c.add_player("green", "player3")
    self.c.init({})
    self.assertCountEqual(self.c.placement_islands, [(-1, 3)])

    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(0, {"type": "settle", "location": [3, 9]})
    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(0, {"type": "settle", "location": [18, 4]})
    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(0, {"type": "settle", "location": [15, 9]})
    self.c.handle(0, {"type": "settle", "location": [3, 3]})

  def testShores4Placement(self):
    self.c = catan.SeafarerShores()
    self.c.add_player("red", "player1")
    self.c.add_player("blue", "player2")
    self.c.add_player("green", "player3")
    self.c.add_player("violet", "player4")
    self.c.init({})
    self.assertCountEqual(self.c.placement_islands, [(-1, 3)])

    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(0, {"type": "settle", "location": [3, 11]})
    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(0, {"type": "settle", "location": [18, 4]})
    with self.assertRaisesRegex(InvalidMove, "first settlements"):
      self.c.handle(0, {"type": "settle", "location": [17, 11]})
    self.c.handle(0, {"type": "settle", "location": [3, 3]})


class TestIslandCalculations(BreakpointTest):

  def setUp(self):
    self.c = catan.SeafarerIslands()
    self.c.add_player("red", "player1")
    self.c.add_player("blue", "player2")
    self.c.add_player("green", "player3")
    self.c.init({})
    self.c.handle(0, {"type": "settle", "location": [12, 4]})
    self.c.handle(0, {"type": "ship", "location": [11, 3, 12, 4]})
    self.c.handle(1, {"type": "settle", "location": [5, 5]})
    self.c.handle(1, {"type": "ship", "location": [5, 5, 6, 6]})
    self.c.handle(2, {"type": "settle", "location": [8, 8]})
    self.c.handle(2, {"type": "ship", "location": [8, 8, 9, 7]})
    self.c.handle(2, {"type": "settle", "location": [18, 8]})
    self.c.handle(2, {"type": "road", "location": [18, 8, 20, 8]})
    self.c.handle(1, {"type": "settle", "location": [9, 1]})
    self.c.handle(1, {"type": "ship", "location": [9, 1, 11, 1]})
    self.c.game_phase = "main"
    self.c.turn_phase = "main"
    self.c.pirate = None
    self.g = catan.CatanGame()
    self.g.update_rulesets_and_choices({"Scenario": "The Four Islands", "5-6 Players": False})
    self.g.game = self.c

  def testHomeIslands(self):
    self.assertCountEqual(self.c.home_corners[0], [(12, 4)])
    self.assertCountEqual(self.c.home_corners[1], [(5, 5), (9, 1)])
    self.assertCountEqual(self.c.home_corners[2], [(8, 8), (18, 8)])

  def settleForeignIslands(self):
    for rsrc in catan.RESOURCES:
      self.c.player_data[2].cards[rsrc] += 2
    # Player1 settles a foreign island.
    self.c.add_piece(catan.Piece(9, 3, "settlement", 0))
    # Player2 settles two foreign islands.
    self.c.add_piece(catan.Piece(12, 2, "settlement", 1))
    self.c.add_piece(catan.Piece(5, 7, "settlement", 1))
    # Two settlements, but only one is on a foreign island.
    self.c.add_road(Road([8, 6, 9, 7], "ship", 2))
    self.c.add_road(Road([9, 7, 11, 7], "ship", 2))
    self.c.turn_idx = 2
    self.c.handle_settle([8, 6], 2)
    self.c.handle_settle([11, 7], 2)

  def testLandingEventLog(self):
    self.settleForeignIslands()
    self.assertEqual(self.c.event_log[-1].event_type, "settlement")
    self.assertEqual(self.c.event_log[-2].event_type, "landing")
    self.assertEqual(self.c.event_log[-2].public_text, "{player2} settled on a new island")
    self.assertEqual(self.c.event_log[-3].public_text, "{player2} built a settlement")

  def testForeignIslands(self):
    self.settleForeignIslands()
    self.assertCountEqual(self.c.foreign_landings[0], [(9, 3)])
    self.assertCountEqual(self.c.foreign_landings[1], [(12, 2), (5, 7)])
    # An extra settlement on a foreign island changes nothing.
    self.c.add_piece(catan.Piece(2, 8, "settlement", 1))
    self.assertCountEqual(self.c.foreign_landings[1], [(12, 2), (5, 7)])
    self.assertCountEqual(self.c.foreign_landings[2], [(8, 6)])

  def testPlayerPoints(self):
    self.settleForeignIslands()
    self.assertEqual(self.c.player_points(0, True), 4)
    self.assertEqual(self.c.player_points(1, True), 8)
    self.assertEqual(self.c.player_points(2, True), 6)

  def testClientJson(self):
    self.settleForeignIslands()
    data = self.c.for_player(None)
    self.assertIn("landings", data)
    self.assertCountEqual(
        data["landings"], [
          {"player": 0, "location": (9, 3)},
          {"player": 1, "location": (12, 2)},
          {"player": 1, "location": (5, 7)},
          {"player": 2, "location": (8, 6)},
    ])

  def testSaveAndLoad(self):
    self.settleForeignIslands()
    dump = self.g.json_str()
    loaded = catan.CatanGame.parse_json(dump)
    game = loaded.game
    self.assertIsInstance(game.home_corners, collections.defaultdict)
    self.assertIsInstance(game.foreign_landings, collections.defaultdict)
    self.assertCountEqual(game.home_corners[0], [(12, 4)])
    self.assertCountEqual(game.home_corners[1], [(5, 5), (9, 1)])
    self.assertCountEqual(game.home_corners[2], [(8, 8), (18, 8)])
    self.assertCountEqual(self.c.foreign_landings[0], [(9, 3)])
    self.assertCountEqual(self.c.foreign_landings[1], [(12, 2), (5, 7)])
    self.assertCountEqual(self.c.foreign_landings[2], [(8, 6)])


class BaseInputHandlerTest(BreakpointTest):

  TEST_FILE = "test.json"
  EXTRA_RULES = []

  def setUp(self):
    with open(self.TEST_FILE) as json_file:
      json_data = json.loads(json_file.read())
    if self.EXTRA_RULES:
      json_data["rules"].extend(self.EXTRA_RULES)
    self.g = catan.CatanGame.parse_json(json.dumps(json_data))
    self.c = self.g.game


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

  EXTRA_RULES = ["Debug"]

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
    self.c._add_road(Road([2, 4, 3, 5], "road", 0))
    self.c._add_road(Road([2, 6, 3, 5], "ship", 0))
    self.c._add_road(Road([3, 5, 5, 5], "ship", 0))
    self.c.add_tile(catan.Tile(-2, 4, "rsrc5", True, 4))

  def testEdgeTypeUnoccupied(self):
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(0, 4, 2, 4)), "road")
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(8, 6, 9, 5)), "coastup")
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(2, 4, 3, 3)), "coastdown")
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(5, 5, 6, 4)), "ship")
    self.assertIsNone(self.c._get_edge_type(catan.EdgeLocation(0, 8, 2, 8)))

  def testEdgeTypeOccupied(self):
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(2, 4, 3, 5)), "road")
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(3, 5, 5, 5)), "ship")
    self.assertEqual(self.c._get_edge_type(catan.EdgeLocation(2, 6, 3, 5)), "ship")


class TestDistributeResources(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_piece(catan.Piece(5, 3, "city", 0))
    self.c.pieces[(5, 5)].piece_type = "city"
    for rsrc in ["rsrc3", "rsrc4", "rsrc5"]:
      self.c.player_data[0].cards[rsrc] = 8
      self.c.player_data[1].cards[rsrc] = 9
    self.c.player_data[0].cards["rsrc1"] = 0
    self.c.player_data[1].cards["rsrc1"] = 0

  def testRemainingResourceCount(self):
    self.assertEqual(self.c.remaining_resources("rsrc1"), 19)
    self.assertEqual(self.c.remaining_resources("rsrc3"), 2)

  def testTooManyResources(self):
    self.c.distribute_resources(self.c.calculate_resource_distribution((2, 3)))
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], 8)
    self.assertEqual(self.c.player_data[1].cards["rsrc4"], 9)

    self.c.distribute_resources(self.c.calculate_resource_distribution((3, 3)))
    self.assertEqual(self.c.player_data[0].cards["rsrc5"], 8)
    self.assertEqual(self.c.player_data[1].cards["rsrc5"], 9)

  def testTooManyResourcesOnlyOnePlayer(self):
    self.c.distribute_resources(self.c.calculate_resource_distribution((4, 5)))
    self.assertEqual(self.c.player_data[0].cards["rsrc3"], 10)
    self.assertEqual(self.c.player_data[1].cards["rsrc3"], 9)
    self.assertEqual(self.c.player_data[1].cards["rsrc1"], 2)


class TestDevCards(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    for card in catan.PLAYABLE_DEV_CARDS:
      self.c.player_data[0].cards[card] = 1
    for p in self.c.player_data:
      p.cards["rsrc1"] = 0

  def testYearOfPlenty(self):
    self.c.player_data[0].cards["rsrc1"] = 3
    self.c.handle_play_dev("yearofplenty", {"rsrc1": 2}, 0)
    self.assertEqual(self.c.player_data[0].cards["rsrc1"], 5)

  def testYearOfPlentyDepletedResource(self):
    self.c.player_data[1].cards["rsrc1"] = 19
    with self.assertRaisesRegex(InvalidMove, "not enough {rsrc1} in the bank"):
      self.c.handle_play_dev("yearofplenty", {"rsrc1": 1, "rsrc2": 1}, 0)
    self.c.handle_play_dev("yearofplenty", {"rsrc2": 2}, 0)

  def testYearOfPlentyMostlyDepletedResource(self):
    self.c.player_data[1].cards["rsrc1"] = 18
    with self.assertRaisesRegex(InvalidMove, "not enough {rsrc1} in the bank"):
      self.c.handle_play_dev("yearofplenty", {"rsrc1": 2}, 0)
    self.c.handle_play_dev("yearofplenty", {"rsrc1": 1, "rsrc2": 1}, 0)

  def testYearOfPlentyEmptyBank(self):
    for rsrc in catan.RESOURCES:
      self.c.player_data[1].cards[rsrc] = 19
      self.c.player_data[0].cards[rsrc] = 0
    # There are no cards left in the bank.
    with self.assertRaisesRegex(InvalidMove, "no resources left"):
      self.c.handle_play_dev("yearofplenty", {"rsrc1": 2}, 0)
    self.c.player_data[1].cards["rsrc1"] -= 1
    # There is only one card left in the bank. You cannot draw two cards.
    with self.assertRaisesRegex(InvalidMove, "no resources left"):
      self.c.handle_play_dev("yearofplenty", {"rsrc1": 2}, 0)

  def testMonopoly(self):
    self.c.player_data[0].cards["rsrc1"] = 2
    self.c.player_data[0].cards["rsrc2"] = 0
    self.c.player_data[1].cards["rsrc1"] = 3
    self.c.player_data[1].cards["rsrc2"] = 3
    self.c.handle_play_dev("monopoly", {"rsrc1": 1}, 0)
    # Should receive all rsrc1 cards from the other player.
    self.assertEqual(self.c.player_data[0].cards["rsrc1"], 5)
    self.assertEqual(self.c.player_data[1].cards["rsrc1"], 0)
    # Other resources should remain untouched.
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], 0)
    self.assertEqual(self.c.player_data[1].cards["rsrc2"], 3)

  def testMonopolyInvalidSelection(self):
    with self.assertRaisesRegex(InvalidMove, "exactly one resource"):
      self.c.handle_play_dev("monopoly", {"rsrc2": 1, "rsrc1": 1}, 0)
    with self.assertRaisesRegex(InvalidMove, "Invalid resource selection"):
      self.c.handle_play_dev("monopoly", {}, 0)
    with self.assertRaisesRegex(InvalidMove, "exactly one resource"):
      self.c.handle_play_dev("monopoly", {"rsrc2": 2}, 0)
    with self.assertRaisesRegex(InvalidMove, "exactly one resource"):
      self.c.handle_play_dev("monopoly", {"rsrc1": 1, "rsrc2": 2}, 0)


class TestCollectResources(BaseInputHandlerTest):

  TEST_FILE = "sea_test.json"
  EXTRA_RULES = ["Debug"]

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_player("green", "Bob")
    self.c.add_piece(catan.Piece(0, 4, "city", 1))
    self.c.add_piece(catan.Piece(0, 6, "city", 2))
    self.c.tiles[(1, 3)].tile_type = "anyrsrc"
    self.c.tiles[(1, 5)].tile_type = "anyrsrc"
    self.c.add_piece(catan.Piece(3, 7, "city", 1))
    self.c.add_piece(catan.Piece(6, 8, "city", 2))
    self.c.tiles[(4, 8)].number = 5
    self.c.add_piece(catan.Piece(9, 5, "settlement", 0))
    self.c.tiles[(10, 6)].number = 9
    for p in self.c.player_data:
      p.cards.clear()
      p.cards["rsrc3"] = 4

  def testSimpleCollection(self):
    self.c.turn_phase = "dice"
    self.c.next_die_roll = 9
    self.c.handle_roll_dice()
    self.assertIn("rolled a 9", self.c.event_log[-2].public_text)
    self.assertIn("{player0} received 1 {rsrc4}", self.c.event_log[-1].public_text)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], 1)
    self.assertEqual(self.c.player_data[1].cards["rsrc4"], 0)
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {1: 2})
    # With only 2 resources being collected, no need to go in order.
    self.assertIsNone(self.c.collect_idx)
    # Player 1 cannot collect; they don't have any bonus tiles on a 9.
    with self.assertRaisesRegex(catan.NotYourTurn, "not eligible"):
      self.c.handle(0, {"type": "collect", "selection": {"rsrc3": 1}})
    # Player 2 should be able to collect even when it is not their turn.
    self.c.handle(1, {"type": "collect", "selection": {"rsrc3": 2}})
    self.assertIn("collected 2 {rsrc3}", self.c.event_log[-1].public_text)

  def testCollectDepletedResource(self):
    self.c.player_data[0].cards["rsrc3"] = 10
    self.c.turn_phase = "dice"
    self.c.next_die_roll = 9
    self.c.handle_roll_dice()
    self.assertEqual(self.c.remaining_resources("rsrc3"), 1)
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {1: 2})
    with self.assertRaisesRegex(InvalidMove, "not enough {rsrc3} in the bank"):
      self.c.handle(1, {"type": "collect", "selection": {"rsrc3": 2}})
    self.c.handle(1, {"type": "collect", "selection": {"rsrc1": 1, "rsrc3": 1}})

  def testCollectScarcityForcesOrder(self):
    self.c.turn_phase = "dice"
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    self.assertEqual(self.c.remaining_resources("rsrc3"), 3)
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {0: 1, 1: 2, 2: 2})
    # Players will collect 5 resources, but only 3 rsrc3 remain. They must take turns.
    # It is Player1's turn, so they should collect first.
    self.assertEqual(self.c.collect_idx, 0)
    with self.assertRaisesRegex(catan.NotYourTurn, "Another player.*before you"):
      self.c.handle(1, {"type": "collect", "selection": {"rsrc3": 2}})
    self.c.handle(0, {"type": "collect", "selection": {"rsrc3": 1}})
    self.assertEqual(self.c.player_data[0].cards["rsrc3"], 5)
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {1: 2, 2: 2})
    self.assertEqual(self.c.collect_idx, 1)

  def testCollectAbundanceUnordered(self):
    for p in self.c.player_data:
      p.cards["rsrc3"] = 3
    # With more cards available than can be claimed, there should not be a player order.
    self.c.turn_phase = "dice"
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    self.assertEqual(self.c.remaining_resources("rsrc3"), 6)
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {0: 1, 1: 2, 2: 2})
    # Players will collect 5 resources, minimum 6 remain. They do not have to take turns.
    self.assertIsNone(self.c.collect_idx)

  def testCollectScarcityDisappears(self):
    self.c.turn_idx = 2
    self.c.turn_phase = "dice"
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {0: 1, 1: 2, 2: 2})
    self.assertEqual(self.c.remaining_resources("rsrc3"), 3)
    # Minimum 3 resources remain, but players will collect a total of 5. They must take turns.
    # Since it is currently player3's turn, they collect first.
    self.assertEqual(self.c.collect_idx, 2)
    self.c.handle(2, {"type": "collect", "selection": {"rsrc1": 2}})
    # The minimum resources available is still 3, but now only 3 resources remain to be collected.
    # The rest of the players may collect in any order.
    self.assertDictEqual(self.c.collect_counts, {0: 1, 1: 2})
    self.assertEqual(self.c.remaining_resources("rsrc3"), 3)
    self.assertIsNone(self.c.collect_idx)

  def testResourceShortage(self):
    for p in self.c.player_data:
      p.cards["rsrc3"] = 6
    self.c.turn_phase = "dice"
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    self.assertIn("rolled a 5", self.c.event_log[-2].public_text)
    self.assertIn("shortage of {rsrc3}", self.c.event_log[-1].public_text)
    # Not enough resources means a shortage; this resource cannot be collected.
    self.assertEqual(self.c.remaining_resources("rsrc3"), 1)
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {0: 1, 1: 2, 2: 2})
    self.assertEqual(self.c.shortage_resources, ["rsrc3"])
    # Only 1 of rsrc3 remains, but it's on the shortage list. Since it is not collectible, there
    # is enough of every other resource to go around, and players do not have to go in order.
    self.assertIsNone(self.c.collect_idx)
    # Assert that you cannot collect resources that suffered a shortage.
    with self.assertRaisesRegex(InvalidMove, "shortage"):
      self.c.handle(0, {"type": "collect", "selection": {"rsrc3": 1}})
    self.c.handle(0, {"type": "collect", "selection": {"rsrc1": 1}})
    self.assertEqual(self.c.turn_phase, "collect")
    # Even after one player collects, other players still cannot collect shortage resources.
    with self.assertRaisesRegex(InvalidMove, "shortage"):
      self.c.handle(2, {"type": "collect", "selection": {"rsrc3": 2}})
    self.c.handle(2, {"type": "collect", "selection": {"rsrc4": 2}})
    self.c.handle(1, {"type": "collect", "selection": {"rsrc2": 2}})
    # After everyone collects, it should be back to the original player's turn.
    self.assertEqual(self.c.turn_phase, "main")

  def testNoRemainingResources(self):
    for idx, p in enumerate(self.c.player_data):
      for rsrc in catan.RESOURCES:
        p.cards[rsrc] = 6
        if idx == 0:
          p.cards[rsrc] += 1
    for rsrc in catan.RESOURCES:
      with self.subTest(rsrc=rsrc):
        self.assertEqual(self.c.remaining_resources(rsrc), 0)
    self.c.turn_phase = "dice"
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    # If there are no cards left, we have to skip collection.
    self.assertDictEqual(self.c.collect_counts, {})
    self.assertIsNone(self.c.collect_idx)
    self.assertEqual(self.c.turn_phase, "main")

  def testNoRemainingResourcesAfterDistribution(self):
    for idx, p in enumerate(self.c.player_data):
      for rsrc in catan.RESOURCES:
        p.cards[rsrc] = 6
        if idx == 0:
          p.cards[rsrc] += 1
    self.c.player_data[0].cards["rsrc3"] -= 4
    # There are exactly four rsrc3 remaining. After the initial distribution (where players 2 and
    # 3 will receive the remaining 4), nobody should be able to collect from the bonus tiles.
    self.assertEqual(self.c.remaining_resources("rsrc3"), 4)
    self.c.turn_phase = "dice"
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    self.assertDictEqual(self.c.collect_counts, {})
    self.assertIsNone(self.c.collect_idx)
    self.assertEqual(self.c.turn_phase, "main")

  def testCollectionConsumesAllResources(self):
    for idx, p in enumerate(self.c.player_data):
      for rsrc in catan.RESOURCES:
        p.cards[rsrc] = 6
        if idx == 0:
          p.cards[rsrc] += 1
    self.c.player_data[0].cards["rsrc1"] -= 2
    # There are exactly two rsrc1 remaining (and nothing else). Player 1 will collect one of them.
    self.assertEqual(self.c.remaining_resources("rsrc1"), 2)
    self.c.turn_phase = "dice"
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    self.assertDictEqual(self.c.collect_counts, {0: 1, 1: 2, 2: 2})
    self.assertEqual(self.c.collect_idx, 0)
    self.c.handle(0, {"type": "collect", "selection": {"rsrc1": 1}})
    # There is exactly 1 rsrc1 remaining. Player 2 (next player) should have their count updated.
    # Player 3's count is not updated yet - that will happen after player 2 collects.
    self.assertDictEqual(self.c.collect_counts, {1: 1, 2: 2})
    with self.assertRaisesRegex(InvalidMove, "not enough {rsrc2} in the bank"):
      self.c.handle(1, {"type": "collect", "selection": {"rsrc2": 1}})
    self.c.handle(1, {"type": "collect", "selection": {"rsrc1": 1}})
    # Now that the bank is empty, player 3's collection is skipped.
    self.assertDictEqual(self.c.collect_counts, {})
    self.assertIsNone(self.c.collect_idx)
    self.assertEqual(self.c.turn_phase, "main")


class TestRobberMovement(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.turn_phase = "robber"
    self.c.handle_robber((4, 4), 1)
    self.c.turn_phase = "robber"

  def testRobberInvalidMove(self):
    with self.assertRaises(InvalidMove):
      self.c.handle_robber((0, 0), 1)

  def testRobberInvalidMoveRegex(self):
    with self.assertRaisesRegex(InvalidMove, "valid land tile"):
      self.c.handle_robber((0, 0), 1)

  def testRobberStationaryMove(self):
    with self.assertRaises(InvalidMove):
      self.c.handle_robber(self.c.robber.as_tuple(), 1)

  def testRobberStationaryMoveRegex(self):
    with self.assertRaisesRegex(InvalidMove, "You must move the robber."):
      self.c.handle_robber(self.c.robber.as_tuple(), 1)

  def testRobberLandMove(self):
    with self.assertRaises(InvalidMove):
      self.c.handle_robber((4, 2), 1)

  def testRobberLandMoveRegex(self):
    with self.assertRaisesRegex(InvalidMove, "valid land tile"):
      self.c.handle_robber((4, 2), 1)

  def testNoRobbingFromTwoPointsRegex(self):
    self.c.rob_at_two = False
    with self.assertRaisesRegex(InvalidMove, "Robbers refuse to rob such poor people."):
      self.c.handle_robber((4, 6), 0)

  def testRobbingFromMoreThanTwoPoints(self):
    self.c.rob_at_two = False
    self.c.add_piece(catan.Piece(6, 2, "city", 1))
    self.c.handle_robber((4, 6), 0)
    self.assertEqual(self.c.event_log[-2].event_type, "robber")
    self.assertEqual(self.c.event_log[-1].event_type, "rob")
    self.assertIn("stole a card", self.c.event_log[-1].public_text)
    self.assertNotIn("stole a card", self.c.event_log[-1].secret_text)
    self.assertCountEqual(self.c.event_log[-1].visible_players, [0, 1])

  def testRobbingFromTwoPointsMixedPlayerRegex(self):
    self.c.rob_at_two = False
    self.c.add_piece(catan.Piece(6, 2, "city", 1))
    self.c.add_player("green", "Player3")
    self.c.add_piece(catan.Piece(2, 6, "city", 2))
    with self.assertRaisesRegex(InvalidMove, "Robbers refuse to rob such poor people."):
      self.c.handle_robber((4, 6), 0)

  def testNoRobbingFromTwoPointsWithHiddenRegex(self):
    self.c.rob_at_two = False
    self.c.player_data[1].cards.update({"library": 1})
    with self.assertRaisesRegex(InvalidMove, "Robbers refuse to rob such poor people."):
      self.c.handle_robber((4, 6), 0)

  def testRobbingFromSelfAtTwoPoints(self):
    self.c.rob_at_two = False
    self.c.add_piece(catan.Piece(6, 2, "city", 1))
    self.c.handle_robber((7, 5), 0)


class TestPiratePlacement(BaseInputHandlerTest):

  TEST_FILE = "ship_test.json"

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_piece(catan.Piece(5, 7, "settlement", 1))
    self.c.add_piece(catan.Piece(8, 6, "settlement", 1))
    self.c.add_road(Road([6, 6, 8, 6], "ship", 1))
    self.c.pirate = catan.TileLocation(4, 4)
    self.c.ships_moved = 0
    self.c.built_this_turn.clear()
    self.c.player_data[0].cards["rsrc1"] += 5
    self.c.player_data[0].cards["rsrc2"] += 5

  def testBuildNearPirate(self):
    old_count = sum([self.c.player_data[0].cards[x] for x in catan.RESOURCES])
    with self.assertRaisesRegex(InvalidMove, "next to the pirate"):
      self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_count = sum([self.c.player_data[0].cards[x] for x in catan.RESOURCES])
    self.assertEqual(old_count, new_count)
    self.c.handle_road([5, 5, 6, 6], 1, "ship", [])

  def testBuildRoadNearPirate(self):
    self.c.roads[(2, 4, 3, 5)].road_type = "road"
    self.c.handle_road([2, 4, 3, 3], 0, "road", [])

  def testMoveToPirate(self):
    with self.assertRaisesRegex(InvalidMove, "next to the pirate"):
      self.c.handle_move_ship([2, 6, 3, 5], [3, 5, 5, 5], 0)

  def testMoveAwayFromPirate(self):
    with self.assertRaisesRegex(InvalidMove, "next to the pirate"):
      self.c.handle_move_ship([2, 4, 3, 5], [3, 5, 5, 5], 0)

  def testMovePirate(self):
    self.c.add_player("green", "Bob")
    self.c.turn_idx = 2
    self.c.turn_phase = "robber"
    old_count = sum([self.c.player_data[0].cards[x] for x in catan.RESOURCES])
    self.c.handle_pirate(2, [4, 6])
    new_count = sum([self.c.player_data[0].cards[x] for x in catan.RESOURCES])
    self.assertEqual(new_count, old_count - 1)
    self.assertEqual(self.c.turn_phase, "main")

  def testMovePirateRobTwoPlayers(self):
    self.c.add_player("green", "Bob")
    self.c.turn_idx = 2
    self.c.turn_phase = "robber"
    self.c._add_road(Road([3, 7, 5, 7], "ship", 1))
    self.c.handle_pirate(2, [4, 6])
    self.assertEqual(self.c.event_log[-1].public_text, "{player2} moved the pirate")
    self.assertEqual(self.c.turn_phase, "rob")
    self.assertCountEqual(self.c.rob_players, [0, 1])

  def testPirateDoesNotRobRoads(self):
    self.c.add_player("green", "Bob")
    self.c.turn_idx = 2
    self.c.turn_phase = "robber"
    self.c._add_road(Road([3, 7, 5, 7], "road", 1))
    self.c.handle_pirate(2, [4, 6])
    self.assertEqual(self.c.turn_phase, "main")
    self.assertEqual(self.c.event_log[-1].public_text, "{player2} stole a card from {player0}")


class TestHandleSettleInput(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c._add_road(Road([5, 3, 6, 4], "road", 0))
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    self.c._add_road(Road([8, 4, 9, 3], "road", 0))

  def testSettle(self):
    resources = ["rsrc1", "rsrc2", "rsrc3", "rsrc4"]
    counts = [self.c.player_data[0].cards[x] for x in resources]
    self.c.handle(0, {"type": "settle", "location": [5, 3]})
    for rsrc, orig_count in zip(resources, counts):
      self.assertEqual(self.c.player_data[0].cards[rsrc], orig_count - 1)
    self.assertEqual(self.c.event_log[-1].event_type, "settlement")
    self.assertIn("built a settlement", self.c.event_log[-1].public_text)

  def testMustSettleNextToRoad(self):
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle(0, {"type": "settle", "location": [3, 3]})

  def testMustSettleNextToOwnRoad(self):
    self.c._add_road(Road([6, 6, 8, 6], "road", 1))
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle(0, {"type": "settle", "location": [8, 6]})

  def testCannotSettleTooClose(self):
    self.c._add_road(Road([6, 6, 8, 6], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.c.handle(0, {"type": "settle", "location": [9, 3]})
    # Validate both distance from own settlements and from opponents'.
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.c.handle(0, {"type": "settle", "location": [6, 6]})

  def testCannotSettleSettledLocation(self):
    self.c._add_road(Road([5, 5, 6, 4], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle(0, {"type": "settle", "location": [8, 4]})
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle(0, {"type": "settle", "location": [5, 5]})
    # Also validate you cannot build on top of a city.
    self.c.handle_city([5, 5], 1)
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.c.handle(0, {"type": "settle", "location": [5, 5]})

  def testMustSettleValidLocation(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple of size 2"):
      self.c.handle(0, {"type": "settle", "location": [2]})

  def testCannotBuildTooManySettlements(self):
    self.c.add_piece(catan.Piece(2, 4, "settlement", 0))
    self.c.add_piece(catan.Piece(2, 6, "settlement", 0))
    self.c.add_piece(catan.Piece(8, 6, "settlement", 0))
    self.c.add_piece(catan.Piece(8, 2, "settlement", 0))
    with self.assertRaisesRegex(InvalidMove, "settlements remaining"):
      self.c.handle(0, {"type": "settle", "location": [5, 3]})

    self.c.pieces[(2, 4)].piece_type = "city"
    self.c.pieces[(2, 6)].piece_type = "city"
    self.c.pieces[(8, 6)].piece_type = "city"
    self.c.pieces[(8, 2)].piece_type = "city"
    with self.assertRaisesRegex(InvalidMove, "cities remaining"):
      self.c.handle(0, {"type": "city", "location": [8, 4]})


def AddThirteenRoads(c):
  c._add_road(Road([8, 4, 9, 3], "road", 0))
  c._add_road(Road([8, 2, 9, 3], "road", 0))
  c._add_road(Road([6, 2, 8, 2], "road", 0))
  c._add_road(Road([5, 3, 6, 2], "road", 0))
  c._add_road(Road([3, 3, 5, 3], "road", 0))
  c._add_road(Road([2, 4, 3, 3], "road", 0))
  c._add_road(Road([2, 4, 3, 5], "road", 0))
  c._add_road(Road([2, 6, 3, 5], "road", 0))
  c._add_road(Road([2, 6, 3, 7], "road", 0))
  c._add_road(Road([3, 7, 5, 7], "road", 0))
  c._add_road(Road([5, 7, 6, 6], "road", 0))
  c._add_road(Road([6, 6, 8, 6], "road", 0))
  c._add_road(Road([8, 6, 9, 5], "road", 0))


class TestHandleRoadInput(BaseInputHandlerTest):

  def testRoadsMustConnect(self):
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle(0, {"type": "road", "location": [3, 3, 5, 3]})

  def testRoadsMustConnectToSelf(self):
    # Validate that roads must connect to your own roads, not opponents'.
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle(0, {"type": "road", "location": [6, 6, 8, 6]})

  def testBuildRoad(self):
    count2 = self.c.player_data[0].cards["rsrc2"]
    count4 = self.c.player_data[0].cards["rsrc4"]
    self.c.handle(0, {"type": "road", "location": [5, 3, 6, 4]})
    # Validate that resources were taken away.
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], count2 - 1)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], count4 - 1)
    # Test both connection to a road and connection to a settlement.
    self.c.handle(0, {"type": "road", "location": [8, 4, 9, 3]})
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], count2 - 2)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], count4 - 2)
    self.assertEqual(self.c.event_log[-1].event_type, "road")
    self.assertIn("built a road", self.c.event_log[-1].public_text)

  def testCannotBuildTooManyRoads(self):
    AddThirteenRoads(self.c)
    self.c.handle(0, {"type": "road", "location": [8, 4, 9, 5]})
    with self.assertRaisesRegex(InvalidMove, "no roads remaining"):
      self.c.handle(0, {"type": "road", "location": [5, 3, 6, 4]})

  def testCanPlayRoadBuildingWithOneRoadLeft(self):
    AddThirteenRoads(self.c)
    self.c.player_data[0].cards["roadbuilding"] += 1
    self.c.handle(0, {"type": "play_dev", "card_type": "roadbuilding"})
    self.c.handle(0, {"type": "road", "location": [8, 4, 9, 5]})
    self.assertEqual(self.c.turn_phase, "main")

  def testCannotPlayRoadBuildingAtMaxRoads(self):
    AddThirteenRoads(self.c)
    self.c.handle(0, {"type": "road", "location": [8, 4, 9, 5]})
    self.c.player_data[0].cards["roadbuilding"] += 1
    with self.assertRaisesRegex(InvalidMove, "no roads remaining"):
      self.c.handle(0, {"type": "play_dev", "card_type": "roadbuilding"})

  def testCannotBuildWithoutResources(self):
    self.c.player_data[0].cards["rsrc2"] = 0
    with self.assertRaisesRegex(InvalidMove, "need an extra 1 {rsrc2}"):
      self.c.handle(0, {"type": "road", "location": [5, 3, 6, 4]})

  def testRoadLocationMustBeAnEdge(self):
    with self.assertRaisesRegex(InvalidMove, "not a valid edge"):
      self.c.handle(0, {"type": "road", "location": [3, 3, 6, 4]})

  def testRoadLocationMustBeValid(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple"):
      self.c.handle(0, {"type": "road", "location": [2, 3, 4]})
    with self.assertRaisesRegex(AssertionError, "must be left"):
      self.c.handle(0, {"type": "road", "location": [6, 4, 5, 3]})

  def testCannotBuildOnWater(self):
    self.c._add_road(Road([8, 4, 9, 3], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "must be land"):
      self.c.handle(0, {"type": "road", "location": [9, 3, 11, 3]})

  def testCannotBuildAcrossOpponentSettlement(self):
    self.c._add_road(Road([5, 5, 6, 4], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle(0, {"type": "road", "location": [3, 5, 5, 5]})


class TestHandleShipInput(BaseInputHandlerTest):

  TEST_FILE = "sea_test.json"

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_tile(catan.Tile(-2, 6, "space", False, None))
    self.c.add_tile(catan.Tile(-2, 4, "rsrc5", True, 4))

  def testShipsMustConnectToNetwork(self):
    with self.assertRaisesRegex(InvalidMove, "Ships.*must be connected.*ship network"):
      self.c.handle(0, {"type": "ship", "location": [6, 4, 8, 4]})

  def testShipsCannotConnectToRoads(self):
    self.c._add_road(Road([2, 4, 3, 5], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "must be connected.*ship network"):
      self.c.handle(0, {"type": "ship", "location": [2, 4, 3, 3]})
    # Verify that you can build a road in that same spot that you can't build a ship.
    self.c.handle(0, {"type": "road", "location": [2, 4, 3, 3]})

  def testBuildShip(self):
    old_counts = {x: self.c.player_data[0].cards[x] for x in catan.RESOURCES}
    self.c.handle(0, {"type": "ship", "location": [3, 5, 5, 5]})
    new_counts = {x: self.c.player_data[0].cards[x] for x in catan.RESOURCES}
    self.assertEqual(new_counts.pop("rsrc1"), old_counts.pop("rsrc1") - 1)
    self.assertEqual(new_counts.pop("rsrc2"), old_counts.pop("rsrc2") - 1)
    # Validate that no other resources were deducted.
    self.assertDictEqual(new_counts, old_counts)

  def testNotEnoughResources(self):
    self.c.player_data[0].cards.update({"rsrc1": 0, "rsrc2": 1, "rsrc4": 1})
    with self.assertRaisesRegex(InvalidMove, "1 {rsrc1}"):
      self.c.handle(0, {"type": "ship", "location": [3, 5, 5, 5]})

  def testCannotBuildOnLand(self):
    self.c._add_road(Road([2, 6, 3, 5], "ship", 0))
    self.c._add_road(Road([0, 6, 2, 6], "ship", 0))
    self.c._add_road(Road([-1, 5, 0, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "must be water"):
      self.c.handle(0, {"type": "ship", "location": [-1, 5, 0, 4]})

  def testCannotBuildOnRoad(self):
    self.c._add_road(Road([2, 6, 3, 5], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "already a road"):
      self.c.handle(0, {"type": "ship", "location": [2, 6, 3, 5]})

  def testCanStillBuildWithTooManyRoads(self):
    roads = [
        [-4, 4, -3, 3], [-3, 3, -1, 3], [-1, 3, 0, 2], [0, 2, 2, 2], [2, 2, 3, 3],
        [-4, 4, -3, 5], [-3, 5, -1, 5], [-1, 5, 0, 4], [-1, 3, 0, 4], [0, 4, 2, 4], [2, 4, 3, 3],
        [-1, 5, 0, 6], [0, 6, 2, 6], [2, 4, 3, 5], [2, 6, 3, 5],
    ]
    for road in roads:
      self.c._add_road(Road(road, "road", 0))
    self.assertEqual(
        len([x for x in self.c.roads.values() if x.player == 0 and x.road_type == "road"]), 15)
    self.c.handle(0, {"type": "ship", "location": [3, 5, 5, 5]})

  def testRoadBuildingCanBuildShips(self):
    self.c.player_data[0].cards.clear()
    self.c.turn_phase = "dev_road"
    self.c.handle(0, {"type": "ship", "location": [3, 5, 5, 5]})
    self.assertEqual(self.c.turn_phase, "dev_road")
    self.assertEqual(self.c.dev_roads_placed, 1)
    self.c.handle(0, {"type": "ship", "location": [5, 5, 6, 4]})
    self.assertEqual(self.c.turn_phase, "main")

  def testRoadBuildingCanBuildMixed(self):
    self.c.player_data[0].cards.clear()
    self.c.turn_phase = "dev_road"
    self.c.handle(0, {"type": "road", "location": [2, 4, 3, 5]})
    self.assertEqual(self.c.turn_phase, "dev_road")
    self.assertEqual(self.c.dev_roads_placed, 1)
    self.c.handle(0, {"type": "ship", "location": [3, 5, 5, 5]})
    self.assertEqual(self.c.turn_phase, "main")

  def testCanBuildShipInPlacePhase(self):
    self.c.game_phase = "place2"
    self.c.turn_phase = "road"
    self.c.add_piece(catan.Piece(5, 7, "settlement", 0))
    self.c.handle(0, {"type": "ship", "location": [5, 7, 6, 6]})
    self.assertEqual(self.c.game_phase, "main")

  def testCannotBuildTooManyShips(self):
    roads = [
        [2, 4, 3, 5], [2, 6, 3, 5], [2, 6, 3, 7], [3, 7, 5, 7], [5, 7, 6, 6], [5, 5, 6, 6],
        [5, 5, 6, 4], [6, 4, 8, 4], [8, 4, 9, 5], [6, 6, 8, 6], [8, 6, 9, 5],
        [5, 3, 6, 4], [5, 3, 6, 2], [8, 4, 9, 3], [8, 2, 9, 3],
    ]
    for road in roads:
      self.c._add_road(Road(road, "ship", 0))
    self.assertEqual(
        len([x for x in self.c.roads.values() if x.player == 0 and x.road_type == "ship"]), 15)
    with self.assertRaisesRegex(InvalidMove, "no ships remaining"):
      self.c.handle(0, {"type": "ship", "location": [6, 2, 8, 2]})


class TestShipOpenClosedCalculation(BaseInputHandlerTest):

  TEST_FILE = "sea_test.json"

  def testBasicMovable(self):
    road1_loc = (3, 5, 5, 5)
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.assertTrue(self.c.roads[road1_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.assertEqual(self.c.roads[road1_loc].source.as_tuple(), (3, 5))

    road2_loc = (5, 5, 6, 6)
    self.c.add_road(Road(road2_loc, "ship", 0))
    self.assertFalse(self.c.roads[road1_loc].movable)  # Original no longer movable
    self.assertFalse(self.c.roads[road1_loc].closed)  # Should still be open
    self.assertEqual(self.c.roads[road1_loc].source.as_tuple(), (3, 5))
    self.assertTrue(self.c.roads[road2_loc].movable)
    self.assertFalse(self.c.roads[road2_loc].closed)
    self.assertEqual(self.c.roads[road2_loc].source.as_tuple(), (3, 5))

  def testBasicOpenClosed(self):
    road1_loc = (2, 6, 3, 5)
    road2_loc = (2, 6, 3, 7)
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.c.add_road(Road(road2_loc, "ship", 0))
    self.assertFalse(self.c.roads[road1_loc].movable)
    self.assertTrue(self.c.roads[road2_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.assertFalse(self.c.roads[road2_loc].closed)
    self.c.add_piece(catan.Piece(3, 7, "settlement", 0))
    self.assertTrue(self.c.roads[road1_loc].closed)
    self.assertTrue(self.c.roads[road2_loc].closed)
    # We don't assert on movable here - once the shipping path is closed, movable is irrelevant.

  def testCanClosePathFromOtherSide(self):
    # Same test as basic open closed, but put the settlement in first. The ship's source
    # will be the far settlement, but this shouldn't stop the DFS from doing its thing.
    road1_loc = (2, 6, 3, 5)
    road2_loc = (2, 6, 3, 7)
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.c.add_piece(catan.Piece(3, 7, "settlement", 0))
    self.assertTrue(self.c.roads[road1_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.c.add_road(Road(road2_loc, "ship", 0))
    self.assertTrue(self.c.roads[road1_loc].closed)
    self.assertTrue(self.c.roads[road2_loc].closed)

  def testDontConsiderOtherPlayersShips(self):
    # Test that movable does not consider other players' ships or settlements.
    road1_loc = (2, 6, 3, 5)
    road2_loc = (2, 6, 3, 7)
    self.c.add_piece(catan.Piece(3, 7, "settlement", 1))
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.assertTrue(self.c.roads[road1_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.c.add_road(Road(road2_loc, "ship", 1))
    self.assertTrue(self.c.roads[road1_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.assertTrue(self.c.roads[road2_loc].movable)
    self.assertFalse(self.c.roads[road2_loc].closed)

  def testBranchingOpenClosedPaths(self):
    self.c.add_piece(catan.Piece(8, 6, "settlement", 0))
    road1_loc = (3, 5, 5, 5)
    road3_loc = (6, 6, 8, 6)
    road2_loc = (5, 5, 6, 6)
    road4_loc = (5, 7, 6, 6)

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
    self.assertEqual(self.c.roads[road4_loc].source.as_tuple(), (8, 6))

    # The settlement: after settling the third island, all roads should be closed.
    self.c.add_piece(catan.Piece(5, 7, "settlement", 0))
    self.assertTrue(self.c.roads[road4_loc].closed)

  def testCloseMiddleOfPath(self):
    # We build a shipping route past an island, then settle the island, and validate that the
    # ships on the other side of the route are still open and get updated correctly.
    locs = [(2, 4, 3, 5), (2, 4, 3, 3), (3, 3, 5, 3), (5, 3, 6, 4)]
    for loc in locs[:-1]:
      self.c.add_road(Road(loc, "ship", 0))

    for loc in locs[:-1]:
      with self.subTest(loc=loc):
        self.assertEqual(self.c.roads[loc].source.as_tuple(), (3, 5))

    self.c.add_piece(catan.Piece(3, 3, "settlement", 0))
    for loc in locs[:-1]:
      with self.subTest(loc=loc):
        self.assertEqual(self.c.roads[loc].source.as_tuple(), (3, 5))
    self.assertTrue(self.c.roads[locs[-2]].movable)

    self.c.add_road(Road(locs[-1], "ship", 0))
    self.assertFalse(self.c.roads[locs[-2]].movable)
    self.assertTrue(self.c.roads[locs[-1]].movable)
    self.assertFalse(self.c.roads[locs[-2]].closed)
    self.assertFalse(self.c.roads[locs[-1]].closed)

  def testReturnToOrigin(self):
    road_locs = [
        (3, 5, 5, 5), (5, 5, 6, 6), (5, 7, 6, 6), (3, 7, 5, 7), (2, 6, 3, 7), (2, 6, 3, 5),
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

    # Just for fun, add a settlement at 5, 7 and make sure all roads are now marked as closed.
    self.c.add_piece(catan.Piece(5, 7, "settlement", 0))
    for loc in road_locs:
      with self.subTest(loc=loc):
        self.assertTrue(self.c.roads[loc].closed)

  def testMakeALoop(self):
    first_loc = (3, 5, 5, 5)
    self.c.add_road(Road(first_loc, "ship", 0))
    road_locs = [
        (5, 5, 6, 4), (6, 4, 8, 4), (8, 4, 9, 5), (5, 5, 6, 6), (6, 6, 8, 6), (8, 6, 9, 5),
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
        (3, 5, 5, 5),
        (5, 5, 6, 4), (6, 4, 8, 4), (8, 4, 9, 5), (5, 5, 6, 6), (6, 6, 8, 6), (8, 6, 9, 5),
        (5, 7, 6, 6), (3, 7, 5, 7), (2, 6, 3, 7), (2, 6, 3, 5),
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
    bonus_locs = [(5, 3, 6, 4), (3, 3, 5, 3), (2, 4, 3, 3), (2, 4, 3, 5)]
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
    self.c.add_piece(catan.Piece(9, 5, "settlement", 0))
    for loc in road_locs + bonus_locs:
      with self.subTest(loc=loc):
        self.assertTrue(self.c.roads[loc].closed)

  def testRecomputeMovableAfterShipMoveToDifferentNetwork(self):
    self.c.add_piece(catan.Piece(9, 5, "settlement", 0))
    self.c.add_piece(catan.Piece(3, 7, "settlement", 0))
    roads = [(2, 6, 3, 5), (8, 4, 9, 5), (6, 4, 8, 4)]
    for road in roads:
      self.c.add_road(Road(road, "ship", 0))
    # Start with one ship attached to 3, 5, and two ships connected to 9, 5.
    for road in roads:
      self.assertFalse(self.c.roads[road].closed)
    self.assertTrue(self.c.roads[roads[0]].movable)
    self.assertTrue(self.c.roads[roads[2]].movable)
    self.assertFalse(self.c.roads[roads[1]].movable)
    self.assertEqual(self.c.roads[roads[0]].source.as_tuple(), (3, 5))
    self.assertEqual(self.c.roads[roads[1]].source.as_tuple(), (9, 5))
    self.assertEqual(self.c.roads[roads[2]].source.as_tuple(), (9, 5))

    # Move the outermost ship to attach to 3, 5. Its source should change. Also,
    # the ship that remains attached to 9, 5 should become movable again.
    new_loc = (0, 6, 2, 6)
    self.c.built_this_turn.clear()
    self.c.handle(0, {"type": "move_ship", "from": roads[2], "to": new_loc})
    self.assertEqual(self.c.roads[new_loc].source.as_tuple(), (3, 5))
    self.assertTrue(self.c.roads[new_loc].movable)
    self.assertFalse(self.c.roads[new_loc].closed)
    self.assertFalse(self.c.roads[roads[0]].movable)
    self.assertFalse(self.c.roads[roads[0]].closed)
    self.assertTrue(self.c.roads[roads[1]].movable)
    self.assertFalse(self.c.roads[roads[1]].closed)

    # Move the other ship attached to 9, 5 to close the connection between 3, 5 and 3, 7.
    # These two ships should become closed, the previously moved ship should remain movable.
    last_loc = (2, 6, 3, 7)
    self.c.ships_moved = 0
    self.c.handle(0, {"type": "move_ship", "from": roads[1], "to": last_loc})
    self.assertIn(self.c.roads[last_loc].source.as_tuple(), [(3, 5), (3, 7)])
    self.assertTrue(self.c.roads[last_loc].closed)
    self.assertTrue(self.c.roads[roads[0]].closed)
    self.assertFalse(self.c.roads[new_loc].closed)
    self.assertTrue(self.c.roads[new_loc].movable)


class TestShipMovement(BaseInputHandlerTest):
  
  TEST_FILE = "sea_test.json"

  def setUp(self):
    super(TestShipMovement, self).setUp()
    self.c.add_road(Road([3, 5, 5, 5], "ship", 0))

  def testMoveShip(self):
    self.c.handle(0, {"type": "move_ship", "from": [3, 5, 5, 5], "to": [2, 4, 3, 5]})
    self.assertEqual(self.c.event_log[-1].event_type, "move_ship")

  def testInvalidInput(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple of size 4"):
      self.c.handle(0, {"type": "move_ship", "from": [2, 4, 3, 5], "to": [5, 5, 4]})
    with self.assertRaisesRegex(InvalidMove, "should be a tuple of size 4"):
      self.c.handle(0, {"type": "move_ship", "from": [2, 4, 3, 5, 5], "to": [5, 5, 6, 4]})

  def testMustMoveExistingShip(self):
    with self.assertRaisesRegex(InvalidMove, "do not have a ship"):
      self.c.handle(0, {"type": "move_ship", "from": [2, 4, 3, 5], "to": [5, 5, 6, 4]})

  def testNewLocationMustConnectToNetwork(self):
    self.c.add_road(Road([5, 5, 6, 4], "ship", 0))
    # Extra check: the new location is a location that would be connected to the network
    # if the ship were not moving.
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.c.handle(0, {"type": "move_ship", "from": [5, 5, 6, 4], "to": [6, 4, 8, 4]})
    # Check that the old ship is still there.
    self.assertIn((5, 5, 6, 4), self.c.roads)

  def testCannotMoveOnTopOfExistingShip(self):
    self.c.add_road(Road([2, 4, 3, 5], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "already a ship"):
      self.c.handle(0, {"type": "move_ship", "from": [3, 5, 5, 5], "to": [2, 4, 3, 5]})

  def testCannotMoveRoads(self):
    self.c.add_road(Road([2, 4, 3, 5], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "only move ships"):
      self.c.handle(0, {"type": "move_ship", "from": [2, 4, 3, 5], "to": [2, 6, 3, 5]})

  def testCannotMoveOtherPlayersShips(self):
    self.c.add_piece(catan.Piece(9, 5, "settlement", 1))
    self.c.add_road(Road([8, 4, 9, 5], "ship", 1))
    with self.assertRaisesRegex(InvalidMove, "only move your"):
      self.c.handle(0, {"type": "move_ship", "from": [8, 4, 9, 5], "to": [2, 4, 3, 5]})

  def testCannotMoveShipOnClosedRoute(self):
    self.c.add_piece(catan.Piece(3, 7, "settlement", 0))
    self.c.add_road(Road([2, 6, 3, 5], "ship", 0))
    self.c.add_road(Road([2, 6, 3, 7], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "that connects two"):
      self.c.handle(0, {"type": "move_ship", "from": [2, 6, 3, 7], "to": [2, 4, 3, 5]})
    # Validate that moving a different ship here will work.
    self.c.handle(0, {"type": "move_ship", "from": [3, 5, 5, 5], "to": [2, 4, 3, 5]})

  def testMustMoveShipAtEndOfRoute(self):
    self.c.add_road(Road([5, 5, 6, 4], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "at the end"):
      self.c.handle(0, {"type": "move_ship", "from": [3, 5, 5, 5], "to": [2, 4, 3, 5]})
    # Validate that moving a ship at the end of the network will work.
    self.c.handle(0, {"type": "move_ship", "from": [5, 5, 6, 4], "to": [2, 4, 3, 5]})

  def testCannotMoveTwoShipsInOneTurn(self):
    self.c.add_road(Road([5, 5, 6, 4], "ship", 0))
    self.c.handle(0, {"type": "move_ship", "from": [5, 5, 6, 4], "to": [2, 4, 3, 5]})
    with self.assertRaisesRegex(InvalidMove, "already moved a ship"):
      self.c.handle(0, {"type": "move_ship", "from": [3, 5, 5, 5], "to": [2, 6, 3, 5]})

  def testCannotMoveShipBuiltThisTurn(self):
    self.c.handle(0, {"type": "ship", "location": [5, 5, 6, 4]})
    with self.assertRaisesRegex(InvalidMove, "built this turn"):
      self.c.handle(0, {"type": "move_ship", "from": [5, 5, 6, 4], "to": [2, 6, 3, 5]})


class TestShipMovement(BaseInputHandlerTest):
  
  TEST_FILE = "ship_test.json"

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_piece(catan.Piece(9, 5, "settlement", 1))
    p0_roads = [
        (2, 4, 3, 3), (3, 3, 5, 3),
    ]
    p1_roads = [
        (8, 6, 9, 5), (8, 4, 9, 5), (8, 4, 9, 3), (8, 2, 9, 3), (9, 5, 11, 5),
    ]
    for road in p0_roads:
      self.c.add_road(Road(road, "ship", 0))
    for road in p1_roads:
      self.c.add_road(Road(road, "ship", 1))

    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertEqual(self.c.player_data[1].longest_route, 4)
    self.assertIsNone(self.c.longest_route_player)
    self.c.add_road(Road((5, 3, 6, 2), "ship", 0))
    self.assertEqual(self.c.player_data[0].longest_route, 5)
    self.assertEqual(self.c.longest_route_player, 0)
    self.c.ships_moved = 0

  def testCanMoveShipToMakeLongerRoute(self):
    self.c.add_road(Road((6, 2, 8, 2), "ship", 1))
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.assertEqual(self.c.longest_route_player, 0)
    self.c.handle_move_ship([9, 5, 11, 5], [6, 6, 8, 6], 1)
    self.assertEqual(self.c.player_data[1].longest_route, 6)
    self.assertEqual(self.c.longest_route_player, 1)

  def testCanLoseLongestRouteByMovingShip(self):
    self.c.handle_move_ship([2, 6, 3, 5], [5, 3, 6, 4], 0)
    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertIsNone(self.c.longest_route_player)

  def testCanLoseLongestRouteToOtherPlayerByMovingShip(self):
    self.c.add_road(Road((6, 2, 8, 2), "ship", 1))
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.assertEqual(self.c.longest_route_player, 0)

    self.c.handle_move_ship([2, 6, 3, 5], [5, 3, 6, 4], 0)
    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertEqual(self.c.longest_route_player, 1)


class TestCalculateRobPlayers(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_player("green", "Player3")  # New player's index is 2.
    self.c.turn_idx = 2
    self.c.dice_roll = (6, 1)
    self.c.turn_phase = "robber"
    moved_piece = self.c.pieces.pop((5, 5))
    moved_piece.location = catan.CornerLocation(6, 6)
    self.c.add_piece(moved_piece)
    # Give these players some dev cards to make sure we don't rob dev cards.
    self.c.player_data[0].cards["knight"] = 10
    self.c.player_data[1].cards["knight"] = 10

  def testRobNoAdjacentPieces(self):
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.handle(2, {"type": "robber", "location": [4, 4]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count)

  def testRobTwoAdjacentPlayers(self):
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.handle(2, {"type": "robber", "location": [7, 5]})
    self.assertEqual(self.c.turn_phase, "rob")
    self.assertCountEqual(self.c.rob_players, [0, 1])
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
    self.c.handle(2, {"type": "robber", "location": [7, 3]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count - 1)
    self.assertEqual(p2_new_count, p2_old_count)
    self.assertEqual(p3_new_count, 1)

  def testRobSingleAdjacentPlayerWithoutCards(self):
    self.c.player_data[0].cards.clear()
    self.c.handle(2, {"type": "robber", "location": [7, 3]})
    self.assertEqual(self.c.turn_phase, "main")
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p3_new_count, 0)

  def testRobTwoAdjacentPlayersOneWithoutCards(self):
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.player_data[0].cards.clear()
    self.c.handle(2, {"type": "robber", "location": [7, 5]})
    self.assertEqual(self.c.turn_phase, "main")
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p2_new_count, p2_old_count - 1)
    self.assertEqual(p3_new_count, 1)

  def testRobSelf(self):
    self.c.add_piece(catan.Piece(6, 4, "settlement", 2))
    self.c.player_data[2].cards["rsrc3"] = 1
    p3_old_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.c.handle(2, {"type": "robber", "location": [4, 4]})
    self.assertEqual(self.c.turn_phase, "main")
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p3_old_count, p3_new_count)

  def testRobSelfAndOneMore(self):
    self.c.add_piece(catan.Piece(6, 4, "settlement", 2))
    self.c.player_data[2].cards["rsrc3"] = 1
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.handle(2, {"type": "robber", "location": [7, 3]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count - 1)
    self.assertEqual(p2_new_count, p2_old_count)
    self.assertEqual(p3_new_count, 2)

  def testRobSelfAndTwoMore(self):
    self.c.add_piece(catan.Piece(6, 4, "settlement", 2))
    self.c.player_data[2].cards["rsrc3"] = 1
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    self.c.handle(2, {"type": "robber", "location": [7, 5]})
    self.assertEqual(self.c.turn_phase, "rob")
    self.assertCountEqual(self.c.rob_players, [0, 1])
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in catan.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in catan.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in catan.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count)
    self.assertEqual(p3_new_count, 1)


class TestLongestRouteCalculation(BaseInputHandlerTest):

  def setUp(self):
    BaseInputHandlerTest.setUp(self)

  def testSingleRoad(self):
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 4), set([]), None)
    self.assertEqual(val, 1)

  def testTwoRoads(self):
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 4), set([]), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, catan.CornerLocation(9, 5), set([]), None)
    self.assertEqual(val, 2)
    # Starting from the middle should give a length of 1.
    val = self.c._dfs_depth(0, catan.CornerLocation(8, 4), set([]), None)
    self.assertEqual(val, 1)

  def testThreeRoads(self):
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    self.c._add_road(Road([8, 4, 9, 3], "road", 0))
    # Starting on any end of the network should still get you 2.
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 4), set([]), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, catan.CornerLocation(9, 5), set([]), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, catan.CornerLocation(9, 3), set([]), None)
    self.assertEqual(val, 2)
    # Starting from the middle should give a length of 1.
    val = self.c._dfs_depth(0, catan.CornerLocation(8, 4), set([]), None)
    self.assertEqual(val, 1)

  def testRoadInterruption(self):
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    self.c._add_road(Road([8, 6, 9, 5], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 4), set([]), None)
    self.assertEqual(val, 3)
    val = self.c._dfs_depth(0, catan.CornerLocation(8, 6), set([]), None)
    self.assertEqual(val, 3)
    # Add a piece for the other player to interrupt the road.
    self.c.add_piece(catan.Piece(9, 5, "settlement", 1))
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 4), set([]), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, catan.CornerLocation(8, 6), set([]), None)
    self.assertEqual(val, 1)

  def testSandwichedRoad(self):
    # Test that you can still start a road at someone else's settlement.
    self.c.add_piece(catan.Piece(8, 6, "settlement", 1))
    self.c._add_road(Road([5, 5, 6, 4], "road", 0))
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    self.c._add_road(Road([8, 6, 9, 5], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 4), set([]), None)
    self.assertEqual(val, 3)
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 5), set([]), None)
    self.assertEqual(val, 4)
    val = self.c._dfs_depth(0, catan.CornerLocation(8, 6), set([]), None)
    self.assertEqual(val, 4)

  def testCircularRoad(self):
    self.c._add_road(Road([5, 3, 6, 4], "road", 0))
    self.c._add_road(Road([5, 3, 6, 2], "road", 0))
    self.c._add_road(Road([6, 2, 8, 2], "road", 0))
    self.c._add_road(Road([8, 2, 9, 3], "road", 0))
    self.c._add_road(Road([8, 4, 9, 3], "road", 0))

    # Start by testing a simple loop.
    for corner in [(5, 3), (6, 4), (8, 4), (9, 3), (8, 2), (6, 2)]:
      val = self.c._dfs_depth(0, catan.CornerLocation(*corner), set([]), None)
      self.assertEqual(val, 6, "loop length for corner %s" % (corner,))

    # Add two tips onto the end of the loop. Length from either end should be 7.
    self.c._add_road(Road([3, 3, 5, 3], "road", 0))
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(3, 3), set([]), None)
    self.assertEqual(val, 7, "enter and loop around")
    val = self.c._dfs_depth(0, catan.CornerLocation(9, 5), set([]), None)
    self.assertEqual(val, 7, "enter and loop around")

    # Make the road longer without using the loop than with the loop.
    self.c._add_road(Road([2, 4, 3, 3], "road", 0))
    self.c._add_road(Road([2, 4, 3, 5], "road", 0))
    self.c._add_road(Road([8, 6, 9, 5], "road", 0))
    self.c._add_road(Road([6, 6, 8, 6], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 6), set([]), None)
    self.assertEqual(val, 10, "take long route around loop")
    val = self.c._dfs_depth(0, catan.CornerLocation(3, 5), set([]), None)
    self.assertEqual(val, 10, "take long route around loop")

  def testPortConnection(self):
    # Start with 2 ships and 4 roads, but no connection between them.
    self.c._add_road(Road([5, 3, 6, 4], "road", 0))
    self.c._add_road(Road([5, 3, 6, 2], "ship", 0))
    self.c._add_road(Road([6, 2, 8, 2], "ship", 0))
    self.c._add_road(Road([8, 2, 9, 3], "road", 0))
    self.c._add_road(Road([8, 4, 9, 3], "road", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 3), set([]), None)
    self.assertEqual(val, 4, "no road -> ship connection")
    val = self.c._dfs_depth(0, catan.CornerLocation(8, 2), set([]), None)
    self.assertEqual(val, 4, "no road -> ship connection")
    val = self.c._dfs_depth(0, catan.CornerLocation(6, 2), set([]), None)
    self.assertEqual(val, 1, "single ship length in either direction")
    val = self.c._dfs_depth(0, catan.CornerLocation(8, 4), set([]), None)
    self.assertEqual(val, 2, "two roads in either direction")

    # Add a connector piece.
    self.c.add_piece(catan.Piece(5, 3, "settlement", 0))
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 3), set([]), None)
    self.assertEqual(val, 4, "still cannot go road->ship in the middle")
    val = self.c._dfs_depth(0, catan.CornerLocation(8, 2), set([]), None)
    self.assertEqual(val, 6, "but can go road->ship through a port")

    # Make sure somebody else's settlement doesn't count.
    self.c.pieces[(5, 3)].player = 1
    val = self.c._dfs_depth(0, catan.CornerLocation(5, 3), set([]), None)
    self.assertEqual(val, 4, "cannot go through someone else's port")
    val = self.c._dfs_depth(0, catan.CornerLocation(8, 2), set([]), None)
    self.assertEqual(val, 4, "cannot go through someone else's port")


class TestLongestRouteAssignment(BreakpointTest):

  def setUp(self):
    # Be sure to call add_road on the last road for each player to recalculate longest road.
    with open("beginner.json") as json_file:
      json_data = json_file.read()
    self.c = catan.CatanState.parse_json(json.loads(json_data))
    self.c.add_player("blue", "PlayerA")
    self.c.add_player("green", "PlayerB")
    self.c._add_road(Road([6, 4, 8, 4], "road", 0))
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    self.c.add_road(Road([11, 5, 12, 6], "road", 0))
    self.c._add_road(Road([5, 3, 6, 2], "road", 1))
    self.c._add_road(Road([6, 2, 8, 2], "road", 1))
    self.c._add_road(Road([8, 2, 9, 1], "road", 1))
    self.c.add_road(Road([9, 1, 11, 1], "road", 1))
    self.c._add_road(Road([5, 7, 6, 8], "road", 2))
    self.c._add_road(Road([6, 8, 8, 8], "road", 2))
    self.c._add_road(Road([8, 8, 9, 9], "road", 2))
    self.c.add_road(Road([9, 9, 11, 9], "road", 2))
    for rsrc in catan.RESOURCES:
      self.c.player_data[2].cards[rsrc] += 1
    self.g = catan.CatanGame()
    self.g.update_rulesets_and_choices({"Scenario": "Beginner's Map", "5-6 Players": False})
    self.g.game = self.c

  def testCreateLongestRoad(self):
    self.assertIsNone(self.c.longest_route_player)
    # Add a fifth road to playerA's network, giving them longest road.
    self.c.add_road(Road([11, 1, 12, 2], "road", 1))
    self.assertEqual(self.c.longest_route_player, 1)
    self.assertEqual("{player1} takes longest route", self.c.event_log[-1].public_text)
    # Connect two segments of first player's roads, giving them longest road.
    self.c.add_road(Road([9, 5, 11, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    self.assertEqual(
        "{player0} takes longest route from {player1}", self.c.event_log[-1].public_text)

  def testBreakLongestRoad(self):
    self.c.add_road(Road([11, 1, 12, 2], "road", 1))
    self.c.add_road(Road([9, 5, 11, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    # Break first player's longest road with a piece from playerB.
    self.c.add_piece(catan.Piece(8, 4, "settlement", 2))
    # PlayerA should get longest road since first player's is broken.
    self.assertEqual(self.c.longest_route_player, 1)
    self.assertEqual(self.c.player_data[0].longest_route, 4)

  def testBreakLongestRoadNoEligiblePlayers(self):
    self.c.add_road(Road([9, 5, 11, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    self.c.add_piece(catan.Piece(8, 4, "settlement", 2))
    self.assertIsNone(self.c.longest_route_player)
    self.assertEqual("{player0} loses longest route", self.c.event_log[-1].public_text)

  def testBreakLongestRoadMultipleEligiblePlayers(self):
    self.c.add_road(Road([11, 1, 12, 2], "road", 1))
    self.c.add_road(Road([11, 9, 12, 8], "road", 2))
    self.c.add_road(Road([9, 5, 11, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    self.c.add_piece(catan.Piece(8, 4, "settlement", 2))
    # Now that first player's road is broken, nobody gets longest road because playerA
    # and playerB are tied.
    self.assertIsNone(self.c.longest_route_player)
    self.assertIn("because of a tie", self.c.event_log[-1].public_text)

  def testBreakLongestRoadNextRoadTooShort(self):
    self.c.add_road(Road([9, 5, 11, 5], "road", 0))
    # Break playerB's road of 4 so that this scenario is distinguishable from the one
    # where multiple players are tied for next longest road.
    self.c.add_piece(catan.Piece(8, 8, "settlement", 0))
    self.assertEqual(self.c.player_data[2].longest_route, 2)
    self.assertEqual(self.c.longest_route_player, 0)
    # Break first player's longest road. Their longest road should now be 3.
    self.c.add_piece(catan.Piece(9, 5, "settlement", 2))
    self.assertEqual(self.c.player_data[0].longest_route, 3)
    self.assertEqual(self.c.player_data[1].longest_route, 4)
    self.assertIsNone(self.c.longest_route_player)

  def testBreakLongestRoadStayingTied(self):
    # Give first player a longest road of 6.
    self.c.add_road(Road([3, 5, 5, 5], "road", 0))
    self.c.add_road(Road([2, 4, 3, 5], "road", 0))
    self.c.add_road(Road([2, 4, 3, 3], "road", 0))
    # Give playerA a longest road of 5.
    self.c.add_road(Road([11, 1, 12, 2], "road", 1))
    self.assertEqual(self.c.longest_route_player, 0)
    self.assertEqual(self.c.player_data[0].longest_route, 6)
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    # Break first player's road one road away from the edge, cutting them down to 5.
    self.c.add_road(Road([8, 4, 9, 3], "road", 2))  # Just here to attach the settlement to.
    self.c.handle_settle([8, 4], 2)  # Use handle_settle to create an event log.
    self.assertEqual(self.c.player_data[0].longest_route, 5)
    # They should retain longest route.
    self.assertEqual(self.c.longest_route_player, 0)
    self.assertNotEqual(self.c.event_log[-1].event_type, "longest_route")

  def testBreakRoadButStaysSameLength(self):
    # Give first player a circular road.
    self.c.add_road(Road([5, 5, 6, 6], "road", 0))
    self.c.add_road(Road([6, 6, 8, 6], "road", 0))
    self.c.add_road(Road([8, 6, 9, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    self.assertEqual(self.c.player_data[0].longest_route, 6)
    # Break the circular road in the middle. The road length should stay the same.
    self.c.add_piece(catan.Piece(9, 5, "settlement", 2))
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
    self.assertIn("{player0} took largest army", self.c.event_log[-1].public_text)

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
    self.assertEqual(self.c.event_log[-2].event_type, "knight")
    self.assertEqual(self.c.event_log[-1].event_type, "largest_army")
    self.assertIn("{player1} took largest army from {player0}", self.c.event_log[-1].public_text)


@mock.patch.object(catan.random, "randint", return_value=3.5)
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
    self.assertEqual(self.c.event_log[-1].event_type, "dice")
    self.assertIn("rolled a 7", self.c.event_log[-1].public_text)
    # Player 0 has 16 cards, and must discard 8.
    # Player 1 does not have to discard because dev cards don't count.
    # Player 2 must discard 9/2 rounded down = 4.
    self.assertDictEqual(self.c.discard_players, {0: 8, 2: 4})

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
    self.assertEqual(self.c.event_log[-1].event_type, "discard")
    self.assertIn("discarded 4 {rsrc1}, 4 {rsrc2}", self.c.event_log[-1].public_text)
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
    self.assertEqual(self.c.event_log[-1].event_type, "buy_dev")
    self.assertIn("bought a dev card", self.c.event_log[-1].public_text)
    self.assertIn("bought a", self.c.event_log[-1].secret_text)
    self.assertNotIn("bought a dev card", self.c.event_log[-1].secret_text)
    self.assertEqual(self.c.event_log[-1].visible_players, [1])
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


class TestExtraBuildPhase(BreakpointTest):

  def setUp(self):
    self.g = catan.CatanGame()
    self.g.connected = {"player1", "player2", "player3", "player4", "player5"}
    self.g.host = "player1"
    for u in self.g.connected:
      self.g.handle_join(u, {"name": u})
    self.g.handle_start("player1", {"options": {"Scenario": "Random Map"}})
    self.c = self.g.game

  def testNoExtraBuildDuringPlacePhase(self):
    self.c.handle(0, {"type": "settle", "location": [3, 3]})
    self.c.handle(0, {"type": "road", "location": [3, 3, 5, 3]})
    self.assertEqual(self.c.game_phase, "place1")
    self.assertEqual(self.c.turn_phase, "settle")
    self.assertEqual(self.c.turn_idx, 1)

    # Also validate that there is no special build phase after the last settlement/road.
    self.c.game_phase = "place2"
    self.c.turn_phase = "settle"
    self.c.turn_idx = 0
    self.c.handle(0, {"type": "settle", "location": [9, 3]})
    self.c.handle(0, {"type": "road", "location": [9, 3, 11, 3]})
    self.assertEqual(self.c.game_phase, "main")
    self.assertEqual(self.c.turn_phase, "dice")
    self.assertEqual(self.c.turn_idx, 0)

  def testExtraBuildActions(self):
    self.c.game_phase = "main"
    self.c.turn_phase = "main"
    self.c.turn_idx = 4
    self.c.add_piece(catan.Piece(3, 3, "settlement", 0))
    self.c._add_road(Road([3, 3, 5, 3], "road", 0))
    self.c._add_road(Road([5, 3, 6, 4], "road", 0))
    self.c.player_data[0].cards.update({"rsrc1": 3, "rsrc2": 3, "rsrc3": 5, "rsrc4": 3, "rsrc5": 5})
    self.c.player_data[4].cards.update({"rsrc1": 3, "rsrc2": 3, "rsrc3": 5, "rsrc4": 3, "rsrc5": 5})

    with self.assertRaises(catan.NotYourTurn):
      self.c.handle(0, {"type": "settle", "location": [6, 4]})

    self.c.handle(4, {"type": "end_turn"})
    self.assertEqual(self.c.game_phase, "main")
    self.assertEqual(self.c.turn_phase, "extra_build")
    self.assertEqual(self.c.extra_build_idx, 0)
    self.c.handle(0, {"type": "settle", "location": [6, 4]})
    self.c.handle(0, {"type": "road", "location": [6, 4, 8, 4]})
    self.c.handle(0, {"type": "city", "location": [3, 3]})
    self.c.handle(0, {"type": "buy_dev"})

    with self.assertRaises(catan.NotYourTurn):
      self.c.handle(0, {"type": "end_turn"})
    with self.assertRaises(catan.NotYourTurn):
      self.c.handle(0, {"type": "play_dev", "card_type": "knight"})
    self.c.handle(0, {"type": "end_extra_build"})
    self.assertEqual(self.c.game_phase, "main")
    self.assertEqual(self.c.turn_phase, "extra_build")
    self.assertEqual(self.c.extra_build_idx, 1)

    with self.assertRaises(catan.NotYourTurn):
      self.c.handle(4, {"type": "buy_dev"})

  def testLastExtraBuild(self):
    self.c.game_phase = "main"
    self.c.turn_phase = "extra_build"
    self.c.turn_idx = 4
    self.c.extra_build_idx = 3

    self.c.handle(3, {"type": "end_extra_build"})
    self.assertEqual(self.c.game_phase, "main")
    self.assertEqual(self.c.turn_phase, "dice")
    self.assertIsNone(self.c.extra_build_idx)
    self.assertEqual(self.c.turn_idx, 0)


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
      self.c.handle_start("one", {"options": {"Scenario": "Random Map"}})

    self.c.handle_join("one", {"name": "player1"})
    self.c.handle_join("two", {"name": "player2"})
    self.c.handle_join("three", {"name": "player3"})
    self.c.handle_join("four", {"name": "player4"})
    with self.assertRaisesRegex(InvalidMove, "not the host"):
      self.c.handle_start("two", {"options": {"Scenario": "Random Map"}})
    with self.assertRaisesRegex(InvalidMove, "Unknown scenario"):
      self.c.handle_start("one", {"options": {"Scenario": "nsaoeu"}})
    with self.assertRaisesRegex(InvalidMove, "must select"):
      self.c.handle_start("one", {"options": {}})
    self.assertIsNone(self.c.game)

    self.c.handle_start("one", {"options": {"Scenario": "Random Map", "5-6 Players": False}})
    self.assertIsNotNone(self.c.game)
    self.assertIsNone(self.c.host)
    self.assertGreater(len(self.c.game.tiles.keys()), 0)

    with self.assertRaisesRegex(InvalidMove, "already started"):
      self.c.handle_start("one", {"options": {"Scenario": "Random Map"}})
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
    self.c.handle_start(self.c.host, {"options": {"Scenario": "Random Map", "5-6 Players": False}})

    self.assertIsNotNone(self.c.game)
    self.assertEqual(len(self.c.game.player_data), 2)
    self.assertCountEqual(self.c.player_sessions.keys(), ["two", "four"])
    self.assertEqual(self.c.game.player_data[self.c.player_sessions["two"]].name, "player2")
    self.assertEqual(self.c.game.player_data[self.c.player_sessions["four"]].name, "player4")
    self.assertDictEqual(self.c.game.discard_players, {})
    self.assertDictEqual(self.c.game.counter_offers, {})


class TestGameOptions(unittest.TestCase):

  def setUp(self):
    self.c = catan.CatanGame()

  def testInitialState(self):
    self.assertDictEqual(self.c.choices, {})
    self.assertSetEqual(self.c.rules, set())
    self.assertEqual(self.c.scenario, "Random Map")
    self.assertTrue(issubclass(self.c.game_class, catan.RandomMap))
    self.assertFalse(issubclass(self.c.game_class, catan.DebugRules))

  def testOptions(self):
    self.c.scenario = "Beginner's Map"
    json_for_player = json.loads(self.c.for_player(None))
    option_data = {option["name"]: option for option in json_for_player["options"]}
    self.assertIn("Scenario", option_data)
    self.assertEqual(option_data["Scenario"]["value"], "Beginner's Map")
    self.assertIn("Debug", option_data)
    self.assertFalse(option_data["Debug"]["value"])
    self.assertIsNone(option_data["Debug"]["choices"])
    self.assertIn("5-6 Players", option_data)
    self.assertFalse(option_data["5-6 Players"]["value"])

  def testModifyOptions(self):
    self.c.host = "a"
    self.c.handle_select_option(
        "a", {"options": {"Scenario": "Test Map", "Debug": True, "Friendly Robber": True}})
    self.assertEqual(self.c.scenario, "Test Map")
    self.assertSetEqual(self.c.rules, {"Debug"})
    self.assertIn("Friendly Robber", self.c.choices)
    self.assertTrue(self.c.choices["Friendly Robber"])

    self.c.handle_select_option(
        "a", {"options": {"Scenario": "Beginner's Map", "Debug": False, "Friendly Robber": True}})
    self.assertEqual(self.c.scenario, "Beginner's Map")
    self.assertSetEqual(self.c.rules, set())
    self.assertIn("Friendly Robber", self.c.choices)
    self.assertTrue(self.c.choices["Friendly Robber"])

    self.c.handle_select_option(
        "a", {"options": {"Scenario": "Random Map", "Debug": False, "Friendly Robber": True}})
    self.assertEqual(self.c.scenario, "Random Map")
    self.assertSetEqual(self.c.rules, set())
    self.assertIn("Friendly Robber", self.c.choices)
    # Friendly robber should be reset to default because the default changed.
    self.assertFalse(self.c.choices["Friendly Robber"])
    self.assertIn("Friendly Robber", self.c.choices)
    self.assertNotIn("Debug", self.c.choices)
    self.assertNotIn("Scenario", self.c.choices)

    self.c.handle_select_option("a", {"options": {"Scenario": "The Four Islands"}})
    self.assertEqual(self.c.scenario, "The Four Islands")
    self.assertSetEqual(self.c.rules, set())
    # Should set the option to its default even if it wasn't in the provided options.
    self.assertIn("Friendly Robber", self.c.choices)
    self.assertIn("Seafarers", self.c.choices)
    self.assertFalse(self.c.choices["Friendly Robber"])
    self.assertTrue(self.c.choices["Seafarers"])

    self.c.handle_select_option(
        "a", {"options": {"Scenario": "The Four Islands", "Seafarers": False}})
    # You cannot override a forced option.
    self.assertTrue(self.c.choices["Seafarers"])

  def testStartWithOptions(self):
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.handle_join("one", {"name": "player1"})
    self.c.handle_join("two", {"name": "player2"})
    self.c.handle_join("three", {"name": "player3"})

    self.c.handle_select_option("one", {"options": {"Scenario": "Random Map", "Debug": True}})
    # Completely change the options before starting the game; make sure they're honored.
    self.c.handle_start(
        "one", {"options": {"Scenario": "The Four Islands", "Friendly Robber": True}})
    self.assertIsInstance(self.c.game, catan.SeafarerIslands)
    self.assertNotIsInstance(self.c.game, catan.DebugRules)
    self.assertFalse(self.c.game.rob_at_two)

  def testStartWithFourPlayers(self):
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.connect_user("four")
    self.c.connect_user("five")
    self.c.handle_join("one", {"name": "player1"})
    self.c.handle_join("two", {"name": "player2"})
    self.c.handle_join("three", {"name": "player3"})
    self.c.handle_join("four", {"name": "player4"})
    self.c.handle_join("five", {"name": "player5"})

    self.c.handle_select_option("one", {"options": {"Scenario": "Random Map"}})
    self.assertIn("5-6 Players", self.c.rules)

    self.c.disconnect_user("two")
    self.assertNotIn("5-6 Players", self.c.rules)

    self.c.handle_start("one", {"options": {"Scenario": "Random Map"}})
    self.assertNotIsInstance(self.c.game, catan.ExtraPlayers)

  def testStartWithFivePlayers(self):
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.connect_user("four")
    self.c.connect_user("five")
    self.c.handle_join("one", {"name": "player1"})
    self.c.handle_join("two", {"name": "player2"})
    self.c.handle_join("three", {"name": "player3"})
    self.c.handle_join("four", {"name": "player4"})

    self.c.handle_select_option("one", {"options": {"Scenario": "Random Map"}})
    self.assertNotIn("5-6 Players", self.c.rules)

    self.c.handle_join("five", {"name": "player5"})
    self.assertIn("5-6 Players", self.c.rules)

    self.c.handle_start("one", {"options": {"Scenario": "Random Map"}})
    self.assertIsInstance(self.c.game, catan.ExtraPlayers)


if __name__ == '__main__':
  unittest.main()
