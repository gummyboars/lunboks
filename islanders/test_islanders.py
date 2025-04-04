#!/usr/bin/env python3

import collections
import json
import os
import sys
import threading
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from islanders import islanders
import game
import server

# pylint: disable=protected-access
# pylint: disable=invalid-name

InvalidMove = islanders.InvalidMove
Road = islanders.Road


class TestInitBoard(unittest.TestCase):
  def testBeginner(self):
    state = islanders.IslandersState()
    state.add_player("red", "player1")
    state.add_player("blue", "player2")
    state.add_player("forestgreen", "player3")
    islanders.BeginnerMap.mutate_options(state.options)
    islanders.BeginnerMap.init(state)

    self.assertEqual(len(state.tiles), 4 + 5 + 6 + 7 + 6 + 5 + 4, "number of tiles")
    for loc, tile in state.tiles.items():
      self.assertEqual(loc, tile.location, "tiles mapped to location")

  def testRandomized(self):
    state = islanders.IslandersState()
    state.add_player("red", "player1")
    state.add_player("blue", "player2")
    islanders.StandardMap.mutate_options(state.options)
    islanders.StandardMap.init(state)
    counts = collections.defaultdict(int)
    for card in state.dev_cards:
      counts[card] += 1
    expected = {
      "knight": 14,
      "monopoly": 2,
      "yearofplenty": 2,
      "roadbuilding": 2,
      "chapel": 1,
      "university": 1,
      "palace": 1,
      "library": 1,
      "market": 1,
    }
    self.assertDictEqual(counts, expected)
    self.assertIsNone(state.dice_cards)

  def testLowLuck(self):
    state = islanders.IslandersState()
    state.add_player("red", "player1")
    state.add_player("blue", "player2")
    islanders.StandardMap.mutate_options(state.options)
    state.options["randomness"].force(5)
    islanders.StandardMap.init(state)
    self.assertEqual(len(state.dice_cards), 36)

  def testInitNumbers(self):
    state = islanders.IslandersState()
    state.add_player("red", "player1")
    state.add_player("blue", "player2")
    islanders.StandardMap.mutate_options(state.options)
    islanders.StandardMap.init(state)
    # Put the desert in a few different spots to test that it gets skipped properly.
    for desert_spot in [(7, 1), (4, 2), (1, 7), (10, 2), (7, 3), (10, 4), (7, 5)]:
      # Reset the tile numbers to None
      for tile in state.tiles.values():
        tile.number = None
      desert = [(loc, tile) for loc, tile in state.tiles.items() if tile.tile_type == "norsrc"]
      self.assertEqual(len(desert), 1)
      state.tiles[desert[0][0]].tile_type = state.tiles[desert_spot].tile_type
      state.tiles[desert_spot].tile_type = "norsrc"
      state.init_numbers((7, 1), islanders.TILE_NUMBERS)
      nums = [tile.number for tile in state.tiles.values() if tile.is_land]
      self.assertCountEqual(nums, islanders.TILE_NUMBERS + [None])  # None for the desert.
      self.assertIsNone(state.tiles[desert_spot].number)

  def testInitLarge(self):
    state = islanders.IslandersState()
    state.add_player("red", "player1")
    state.add_player("blue", "player2")
    state.add_player("green", "player3")
    state.add_player("yellow", "player4")
    state.add_player("brown", "player5")
    state.add_player("cyan", "player6")
    islanders.StandardMap.mutate_options(state.options)
    state.options["extra_build"].force(True)
    islanders.StandardMap.init(state)
    counts = collections.defaultdict(int)
    for card in state.dev_cards:
      counts[card] += 1
    expected = {
      "knight": 20,
      "monopoly": 3,
      "yearofplenty": 3,
      "roadbuilding": 3,
      "chapel": 1,
      "university": 1,
      "palace": 1,
      "library": 1,
      "market": 1,
    }
    self.assertDictEqual(counts, expected)

  def testRobberNotOnFog(self):
    state = islanders.IslandersState()
    state.add_player("red", "player1")
    state.add_player("blue", "player2")
    state.add_player("forestgreen", "player3")
    islanders.TreasureIslands.mutate_options(state.options)
    islanders.TreasureIslands.init(state)

    self.assertTrue(state.robber)
    self.assertEqual(state.tiles[state.robber].tile_type, "norsrc")


class TestLoadState(unittest.TestCase):
  def testLoadState(self):
    path = os.path.join(os.path.dirname(__file__), "sample.json")
    with open(path, encoding="ascii") as json_file:
      json_data = json_file.read()
    g = islanders.IslandersGame.parse_json(json_data)
    c = g.game
    self.assertIsInstance(c.player_data, list)
    self.assertEqual(len(c.player_data), 1)
    self.assertIsInstance(c.player_data[0].cards, collections.defaultdict)
    self.assertIsInstance(c.player_data[0].trade_ratios, collections.defaultdict)
    self.assertIsInstance(c.num_dev, collections.Counter)
    # TODO: add some more assertions here

  def testLoadSeafarerState(self):
    path = os.path.join(os.path.dirname(__file__), "ship_test.json")
    with open(path, encoding="ascii") as json_file:
      json_data = json_file.read()
    g = islanders.IslandersGame.parse_json(json_data)
    c = g.game
    self.assertTrue(hasattr(c, "built_this_turn"))
    self.assertTrue(hasattr(c, "ships_moved"))
    self.assertEqual(c.built_this_turn, [(2, 4, 3, 5)])
    self.assertEqual(c.ships_moved, 1)
    self.assertEqual(len(c.roads), 2)
    self.assertEqual(next(iter(c.roads.values())).road_type, "ship")
    self.assertIsInstance(next(iter(c.roads.values())).source, islanders.CornerLocation)

  def testLoadTreasures(self):
    path = os.path.join(os.path.dirname(__file__), "treasure_test.json")
    with open(path, encoding="ascii") as json_file:
      json_data = json_file.read()
    g = islanders.IslandersGame.parse_json(json_data)
    c = g.game
    self.assertEqual(len(c.treasures), 2)
    self.assertIn(islanders.CornerLocation(8, 6), c.treasures)
    self.assertIn(islanders.CornerLocation(5, 7), c.treasures)
    self.assertEqual(c.treasures[(8, 6)], "takedev")
    self.assertEqual(c.treasures[(5, 7)], "roadbuilding")

    self.assertListEqual(c.discoverable_treasures, ["collectpi", "collect2", "takedev"])

  def testLoadKnights(self):
    path = os.path.join(os.path.dirname(__file__), "knight_test.json")
    with open(path, encoding="ascii") as json_file:
      json_data = json_file.read()
    g = islanders.IslandersGame.parse_json(json_data)
    c = g.game
    self.assertEqual(len(c.knights), 2)
    self.assertIn((6, 4, 8, 4), c.knights)
    self.assertIn((5, 5, 6, 4), c.knights)
    self.assertIsInstance(c.knights[(5, 5, 6, 4)].location, islanders.EdgeLocation)
    self.assertIsInstance(c.knights[(5, 5, 6, 4)].source, islanders.EdgeLocation)
    self.assertEqual(c.knights[(5, 5, 6, 4)].player, 1)
    self.assertEqual(c.knights[(5, 5, 6, 4)].movement, -2)

  def testDumpAndLoad(self):
    # TODO: test with different numbers of users
    scenarios = [
      "Standard Map",
      "The Four Islands",
      "Through the Desert",
      "The Fog Islands",
      "The Treasure Islands",
    ]
    for scenario in scenarios:
      with self.subTest(scenario=scenario):
        g = islanders.IslandersGame()
        g.connect_user("se0")
        g.connect_user("se1")
        g.connect_user("se2")
        g.handle_join("se0", {"name": "player1"})
        g.handle_join("se1", {"name": "player2"})
        g.handle_join("se2", {"name": "player3"})
        g.handle_change_scenario("se0", {"scenario": scenario})
        g.handle_start("se0", {"options": {}})
        c = g.game
        data = g.json_str()
        d = islanders.IslandersGame.parse_json(data).game

        self.recursiveAssertEqual(c, d, "")

  def recursiveAssertEqual(self, obja, objb, path):
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


class BreakpointTestMixin(unittest.TestCase):
  def breakpoint(self):
    t = threading.Thread(target=server.ws_main, args=(server.GLOBAL_LOOP,))
    t.start()
    server.GAMES["test"] = game.GameHandler("test", islanders.IslandersGame)
    server.GAMES["test"].game = self.g
    server.main(8001)
    t.join()

  def handle(self, player_idx, data):
    return [*self.c.handle(player_idx, data)]  # Loop through generator results


class CornerComputationTest(unittest.TestCase):
  def testIslandCorners(self):
    c = islanders.IslandersState()
    islanders.SeafarerIslands.mutate_options(c.options)
    islanders.SeafarerIslands.load_file(c, "islands3.json")
    self.assertIn((3, 1), c.corners_to_islands)
    self.assertIn((5, 5), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(3, 1)], c.corners_to_islands[(5, 5)])

    self.assertIn((15, 1), c.corners_to_islands)
    self.assertIn((12, 4), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(15, 1)], c.corners_to_islands[(12, 4)])

    self.assertNotEqual(c.corners_to_islands[(3, 1)], c.corners_to_islands[(12, 4)])

  def testShoreCorners(self):
    c = islanders.IslandersState()
    islanders.SeafarerShores.mutate_options(c.options)
    islanders.SeafarerShores.load_file(c, "shores4.json")
    self.assertIn((3, 3), c.corners_to_islands)
    self.assertIn((14, 8), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(3, 3)], c.corners_to_islands[(14, 8)])

    self.assertIn((18, 4), c.corners_to_islands)
    self.assertIn((20, 6), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(18, 4)], c.corners_to_islands[(20, 6)])

    self.assertIn((14, 10), c.corners_to_islands)
    self.assertIn((18, 12), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(14, 10)], c.corners_to_islands[(18, 12)])

    # Assert that the island number for each of these corners is unique.
    islands = [c.corners_to_islands[loc] for loc in [(3, 3), (20, 6), (14, 10)]]
    self.assertEqual(len(islands), len(set(islands)))

  def testDesertCorners(self):
    c = islanders.IslandersState()
    islanders.SeafarerDesert.mutate_options(c.options)
    islanders.SeafarerDesert.load_file(c, "desert3.json")
    self.assertIn((3, 1), c.corners_to_islands)
    self.assertIn((14, 6), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(3, 1)], c.corners_to_islands[(14, 6)])

    self.assertIn((15, 1), c.corners_to_islands)
    self.assertIn((20, 4), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(15, 1)], c.corners_to_islands[(20, 4)])

    self.assertIn((3, 9), c.corners_to_islands)

    # Assert that the island number for each of these corners is unique.
    islands = [c.corners_to_islands[loc] for loc in [(3, 1), (20, 4), (3, 9)]]
    self.assertEqual(len(islands), len(set(islands)))

    # Desert corner that doesn't touch any other land should not have an island number.
    self.assertNotIn((21, 5), c.corners_to_islands)

  def testFogCorners(self):
    c = islanders.IslandersState()
    islanders.SeafarerFog.mutate_options(c.options)
    islanders.SeafarerFog.load_file(c, "fog3.json")
    self.assertIn((5, 7), c.corners_to_islands)
    self.assertIn((14, 4), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(5, 7)], c.corners_to_islands[(14, 4)])

    self.assertIn((17, 7), c.corners_to_islands)
    self.assertIn((5, 11), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(17, 7)], c.corners_to_islands[(5, 11)])

    self.assertIn((23, 9), c.corners_to_islands)
    self.assertIn((15, 13), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(23, 9)], c.corners_to_islands[(15, 13)])

    # Assert that the island number for each of these corners is unique.
    islands = [c.corners_to_islands[loc] for loc in [(5, 7), (5, 11), (23, 9)]]
    self.assertEqual(len(islands), len(set(islands)))

  def testTreasureCorners(self):
    c = islanders.IslandersState()
    islanders.TreasureIslands.mutate_options(c.options)
    islanders.TreasureIslands.load_file(c, "treasure4.json")
    self.assertIn((5, 9), c.corners_to_islands)
    self.assertIn((11, 5), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(5, 9)], c.corners_to_islands[(11, 5)])

    self.assertIn((2, 6), c.corners_to_islands)
    self.assertIn((3, 11), c.corners_to_islands)
    self.assertEqual(c.corners_to_islands[(2, 6)], c.corners_to_islands[(3, 11)])

    # Assert that the island number for each of these corners is unique.
    islands = [c.corners_to_islands[loc] for loc in [(5, 9), (3, 11), (12, 2)]]
    self.assertEqual(len(islands), len(set(islands)))


class PlacementRestrictionsTest(unittest.TestCase):
  def handle(self, state, player_idx, data):
    return [*state.handle(player_idx, data)]

  def testSaveAndLoad(self):
    c = islanders.IslandersState()
    c.add_player("red", "player1")
    c.add_player("blue", "player2")
    c.add_player("green", "player3")
    islanders.SeafarerDesert.mutate_options(c.options)
    islanders.SeafarerDesert.init(c)
    self.assertCountEqual(c.placement_islands, [(-1, 3)])
    g = islanders.IslandersGame()
    g.game = c

    dump = g.json_str()
    loaded = islanders.IslandersGame.parse_json(dump)
    loaded_game = loaded.game
    self.assertCountEqual(loaded_game.placement_islands, [(-1, 3)])

  def testDesert3Placement(self):
    c = islanders.IslandersState()
    c.add_player("red", "player1")
    c.add_player("blue", "player2")
    c.add_player("green", "player3")
    islanders.SeafarerDesert.mutate_options(c.options)
    islanders.SeafarerDesert.init(c)
    self.assertCountEqual(c.placement_islands, [(-1, 3)])

    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [0, 8]})
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [12, 0]})
    self.handle(c, 0, {"type": "settle", "location": [3, 3]})

    # We're going to skip a bunch of placements.
    c.game_phase = "place2"
    c.action_stack = ["road", "settle"]
    c.turn_idx = 1

    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 1, {"type": "settle", "location": [9, 9]})
    self.handle(c, 1, {"type": "settle", "location": [3, 5]})

  def testDesert4Placement(self):
    c = islanders.IslandersState()
    c.add_player("red", "player1")
    c.add_player("blue", "player2")
    c.add_player("green", "player3")
    c.add_player("violet", "player4")
    islanders.SeafarerDesert.mutate_options(c.options)
    islanders.SeafarerDesert.init(c)
    self.assertCountEqual(c.placement_islands, [(-1, 5)])

    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [0, 8]})
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [12, 0]})
    self.handle(c, 0, {"type": "settle", "location": [3, 3]})

    # We're going to skip a bunch of placements.
    c.game_phase = "place2"
    c.action_stack = ["road", "settle"]
    c.turn_idx = 1

    # It should still validate islands in the second placement round.
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 1, {"type": "settle", "location": [12, 12]})
    self.handle(c, 1, {"type": "settle", "location": [12, 8]})

  def testShores3Placement(self):
    c = islanders.IslandersState()
    c.add_player("red", "player1")
    c.add_player("blue", "player2")
    c.add_player("green", "player3")
    islanders.SeafarerShores.mutate_options(c.options)
    islanders.SeafarerShores.init(c)
    self.assertCountEqual(c.placement_islands, [(-1, 3)])

    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [3, 9]})
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [18, 4]})
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [15, 9]})
    self.handle(c, 0, {"type": "settle", "location": [3, 3]})

  def testShores4Placement(self):
    c = islanders.IslandersState()
    c.add_player("red", "player1")
    c.add_player("blue", "player2")
    c.add_player("green", "player3")
    c.add_player("violet", "player4")
    islanders.SeafarerShores.mutate_options(c.options)
    islanders.SeafarerShores.init(c)
    self.assertCountEqual(c.placement_islands, [(-1, 3)])

    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [3, 11]})
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [18, 4]})
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [17, 11]})
    self.handle(c, 0, {"type": "settle", "location": [3, 3]})

  def testFog3Placement(self):
    c = islanders.IslandersState()
    c.add_player("red", "player1")
    c.add_player("blue", "player2")
    c.add_player("green", "player3")
    islanders.SeafarerFog.mutate_options(c.options)
    islanders.SeafarerFog.init(c)
    self.assertCountEqual(c.placement_islands, [(2, 6), (11, 13)])

    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [17, 3]})
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [5, 11]})
    self.handle(c, 0, {"type": "settle", "location": [9, 7]})
    c.game_phase = "place2"
    c.action_stack = ["road", "settle"]
    c.turn_idx = 1
    self.handle(c, 1, {"type": "settle", "location": [17, 13]})

  def testFog4Placement(self):
    c = islanders.IslandersState()
    c.add_player("red", "player1")
    c.add_player("blue", "player2")
    c.add_player("green", "player3")
    c.add_player("violet", "player4")
    islanders.SeafarerFog.mutate_options(c.options)
    islanders.SeafarerFog.init(c)
    self.assertCountEqual(c.placement_islands, [(2, 4), (8, 14)])

    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [20, 4]})
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [5, 9]})
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [9, 7]})
    self.handle(c, 0, {"type": "settle", "location": [9, 5]})
    c.game_phase = "place2"
    c.action_stack = ["road", "settle"]
    c.turn_idx = 1
    self.handle(c, 1, {"type": "settle", "location": [20, 10]})

  def testTreasurePlacement(self):
    c = islanders.IslandersState()
    c.add_player("red", "player1")
    c.add_player("blue", "player2")
    c.add_player("green", "player3")
    islanders.TreasureIslands.mutate_options(c.options)
    islanders.TreasureIslands.init(c)
    self.assertCountEqual(c.placement_islands, [(5, 7)])

    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [2, 4]})
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [3, 11]})
    with self.assertRaisesRegex(InvalidMove, "starting settlement"):
      self.handle(c, 0, {"type": "settle", "location": [15, 15]})
    self.handle(c, 0, {"type": "settle", "location": [18, 6]})


class TestIslandCalculations(BreakpointTestMixin):
  def setUp(self):
    self.c = islanders.IslandersState()
    self.c.add_player("red", "player1")
    self.c.add_player("blue", "player2")
    self.c.add_player("green", "player3")
    islanders.SeafarerIslands.mutate_options(self.c.options)
    islanders.SeafarerIslands.init(self.c)
    # TODO: we should have a helper to init a game with the default options for a scenario.
    self.c.options["foreign_island_points"].set(2)
    self.handle(0, {"type": "settle", "location": [12, 4]})
    self.handle(0, {"type": "ship", "location": [11, 3, 12, 4]})
    self.handle(1, {"type": "settle", "location": [5, 5]})
    self.handle(1, {"type": "ship", "location": [5, 5, 6, 6]})
    self.handle(2, {"type": "settle", "location": [8, 8]})
    self.handle(2, {"type": "ship", "location": [8, 8, 9, 7]})
    self.handle(2, {"type": "settle", "location": [18, 8]})
    self.handle(2, {"type": "road", "location": [18, 8, 20, 8]})
    self.handle(1, {"type": "settle", "location": [9, 1]})
    self.handle(1, {"type": "ship", "location": [9, 1, 11, 1]})
    self.c.game_phase = "main"
    self.c.action_stack.clear()
    self.c.pirate = None
    self.g = islanders.IslandersGame()
    self.g.game = self.c

  def testHomeIslands(self):
    self.assertCountEqual(self.c.home_corners[0], [(12, 4)])
    self.assertCountEqual(self.c.home_corners[1], [(5, 5), (9, 1)])
    self.assertCountEqual(self.c.home_corners[2], [(8, 8), (18, 8)])

  def settleForeignIslands(self):
    for rsrc in islanders.RESOURCES:
      self.c.player_data[2].cards[rsrc] += 2
    # Player1 settles a foreign island.
    self.c.add_piece(islanders.Piece(9, 3, "settlement", 0))
    # Player2 settles two foreign islands.
    self.c.add_piece(islanders.Piece(12, 2, "settlement", 1))
    self.c.add_piece(islanders.Piece(5, 7, "settlement", 1))
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
    self.c.add_piece(islanders.Piece(2, 8, "settlement", 1))
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
      data["landings"],
      [
        {"player": 0, "location": (9, 3)},
        {"player": 1, "location": (12, 2)},
        {"player": 1, "location": (5, 7)},
        {"player": 2, "location": (8, 6)},
      ],
    )

  def testSaveAndLoad(self):
    self.settleForeignIslands()
    dump = self.g.json_str()
    loaded = islanders.IslandersGame.parse_json(dump)
    loaded_game = loaded.game
    self.assertIsInstance(loaded_game.home_corners, collections.defaultdict)
    self.assertIsInstance(loaded_game.foreign_landings, collections.defaultdict)
    self.assertCountEqual(loaded_game.home_corners[0], [(12, 4)])
    self.assertCountEqual(loaded_game.home_corners[1], [(5, 5), (9, 1)])
    self.assertCountEqual(loaded_game.home_corners[2], [(8, 8), (18, 8)])
    self.assertCountEqual(loaded_game.foreign_landings[0], [(9, 3)])
    self.assertCountEqual(loaded_game.foreign_landings[1], [(12, 2), (5, 7)])
    self.assertCountEqual(loaded_game.foreign_landings[2], [(8, 6)])


class TestFogLandingCalculations(BreakpointTestMixin):
  def setUp(self):
    self.c = islanders.IslandersState()
    self.c.add_player("red", "player1")
    self.c.add_player("blue", "player2")
    self.c.add_player("green", "player3")
    islanders.TreasureIslands.mutate_options(self.c.options)
    islanders.TreasureIslands.init(self.c)
    # TODO: we should have a helper to init a game with the default options for a scenario.
    self.c.options["foreign_island_points"].set(1)

    self.handle(0, {"type": "settle", "location": [6, 8]})
    self.handle(0, {"type": "ship", "location": [5, 7, 6, 8]})
    self.c.game_phase = "main"
    self.c.turn_idx = 0
    self.c.action_stack.clear()
    self.g = islanders.IslandersGame()
    self.g.game = self.c
    self.g.scenario = "The Treasure Islands"

  def discoverAndLand(self):
    for rsrc in islanders.RESOURCES:
      self.c.player_data[0].cards[rsrc] += 10
    # Player will discover a land tile, then sea, then land again.
    self.c.discoverable_tiles = ["rsrc1", "space", "rsrc2"]
    self.c.discoverable_numbers = [12, 2]
    self.c.discoverable_treasures = ["takedev"]  # To be drawn when discovering the sea tile.

    # Discover the first land tile.
    self.handle(0, {"type": "ship", "location": [3, 7, 5, 7]})
    # Build and check that this counts as a foreign landing.
    self.handle(0, {"type": "settle", "location": [3, 7]})
    self.assertCountEqual(self.c.foreign_landings[0], [(3, 7)])

    # Discover the next tile, which should be a sea tile.
    self.handle(0, {"type": "ship", "location": [2, 8, 3, 7]})
    self.assertEqual(self.c.tiles[(1, 9)].tile_type, "space")
    self.handle(0, {"type": "ship", "location": [2, 8, 3, 9]})
    self.assertCountEqual(self.c.foreign_landings[0], [(3, 7)])

  def testSplitFogIslandIsOnlyOne(self):
    # Test that if you discover a sea that splits an island, it still only counts as 1.
    self.discoverAndLand()
    self.handle(0, {"type": "ship", "location": [2, 10, 3, 9]})
    self.handle(0, {"type": "settle", "location": [2, 10]})
    self.assertCountEqual(self.c.foreign_landings[0], [(3, 7)])

  def testIslandSplitCalculationOnSaveLoad(self):
    # Test that loading a saved game does not split the original fog island.
    self.discoverAndLand()
    dump = self.g.json_str()
    loaded = islanders.IslandersGame.parse_json(dump)
    self.c = loaded.game
    self.handle(0, {"type": "ship", "location": [2, 10, 3, 9]})
    self.handle(0, {"type": "settle", "location": [2, 10]})
    self.assertCountEqual(self.c.foreign_landings[0], [(3, 7)])
    self.assertEqual(self.c.tiles[(1, 9)].tile_type, "space")


class BaseInputHandlerTest(BreakpointTestMixin):
  TEST_FILE = "test.json"
  DEBUG = False

  def setUp(self):
    path = os.path.join(os.path.dirname(__file__), self.TEST_FILE)
    with open(path, encoding="ascii") as json_file:
      json_data = json.loads(json_file.read())
    if self.DEBUG:
      json_data["options"]["debug"] = {
        "name": "Debug",
        "forced": False,
        "default": True,
        "choices": None,
        "hidden": False,
        "value": True,
      }
    self.g = islanders.IslandersGame.parse_json(json.dumps(json_data))
    self.c = self.g.game


class TestLoadTestData(BaseInputHandlerTest):
  def testSessions(self):
    self.assertIn("Player1", self.g.player_sessions)
    self.assertEqual(self.g.player_sessions["Player1"], 0)

  def testTradeRatios(self):
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc1"], 2)
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc2"], 3)
    self.assertEqual(self.c.player_data[1].trade_ratios["rsrc1"], 4)
    self.assertEqual(self.c.player_data[0].trade_ratios.default_factory(), 3)
    self.assertEqual(self.c.player_data[1].trade_ratios.default_factory(), 4)


class DebugRulesOffTest(BaseInputHandlerTest):
  def testDebugDisabledNormalGame(self):
    with mock.patch.object(self.c, "distribute_resources") as dist:
      with self.assertRaisesRegex(InvalidMove, "debug mode"):
        _ = [*self.g.handle("Player1", {"type": "debug_roll_dice", "count": 5})]
        self.assertFalse(dist.called)


class DebugRulesOnTest(BaseInputHandlerTest):
  DEBUG = True

  def testDebugEnabledRollDice(self):
    with mock.patch.object(self.c, "distribute_resources") as dist:
      _ = [*self.g.handle("Player1", {"type": "debug_roll_dice", "count": 5})]
      self.assertEqual(dist.call_count, 5)

  def testDebugEnabledForceDice(self):
    _ = [*self.g.handle("Player1", {"type": "force_dice", "value": 5})]
    self.c.action_stack = ["dice"]
    self.c.handle_roll_dice()
    self.assertTupleEqual(self.c.dice_roll, (2, 3))
    for _ in range(4):  # 1 in 1.68 million chance of failing.
      self.c.action_stack = ["dice"]
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
    self.c.add_tile(islanders.Tile(-2, 4, "rsrc5", True, 4))

  def testEdgeTypeUnoccupied(self):
    self.assertEqual(self.c._get_edge_type(islanders.EdgeLocation(0, 4, 2, 4)), "road")
    self.assertEqual(self.c._get_edge_type(islanders.EdgeLocation(8, 6, 9, 5)), "coastup")
    self.assertEqual(self.c._get_edge_type(islanders.EdgeLocation(2, 4, 3, 3)), "coastdown")
    self.assertEqual(self.c._get_edge_type(islanders.EdgeLocation(5, 5, 6, 4)), "ship")
    self.assertIsNone(self.c._get_edge_type(islanders.EdgeLocation(0, 8, 2, 8)))

  def testEdgeTypeOccupied(self):
    self.assertEqual(self.c._get_edge_type(islanders.EdgeLocation(2, 4, 3, 5)), "road")
    self.assertEqual(self.c._get_edge_type(islanders.EdgeLocation(3, 5, 5, 5)), "ship")
    self.assertEqual(self.c._get_edge_type(islanders.EdgeLocation(2, 6, 3, 5)), "ship")


class TestDistributeResources(BaseInputHandlerTest):
  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_piece(islanders.Piece(5, 3, "city", 0))
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
    self.c.distribute_resources((2, 3))
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], 8)
    self.assertEqual(self.c.player_data[1].cards["rsrc4"], 9)

    self.c.distribute_resources((3, 3))
    self.assertEqual(self.c.player_data[0].cards["rsrc5"], 8)
    self.assertEqual(self.c.player_data[1].cards["rsrc5"], 9)

  def testTooManyResourcesOnlyOnePlayer(self):
    self.c.distribute_resources((4, 5))
    self.assertEqual(self.c.player_data[0].cards["rsrc3"], 10)
    self.assertEqual(self.c.player_data[1].cards["rsrc3"], 9)
    self.assertEqual(self.c.player_data[1].cards["rsrc1"], 2)

  def testConqueredTilesGiveNoResources(self):
    self.c.tiles[(4, 6)].barbarians = 1
    self.c.tiles[(4, 6)].conquered = True
    self.c.distribute_resources((4, 5))
    self.assertEqual(self.c.player_data[0].cards["rsrc3"], 10)
    self.assertEqual(self.c.player_data[1].cards["rsrc1"], 0)


class TestDevCards(BaseInputHandlerTest):
  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    for card in islanders.PLAYABLE_DEV_CARDS:
      self.c.player_data[0].cards[card] = 1
    for p in self.c.player_data:
      p.cards["rsrc1"] = 0

  def testYearOfPlenty(self):
    self.c.player_data[0].cards["rsrc1"] = 3
    self.c.handle_play_dev("yearofplenty", {"rsrc1": 2}, 0)
    self.assertEqual(self.c.player_data[0].cards["rsrc1"], 5)

  def testYearOfPlentyDepletedResource(self):
    self.c.player_data[1].cards["rsrc1"] = 19
    orig = self.c.player_data[0].cards["rsrc2"]
    with self.assertRaisesRegex(InvalidMove, "not enough {rsrc1} in the bank"):
      self.c.handle_play_dev("yearofplenty", {"rsrc1": 1, "rsrc2": 1}, 0)
    self.c.handle_play_dev("yearofplenty", {"rsrc2": 2}, 0)
    self.assertEqual(self.c.player_data[0].cards["rsrc1"], 0)
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], orig + 2)

  def testYearOfPlentyCannotGetGold(self):
    with self.assertRaisesRegex(InvalidMove, "Invalid resource"):
      self.c.handle_play_dev("yearofplenty", {"gold": 2}, 0)
    self.assertEqual(self.c.player_data[0].cards["gold"], 0)

  def testYearOfPlentyMostlyDepletedResource(self):
    self.c.player_data[1].cards["rsrc1"] = 18
    with self.assertRaisesRegex(InvalidMove, "not enough {rsrc1} in the bank"):
      self.c.handle_play_dev("yearofplenty", {"rsrc1": 2}, 0)
    self.c.handle_play_dev("yearofplenty", {"rsrc1": 1, "rsrc2": 1}, 0)

  def testYearOfPlentyEmptyBank(self):
    for rsrc in islanders.RESOURCES:
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


class TestRollDice(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["randomness"].force(5)
    self.c.init_dice_cards()

  def testDiceRollFromCards(self):
    self.assertEqual(len(self.c.dice_cards), 36)
    self.c.action_stack = ["dice"]
    self.c.handle_roll_dice()
    self.assertEqual(len(self.c.dice_cards), 35)
    first_roll = self.c.dice_roll

    self.c.action_stack = ["dice"]
    self.c.handle_roll_dice()
    self.assertEqual(len(self.c.dice_cards), 34)
    self.assertNotEqual(self.c.dice_roll, first_roll)

  def testReshuffleDiceCards(self):
    self.c.dice_cards = self.c.dice_cards[:5]
    self.c.action_stack = ["dice"]
    self.c.handle_roll_dice()
    self.assertEqual(len(self.c.dice_cards), 35)


class TestCollectResources(BaseInputHandlerTest):
  TEST_FILE = "sea_test.json"
  DEBUG = True

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_player("green", "Bob")
    self.c.add_piece(islanders.Piece(0, 4, "city", 1))
    self.c.add_piece(islanders.Piece(0, 6, "city", 2))
    self.c.tiles[(1, 3)].tile_type = "anyrsrc"
    self.c.tiles[(1, 5)].tile_type = "anyrsrc"
    self.c.add_piece(islanders.Piece(3, 7, "city", 1))
    self.c.add_piece(islanders.Piece(6, 8, "city", 2))
    self.c.tiles[(4, 8)].number = 5
    self.c.add_piece(islanders.Piece(9, 5, "settlement", 0))
    self.c.tiles[(10, 6)].number = 9
    for p in self.c.player_data:
      p.cards.clear()
      p.cards["rsrc3"] = 4

  def testSimpleCollection(self):
    self.c.action_stack = ["dice"]
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
    with self.assertRaisesRegex(islanders.NotYourTurn, "not eligible"):
      self.handle(0, {"type": "collect", "selection": {"rsrc3": 1}})
    # Player 2 should be able to collect even when it is not their turn.
    self.handle(1, {"type": "collect", "selection": {"rsrc3": 2}})
    self.assertIn("collected 2 {rsrc3}", self.c.event_log[-1].public_text)

  def testCollectDepletedResource(self):
    self.c.player_data[0].cards["rsrc3"] = 10
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 9
    self.c.handle_roll_dice()
    self.assertEqual(self.c.remaining_resources("rsrc3"), 1)
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {1: 2})
    with self.assertRaisesRegex(InvalidMove, "not enough {rsrc3} in the bank"):
      self.handle(1, {"type": "collect", "selection": {"rsrc3": 2}})
    self.handle(1, {"type": "collect", "selection": {"rsrc1": 1, "rsrc3": 1}})

  def testCollectScarcityForcesOrder(self):
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    self.assertEqual(self.c.remaining_resources("rsrc3"), 3)
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {0: 1, 1: 2, 2: 2})
    # Players will collect 5 resources, but only 3 rsrc3 remain. They must take turns.
    # It is Player1's turn, so they should collect first.
    self.assertEqual(self.c.collect_idx, 0)
    with self.assertRaisesRegex(islanders.NotYourTurn, "Another player.*before you"):
      self.handle(1, {"type": "collect", "selection": {"rsrc3": 2}})
    self.handle(0, {"type": "collect", "selection": {"rsrc3": 1}})
    self.assertEqual(self.c.player_data[0].cards["rsrc3"], 5)
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {1: 2, 2: 2})
    self.assertEqual(self.c.collect_idx, 1)

  def testCollectAbundanceUnordered(self):
    for p in self.c.player_data:
      p.cards["rsrc3"] = 3
    # With more cards available than can be claimed, there should not be a player order.
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    self.assertEqual(self.c.remaining_resources("rsrc3"), 6)
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {0: 1, 1: 2, 2: 2})
    # Players will collect 5 resources, minimum 6 remain. They do not have to take turns.
    self.assertIsNone(self.c.collect_idx)

  def testCollectScarcityDisappears(self):
    self.c.turn_idx = 2
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {0: 1, 1: 2, 2: 2})
    self.assertEqual(self.c.remaining_resources("rsrc3"), 3)
    # Minimum 3 resources remain, but players will collect a total of 5. They must take turns.
    # Since it is currently player3's turn, they collect first.
    self.assertEqual(self.c.collect_idx, 2)
    self.handle(2, {"type": "collect", "selection": {"rsrc1": 2}})
    # The minimum resources available is still 3, but now only 3 resources remain to be collected.
    # The rest of the players may collect in any order.
    self.assertDictEqual(self.c.collect_counts, {0: 1, 1: 2})
    self.assertEqual(self.c.remaining_resources("rsrc3"), 3)
    self.assertIsNone(self.c.collect_idx)

  def testResourceShortage(self):
    for p in self.c.player_data:
      p.cards["rsrc3"] = 6
    self.c.action_stack = ["dice"]
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
      self.handle(0, {"type": "collect", "selection": {"rsrc3": 1}})
    self.handle(0, {"type": "collect", "selection": {"rsrc1": 1}})
    self.assertEqual(self.c.turn_phase, "collect")
    # Even after one player collects, other players still cannot collect shortage resources.
    with self.assertRaisesRegex(InvalidMove, "shortage"):
      self.handle(2, {"type": "collect", "selection": {"rsrc3": 2}})
    self.handle(2, {"type": "collect", "selection": {"rsrc4": 2}})
    self.handle(1, {"type": "collect", "selection": {"rsrc2": 2}})
    # After everyone collects, it should be back to the original player's turn.
    self.assertEqual(self.c.turn_phase, "main")

  def testNoRemainingResources(self):
    for idx, p in enumerate(self.c.player_data):
      for rsrc in islanders.RESOURCES:
        p.cards[rsrc] = 6
        if idx == 0:
          p.cards[rsrc] += 1
    for rsrc in islanders.RESOURCES:
      with self.subTest(rsrc=rsrc):
        self.assertEqual(self.c.remaining_resources(rsrc), 0)
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    # If there are no cards left, we have to skip collection.
    self.assertDictEqual(self.c.collect_counts, {})
    self.assertIsNone(self.c.collect_idx)
    self.assertEqual(self.c.turn_phase, "main")

  def testNoRemainingResourcesAfterDistribution(self):
    for idx, p in enumerate(self.c.player_data):
      for rsrc in islanders.RESOURCES:
        p.cards[rsrc] = 6
        if idx == 0:
          p.cards[rsrc] += 1
    self.c.player_data[0].cards["rsrc3"] -= 4
    # There are exactly four rsrc3 remaining. After the initial distribution (where players 2 and
    # 3 will receive the remaining 4), nobody should be able to collect from the bonus tiles.
    self.assertEqual(self.c.remaining_resources("rsrc3"), 4)
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    self.assertDictEqual(self.c.collect_counts, {})
    self.assertIsNone(self.c.collect_idx)
    self.assertEqual(self.c.turn_phase, "main")

  def testCollectionConsumesAllResources(self):
    for idx, p in enumerate(self.c.player_data):
      for rsrc in islanders.RESOURCES:
        p.cards[rsrc] = 6
        if idx == 0:
          p.cards[rsrc] += 1
    self.c.player_data[0].cards["rsrc1"] -= 2
    # There are exactly two rsrc1 remaining (and nothing else). Player 1 will collect one of them.
    self.assertEqual(self.c.remaining_resources("rsrc1"), 2)
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 5
    self.c.handle_roll_dice()
    self.assertDictEqual(self.c.collect_counts, {0: 1, 1: 2, 2: 2})
    self.assertEqual(self.c.collect_idx, 0)
    self.handle(0, {"type": "collect", "selection": {"rsrc1": 1}})
    # There is exactly 1 rsrc1 remaining. Player 2 (next player) should have their count updated.
    # Player 3's count is not updated yet - that will happen after player 2 collects.
    self.assertDictEqual(self.c.collect_counts, {1: 1, 2: 2})
    with self.assertRaisesRegex(InvalidMove, "not enough {rsrc2} in the bank"):
      self.handle(1, {"type": "collect", "selection": {"rsrc2": 1}})
    self.handle(1, {"type": "collect", "selection": {"rsrc1": 1}})
    # Now that the bank is empty, player 3's collection is skipped.
    self.assertDictEqual(self.c.collect_counts, {})
    self.assertIsNone(self.c.collect_idx)
    self.assertEqual(self.c.turn_phase, "main")

  def testCollectDuringSettlementPhase(self):
    self.c.pieces.clear()
    self.c.game_phase = "place2"
    self.c.action_stack = ["road", "settle"]
    self.c.handle_settle([2, 4], 0)
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {0: 2})

    self.c.handle_collect(0, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.game_phase, "place2")
    self.assertEqual(self.c.turn_phase, "road")


class TestDiscovery(BaseInputHandlerTest):
  TEST_FILE = "sea_test.json"

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.tiles[(1, 3)].tile_type = "discover"
    self.c.tiles[(1, 3)].number = None
    self.c.discoverable_tiles = ["rsrc3"]
    self.c.discoverable_numbers = [10]

  def testDiscoverByRoad(self):
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 4, 3, 5], 0, "road", [("rsrc2", 1), ("rsrc4", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"rsrc3": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc2": 1, "rsrc4": 1})
    self.assertEqual(self.c.tiles[(1, 3)].tile_type, "rsrc3")
    self.assertEqual(self.c.tiles[(1, 3)].number, 10)
    self.assertFalse(self.c.discoverable_tiles)
    self.assertFalse(self.c.discoverable_numbers)
    self.assertEqual(self.c.turn_phase, "main")
    self.assertEqual(self.c.event_log[-1].public_text, "{player0} discovered {rsrc3}")

  def testDiscoverByShip(self):
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 4, 3, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"rsrc3": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.tiles[(1, 3)].tile_type, "rsrc3")
    self.assertEqual(self.c.tiles[(1, 3)].number, 10)
    self.assertFalse(self.c.discoverable_tiles)
    self.assertFalse(self.c.discoverable_numbers)
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverSea(self):
    self.c.discoverable_tiles = ["space"]
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 4, 3, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.tiles[(1, 3)].tile_type, "space")
    self.assertFalse(self.c.tiles[(1, 3)].is_land)
    self.assertIsNone(self.c.tiles[(1, 3)].number)
    self.assertFalse(self.c.discoverable_tiles)
    self.assertEqual(self.c.discoverable_numbers, [10])
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverDesert(self):
    self.c.discoverable_tiles = ["norsrc"]
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 4, 3, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.tiles[(1, 3)].tile_type, "norsrc")
    self.assertTrue(self.c.tiles[(1, 3)].is_land)
    self.assertIsNone(self.c.tiles[(1, 3)].number)
    self.assertFalse(self.c.discoverable_tiles)
    self.assertEqual(self.c.discoverable_numbers, [10])
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverAndCollect(self):
    self.c.discoverable_tiles = ["anyrsrc"]
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 4, 3, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.tiles[(1, 3)].tile_type, "anyrsrc")
    self.assertEqual(self.c.tiles[(1, 3)].number, 10)
    self.assertFalse(self.c.discoverable_tiles)
    self.assertFalse(self.c.discoverable_numbers)
    self.assertEqual(self.c.event_log[-1].public_text, "{player0} discovered {anyrsrc}")
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {0: 1})
    self.c.handle_collect(0, {"rsrc5": 1})
    final_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(final_rsrcs - new_rsrcs, {"rsrc5": 1})
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverDoesNotOverrideNumbers(self):
    self.c.tiles[(1, 3)].number = 3
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 4, 3, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"rsrc3": 1})
    self.assertEqual(self.c.tiles[(1, 3)].tile_type, "rsrc3")
    self.assertEqual(self.c.tiles[(1, 3)].number, 3)
    self.assertFalse(self.c.discoverable_tiles)
    self.assertEqual(self.c.discoverable_numbers, [10])
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverDuringExtraBuild(self):
    self.c.action_stack = ["extra_build"]
    self.c.extra_build_idx = 0
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 4, 3, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"rsrc3": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.turn_phase, "extra_build")
    self.assertEqual(self.c.extra_build_idx, 0)

  def testDiscoverAndCollectExtraBuild(self):
    self.c.discoverable_tiles = ["anyrsrc"]
    self.c.action_stack = ["extra_build"]
    self.c.extra_build_idx = 0
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 4, 3, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.turn_phase, "collect")
    self.c.handle_collect(0, {"rsrc5": 1})
    final_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(final_rsrcs - new_rsrcs, {"rsrc5": 1})
    self.assertEqual(self.c.turn_phase, "extra_build")
    self.assertEqual(self.c.extra_build_idx, 0)

  def testDiscoverDuringRoadBuilding1(self):
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.player_data[0].cards["roadbuilding"] = 1
    self.c.handle_play_dev("roadbuilding", None, 0)

    self.c.handle_road([2, 4, 3, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"rsrc3": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {})
    self.assertEqual(self.c.action_stack, ["dev_road"])

  def testDiscoverDuringRoadBuilding2(self):
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.player_data[0].cards["roadbuilding"] = 1
    self.c.handle_play_dev("roadbuilding", None, 0)

    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.action_stack, ["dev_road"])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})

    self.c.handle_road([2, 4, 3, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"rsrc3": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {})
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverAndCollectRoadBuilding1(self):
    self.c.discoverable_tiles = ["anyrsrc"]
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.player_data[0].cards["roadbuilding"] = 1
    self.c.handle_play_dev("roadbuilding", None, 0)

    self.c.handle_road([2, 4, 3, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {0: 1})
    self.c.handle_collect(0, {"rsrc5": 1})
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"rsrc5": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {})
    self.assertEqual(self.c.action_stack, ["dev_road"])

  def testDiscoverAndCollectRoadBuilding2(self):
    self.c.discoverable_tiles = ["anyrsrc"]
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.player_data[0].cards["roadbuilding"] = 1
    self.c.handle_play_dev("roadbuilding", None, 0)

    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.action_stack, ["dev_road"])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})

    self.c.handle_road([2, 4, 3, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "collect")
    self.assertDictEqual(self.c.collect_counts, {0: 1})
    self.c.handle_collect(0, {"rsrc5": 1})
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"rsrc5": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {})
    self.assertEqual(self.c.turn_phase, "main")


class TestDepletion(BaseInputHandlerTest):
  TEST_FILE = "sea_test.json"

  def setUp(self):
    super().setUp()
    self.c.placement_islands = [(-1, 3)]
    self.c.home_corners[1].append(islanders.CornerLocation(3, 3))
    self.c.tiles[(7, 7)].tile_type = "rsrc5"
    self.c.tiles[(7, 7)].is_land = True
    self.c.tiles[(7, 7)].number = 0
    self.c.tiles[(4, 4)].tile_type = "rsrc4"
    self.c.tiles[(4, 4)].is_land = True
    self.c.tiles[(4, 4)].number = 6
    self.c.tiles[(4, 2)].tile_type = "rsrc3"
    self.c.tiles[(4, 2)].is_land = True
    self.c.tiles[(4, 2)].number = 6
    self.c.recompute()
    self.c.add_piece(islanders.Piece(3, 3, "city", 1))
    self.c.add_road(Road([3, 5, 5, 5], "ship", 0))

  def testFirstDiscoverDoesNotDeplete(self):
    self.c.discoverable_numbers = [2]
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    self.assertEqual(self.c.tiles[(7, 7)].number, 2)
    self.assertEqual(self.c.action_stack, [])

  def testDepleteOne(self):
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    self.assertListEqual(self.c.action_stack, ["deplete"])
    self.c.handle_deplete(islanders.TileLocation(1, 5), 0)
    self.assertEqual(self.c.tiles[(7, 7)].number, 5)
    self.assertIsNone(self.c.tiles[(1, 5)].number)
    self.assertEqual(self.c.action_stack, [])

  def testNothingLeftToDeplete(self):
    self.c.tiles[(4, 2)].number = None
    self.c.tiles[(1, 3)].number = None
    self.c.tiles[(1, 5)].number = None
    self.c.tiles[(4, 4)].number = None
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    self.assertListEqual(self.c.action_stack, [])
    with self.assertRaisesRegex(InvalidMove, "cannot deplete.*right now"):
      self.c.handle_deplete(islanders.TileLocation(4, 4), 0)

  def testCannotDepleteForeignIslands(self):
    self.c.tiles[(7, 7)].number = 9
    self.c.tiles[(4, 8)].number = 0
    self.c.add_piece(islanders.Piece(8, 6, "settlement", 0))
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    self.c.add_road(Road([5, 7, 6, 6], "ship", 0))
    self.assertListEqual(self.c.action_stack, ["deplete"])
    with self.assertRaisesRegex(InvalidMove, "the home island"):
      self.c.handle_deplete(islanders.TileLocation(7, 7), 0)
    self.c.handle_deplete(islanders.TileLocation(1, 5), 0)

  def testCannotLeaveSettlementEmpty(self):
    self.c.tiles[(4, 4)].number = 9
    self.c.tiles[(1, 3)].number = None
    self.c.tiles[(4, 2)].number = None
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "at least one number next to"):
      self.c.handle_deplete(islanders.TileLocation(4, 4), 0)
    self.c.handle_deplete(islanders.TileLocation(1, 5), 0)

  def testMustTakeFromOwnSettlement(self):
    self.c.tiles[(4, 4)].number = 9
    self.c.tiles[(4, 2)].number = None
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "one of your"):
      self.c.handle_deplete(islanders.TileLocation(1, 3), 0)
    self.c.handle_deplete(islanders.TileLocation(4, 4), 0)

  def testCannotPutSixNextToEight(self):
    self.c.tiles[(4, 2)].number = None
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "6 and 8"):
      self.c.handle_deplete(islanders.TileLocation(4, 4), 0)
    self.c.tiles[(4, 4)].number = 8
    with self.assertRaisesRegex(InvalidMove, "6 and 8"):
      self.c.handle_deplete(islanders.TileLocation(4, 4), 0)
    self.c.handle_deplete(islanders.TileLocation(1, 5), 0)

  def testPutSixNextToEight(self):
    self.c.tiles[(1, 5)].number = 8
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "one of your"):
      self.c.handle_deplete(islanders.TileLocation(1, 3), 0)
    self.c.handle_deplete(islanders.TileLocation(1, 5), 0)

  def testDepleteNotYourOwn(self):
    self.c.pieces.pop((3, 5))
    self.c.add_piece(islanders.Piece(5, 5, "settlement", 0))
    self.c.tiles[(4, 2)].number = None
    self.c.tiles[(1, 3)].number = None
    self.c.tiles[(4, 4)].number = 9
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "at least one number next to"):
      self.c.handle_deplete(islanders.TileLocation(4, 4), 0)
    self.c.handle_deplete(islanders.TileLocation(1, 5), 0)

  def testDepleteNextToAnotherPlayer(self):
    self.c.pieces.pop((3, 5))
    self.c.add_piece(islanders.Piece(5, 5, "settlement", 0))
    self.c.pieces.pop((3, 3))
    self.c.add_piece(islanders.Piece(5, 3, "city", 1))
    self.c.add_piece(islanders.Piece(0, 4, "settlement", 1))
    self.c.tiles[(4, 2)].number = None
    self.c.tiles[(4, 4)].number = 9
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "at least one number next to"):
      self.c.handle_deplete(islanders.TileLocation(4, 4), 0)
    self.c.handle_deplete(islanders.TileLocation(1, 5), 0)

  def testNotYourOwnSixNextToEight(self):
    self.c.pieces.pop((3, 5))
    self.c.add_piece(islanders.Piece(5, 5, "settlement", 0))
    self.c.tiles[(4, 2)].number = None
    self.c.tiles[(1, 3)].number = None
    self.c.tiles[(4, 4)].number = 9
    self.c.tiles[(1, 5)].number = 8
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "at least one number next to"):
      self.c.handle_deplete(islanders.TileLocation(4, 4), 0)
    self.c.handle_deplete(islanders.TileLocation(1, 5), 0)

  def testLeaveEmptySettlement(self):
    self.c.tiles[(4, 2)].number = None
    self.c.tiles[(1, 3)].number = None
    self.c.tiles[(1, 5)].number = None
    self.c.tiles[(4, 4)].number = 9
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "must take a number"):
      self.c.handle_deplete(islanders.TileLocation(1, 5), 0)
    self.c.handle_deplete(islanders.TileLocation(4, 4), 0)

  def testLeaveEmptySettlementSixNextToEight(self):
    self.c.tiles[(4, 2)].number = None
    self.c.tiles[(1, 3)].number = None
    self.c.tiles[(1, 5)].number = None
    self.c.tiles[(4, 4)].number = 8
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    self.c.handle_deplete(islanders.TileLocation(4, 4), 0)

  def testLeaveEmptySettlementNotYourOwn(self):
    self.c.tiles[(4, 2)].number = 9
    self.c.tiles[(1, 3)].number = None
    self.c.tiles[(1, 5)].number = None
    self.c.tiles[(4, 4)].number = None
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    self.c.handle_deplete(islanders.TileLocation(4, 2), 0)

  def testBreakAllThreeRules(self):
    self.c.tiles[(4, 2)].number = 6
    self.c.tiles[(1, 3)].number = None
    self.c.tiles[(1, 5)].number = None
    self.c.tiles[(4, 4)].number = None
    self.c.add_road(Road([5, 5, 6, 6], "ship", 0))
    self.c.handle_deplete(islanders.TileLocation(4, 2), 0)


class TestTreasures(BaseInputHandlerTest):
  TEST_FILE = "treasure_test.json"

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.tiles[(4, 8)].tile_type = "discover"
    self.c.tiles[(4, 8)].number = None
    self.c.discoverable_tiles = ["norsrc"]

  def testDiscoverDevCard(self):
    self.c.dev_cards.append("market")
    self.c.discoverable_treasures.append("takedev")
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 6, 3, 7], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"market": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverDevCardReshuffle(self):
    self.c.options["shuffle_discards"].force(True)
    self.c.dev_cards.clear()
    self.c.discoverable_treasures.append("takedev")
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    with mock.patch.object(islanders.random, "shuffle", new=lambda cards: cards.sort()):
      self.c.handle_road([2, 6, 3, 7], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"yearofplenty": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverCollect(self):
    self.c.discoverable_treasures.append("collect1")
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 6, 3, 7], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "collect1")
    with self.assertRaises(game.NotYourTurn):
      self.handle(1, {"type": "collect", "rsrc5": 1})
    self.c.handle_collect(0, {"rsrc5": 1})
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"rsrc5": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})

  def testLimitedCollect(self):
    self.c.discoverable_treasures.append("collectpi")
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 6, 3, 7], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "collectpi")
    with self.assertRaisesRegex(InvalidMove, "may only select"):
      self.c.handle_collect(0, {"rsrc2": 1})
    self.c.handle_collect(0, {"rsrc3": 1})
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"rsrc3": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverRoadbuilding(self):
    self.c.discoverable_treasures.append("roadbuilding")
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([2, 6, 3, 7], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "dev_road")
    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([2, 4, 3, 3], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverGoldAndCollect(self):
    self.c.discoverable_tiles = ["anyrsrc"]
    self.c.treasures[islanders.CornerLocation(5, 7)] = "collect1"
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 5, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 7, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "collect")
    self.c.handle_collect(0, {"rsrc1": 1})
    self.assertEqual(self.c.turn_phase, "collect1")
    self.c.handle_collect(0, {"rsrc2": 1})
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 2, "rsrc2": 2})
    self.assertEqual(self.c.turn_phase, "main")

  def testRoadbuildingIntoSecondDiscover(self):
    self.c.dev_cards.append("market")
    self.c.treasures[islanders.CornerLocation(5, 5)] = "roadbuilding"
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "dev_road")
    self.c.handle_road([5, 5, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([6, 6, 8, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"market": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc2": 1})
    self.assertEqual(self.c.turn_phase, "main")

  def testChainedRoadbuilding(self):
    self.c.treasures[islanders.CornerLocation(6, 6)] = "roadbuilding"
    self.c.treasures[islanders.CornerLocation(8, 6)] = "roadbuilding"
    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 5, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "dev_road")
    self.c.handle_road([6, 6, 8, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.action_stack, ["dev_road"] * 3)
    self.c.handle_road([8, 6, 9, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([8, 4, 9, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([6, 4, 8, 4], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverSeaGivesTreasure(self):
    self.c.discoverable_tiles = ["space"]
    self.c.discoverable_treasures.append("collect1")
    self.c.handle_road([2, 6, 3, 7], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "collect1")

  def testDiscoverTwoTreasures(self):
    # build to a treasure while at the same time discovering a sea/desert tile
    self.c.discoverable_treasures.append("collect1")
    self.c.treasures[islanders.CornerLocation(5, 7)] = "collect2"
    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 5, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 7, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "collect1")
    self.c.handle_collect(0, {"rsrc5": 1})
    self.assertEqual(self.c.turn_phase, "collect2")
    self.c.handle_collect(0, {"rsrc4": 1, "rsrc3": 1})
    self.assertEqual(self.c.turn_phase, "main")

  def testDiscoverDuringSetup(self):
    self.c.treasures[(5, 5)] = "collect1"
    self.c.game_phase = "place2"
    self.c.action_stack = ["road"]
    self.c.roads.clear()
    self.c.pieces[(3, 5)].player = 1
    self.c.turn_idx = 1
    self.c.handle_road((3, 5, 5, 5), 1, "ship", [("rsrc1", 1), ("rsrc2", 2)])
    self.assertEqual(self.c.turn_idx, 1)
    self.assertEqual(self.c.turn_phase, "collect1")
    self.assertEqual(self.c.game_phase, "place2")
    self.c.handle_collect(1, {"rsrc5": 1})
    self.assertEqual(self.c.turn_idx, 0)
    self.assertEqual(self.c.action_stack, ["road", "settle"])
    self.assertEqual(self.c.game_phase, "place2")

  def testChainedDiscoverDuringSetup(self):
    self.c.treasures[(5, 5)] = "roadbuilding"
    self.c.game_phase = "place2"
    self.c.action_stack = ["road"]
    self.c.roads.clear()
    self.c.handle_road((3, 5, 5, 5), 0, "ship", [("rsrc1", 1), ("rsrc2", 2)])
    self.assertEqual(self.c.turn_idx, 0)
    self.assertEqual(self.c.turn_phase, "dev_road")
    self.assertEqual(self.c.game_phase, "place2")
    self.c.handle_road((5, 5, 6, 6), 0, "ship", [("rsrc1", 1), ("rsrc2", 2)])
    self.c.handle_road((6, 6, 8, 6), 0, "ship", [("rsrc1", 1), ("rsrc2", 2)])
    self.assertEqual(self.c.turn_idx, 0)
    self.assertEqual(self.c.turn_phase, "dice")
    self.assertEqual(self.c.game_phase, "main")


class TestBuryTreasures(BaseInputHandlerTest):
  TEST_FILE = "treasure_test.json"

  def setUp(self):
    super().setUp()
    self.c.options["bury_treasure"].force(True)

  def testCanBuryTreasure(self):
    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 5, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 7, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "bury")
    self.assertEqual(self.c.action_stack, ["dev_road", "dev_road", "bury"])
    self.c.handle_bury(0, True)
    self.assertEqual(self.c.player_data[0].buried_treasure, 1)
    self.assertEqual(self.c.turn_phase, "main")
    self.assertEqual(self.c.action_stack, [])

  def testDeclineToBuryTreasure(self):
    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 5, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 7, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "bury")
    self.assertEqual(self.c.action_stack, ["dev_road", "dev_road", "bury"])
    self.c.handle_bury(0, False)
    self.assertEqual(self.c.player_data[0].buried_treasure, 0)
    self.assertEqual(self.c.turn_phase, "dev_road")
    self.assertEqual(self.c.action_stack, ["dev_road", "dev_road"])

  def testCannotBuryMoreThanFour(self):
    self.c.player_data[0].buried_treasure = 4
    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 5, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 7, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "dev_road")
    self.assertEqual(self.c.action_stack, ["dev_road", "dev_road"])

  def testBurySecondTreasurePlacesPort(self):
    self.c.player_data[0].buried_treasure = 1
    self.c.treasures[islanders.CornerLocation(5, 7)] = "collect1"
    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 5, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 7, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "bury")
    self.assertEqual(self.c.action_stack, ["collect1", "bury"])
    self.c.handle_bury(0, True)
    self.assertEqual(self.c.player_data[0].buried_treasure, 2)
    self.assertEqual(self.c.action_stack, ["placeport"])
    self.assertEqual(self.c.turn_phase, "placeport")

  def testBuryRoadbuildingPlacesPort(self):
    self.c.player_data[0].buried_treasure = 1
    self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 5, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.c.handle_road([5, 7, 6, 6], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    self.assertEqual(self.c.turn_phase, "bury")
    self.assertEqual(self.c.action_stack, ["dev_road", "dev_road", "bury"])
    self.c.handle_bury(0, True)
    self.assertEqual(self.c.player_data[0].buried_treasure, 2)
    self.assertEqual(self.c.action_stack, ["placeport"])
    self.assertEqual(self.c.turn_phase, "placeport")

  def testBuryDuringSetup(self):
    self.c.treasures[(5, 5)] = "collect1"
    self.c.game_phase = "place2"
    self.c.action_stack = ["road"]
    self.c.roads.clear()
    self.c.pieces[(3, 5)].player = 1
    self.c.turn_idx = 1
    self.c.handle_road((3, 5, 5, 5), 1, "ship", [("rsrc1", 1), ("rsrc2", 2)])
    self.assertEqual(self.c.turn_idx, 1)
    self.assertEqual(self.c.turn_phase, "bury")
    self.assertEqual(self.c.game_phase, "place2")
    self.c.handle_bury(1, True)
    self.assertEqual(self.c.player_data[1].buried_treasure, 1)
    self.assertEqual(self.c.turn_idx, 0)
    self.assertEqual(self.c.turn_phase, "settle")
    self.assertEqual(self.c.game_phase, "place2")

  def testBurySecondDuringSetup(self):
    self.c.treasures[(5, 5)] = "collect1"
    self.c.game_phase = "place2"
    self.c.action_stack = ["road"]
    self.c.roads.clear()
    self.c.player_data[0].buried_treasure = 1
    self.c.handle_road((3, 5, 5, 5), 0, "ship", [("rsrc1", 1), ("rsrc2", 2)])
    self.assertEqual(self.c.turn_idx, 0)
    self.assertEqual(self.c.turn_phase, "bury")
    self.assertEqual(self.c.game_phase, "place2")

    self.c.handle_bury(0, True)
    self.assertEqual(self.c.player_data[0].buried_treasure, 2)
    self.assertEqual(self.c.turn_idx, 0)
    self.assertEqual(self.c.turn_phase, "placeport")
    self.assertEqual(self.c.game_phase, "place2")

    self.c.handle_place_port(0, (4, 6), 2, "rsrc1")
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc1"], 2)
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc3"], 4)
    self.assertEqual(self.c.turn_idx, 0)
    self.assertEqual(self.c.turn_phase, "dice")
    self.assertEqual(self.c.game_phase, "main")


class PlacePortTest(BaseInputHandlerTest):
  TEST_FILE = "treasure_test.json"

  def setUp(self):
    super().setUp()
    self.c.options["bury_treasure"].force(True)
    self.c.player_data[0].buried_treasure = 2
    self.c.action_stack = ["placeport"]

  def testInvalidPortType(self):
    with self.assertRaisesRegex(InvalidMove, "Unknown port type"):
      self.c.handle_place_port(0, (4, 6), 2, "space")
    with self.assertRaisesRegex(InvalidMove, "Unknown port type"):
      self.c.handle_place_port(0, (4, 6), 2, "gold")

  def testPlacedPortUpdatesTradeRatios(self):
    self.c.handle_place_port(0, (4, 6), 2, "rsrc1")
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc1"], 2)
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc3"], 4)
    self.assertEqual(self.c.player_data[0].trade_ratios.default_factory(), 4)

  def testPlaceOnLand(self):
    with self.assertRaisesRegex(InvalidMove, "place the port on {space}"):
      self.c.handle_place_port(0, (1, 5), 4, "rsrc1")

  def testPlaceBadRotation(self):
    with self.assertRaisesRegex(InvalidMove, "Invalid rotation"):
      self.c.handle_place_port(0, (4, 6), 2.5, "rsrc1")
    with self.assertRaisesRegex(InvalidMove, "Invalid rotation"):
      self.c.handle_place_port(0, (4, 6), -1, "rsrc1")
    with self.assertRaisesRegex(InvalidMove, "Invalid rotation"):
      self.c.handle_place_port(0, (4, 6), "left", "rsrc1")

  def testPlaceOnExistingPort(self):
    self.c.add_port(islanders.Port(4, 6, "rsrc2", 0))
    with self.assertRaisesRegex(InvalidMove, "already a port there"):
      self.c.handle_place_port(0, (4, 6), 2, "rsrc1")

  def testPlaceNotAttachedToSettlement(self):
    with self.assertRaisesRegex(InvalidMove, "next to one of your settlements"):
      self.c.handle_place_port(0, (4, 6), 0, "rsrc1")

  def testPlaceAlreadyTakenPort(self):
    self.c.add_port(islanders.Port(4, 6, "rsrc2", 0))
    with self.assertRaisesRegex(InvalidMove, "already taken"):
      self.c.handle_place_port(0, (4, 4), 1, "rsrc2")

  def testPlaceSharingCornerWithAnotherPort(self):
    self.c.add_port(islanders.Port(4, 6, "rsrc2", 2))
    self.c._compute_ports()
    with self.assertRaisesRegex(InvalidMove, "share a corner"):
      self.c.handle_place_port(0, (4, 4), 1, "rsrc1")


class TestRobberMovement(BaseInputHandlerTest):
  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.action_stack = ["rob", "robber"]
    self.c.handle_robber((4, 4), 1)
    self.c.action_stack = ["rob", "robber"]

  def testRobberInvalidMove(self):
    with self.assertRaises(InvalidMove):
      self.c.handle_robber((1, 1), 1)

  def testRobberInvalidMoveRegex(self):
    with self.assertRaisesRegex(InvalidMove, "valid land tile"):
      self.c.handle_robber((1, 1), 1)

  def testRobberStationaryMove(self):
    with self.assertRaises(InvalidMove):
      self.c.handle_robber(self.c.robber, 1)

  def testRobberStationaryMoveRegex(self):
    with self.assertRaisesRegex(InvalidMove, "You must move the robber."):
      self.c.handle_robber(self.c.robber, 1)

  def testRobberLandMove(self):
    with self.assertRaises(InvalidMove):
      self.c.handle_robber((4, 2), 1)

  def testRobberLandMoveRegex(self):
    with self.assertRaisesRegex(InvalidMove, "valid land tile"):
      self.c.handle_robber((4, 2), 1)

  def testRobberCannotDiscover(self):
    self.c.tiles[(1, 5)].tile_type = "discover"
    with self.assertRaisesRegex(InvalidMove, "valid land tile"):
      self.c.handle_robber((1, 5), 1)

  def testNoRobbingFromTwoPointsRegex(self):
    self.c.options["friendly_robber"].set(True)
    with self.assertRaisesRegex(InvalidMove, "Robbers refuse to rob such poor people."):
      self.c.handle_robber((4, 6), 0)

  def testRobbingFromMoreThanTwoPoints(self):
    self.c.options["friendly_robber"].set(True)
    self.c.add_piece(islanders.Piece(6, 2, "city", 1))
    self.c.handle_robber((4, 6), 0)
    self.assertEqual(self.c.event_log[-2].event_type, "robber")
    self.assertEqual(self.c.event_log[-1].event_type, "rob")
    self.assertIn("stole a card", self.c.event_log[-1].public_text)
    self.assertNotIn("stole a card", self.c.event_log[-1].secret_text)
    self.assertCountEqual(self.c.event_log[-1].visible_players, [0, 1])

  def testRobbingFromTwoPointsMixedPlayerRegex(self):
    self.c.options["friendly_robber"].set(True)
    self.c.add_piece(islanders.Piece(6, 2, "city", 1))
    self.c.add_player("green", "Player3")
    self.c.add_piece(islanders.Piece(2, 6, "city", 2))
    with self.assertRaisesRegex(InvalidMove, "Robbers refuse to rob such poor people."):
      self.c.handle_robber((4, 6), 0)

  def testNoRobbingFromTwoPointsWithHiddenRegex(self):
    self.c.options["friendly_robber"].set(True)
    self.c.player_data[1].cards.update({"library": 1})
    with self.assertRaisesRegex(InvalidMove, "Robbers refuse to rob such poor people."):
      self.c.handle_robber((4, 6), 0)

  def testRobbingFromSelfAtTwoPoints(self):
    self.c.options["friendly_robber"].set(True)
    self.c.add_piece(islanders.Piece(6, 2, "city", 1))
    self.c.handle_robber((7, 5), 0)


class TestPiratePlacement(BaseInputHandlerTest):
  TEST_FILE = "ship_test.json"

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_piece(islanders.Piece(5, 7, "settlement", 1))
    self.c.add_piece(islanders.Piece(8, 6, "settlement", 1))
    self.c.add_road(Road([6, 6, 8, 6], "ship", 1))
    self.c.pirate = islanders.TileLocation(4, 4)
    self.c.ships_moved = 0
    self.c.built_this_turn.clear()
    self.c.player_data[0].cards["rsrc1"] += 5
    self.c.player_data[0].cards["rsrc2"] += 5

  def testBuildNearPirate(self):
    old_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    with self.assertRaisesRegex(InvalidMove, "next to the pirate"):
      self.c.handle_road([3, 5, 5, 5], 0, "ship", [("rsrc1", 1), ("rsrc2", 1)])
    new_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
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
    self.c.action_stack = ["rob", "robber"]
    old_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    self.c.handle_pirate(2, [4, 6])
    new_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    self.assertEqual(new_count, old_count - 1)
    self.assertEqual(self.c.turn_phase, "main")

  def testMovePirateRobTwoPlayers(self):
    self.c.add_player("green", "Bob")
    self.c.turn_idx = 2
    self.c.action_stack = ["rob", "robber"]
    self.c._add_road(Road([3, 7, 5, 7], "ship", 1))
    self.c.handle_pirate(2, [4, 6])
    self.assertEqual(self.c.event_log[-1].public_text, "{player2} moved the pirate")
    self.assertEqual(self.c.turn_phase, "rob")
    self.assertCountEqual(self.c.rob_players, [0, 1])

  def testPirateDoesNotRobRoads(self):
    self.c.add_player("green", "Bob")
    self.c.turn_idx = 2
    self.c.action_stack = ["rob", "robber"]
    self.c._add_road(Road([3, 7, 5, 7], "road", 1))
    self.c.handle_pirate(2, [4, 6])
    self.assertEqual(self.c.turn_phase, "main")
    self.assertEqual(self.c.event_log[-1].public_text, "{player2} stole a card from {player0}")

  def testPirateCannotDiscover(self):
    self.c.turn_idx = 2
    self.c.action_stack = ["rob", "robber"]
    self.c.tiles[(7, 3)].tile_type = "discover"
    with self.assertRaisesRegex(InvalidMove, "before exploring"):
      self.c.handle_pirate(2, [7, 3])

  def testCannotMovePirateIfDisabled(self):
    self.c.options["pirate"].force(False)
    self.c.add_player("green", "Bob")
    self.c.turn_idx = 2
    self.c.action_stack = ["rob", "robber"]
    with self.assertRaisesRegex(InvalidMove, "not used"):
      self.c.handle_pirate(2, [4, 6])


@mock.patch.object(islanders.random, "randint", return_value=3.5)
class TestRobberDisabled(BreakpointTestMixin):
  def setUp(self):
    self.c = islanders.IslandersState()
    self.c.add_player("red", "player0")
    self.c.add_player("blue", "player1")
    self.c.add_player("green", "player2")
    islanders.BeginnerMap.mutate_options(self.c.options)
    islanders.BeginnerMap.init(self.c)
    self.c.options["robber"].force(False)
    self.g = islanders.IslandersGame()
    self.g.game = self.c
    self.g.scenario = "Beginner's Map"

  def testCanRobFromAnyoneIfBothDisabled(self, unused_randint):
    self.c.handle_roll_dice()
    self.assertEqual(self.c.turn_phase, "rob")
    self.assertCountEqual(self.c.rob_players, [1, 2])
    with self.assertRaisesRegex(InvalidMove, "Unknown"):
      self.c.handle_rob(1.0, 0)
    with self.assertRaisesRegex(InvalidMove, "Unknown"):
      self.c.handle_rob(-1, 0)
    with self.assertRaisesRegex(InvalidMove, "yourself"):
      self.c.handle_rob(0, 0)
    self.c.handle_rob(2, 0)
    self.assertEqual(sum(self.c.player_data[0].cards.values()), 4)
    self.assertEqual(sum(self.c.player_data[2].cards.values()), 2)

  def testCannotRobFromPlayersWithNoCards(self, unused_randint):
    self.assertEqual(sum(self.c.player_data[0].cards.values()), 3)
    self.assertEqual(sum(self.c.player_data[2].cards.values()), 3)
    self.c.player_data[1].cards.clear()
    self.c.handle_roll_dice()
    self.assertEqual(sum(self.c.player_data[0].cards.values()), 4)
    self.assertEqual(sum(self.c.player_data[2].cards.values()), 2)

  def testNoPlayersHaveCards(self, unused_randint):
    self.c.player_data[1].cards.clear()
    self.c.player_data[2].cards.clear()
    self.c.handle_roll_dice()
    self.assertEqual(sum(self.c.player_data[0].cards.values()), 3)
    self.assertEqual(sum(self.c.player_data[1].cards.values()), 0)
    self.assertEqual(sum(self.c.player_data[2].cards.values()), 0)


class TestHandleSettleInput(BaseInputHandlerTest):
  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    # Add this to home_corners to avoid getting a landing event.
    self.c.home_corners[0].append(self.c.corners_to_islands[(5, 3)])
    self.c._add_road(Road([5, 3, 6, 4], "road", 0))
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    self.c._add_road(Road([8, 4, 9, 3], "road", 0))

  def testSettle(self):
    resources = ["rsrc1", "rsrc2", "rsrc3", "rsrc4"]
    counts = [self.c.player_data[0].cards[x] for x in resources]
    self.handle(0, {"type": "settle", "location": [5, 3]})
    for rsrc, orig_count in zip(resources, counts):
      self.assertEqual(self.c.player_data[0].cards[rsrc], orig_count - 1)
    self.assertEqual(self.c.event_log[-1].event_type, "settlement")
    self.assertIn("built a settlement", self.c.event_log[-1].public_text)

  def testMustSettleNextToRoad(self):
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.handle(0, {"type": "settle", "location": [3, 3]})

  def testMustSettleNextToOwnRoad(self):
    self.c._add_road(Road([6, 6, 8, 6], "road", 1))
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.handle(0, {"type": "settle", "location": [8, 6]})

  def testCannotSettleTooClose(self):
    self.c._add_road(Road([6, 6, 8, 6], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.handle(0, {"type": "settle", "location": [9, 3]})
    # Validate both distance from own settlements and from opponents'.
    with self.assertRaisesRegex(InvalidMove, "cannot.*next to existing"):
      self.handle(0, {"type": "settle", "location": [6, 6]})

  def testCannotSettleSettledLocation(self):
    self.c._add_road(Road([5, 5, 6, 4], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.handle(0, {"type": "settle", "location": [8, 4]})
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.handle(0, {"type": "settle", "location": [5, 5]})
    # Also validate you cannot build on top of a city.
    self.c.handle_city([5, 5], 1)
    with self.assertRaisesRegex(InvalidMove, "cannot.*settle on top of"):
      self.handle(0, {"type": "settle", "location": [5, 5]})

  def testMustSettleValidLocation(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple of size 2"):
      self.handle(0, {"type": "settle", "location": [2]})

  def testCannotBuildTooManySettlements(self):
    self.c.add_piece(islanders.Piece(2, 4, "settlement", 0))
    self.c.add_piece(islanders.Piece(2, 6, "settlement", 0))
    self.c.add_piece(islanders.Piece(8, 6, "settlement", 0))
    self.c.add_piece(islanders.Piece(8, 2, "settlement", 0))
    with self.assertRaisesRegex(InvalidMove, "settlements remaining"):
      self.handle(0, {"type": "settle", "location": [5, 3]})

    self.c.pieces[(2, 4)].piece_type = "city"
    self.c.pieces[(2, 6)].piece_type = "city"
    self.c.pieces[(8, 6)].piece_type = "city"
    self.c.pieces[(8, 2)].piece_type = "city"
    with self.assertRaisesRegex(InvalidMove, "cities remaining"):
      self.handle(0, {"type": "city", "location": [8, 4]})

  def testCannotBuildConqueredSettlement(self):
    for loc in [(4, 4), (4, 6), (7, 5)]:
      self.c.tiles[loc].barbarians = 1
      self.c.tiles[loc].conquered = True
    self.c.pieces.pop((5, 5))
    self.c.turn_idx = 1
    with self.assertRaisesRegex(InvalidMove, "conquered"):
      self.handle(1, {"type": "settle", "location": [5, 5]})
    self.handle(1, {"type": "settle", "location": [6, 6]})


class TestInitialSettlement(BaseInputHandlerTest):
  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.pieces.clear()
    self.c.roads.clear()
    self.c.game_phase = "place1"
    self.c.action_stack = ["road", "settle"]
    self.c.turn_idx = 0
    for p in self.c.player_data:
      p.cards.clear()

  def testPlaceFirstSettlement(self):
    self.handle(0, {"type": "settle", "location": [3, 7]})
    self.handle(0, {"type": "road", "location": [3, 7, 5, 7]})
    self.handle(1, {"type": "settle", "location": [8, 4]})
    self.handle(1, {"type": "road", "location": [6, 4, 8, 4]})
    self.assertEqual(self.c.game_phase, "place2")
    self.assertEqual(self.c.turn_phase, "settle")
    self.assertEqual(self.c.turn_idx, 1)
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc3"], 2)
    self.assertEqual(self.c.player_data[1].trade_ratios["rsrc1"], 2)

  def testCannotSettleOutOfBounds(self):
    self.c.tiles[(4, 2)].tile_type = "rsrc5"
    self.c.tiles[(4, 2)].is_land = True
    self.c.tiles[(4, 4)].tile_type = "space"
    self.c.tiles[(4, 4)].is_land = False
    with self.assertRaisesRegex(InvalidMove, "in bounds"):
      self.handle(0, {"type": "settle", "location": [5, 1]})
    with self.assertRaisesRegex(InvalidMove, "on land"):
      self.handle(0, {"type": "settle", "location": [2, 4]})

  def testFirstRoadMustBeNextToFirstSettlement(self):
    self.handle(0, {"type": "settle", "location": [3, 7]})
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.handle(0, {"type": "road", "location": [2, 6, 3, 5]})

  def testSecondRoadCannotBeNextToFirstSettlement(self):
    self.handle(0, {"type": "settle", "location": [3, 7]})
    self.handle(0, {"type": "road", "location": [3, 7, 5, 7]})
    self.handle(1, {"type": "settle", "location": [8, 4]})
    self.handle(1, {"type": "road", "location": [6, 4, 8, 4]})
    self.handle(1, {"type": "settle", "location": [5, 5]})
    with self.assertRaisesRegex(InvalidMove, "next to your settlement"):
      self.handle(1, {"type": "road", "location": [5, 3, 6, 4]})
    with self.assertRaisesRegex(InvalidMove, "next to your second settlement"):
      self.handle(1, {"type": "road", "location": [8, 4, 9, 5]})
    self.handle(1, {"type": "road", "location": [5, 5, 6, 4]})

  def testReceiveSecondResources(self):
    self.c.game_phase = "place2"
    self.handle(0, {"type": "settle", "location": [5, 5]})
    expected = collections.Counter({"rsrc1": 1, "rsrc4": 1, "rsrc5": 1})
    received = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(received - expected, {})
    self.assertDictEqual(expected - received, {})
    self.handle(0, {"type": "road", "location": [3, 5, 5, 5]})
    self.assertEqual(self.c.game_phase, "main")
    self.assertEqual(self.c.turn_phase, "dice")
    self.assertEqual(self.c.turn_idx, 0)

  def testReceiveSecondResourcesFromSea(self):
    self.c.game_phase = "place2"
    self.c.tiles[(7, 3)].tile_type = "rsrc5"  # Also test two of the same resource.
    self.handle(0, {"type": "settle", "location": [5, 3]})
    expected = collections.Counter({"rsrc5": 2})
    received = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(received - expected, {})
    self.assertDictEqual(expected - received, {})


class TestSettlementTurnOrder(BreakpointTestMixin):
  def setUp(self):
    self.c = islanders.IslandersState()
    self.c.add_player("red", "player0")
    self.c.add_player("blue", "player1")
    self.c.add_player("green", "player2")
    islanders.SeafarerDesert.mutate_options(self.c.options)
    islanders.SeafarerDesert.init(self.c)
    self.g = islanders.IslandersGame()
    self.g.game = self.c
    self.g.scenario = "Through the Desert"

  def testThreeSettlements(self):
    self.c.options["placements"].force(("settlement", "settlement", "settlement"))
    self.handle(0, {"type": "settle", "location": [15, 7]})
    self.handle(0, {"type": "ship", "location": [15, 7, 17, 7]})
    self.handle(1, {"type": "settle", "location": [15, 5]})
    self.handle(1, {"type": "road", "location": [15, 5, 17, 5]})
    self.handle(2, {"type": "settle", "location": [12, 6]})
    self.handle(2, {"type": "road", "location": [12, 6, 14, 6]})
    self.handle(2, {"type": "settle", "location": [12, 4]})
    self.handle(2, {"type": "road", "location": [12, 4, 14, 4]})
    self.handle(1, {"type": "settle", "location": [9, 7]})
    self.handle(1, {"type": "ship", "location": [9, 7, 11, 7]})
    self.handle(0, {"type": "settle", "location": [9, 5]})
    self.handle(0, {"type": "road", "location": [9, 5, 11, 5]})
    self.handle(0, {"type": "settle", "location": [9, 3]})
    self.handle(0, {"type": "ship", "location": [9, 3, 11, 3]})
    self.handle(1, {"type": "settle", "location": [6, 6]})
    self.handle(1, {"type": "road", "location": [6, 6, 8, 6]})
    self.handle(2, {"type": "settle", "location": [6, 4]})
    self.handle(2, {"type": "road", "location": [6, 4, 8, 4]})

    self.assertEqual(self.c.game_phase, "main")
    self.assertEqual(self.c.turn_phase, "dice")
    self.assertEqual(self.c.turn_idx, 0)

    counts = collections.Counter(piece.piece_type for piece in self.c.pieces.values())
    self.assertDictEqual(counts, {"settlement": 9})

    counts = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(+counts - collections.Counter({"rsrc4": 1, "rsrc5": 1}), {})
    counts = collections.Counter(self.c.player_data[1].cards)
    self.assertDictEqual(+counts - collections.Counter({"rsrc2": 1, "rsrc3": 1, "rsrc4": 1}), {})
    counts = collections.Counter(self.c.player_data[2].cards)
    self.assertDictEqual(+counts - collections.Counter({"rsrc3": 2, "rsrc4": 1}), {})

  def testSettlementCity(self):
    self.c.options["placements"].force(("settlement", "city"))
    self.handle(0, {"type": "settle", "location": [15, 7]})
    self.handle(0, {"type": "ship", "location": [15, 7, 17, 7]})
    self.handle(1, {"type": "settle", "location": [15, 5]})
    self.handle(1, {"type": "road", "location": [15, 5, 17, 5]})
    self.handle(2, {"type": "settle", "location": [12, 6]})
    self.handle(2, {"type": "road", "location": [12, 6, 14, 6]})
    self.handle(2, {"type": "settle", "location": [12, 4]})
    self.handle(2, {"type": "road", "location": [12, 4, 14, 4]})
    self.handle(1, {"type": "settle", "location": [9, 7]})
    self.handle(1, {"type": "ship", "location": [9, 7, 11, 7]})
    self.handle(0, {"type": "settle", "location": [9, 5]})
    self.handle(0, {"type": "road", "location": [9, 5, 11, 5]})

    self.assertEqual(self.c.game_phase, "main")
    self.assertEqual(self.c.turn_phase, "dice")
    self.assertEqual(self.c.turn_idx, 0)

    self.assertEqual(len(self.c.pieces), 6)
    counts = collections.Counter(self.c.pieces[r].piece_type for r in [(15, 7), (15, 5), (12, 6)])
    self.assertDictEqual(counts, {"settlement": 3})
    counts = collections.Counter(self.c.pieces[r].piece_type for r in [(12, 4), (9, 7), (9, 5)])
    self.assertDictEqual(counts, {"city": 3})

    counts = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(+counts - collections.Counter({"rsrc2": 1, "rsrc3": 1, "rsrc5": 1}), {})
    counts = collections.Counter(self.c.player_data[1].cards)
    self.assertDictEqual(+counts - collections.Counter({"rsrc2": 1, "rsrc4": 1}), {})
    counts = collections.Counter(self.c.player_data[2].cards)
    self.assertDictEqual(+counts - collections.Counter({"rsrc4": 1, "rsrc5": 1}), {})


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
      self.handle(0, {"type": "road", "location": [3, 3, 5, 3]})

  def testRoadsMustConnectToSelf(self):
    # Validate that roads must connect to your own roads, not opponents'.
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.handle(0, {"type": "road", "location": [6, 6, 8, 6]})

  def testBuildRoad(self):
    count2 = self.c.player_data[0].cards["rsrc2"]
    count4 = self.c.player_data[0].cards["rsrc4"]
    self.handle(0, {"type": "road", "location": [5, 3, 6, 4]})
    # Validate that resources were taken away.
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], count2 - 1)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], count4 - 1)
    # Test both connection to a road and connection to a settlement.
    self.handle(0, {"type": "road", "location": [8, 4, 9, 3]})
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], count2 - 2)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], count4 - 2)
    self.assertEqual(self.c.event_log[-1].event_type, "road")
    self.assertIn("built a road", self.c.event_log[-1].public_text)

  def testCannotBuildTooManyRoads(self):
    AddThirteenRoads(self.c)
    self.handle(0, {"type": "road", "location": [8, 4, 9, 5]})
    with self.assertRaisesRegex(InvalidMove, "no roads remaining"):
      self.handle(0, {"type": "road", "location": [5, 3, 6, 4]})

  def testCanPlayRoadBuildingWithOneRoadLeft(self):
    AddThirteenRoads(self.c)
    self.c.player_data[0].cards["roadbuilding"] += 1
    self.handle(0, {"type": "play_dev", "card_type": "roadbuilding"})
    self.handle(0, {"type": "road", "location": [8, 4, 9, 5]})
    self.assertEqual(self.c.turn_phase, "main")

  def testRoadBuildingDoesNotEndIfShipsLeft(self):
    self.c.options["seafarers"].value = True
    AddThirteenRoads(self.c)
    self.c.player_data[0].cards["roadbuilding"] += 1
    self.handle(0, {"type": "play_dev", "card_type": "roadbuilding"})
    self.handle(0, {"type": "road", "location": [8, 4, 9, 5]})
    self.assertEqual(self.c.turn_phase, "dev_road")

  def testCannotPlayRoadBuildingAtMaxRoads(self):
    AddThirteenRoads(self.c)
    self.handle(0, {"type": "road", "location": [8, 4, 9, 5]})
    self.c.player_data[0].cards["roadbuilding"] += 1
    with self.assertRaisesRegex(InvalidMove, "no roads remaining"):
      self.handle(0, {"type": "play_dev", "card_type": "roadbuilding"})

  def testCannotBuildWithoutResources(self):
    self.c.player_data[0].cards["rsrc2"] = 0
    with self.assertRaisesRegex(InvalidMove, "need an extra 1 {rsrc2}"):
      self.handle(0, {"type": "road", "location": [5, 3, 6, 4]})

  def testRoadLocationMustBeAnEdge(self):
    with self.assertRaisesRegex(InvalidMove, "not a valid edge"):
      self.handle(0, {"type": "road", "location": [3, 3, 6, 4]})

  def testRoadLocationMustBeValid(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple"):
      self.handle(0, {"type": "road", "location": [2, 3, 4]})
    with self.assertRaisesRegex(AssertionError, "must be left"):
      self.handle(0, {"type": "road", "location": [6, 4, 5, 3]})

  def testCannotBuildOnWater(self):
    self.c.add_tile(islanders.Tile(13, 3, "space", False, None))  # Avoid out of bound issues
    self.c._add_road(Road([8, 4, 9, 3], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "two land tiles"):
      self.handle(0, {"type": "road", "location": [9, 3, 11, 3]})

  def testCannotBuildAcrossOpponentSettlement(self):
    self.c._add_road(Road([5, 5, 6, 4], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.handle(0, {"type": "road", "location": [3, 5, 5, 5]})

  def testCannotBuildConqueredRoad(self):
    for loc in [(4, 4), (4, 6), (7, 5)]:
      self.c.tiles[loc].barbarians = 1
      self.c.tiles[loc].conquered = True
    self.c.roads[(5, 5, 6, 6)].conquered = True
    self.c.turn_idx = 1
    with self.assertRaisesRegex(InvalidMove, "conquered"):
      self.handle(1, {"type": "road", "location": [3, 5, 5, 5]})

  def testCannotAttachToConqueredRoad(self):
    for loc in [(4, 4), (4, 6), (7, 5)]:
      self.c.tiles[loc].barbarians = 1
      self.c.tiles[loc].conquered = True
    self.c.roads[(5, 5, 6, 6)].conquered = True
    self.c.turn_idx = 1
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.handle(1, {"type": "road", "location": [5, 7, 6, 6]})


class TestHandleShipInput(BaseInputHandlerTest):
  TEST_FILE = "sea_test.json"

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_tile(islanders.Tile(-2, 6, "space", False, None))
    self.c.add_tile(islanders.Tile(-2, 4, "rsrc5", True, 4))

  def testShipsMustConnectToNetwork(self):
    with self.assertRaisesRegex(InvalidMove, "Ships.*must be connected.*ship network"):
      self.handle(0, {"type": "ship", "location": [6, 4, 8, 4]})

  def testShipsCannotConnectToRoads(self):
    self.c._add_road(Road([2, 4, 3, 5], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "must be connected.*ship network"):
      self.handle(0, {"type": "ship", "location": [2, 4, 3, 3]})
    # Verify that you can build a road in that same spot that you can't build a ship.
    self.handle(0, {"type": "road", "location": [2, 4, 3, 3]})

  def testBuildShip(self):
    old_counts = {x: self.c.player_data[0].cards[x] for x in islanders.RESOURCES}
    self.handle(0, {"type": "ship", "location": [3, 5, 5, 5]})
    new_counts = {x: self.c.player_data[0].cards[x] for x in islanders.RESOURCES}
    self.assertEqual(new_counts.pop("rsrc1"), old_counts.pop("rsrc1") - 1)
    self.assertEqual(new_counts.pop("rsrc2"), old_counts.pop("rsrc2") - 1)
    # Validate that no other resources were deducted.
    self.assertDictEqual(new_counts, old_counts)

  def testNotEnoughResources(self):
    self.c.player_data[0].cards.update({"rsrc1": 0, "rsrc2": 1, "rsrc4": 1})
    with self.assertRaisesRegex(InvalidMove, "1 {rsrc1}"):
      self.handle(0, {"type": "ship", "location": [3, 5, 5, 5]})

  def testCannotBuildOutOfBounds(self):
    self.c._add_road(Road([2, 6, 3, 5], "ship", 0))
    self.c._add_road(Road([0, 6, 2, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "out of bounds"):
      self.handle(0, {"type": "ship", "location": [-1, 7, 0, 6]})

  def testCannotBuildOnLand(self):
    self.c._add_road(Road([2, 6, 3, 5], "ship", 0))
    self.c._add_road(Road([0, 6, 2, 6], "ship", 0))
    self.c._add_road(Road([-1, 5, 0, 6], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "must be water"):
      self.handle(0, {"type": "ship", "location": [-1, 5, 0, 4]})

  def testCannotBuildOnRoad(self):
    self.c._add_road(Road([2, 6, 3, 5], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "already a road"):
      self.handle(0, {"type": "ship", "location": [2, 6, 3, 5]})

  def testCanStillBuildWithTooManyRoads(self):
    roads = [
        [-4, 4, -3, 3], [-3, 3, -1, 3], [-1, 3, 0, 2], [0, 2, 2, 2], [2, 2, 3, 3],
        [-4, 4, -3, 5], [-3, 5, -1, 5], [-1, 5, 0, 4], [-1, 3, 0, 4], [0, 4, 2, 4], [2, 4, 3, 3],
        [-1, 5, 0, 6], [0, 6, 2, 6], [2, 4, 3, 5], [2, 6, 3, 5],
    ]  # fmt: skip
    for road in roads:
      self.c._add_road(Road(road, "road", 0))
    self.assertEqual(
      len([x for x in self.c.roads.values() if x.player == 0 and x.road_type == "road"]), 15
    )
    self.handle(0, {"type": "ship", "location": [3, 5, 5, 5]})

  def testRoadBuildingCanBuildShips(self):
    self.c.player_data[0].cards.clear()
    self.c.action_stack = ["dev_road", "dev_road"]
    self.handle(0, {"type": "ship", "location": [3, 5, 5, 5]})
    self.assertEqual(self.c.action_stack, ["dev_road"])
    self.handle(0, {"type": "ship", "location": [5, 5, 6, 4]})
    self.assertEqual(self.c.turn_phase, "main")

  def testRoadBuildingCanBuildMixed(self):
    self.c.player_data[0].cards.clear()
    self.c.action_stack = ["dev_road", "dev_road"]
    self.handle(0, {"type": "road", "location": [2, 4, 3, 5]})
    self.assertEqual(self.c.action_stack, ["dev_road"])
    self.handle(0, {"type": "ship", "location": [3, 5, 5, 5]})
    self.assertEqual(self.c.turn_phase, "main")

  def testCanBuildShipInPlacePhase(self):
    self.c.game_phase = "place2"
    self.c.action_stack = ["road"]
    self.c.add_piece(islanders.Piece(5, 7, "settlement", 0))
    self.handle(0, {"type": "ship", "location": [5, 7, 6, 6]})
    self.assertEqual(self.c.game_phase, "main")

  def testCannotBuildTooManyShips(self):
    roads = [
        [2, 4, 3, 5], [2, 6, 3, 5], [2, 6, 3, 7], [3, 7, 5, 7], [5, 7, 6, 6], [5, 5, 6, 6],
        [5, 5, 6, 4], [6, 4, 8, 4], [8, 4, 9, 5], [6, 6, 8, 6], [8, 6, 9, 5],
        [5, 3, 6, 4], [5, 3, 6, 2], [8, 4, 9, 3], [8, 2, 9, 3],
    ]  # fmt: skip
    for road in roads:
      self.c._add_road(Road(road, "ship", 0))
    self.assertEqual(
      len([x for x in self.c.roads.values() if x.player == 0 and x.road_type == "ship"]), 15
    )
    with self.assertRaisesRegex(InvalidMove, "no ships remaining"):
      self.handle(0, {"type": "ship", "location": [6, 2, 8, 2]})


class TestShipOpenClosedCalculation(BaseInputHandlerTest):
  TEST_FILE = "sea_test.json"

  def testBasicMovable(self):
    road1_loc = (3, 5, 5, 5)
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.assertTrue(self.c.roads[road1_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.assertEqual(self.c.roads[road1_loc].source, (3, 5))

    road2_loc = (5, 5, 6, 6)
    self.c.add_road(Road(road2_loc, "ship", 0))
    self.assertFalse(self.c.roads[road1_loc].movable)  # Original no longer movable
    self.assertFalse(self.c.roads[road1_loc].closed)  # Should still be open
    self.assertEqual(self.c.roads[road1_loc].source, (3, 5))
    self.assertTrue(self.c.roads[road2_loc].movable)
    self.assertFalse(self.c.roads[road2_loc].closed)
    self.assertEqual(self.c.roads[road2_loc].source, (3, 5))

  def testBasicOpenClosed(self):
    road1_loc = (2, 6, 3, 5)
    road2_loc = (2, 6, 3, 7)
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.c.add_road(Road(road2_loc, "ship", 0))
    self.assertFalse(self.c.roads[road1_loc].movable)
    self.assertTrue(self.c.roads[road2_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.assertFalse(self.c.roads[road2_loc].closed)
    self.c.add_piece(islanders.Piece(3, 7, "settlement", 0))
    self.assertTrue(self.c.roads[road1_loc].closed)
    self.assertTrue(self.c.roads[road2_loc].closed)
    # We don't assert on movable here - once the shipping path is closed, movable is irrelevant.

  def testCanClosePathFromOtherSide(self):
    # Same test as basic open closed, but put the settlement in first. The ship's source
    # will be the far settlement, but this shouldn't stop the DFS from doing its thing.
    road1_loc = (2, 6, 3, 5)
    road2_loc = (2, 6, 3, 7)
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.c.add_piece(islanders.Piece(3, 7, "settlement", 0))
    self.assertTrue(self.c.roads[road1_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.c.add_road(Road(road2_loc, "ship", 0))
    self.assertTrue(self.c.roads[road1_loc].closed)
    self.assertTrue(self.c.roads[road2_loc].closed)

  def testDontConsiderOtherPlayersShips(self):
    # Test that movable does not consider other players' ships or settlements.
    road1_loc = (2, 6, 3, 5)
    road2_loc = (2, 6, 3, 7)
    self.c.add_piece(islanders.Piece(3, 7, "settlement", 1))
    self.c.add_road(Road(road1_loc, "ship", 0))
    self.assertTrue(self.c.roads[road1_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.c.add_road(Road(road2_loc, "ship", 1))
    self.assertTrue(self.c.roads[road1_loc].movable)
    self.assertFalse(self.c.roads[road1_loc].closed)
    self.assertTrue(self.c.roads[road2_loc].movable)
    self.assertFalse(self.c.roads[road2_loc].closed)

  def testBranchingOpenClosedPaths(self):
    self.c.add_piece(islanders.Piece(8, 6, "settlement", 0))
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
    self.assertEqual(self.c.roads[road4_loc].source, (8, 6))

    # The settlement: after settling the third island, all roads should be closed.
    self.c.add_piece(islanders.Piece(5, 7, "settlement", 0))
    self.assertTrue(self.c.roads[road4_loc].closed)

  def testCloseMiddleOfPath(self):
    # We build a shipping route past an island, then settle the island, and validate that the
    # ships on the other side of the route are still open and get updated correctly.
    locs = [(2, 4, 3, 5), (2, 4, 3, 3), (3, 3, 5, 3), (5, 3, 6, 4)]
    for loc in locs[:-1]:
      self.c.add_road(Road(loc, "ship", 0))

    for loc in locs[:-1]:
      with self.subTest(loc=loc):
        self.assertEqual(self.c.roads[loc].source, (3, 5))

    self.c.add_piece(islanders.Piece(3, 3, "settlement", 0))
    for loc in locs[:-1]:
      with self.subTest(loc=loc):
        self.assertEqual(self.c.roads[loc].source, (3, 5))
    self.assertTrue(self.c.roads[locs[-2]].movable)

    self.c.add_road(Road(locs[-1], "ship", 0))
    self.assertFalse(self.c.roads[locs[-2]].movable)
    self.assertTrue(self.c.roads[locs[-1]].movable)
    self.assertFalse(self.c.roads[locs[-2]].closed)
    self.assertFalse(self.c.roads[locs[-1]].closed)

  def testReturnToOrigin(self):
    road_locs = [(3, 5, 5, 5), (5, 5, 6, 6), (5, 7, 6, 6), (3, 7, 5, 7), (2, 6, 3, 7), (2, 6, 3, 5)]
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
    self.c.add_piece(islanders.Piece(5, 7, "settlement", 0))
    for loc in road_locs:
      with self.subTest(loc=loc):
        self.assertTrue(self.c.roads[loc].closed)

  def testMakeALoop(self):
    first_loc = (3, 5, 5, 5)
    self.c.add_road(Road(first_loc, "ship", 0))
    road_locs = [(5, 5, 6, 4), (6, 4, 8, 4), (8, 4, 9, 5), (5, 5, 6, 6), (6, 6, 8, 6), (8, 6, 9, 5)]
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
    ]  # fmt: skip

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
    self.c.add_piece(islanders.Piece(9, 5, "settlement", 0))
    for loc in road_locs + bonus_locs:
      with self.subTest(loc=loc):
        self.assertTrue(self.c.roads[loc].closed)

  def testRecomputeMovableAfterShipMoveToDifferentNetwork(self):
    self.c.add_tile(islanders.Tile(-2, 6, "space", False, None))  # Avoid out of bound issues
    self.c.add_piece(islanders.Piece(9, 5, "settlement", 0))
    self.c.add_piece(islanders.Piece(3, 7, "settlement", 0))
    roads = [(2, 6, 3, 5), (8, 4, 9, 5), (6, 4, 8, 4)]
    for road in roads:
      self.c.add_road(Road(road, "ship", 0))
    # Start with one ship attached to 3, 5, and two ships connected to 9, 5.
    for road in roads:
      self.assertFalse(self.c.roads[road].closed)
    self.assertTrue(self.c.roads[roads[0]].movable)
    self.assertTrue(self.c.roads[roads[2]].movable)
    self.assertFalse(self.c.roads[roads[1]].movable)
    self.assertEqual(self.c.roads[roads[0]].source, (3, 5))
    self.assertEqual(self.c.roads[roads[1]].source, (9, 5))
    self.assertEqual(self.c.roads[roads[2]].source, (9, 5))

    # Move the outermost ship to attach to 3, 5. Its source should change. Also,
    # the ship that remains attached to 9, 5 should become movable again.
    new_loc = (0, 6, 2, 6)
    self.c.built_this_turn.clear()
    self.handle(0, {"type": "move_ship", "from": roads[2], "to": new_loc})
    self.assertEqual(self.c.roads[new_loc].source, (3, 5))
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
    self.handle(0, {"type": "move_ship", "from": roads[1], "to": last_loc})
    self.assertIn(self.c.roads[last_loc].source, [(3, 5), (3, 7)])
    self.assertTrue(self.c.roads[last_loc].closed)
    self.assertTrue(self.c.roads[roads[0]].closed)
    self.assertFalse(self.c.roads[new_loc].closed)
    self.assertTrue(self.c.roads[new_loc].movable)


class TestShipMovement(BaseInputHandlerTest):
  TEST_FILE = "sea_test.json"

  def setUp(self):
    super().setUp()
    self.c.add_road(Road([3, 5, 5, 5], "ship", 0))

  def testMoveShip(self):
    self.c.built_this_turn.clear()
    self.handle(0, {"type": "move_ship", "from": [3, 5, 5, 5], "to": [2, 4, 3, 5]})
    self.assertEqual(self.c.event_log[-1].event_type, "move_ship")

  def testInvalidInput(self):
    with self.assertRaisesRegex(InvalidMove, "should be a tuple of size 4"):
      self.handle(0, {"type": "move_ship", "from": [2, 4, 3, 5], "to": [5, 5, 4]})
    with self.assertRaisesRegex(InvalidMove, "should be a tuple of size 4"):
      self.handle(0, {"type": "move_ship", "from": [2, 4, 3, 5, 5], "to": [5, 5, 6, 4]})

  def testMustMoveExistingShip(self):
    with self.assertRaisesRegex(InvalidMove, "do not have a ship"):
      self.handle(0, {"type": "move_ship", "from": [2, 4, 3, 5], "to": [5, 5, 6, 4]})

  def testNewLocationMustConnectToNetwork(self):
    self.c.add_road(Road([5, 5, 6, 4], "ship", 0))
    self.c.built_this_turn.clear()
    # Extra check: the new location is a location that would be connected to the network
    # if the ship were not moving.
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.handle(0, {"type": "move_ship", "from": [5, 5, 6, 4], "to": [6, 4, 8, 4]})
    # Check that the old ship is still there.
    self.assertIn((5, 5, 6, 4), self.c.roads)

  def testCannotMoveOnTopOfExistingShip(self):
    self.c.add_road(Road([2, 4, 3, 5], "ship", 0))
    self.c.built_this_turn.clear()
    with self.assertRaisesRegex(InvalidMove, "already a ship"):
      self.handle(0, {"type": "move_ship", "from": [3, 5, 5, 5], "to": [2, 4, 3, 5]})

  def testCannotMoveRoads(self):
    self.c.add_road(Road([2, 4, 3, 5], "road", 0))
    self.c.built_this_turn.clear()
    with self.assertRaisesRegex(InvalidMove, "only move ships"):
      self.handle(0, {"type": "move_ship", "from": [2, 4, 3, 5], "to": [2, 6, 3, 5]})

  def testCannotMoveOtherPlayersShips(self):
    self.c.add_piece(islanders.Piece(9, 5, "settlement", 1))
    self.c.add_road(Road([8, 4, 9, 5], "ship", 1))
    self.c.built_this_turn.clear()
    with self.assertRaisesRegex(InvalidMove, "only move your"):
      self.handle(0, {"type": "move_ship", "from": [8, 4, 9, 5], "to": [2, 4, 3, 5]})

  def testCannotMoveShipOnClosedRoute(self):
    self.c.add_piece(islanders.Piece(3, 7, "settlement", 0))
    self.c.add_road(Road([2, 6, 3, 5], "ship", 0))
    self.c.add_road(Road([2, 6, 3, 7], "ship", 0))
    self.c.built_this_turn.clear()
    with self.assertRaisesRegex(InvalidMove, "that connects two"):
      self.handle(0, {"type": "move_ship", "from": [2, 6, 3, 7], "to": [2, 4, 3, 5]})
    # Validate that moving a different ship here will work.
    self.handle(0, {"type": "move_ship", "from": [3, 5, 5, 5], "to": [2, 4, 3, 5]})

  def testMustMoveShipAtEndOfRoute(self):
    self.c.add_road(Road([5, 5, 6, 4], "ship", 0))
    self.c.built_this_turn.clear()
    with self.assertRaisesRegex(InvalidMove, "at the end"):
      self.handle(0, {"type": "move_ship", "from": [3, 5, 5, 5], "to": [2, 4, 3, 5]})
    # Validate that moving a ship at the end of the network will work.
    self.handle(0, {"type": "move_ship", "from": [5, 5, 6, 4], "to": [2, 4, 3, 5]})

  def testCannotMoveTwoShipsInOneTurn(self):
    self.c.add_road(Road([5, 5, 6, 4], "ship", 0))
    self.c.built_this_turn.clear()
    self.handle(0, {"type": "move_ship", "from": [5, 5, 6, 4], "to": [2, 4, 3, 5]})
    with self.assertRaisesRegex(InvalidMove, "already moved a ship"):
      self.handle(0, {"type": "move_ship", "from": [3, 5, 5, 5], "to": [2, 6, 3, 5]})

  def testCannotMoveShipBuiltThisTurn(self):
    self.handle(0, {"type": "ship", "location": [5, 5, 6, 4]})
    with self.assertRaisesRegex(InvalidMove, "built this turn"):
      self.handle(0, {"type": "move_ship", "from": [5, 5, 6, 4], "to": [2, 6, 3, 5]})


class TestShipMovementLongestRoute(BaseInputHandlerTest):
  TEST_FILE = "ship_test.json"

  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_piece(islanders.Piece(9, 5, "settlement", 1))
    p0_roads = [(2, 4, 3, 3), (3, 3, 5, 3)]
    p1_roads = [(8, 6, 9, 5), (8, 4, 9, 5), (8, 4, 9, 3), (8, 2, 9, 3), (9, 5, 11, 5)]
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
    self.c.built_this_turn.clear()
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
    self.c.action_stack = ["rob", "robber"]
    moved_piece = self.c.pieces.pop((5, 5))
    moved_piece.location = islanders.CornerLocation(6, 6)
    self.c.add_piece(moved_piece)
    # Give these players some dev cards to make sure we don't rob dev cards.
    self.c.player_data[0].cards["knight"] = 10
    self.c.player_data[1].cards["knight"] = 10
    self.c.player_data[0].cards["gold"] = 3

  def testRobNoAdjacentPieces(self):
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    self.handle(2, {"type": "robber", "location": [4, 4]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count)

  def testRobTwoAdjacentPlayers(self):
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    self.handle(2, {"type": "robber", "location": [7, 5]})
    self.assertEqual(self.c.turn_phase, "rob")
    self.assertCountEqual(self.c.rob_players, [0, 1])
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count)

    self.handle(2, {"type": "rob", "player": 1})
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in islanders.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count - 1)
    self.assertEqual(p3_new_count, 1)

  def testRobSingleAdjacentPlayer(self):
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    self.handle(2, {"type": "robber", "location": [7, 3]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in islanders.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count - 1)
    self.assertEqual(p2_new_count, p2_old_count)
    self.assertEqual(p3_new_count, 1)

  def testCannotRobGold(self):
    self.c.player_data[0].cards.clear()
    self.c.player_data[0].cards["rsrc1"] = 1
    self.c.player_data[0].cards["gold"] = 1

    # Will choose gold if it's in the list; otherwise we don't care.
    with mock.patch.object(islanders.random, "choice", new=lambda lst: sorted(lst)[0]):
      self.handle(2, {"type": "robber", "location": [7, 3]})
    self.assertEqual(self.c.player_data[0].cards["rsrc1"], 0)
    self.assertEqual(self.c.player_data[0].cards["gold"], 1)

  def testRobSingleAdjacentPlayerWithoutCards(self):
    self.c.player_data[0].cards.clear()
    self.handle(2, {"type": "robber", "location": [7, 3]})
    self.assertEqual(self.c.turn_phase, "main")
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in islanders.RESOURCES)
    self.assertEqual(p3_new_count, 0)

  def testRobTwoAdjacentPlayersOneWithoutCards(self):
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    self.c.player_data[0].cards.clear()
    self.handle(2, {"type": "robber", "location": [7, 5]})
    self.assertEqual(self.c.turn_phase, "main")
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in islanders.RESOURCES)
    self.assertEqual(p2_new_count, p2_old_count - 1)
    self.assertEqual(p3_new_count, 1)

  def testRobSelf(self):
    self.c.add_piece(islanders.Piece(6, 4, "settlement", 2))
    self.c.player_data[2].cards["rsrc3"] = 1
    p3_old_count = sum(self.c.player_data[2].cards[x] for x in islanders.RESOURCES)
    self.handle(2, {"type": "robber", "location": [4, 4]})
    self.assertEqual(self.c.turn_phase, "main")
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in islanders.RESOURCES)
    self.assertEqual(p3_old_count, p3_new_count)

  def testRobSelfAndOneMore(self):
    self.c.add_piece(islanders.Piece(6, 4, "settlement", 2))
    self.c.player_data[2].cards["rsrc3"] = 1
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    self.handle(2, {"type": "robber", "location": [7, 3]})
    self.assertEqual(self.c.turn_phase, "main")
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in islanders.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count - 1)
    self.assertEqual(p2_new_count, p2_old_count)
    self.assertEqual(p3_new_count, 2)

  def testRobSelfAndTwoMore(self):
    self.c.add_piece(islanders.Piece(6, 4, "settlement", 2))
    self.c.player_data[2].cards["rsrc3"] = 1
    p1_old_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    p2_old_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    self.handle(2, {"type": "robber", "location": [7, 5]})
    self.assertEqual(self.c.turn_phase, "rob")
    self.assertCountEqual(self.c.rob_players, [0, 1])
    p1_new_count = sum(self.c.player_data[0].cards[x] for x in islanders.RESOURCES)
    p2_new_count = sum(self.c.player_data[1].cards[x] for x in islanders.RESOURCES)
    p3_new_count = sum(self.c.player_data[2].cards[x] for x in islanders.RESOURCES)
    self.assertEqual(p1_new_count, p1_old_count)
    self.assertEqual(p2_new_count, p2_old_count)
    self.assertEqual(p3_new_count, 1)


class TestLongestRouteCalculation(BaseInputHandlerTest):
  def setUp(self):
    BaseInputHandlerTest.setUp(self)

  def testSingleRoad(self):
    val = self.c._dfs_depth(0, islanders.CornerLocation(6, 4), set(), None)
    self.assertEqual(val, 1)

  def testTwoRoads(self):
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    val = self.c._dfs_depth(0, islanders.CornerLocation(6, 4), set(), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, islanders.CornerLocation(9, 5), set(), None)
    self.assertEqual(val, 2)
    # Starting from the middle should give a length of 1.
    val = self.c._dfs_depth(0, islanders.CornerLocation(8, 4), set(), None)
    self.assertEqual(val, 1)

  def testThreeRoads(self):
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    self.c._add_road(Road([8, 4, 9, 3], "road", 0))
    # Starting on any end of the network should still get you 2.
    val = self.c._dfs_depth(0, islanders.CornerLocation(6, 4), set(), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, islanders.CornerLocation(9, 5), set(), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, islanders.CornerLocation(9, 3), set(), None)
    self.assertEqual(val, 2)
    # Starting from the middle should give a length of 1.
    val = self.c._dfs_depth(0, islanders.CornerLocation(8, 4), set(), None)
    self.assertEqual(val, 1)

  def testRoadInterruption(self):
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    self.c._add_road(Road([8, 6, 9, 5], "road", 0))
    val = self.c._dfs_depth(0, islanders.CornerLocation(6, 4), set(), None)
    self.assertEqual(val, 3)
    val = self.c._dfs_depth(0, islanders.CornerLocation(8, 6), set(), None)
    self.assertEqual(val, 3)
    # Add a piece for the other player to interrupt the road.
    self.c.add_piece(islanders.Piece(9, 5, "settlement", 1))
    val = self.c._dfs_depth(0, islanders.CornerLocation(6, 4), set(), None)
    self.assertEqual(val, 2)
    val = self.c._dfs_depth(0, islanders.CornerLocation(8, 6), set(), None)
    self.assertEqual(val, 1)

  def testSandwichedRoad(self):
    # Test that you can still start a road at someone else's settlement.
    self.c.add_piece(islanders.Piece(8, 6, "settlement", 1))
    self.c._add_road(Road([5, 5, 6, 4], "road", 0))
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    self.c._add_road(Road([8, 6, 9, 5], "road", 0))
    val = self.c._dfs_depth(0, islanders.CornerLocation(6, 4), set(), None)
    self.assertEqual(val, 3)
    val = self.c._dfs_depth(0, islanders.CornerLocation(5, 5), set(), None)
    self.assertEqual(val, 4)
    val = self.c._dfs_depth(0, islanders.CornerLocation(8, 6), set(), None)
    self.assertEqual(val, 4)

  def testCircularRoad(self):
    self.c._add_road(Road([5, 3, 6, 4], "road", 0))
    self.c._add_road(Road([5, 3, 6, 2], "road", 0))
    self.c._add_road(Road([6, 2, 8, 2], "road", 0))
    self.c._add_road(Road([8, 2, 9, 3], "road", 0))
    self.c._add_road(Road([8, 4, 9, 3], "road", 0))

    # Start by testing a simple loop.
    for corner in [(5, 3), (6, 4), (8, 4), (9, 3), (8, 2), (6, 2)]:
      val = self.c._dfs_depth(0, islanders.CornerLocation(*corner), set(), None)
      self.assertEqual(val, 6, f"loop length for corner {corner}")

    # Add two tips onto the end of the loop. Length from either end should be 7.
    self.c._add_road(Road([3, 3, 5, 3], "road", 0))
    self.c._add_road(Road([8, 4, 9, 5], "road", 0))
    val = self.c._dfs_depth(0, islanders.CornerLocation(3, 3), set(), None)
    self.assertEqual(val, 7, "enter and loop around")
    val = self.c._dfs_depth(0, islanders.CornerLocation(9, 5), set(), None)
    self.assertEqual(val, 7, "enter and loop around")

    # Make the road longer without using the loop than with the loop.
    self.c._add_road(Road([2, 4, 3, 3], "road", 0))
    self.c._add_road(Road([2, 4, 3, 5], "road", 0))
    self.c._add_road(Road([8, 6, 9, 5], "road", 0))
    self.c._add_road(Road([6, 6, 8, 6], "road", 0))
    val = self.c._dfs_depth(0, islanders.CornerLocation(6, 6), set(), None)
    self.assertEqual(val, 10, "take long route around loop")
    val = self.c._dfs_depth(0, islanders.CornerLocation(3, 5), set(), None)
    self.assertEqual(val, 10, "take long route around loop")

  def testPortConnection(self):
    # Start with 2 ships and 4 roads, but no connection between them.
    self.c._add_road(Road([5, 3, 6, 4], "road", 0))
    self.c._add_road(Road([5, 3, 6, 2], "ship", 0))
    self.c._add_road(Road([6, 2, 8, 2], "ship", 0))
    self.c._add_road(Road([8, 2, 9, 3], "road", 0))
    self.c._add_road(Road([8, 4, 9, 3], "road", 0))
    val = self.c._dfs_depth(0, islanders.CornerLocation(5, 3), set(), None)
    self.assertEqual(val, 4, "no road -> ship connection")
    val = self.c._dfs_depth(0, islanders.CornerLocation(8, 2), set(), None)
    self.assertEqual(val, 4, "no road -> ship connection")
    val = self.c._dfs_depth(0, islanders.CornerLocation(6, 2), set(), None)
    self.assertEqual(val, 1, "single ship length in either direction")
    val = self.c._dfs_depth(0, islanders.CornerLocation(8, 4), set(), None)
    self.assertEqual(val, 2, "two roads in either direction")

    # Add a connector piece.
    self.c.add_piece(islanders.Piece(5, 3, "settlement", 0))
    val = self.c._dfs_depth(0, islanders.CornerLocation(5, 3), set(), None)
    self.assertEqual(val, 4, "still cannot go road->ship in the middle")
    val = self.c._dfs_depth(0, islanders.CornerLocation(8, 2), set(), None)
    self.assertEqual(val, 6, "but can go road->ship through a port")

    # Make sure somebody else's settlement doesn't count.
    self.c.pieces[(5, 3)].player = 1
    val = self.c._dfs_depth(0, islanders.CornerLocation(5, 3), set(), None)
    self.assertEqual(val, 4, "cannot go through someone else's port")
    val = self.c._dfs_depth(0, islanders.CornerLocation(8, 2), set(), None)
    self.assertEqual(val, 4, "cannot go through someone else's port")

  def testConqueredRoadsDontCount(self):
    self.c._add_road(Road([5, 3, 6, 4], "road", 0))
    for loc in [(4, 4), (7, 3)]:
      self.c.tiles[loc].barbarians = 1
      self.c.tiles[loc].conquered = True
    self.c.roads[(5, 3, 6, 4)].conquered = True
    val = self.c._dfs_depth(0, islanders.CornerLocation(8, 4), set(), None)
    self.assertEqual(val, 1, "conquered road doesn't count")


class TestLongestRouteAssignment(BreakpointTestMixin):
  def setUp(self):
    # Be sure to call add_road on the last road for each player to recalculate longest road.
    path = os.path.join(os.path.dirname(__file__), "sample.json")
    with open(path, encoding="ascii") as json_file:
      json_data = json_file.read()
    self.c = islanders.IslandersState.parse_json(json.loads(json_data))
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
    for rsrc in islanders.RESOURCES:
      self.c.player_data[2].cards[rsrc] += 1
    # Add this island to home_corners to avoid getting a landing event in the event log.
    self.c.home_corners[2].append(self.c.corners_to_islands[(8, 4)])
    self.g = islanders.IslandersGame()
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
      "{player0} takes longest route from {player1}", self.c.event_log[-1].public_text
    )

  def testBreakLongestRoad(self):
    self.c.add_road(Road([11, 1, 12, 2], "road", 1))
    self.c.add_road(Road([9, 5, 11, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    # Break first player's longest road with a piece from playerB.
    self.c.add_piece(islanders.Piece(8, 4, "settlement", 2))
    # PlayerA should get longest road since first player's is broken.
    self.assertEqual(self.c.longest_route_player, 1)
    self.assertEqual(self.c.player_data[0].longest_route, 4)

  def testBreakLongestRoadNoEligiblePlayers(self):
    self.c.add_road(Road([9, 5, 11, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    self.c.add_piece(islanders.Piece(8, 4, "settlement", 2))
    self.assertIsNone(self.c.longest_route_player)
    self.assertEqual("{player0} loses longest route", self.c.event_log[-1].public_text)

  def testBreakLongestRoadMultipleEligiblePlayers(self):
    self.c.add_road(Road([11, 1, 12, 2], "road", 1))
    self.c.add_road(Road([11, 9, 12, 8], "road", 2))
    self.c.add_road(Road([9, 5, 11, 5], "road", 0))
    self.assertEqual(self.c.longest_route_player, 0)
    self.c.add_piece(islanders.Piece(8, 4, "settlement", 2))
    # Now that first player's road is broken, nobody gets longest road because playerA
    # and playerB are tied.
    self.assertIsNone(self.c.longest_route_player)
    self.assertIn("because of a tie", self.c.event_log[-1].public_text)

  def testBreakLongestRoadNextRoadTooShort(self):
    self.c.add_road(Road([9, 5, 11, 5], "road", 0))
    # Break playerB's road of 4 so that this scenario is distinguishable from the one
    # where multiple players are tied for next longest road.
    self.c.add_piece(islanders.Piece(8, 8, "settlement", 0))
    self.assertEqual(self.c.player_data[2].longest_route, 2)
    self.assertEqual(self.c.longest_route_player, 0)
    # Break first player's longest road. Their longest road should now be 3.
    self.c.add_piece(islanders.Piece(9, 5, "settlement", 2))
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
    self.c.add_piece(islanders.Piece(9, 5, "settlement", 2))
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


class TestPlayerPoints(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.pieces[(8, 4)].piece_type = "city"
    self.c.add_piece(islanders.Piece(5, 3, "settlement", 0))
    self.c.add_piece(islanders.Piece(8, 6, "settlement", 1))
    for loc in [(4, 4), (4, 6), (7, 5)]:
      self.c.tiles[loc].barbarians = 1
      self.c.tiles[loc].conquered = True
    self.c.player_data[1].cards["market"] = 1

  def testVisiblePlayerPoints(self):
    self.assertEqual(self.c.player_points(0, visible=True), 3)
    self.assertEqual(self.c.player_points(1, visible=True), 2)

  def testHiddenPlayerPoints(self):
    self.assertEqual(self.c.player_points(0, visible=False), 3)
    self.assertEqual(self.c.player_points(1, visible=False), 3)

  def testConqueredSettlementsDontGivePoints(self):
    self.c.pieces[(5, 5)].conquered = True
    self.assertEqual(self.c.player_points(0, visible=True), 3)
    self.assertEqual(self.c.player_points(1, visible=True), 1)

  def testTwoBarbariansAreOnePoint(self):
    self.c.player_data[0].captured_barbarians = 4
    self.c.player_data[1].captured_barbarians = 1
    self.assertEqual(self.c.player_points(0, visible=True), 5)
    self.assertEqual(self.c.player_points(1, visible=True), 2)

  def testBuriedCountsForVictoryPoints(self):
    self.c.player_data[0].buried_treasure = 2
    self.c.player_data[1].buried_treasure = 3
    self.assertEqual(self.c.player_points(0, visible=True), 3)
    self.assertEqual(self.c.player_points(1, visible=True), 3)
    self.c.player_data[1].buried_treasure = 4
    self.assertEqual(self.c.player_points(1, visible=True), 4)


@mock.patch.object(islanders.random, "randint", return_value=3.5)
class TestDiscard(BaseInputHandlerTest):
  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.add_player("green", "Player3")
    for pdata in self.c.player_data:
      pdata.cards.clear()

  def testCalculateDiscardPlayers(self, unused_randint):
    self.c.player_data[0].cards.update({"rsrc1": 4, "rsrc2": 4, "rsrc3": 4, "rsrc5": 4})
    self.c.player_data[1].cards.update({"rsrc1": 4, "rsrc3": 2, "rsrc5": 1, "knight": 5, "gold": 4})
    self.c.player_data[2].cards.update({"rsrc1": 2, "rsrc2": 4, "rsrc3": 2, "rsrc5": 1, "gold": 2})
    self.c.action_stack = ["dice"]
    self.c.handle_roll_dice()
    self.assertEqual(self.c.turn_phase, "discard")
    self.assertEqual(self.c.event_log[-1].event_type, "dice")
    self.assertIn("rolled a 7", self.c.event_log[-1].public_text)
    # Player 0 has 16 cards, and must discard 8.
    # Player 1 does not have to discard because dev cards and gold don't count.
    # Player 2 must discard 9/2 rounded down = 4.
    self.assertDictEqual(self.c.discard_players, {0: 8, 2: 4})

    # Player 1 does not need to discard.
    with self.assertRaisesRegex(InvalidMove, "do not need to discard"):
      self.c.handle_discard({"rsrc1": 4}, 1)
    # Player 2 must discard the correct number of cards.
    with self.assertRaisesRegex(InvalidMove, "must discard 4"):
      self.c.handle_discard({"rsrc2": 4, "rsrc5": 1}, 2)
    # Player 2 cannot discard gold instead of cards.
    with self.assertRaisesRegex(InvalidMove, "Invalid resource"):
      self.c.handle_discard({"rsrc2": 2, "gold": 2}, 2)
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

  def testNobodyDiscards(self, unused_randint):
    self.c.player_data[0].cards.update({"rsrc1": 2, "rsrc2": 2, "rsrc3": 1, "rsrc5": 1})
    self.c.player_data[1].cards.update({"rsrc1": 4, "rsrc3": 2, "rsrc5": 1, "knight": 5})
    self.c.player_data[2].cards.update({"rsrc1": 2, "rsrc2": 0, "rsrc3": 2, "rsrc5": 1})
    self.c.action_stack = ["dice"]
    self.c.handle_roll_dice()
    self.assertEqual(self.c.turn_phase, "robber")

  def testBuriedTreasureIncreasesThreshold(self, unused_randint):
    self.c.player_data[0].cards.update({"rsrc1": 4, "rsrc2": 4})
    self.c.player_data[1].cards.update({"rsrc1": 4, "rsrc3": 5, "knight": 5})
    self.c.player_data[2].cards.update({"rsrc1": 5, "rsrc2": 5})
    for player in self.c.player_data:
      player.buried_treasure = 1
    self.c.action_stack = ["dice"]
    self.c.handle_roll_dice()
    self.assertEqual(self.c.turn_phase, "discard")
    # Player 0 has 8 cards, and does not need to discard.
    # Player 1 has 9 cards, and does not need to discard.
    # Player 2 has 10 cards, and must discard 5.
    self.assertDictEqual(self.c.discard_players, {2: 5})


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

  def testBuyReshuffle(self):
    self.c.options["shuffle_discards"].force(True)
    self.c.handle_buy_dev(0)
    self.c.handle_buy_dev(0)
    self.c.handle_buy_dev(0)
    with mock.patch.object(islanders.random, "shuffle", new=lambda cards: cards.sort()):
      self.c.handle_buy_dev(0)
    self.assertEqual(self.c.player_data[0].cards["knight"], 2)
    self.assertEqual(self.c.player_data[0].cards["yearofplenty"], 2)
    count = collections.Counter({"knight": 12, "monopoly": 2, "roadbuilding": 2, "yearofplenty": 0})
    self.assertCountEqual(self.c.dev_cards, count.elements())

  def testBuyImmediateDev(self):
    self.c.options["immediate_dev"].force(True)
    self.c.handle_buy_dev(0)
    self.assertEqual(self.c.action_stack, ["knight"])
    self.assertEqual(self.c.player_data[0].cards.get("knight", 0), 0)


class TestBuildKnight(BaseInputHandlerTest):
  TEST_FILE = "knight_test.json"

  def testPlaceKnight(self):
    self.c.dev_cards.append("knight")
    self.c.handle_buy_dev(0)
    self.assertEqual(self.c.turn_phase, "knight")
    self.assertEqual(len(self.c.knights), 2)
    self.c.handle_place_knight([3, 5, 5, 5], 0)
    self.assertEqual(len(self.c.knights), 3)

  def testPlaceKnightOnCoast(self):
    self.c.dev_cards.append("knight")
    self.c.handle_buy_dev(0)
    self.assertEqual(self.c.turn_phase, "knight")
    self.assertEqual(len(self.c.knights), 2)
    self.c.handle_place_knight([3, 7, 5, 7], 0)
    self.assertEqual(len(self.c.knights), 3)

  def testInvalidPlacement(self):
    self.c.dev_cards.append("knight")
    self.c.handle_buy_dev(0)
    self.assertEqual(self.c.turn_phase, "knight")
    self.assertEqual(len(self.c.knights), 2)
    with self.assertRaisesRegex(InvalidMove, "tuple of size 4"):
      self.c.handle_place_knight([3, 5], 0)
    with self.assertRaisesRegex(InvalidMove, "not a valid edge"):
      self.c.handle_place_knight([3, 5, 6, 6], 0)
    with self.assertRaisesRegex(InvalidMove, "next to a castle"):
      self.c.handle_place_knight([3, 3, 5, 3], 0)
    self.assertEqual(len(self.c.knights), 2)

  def testPlaceFastKnight(self):
    self.c.dev_cards.append("fastknight")
    self.c.handle_buy_dev(0)
    self.assertEqual(self.c.turn_phase, "fastknight")
    self.assertEqual(len(self.c.knights), 2)
    with self.assertRaisesRegex(InvalidMove, "valid edge"):
      self.c.handle_place_knight([2, 8, 3, 7], 0)
    with self.assertRaisesRegex(InvalidMove, "already a knight there"):
      self.c.handle_place_knight([6, 4, 8, 4], 0)
    self.c.handle_place_knight([6, 2, 8, 2], 0)
    self.assertEqual(len(self.c.knights), 3)

  def testCannotHaveMoreThanSixKnights(self):
    locs = [(6, 2, 8, 2), (3, 3, 5, 3), (6, 6, 8, 6), (5, 3, 6, 4), (2, 4, 3, 3)]
    for loc in locs:
      self.c.knights[loc] = islanders.Knight(loc, 0, loc)
    self.assertEqual(len(self.c.knights), 7)
    self.c.dev_cards.append("knight")
    self.c.handle_buy_dev(0)
    self.assertEqual(self.c.turn_phase, "main")
    self.assertEqual(len(self.c.knights), 7)


class TestMoveKnights(BaseInputHandlerTest):
  TEST_FILE = "knight_test.json"

  def setUp(self):
    super().setUp()
    self.c.handle_end_turn()

  def testMoveKnightsComesAfterTurnEnd(self):
    self.c.action_stack.clear()
    self.assertEqual(self.c.turn_phase, "main")
    self.c.handle_end_turn()
    self.assertEqual(self.c.turn_phase, "move_knights")
    self.assertEqual(self.c.knights[(6, 4, 8, 4)].source, islanders.EdgeLocation(6, 4, 8, 4))
    self.assertEqual(self.c.knights[(6, 4, 8, 4)].movement, 3)

  def testNoMoveKnightsPhaseIfNoKnights(self):
    self.c.action_stack.clear()
    self.assertEqual(self.c.turn_phase, "main")
    self.c.knights.pop((6, 4, 8, 4))
    self.c.handle_end_turn()
    self.assertEqual(self.c.turn_phase, "check_recapture")  # Gets resolved by handle()

  def testMoveOneKnight(self):
    self.c.handle_move_knight((6, 4, 8, 4), (2, 6, 3, 5), 0)
    self.assertEqual(self.c.knights[(2, 6, 3, 5)].location, islanders.EdgeLocation(2, 6, 3, 5))
    self.assertEqual(self.c.knights[(2, 6, 3, 5)].source, islanders.EdgeLocation(6, 4, 8, 4))
    self.assertEqual(self.c.knights[(2, 6, 3, 5)].movement, 0)

    self.c.handle_move_knight((2, 6, 3, 5), (5, 3, 6, 2), 0)
    self.assertEqual(self.c.knights[(5, 3, 6, 2)].location, islanders.EdgeLocation(5, 3, 6, 2))
    self.assertEqual(self.c.knights[(5, 3, 6, 2)].source, islanders.EdgeLocation(6, 4, 8, 4))
    self.assertEqual(self.c.knights[(5, 3, 6, 2)].movement, 1)

    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_end_move_knights(0)
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs, old_rsrcs)

  def testInvalidMoves(self):
    with self.assertRaisesRegex(InvalidMove, "tuple of size 4"):
      self.c.handle_move_knight((6, 4, 8, 4), (2, 6), 0)
    with self.assertRaisesRegex(InvalidMove, "valid edge"):
      self.c.handle_move_knight((6, 4, 8, 4), (5, 5, 9, 5), 0)
    with self.assertRaisesRegex(InvalidMove, "your own knight"):
      self.c.handle_move_knight((5, 5, 6, 4), (2, 6, 3, 5), 0)
    with self.assertRaisesRegex(InvalidMove, "valid edge"):
      self.c.handle_move_knight((6, 4, 8, 4), (9, 3, 11, 3), 0)

  def testMustNotEndOnCastle(self):
    self.c.handle_move_knight((6, 4, 8, 4), (3, 5, 5, 5), 0)
    with self.assertRaisesRegex(InvalidMove, "away from the castle"):
      self.c.handle_end_move_knights(0)

  def testMoveFar(self):
    loc = islanders.EdgeLocation(2, 6, 3, 7)
    self.c.knights[loc] = islanders.Knight(loc, 0, loc)
    self.c.knights[(6, 4, 8, 4)].source = None
    self.c.action_stack.clear()
    self.c.handle_end_turn()
    self.assertEqual(self.c.knights[(6, 4, 8, 4)].source, islanders.EdgeLocation(6, 4, 8, 4))
    self.c.handle_move_knight((2, 6, 3, 7), (5, 3, 6, 2), 0)
    with self.assertRaisesRegex(InvalidMove, "enough movement"):
      self.c.handle_move_knight((5, 3, 6, 2), (6, 2, 8, 2), 0)
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_end_move_knights(0)
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc3": 1})
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})

  def testMoveFarInsufficientFunds(self):
    self.c.player_data[0].cards["rsrc3"] = 0
    loc = islanders.EdgeLocation(2, 6, 3, 7)
    self.c.knights[loc] = islanders.Knight(loc, 0, loc)
    self.c.handle_move_knight((2, 6, 3, 7), (5, 3, 6, 2), 0)
    with self.assertRaisesRegex(InvalidMove, "would need 1.*"):
      self.c.handle_end_move_knights(0)


class TestTradeOffer(BaseInputHandlerTest):
  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.player_data[0].cards.clear()
    self.c.player_data[1].cards.clear()
    self.c.player_data[0].cards.update({"rsrc1": 4, "rsrc2": 4, "rsrc3": 4, "gold": 1})
    self.c.player_data[1].cards.update({"rsrc1": 4, "rsrc4": 4, "rsrc5": 4, "gold": 2})

  def testMakeOffer(self):
    self.c.handle_trade_offer({"want": {"rsrc4": 1}, "give": {"rsrc1": 1}}, 0)
    self.assertDictEqual(self.c.trade_offer, {"want": {"rsrc4": 1}, "give": {"rsrc1": 1}})

  def testCanMakeOpenEndedOffer(self):
    self.c.handle_trade_offer({"want": {"rsrc4": 1}, "give": {}}, 0)
    self.assertDictEqual(self.c.trade_offer, {"want": {"rsrc4": 1}, "give": {}})

  def testMustOfferOwnedResources(self):
    with self.assertRaisesRegex(InvalidMove, "do not have enough"):
      self.c.handle_trade_offer({"want": {"rsrc4": 1}, "give": {"rsrc5": 1}}, 0)

  def testCanOfferGold(self):
    self.c.handle_trade_offer({"want": {"rsrc4": 1}, "give": {"gold": 1}}, 0)

  def testCannotGiveAndReceiveSameResource(self):
    with self.assertRaisesRegex(InvalidMove, "the same resource"):
      self.c.handle_trade_offer({"want": {"rsrc1": 1, "rsrc4": 1}, "give": {"rsrc1": 2}}, 0)


class TestCounterOffer(BaseInputHandlerTest):
  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.player_data[0].cards.clear()
    self.c.player_data[1].cards.clear()
    self.c.player_data[0].cards.update({"rsrc1": 4, "rsrc2": 4, "rsrc3": 4, "gold": 1})
    self.c.player_data[1].cards.update({"rsrc1": 4, "rsrc4": 4, "rsrc5": 4, "gold": 2})
    self.c.handle_trade_offer({"want": {"rsrc4": 1}, "give": {"rsrc1": 1}}, 0)

  def testMakeCounter(self):
    self.assertNotIn(1, self.c.counter_offers)
    self.c.handle_counter_offer({"want": {"rsrc2": 1}, "give": {"rsrc4": 1}}, 1)
    self.assertIn(1, self.c.counter_offers)
    self.assertEqual(self.c.counter_offers[1], {"want": {"rsrc2": 1}, "give": {"rsrc4": 1}}, 1)

  def testRejectOffer(self):
    self.c.handle_counter_offer(0, 1)
    self.assertIn(1, self.c.counter_offers)
    self.assertEqual(self.c.counter_offers[1], 0)

  def testMustOfferOwnedResources(self):
    with self.assertRaisesRegex(InvalidMove, "do not have enough"):
      self.c.handle_counter_offer({"want": {"rsrc2": 1}, "give": {"rsrc3": 1}}, 1)

  def testCanMakeOpenEndedCounter(self):
    self.c.handle_counter_offer({"want": {"rsrc2": 1}, "give": {}}, 1)
    self.assertEqual(self.c.counter_offers[1], {"want": {"rsrc2": 1}, "give": {}})

  def testCannotGiveAndReceiveSameResource(self):
    with self.assertRaisesRegex(InvalidMove, "the same resource"):
      self.c.handle_counter_offer({"want": {"rsrc2": 1}, "give": {"rsrc2": 1}}, 1)


class TestAcceptCounter(BaseInputHandlerTest):
  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.player_data[0].cards.clear()
    self.c.player_data[1].cards.clear()
    self.c.player_data[0].cards.update({"rsrc1": 4, "rsrc2": 4, "rsrc3": 4, "gold": 1})
    self.c.player_data[1].cards.update({"rsrc1": 4, "rsrc4": 4, "rsrc5": 4, "gold": 2})
    self.c.handle_trade_offer({"want": {"rsrc4": 1}, "give": {"rsrc1": 1}}, 0)

  def testOfferAndCounterMustMatch(self):
    self.c.handle_counter_offer({"want": {"rsrc2": 1}, "give": {"rsrc4": 1}}, 1)
    with self.assertRaisesRegex(InvalidMove, "changed their offer"):
      self.c.handle_accept_counter({"want": {"rsrc1": 1}, "give": {"rsrc4": 1}}, 1, 0)
    self.c.handle_accept_counter({"want": {"rsrc2": 1}, "give": {"rsrc4": 1}}, 1, 0)
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], 3)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], 1)

  def testCannotTradeForNothing(self):
    self.c.handle_counter_offer({"want": {"rsrc2": 0}, "give": {"rsrc4": 1}}, 1)
    with self.assertRaisesRegex(InvalidMove, "trade for nothing"):
      self.c.handle_accept_counter({"want": {"rsrc2": 0}, "give": {"rsrc4": 1}}, 1, 0)

  def testMustTradeForDifferentResources(self):
    # bypass counter offer validation for the sake of this test
    self.c.counter_offers[1] = {"want": {"rsrc2": 1, "rsrc1": 1}, "give": {"rsrc4": 1, "rsrc1": 1}}
    with self.assertRaisesRegex(InvalidMove, "the same resource"):
      self.c.handle_accept_counter(
        {"want": {"rsrc2": 1, "rsrc1": 1}, "give": {"rsrc4": 1, "rsrc1": 1}}, 1, 0
      )


class TestTradeBank(BaseInputHandlerTest):
  def setUp(self):
    BaseInputHandlerTest.setUp(self)
    self.c.options["gold"].force(True)
    self.c.player_data[0].cards.clear()
    self.c.player_data[1].cards.clear()
    self.c.player_data[0].cards.update({"rsrc1": 4, "rsrc2": 4, "rsrc3": 4, "gold": 1})
    self.c.player_data[1].cards.update({"rsrc1": 4, "rsrc4": 4, "rsrc5": 4, "gold": 2})
    # Player 0 trade ratios: 2 for rsrc1, 3 otherwise.
    # Player 1 trade ratios: 2 for rsrc4, 4 otherwise.

  def testCannotOverdrawBank(self):
    self.c.player_data[1].cards["rsrc5"] = 18
    with self.assertRaisesRegex(InvalidMove, "remaining"):
      self.c.handle_trade_bank({"want": {"rsrc5": 2}, "give": {"rsrc1": 4}}, 0)
    self.c.handle_trade_bank({"want": {"rsrc5": 1}, "give": {"rsrc1": 2}}, 0)

  def testFourToOneTrade(self):
    self.c.handle_trade_bank({"want": {"rsrc2": 1}, "give": {"rsrc1": 4}}, 1)
    self.assertEqual(self.c.player_data[1].cards["rsrc2"], 1)
    self.assertEqual(self.c.player_data[1].cards["rsrc1"], 0)

  def testThreeToOneTrade(self):
    self.c.handle_trade_bank({"want": {"rsrc5": 1}, "give": {"rsrc2": 3}}, 0)
    self.assertEqual(self.c.player_data[0].cards["rsrc5"], 1)
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], 1)

  def testHybridTwoAndFourTrade(self):
    self.c.handle_trade_bank({"want": {"rsrc2": 2}, "give": {"rsrc4": 2, "rsrc5": 4}}, 1)
    self.assertEqual(self.c.player_data[1].cards["rsrc2"], 2)
    self.assertEqual(self.c.player_data[1].cards["rsrc5"], 0)
    self.assertEqual(self.c.player_data[1].cards["rsrc4"], 2)

  def testHybridTwoAndThreeTrade(self):
    self.c.handle_trade_bank({"want": {"rsrc4": 2}, "give": {"rsrc1": 2, "rsrc2": 3}}, 0)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], 2)
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], 1)
    self.assertEqual(self.c.player_data[0].cards["rsrc1"], 2)

  def testBadTradeRatio(self):
    with self.assertRaisesRegex(InvalidMove, "should receive 3"):
      self.c.handle_trade_bank({"want": {"rsrc4": 2}, "give": {"rsrc1": 4, "rsrc2": 3}}, 0)
    with self.assertRaisesRegex(InvalidMove, "should receive 2"):
      self.c.handle_trade_bank({"want": {"rsrc4": 3}, "give": {"rsrc1": 2, "rsrc2": 3}}, 0)
    with self.assertRaisesRegex(InvalidMove, "must trade .* 2:1 ratio"):
      self.c.handle_trade_bank({"want": {"rsrc4": 2}, "give": {"rsrc1": 3, "rsrc2": 3}}, 0)
    with self.assertRaisesRegex(InvalidMove, "must trade .* 3:1 ratio"):
      self.c.handle_trade_bank({"want": {"rsrc4": 2}, "give": {"rsrc1": 2, "rsrc2": 4}}, 0)

  def testCannotTradeForGoldWhenDisabled(self):
    self.c.options["gold"].force(False)
    with self.assertRaisesRegex(InvalidMove, "There is no gold"):
      self.c.handle_trade_bank({"want": {"gold": 1}, "give": {"rsrc2": 3}}, 0)

  def testTradeForGold(self):
    self.c.handle_trade_bank({"want": {"gold": 1}, "give": {"rsrc2": 3}}, 0)
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], 1)
    self.assertEqual(self.c.player_data[0].cards["gold"], 2)
    self.assertEqual(self.c.player_data[0].gold_traded, 0)

  def testTradeGold(self):
    self.c.handle_trade_bank({"want": {"rsrc2": 1}, "give": {"gold": 2}}, 1)
    self.assertEqual(self.c.player_data[1].cards["rsrc2"], 1)
    self.assertEqual(self.c.player_data[1].cards["gold"], 0)
    self.assertEqual(self.c.player_data[1].gold_traded, 2)

  def testCannotTradeMoreThanFourGoldPerTurn(self):
    self.c.player_data[1].gold_traded = 4
    with self.assertRaisesRegex(InvalidMove, "twice per turn"):
      self.c.handle_trade_bank({"want": {"rsrc2": 1}, "give": {"gold": 2}}, 1)

  def testCannotTradeTwoToOneForGold(self):
    with self.assertRaisesRegex(InvalidMove, "cannot trade for gold .* 2:1 ratio"):
      self.c.handle_trade_bank({"want": {"gold": 1}, "give": {"rsrc1": 2}}, 0)

  def testTradeForGoldAndAnotherResource(self):
    self.c.handle_trade_bank({"want": {"gold": 1, "rsrc4": 1}, "give": {"rsrc1": 2, "rsrc2": 3}}, 0)
    self.assertEqual(self.c.player_data[0].cards["rsrc4"], 1)
    self.assertEqual(self.c.player_data[0].cards["gold"], 2)
    self.assertEqual(self.c.player_data[0].cards["rsrc1"], 2)
    self.assertEqual(self.c.player_data[0].cards["rsrc2"], 1)
    self.assertEqual(self.c.player_data[0].gold_traded, 0)

  def testTradeForGoldUnevenRatios(self):
    self.c.player_data[0].cards.clear()
    self.c.player_data[0].cards.update({"rsrc1": 6, "rsrc2": 3, "rsrc3": 3})
    self.c.handle_trade_bank(
      {"want": {"gold": 2, "rsrc4": 3}, "give": {"rsrc1": 6, "rsrc2": 3, "rsrc3": 3}}, 0
    )

  def testTradeForGoldUseCorrectRatioFirst(self):
    self.c.player_data[0].cards.clear()
    self.c.player_data[0].cards.update({"rsrc1": 6, "rsrc2": 3, "rsrc3": 3})
    with self.assertRaisesRegex(InvalidMove, "should receive 3 cards and 2 gold"):
      self.c.handle_trade_bank(
        {"want": {"gold": 2, "rsrc4": 2}, "give": {"rsrc1": 6, "rsrc2": 3, "rsrc3": 3}}, 0
      )


class TestHastenInvasion(BaseInputHandlerTest):
  TEST_FILE = "test_riders.json"

  def setUp(self):
    super().setUp()
    for rsrc in islanders.RESOURCES:
      self.c.player_data[0].cards[rsrc] += 3
    self.c.add_road(Road([17, 9, 18, 8], "road", 0))

  def testSettlementHastensInvasion(self):
    self.c.handle_settle([18, 8], 0)
    self.assertEqual(self.c.invasion_countdown, 18 - 3)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(num_barbs, 3)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values() if tile.tile_type == "norsrc")
    self.assertEqual(num_barbs, 3)
    max_barbs = max(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(max_barbs, 1)

  def testCityHastensInvasion(self):
    self.c.handle_settle([18, 8], 0)
    self.assertEqual(self.c.invasion_countdown, 18 - 3)
    self.c.handle_city([18, 8], 0)
    self.assertEqual(self.c.invasion_countdown, 18 - 6)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(num_barbs, 6)
    max_barbs = max(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(max_barbs, 2)

  def testFourPlayerHastening(self):
    self.c.add_player("green", "PlayerB")
    self.c.handle_settle([18, 8], 0)
    self.assertEqual(self.c.invasion_countdown, 18 - 2)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(num_barbs, 2)
    max_barbs = max(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(max_barbs, 1)

    self.c.handle_city([18, 8], 0)
    self.assertEqual(self.c.invasion_countdown, 18 - 4)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(num_barbs, 4)
    max_barbs = max(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(max_barbs, 2)

  def testFirstSettlementDoesNothing(self):
    self.c.game_phase = "place1"
    self.c.action_stack = ["road", "settle"]
    self.c.handle_settle([18, 8], 0)
    self.assertEqual(self.c.invasion_countdown, 18)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(num_barbs, 0)

  def testRoadDoesNotHasten(self):
    self.c.handle_settle([18, 8], 0)
    self.assertEqual(self.c.invasion_countdown, 18 - 3)
    self.c.handle_road([17, 7, 18, 8], 0, "road", [("rsrc2", 1), ("rsrc4", 1)])
    self.assertEqual(self.c.invasion_countdown, 18 - 3)

  def testNoEffectAfterInvasionStarts(self):
    self.c.invasion_countdown = 3
    for tile in self.c.tiles.values():
      if tile.tile_type != "norsrc":
        continue
      tile.barbarians = 5

    self.c.handle_settle([18, 8], 0)
    self.assertEqual(self.c.invasion_countdown, 0)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(num_barbs, 18)
    max_barbs = max(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(max_barbs, 6)

    self.c.handle_city([18, 8], 0)
    self.assertEqual(self.c.invasion_countdown, 0)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(num_barbs, 18)
    max_barbs = max(tile.barbarians for tile in self.c.tiles.values())
    self.assertEqual(max_barbs, 6)


class TestInvasion(BaseInputHandlerTest):
  TEST_FILE = "test_riders.json"

  def setUp(self):
    super().setUp()
    self.c.add_piece(islanders.Piece(18, 8, "settlement", 0))
    self.c.add_piece(islanders.Piece(15, 9, "settlement", 1))
    self.c.add_piece(islanders.Piece(15, 5, "settlement", 2))
    self.c.add_piece(islanders.Piece(15, 3, "settlement", 2))
    self.c.add_piece(islanders.Piece(15, 7, "settlement", 1))
    self.c.add_piece(islanders.Piece(18, 10, "settlement", 0))
    self.c._add_road(Road([17, 9, 18, 8], "road", 0))
    self.c._add_road(Road([17, 9, 18, 10], "road", 0))
    self.c._add_road(Road([15, 7, 17, 7], "road", 0))
    self.c._add_road(Road([17, 7, 18, 8], "road", 0))
    self.c.add_road(Road([17, 11, 18, 10], "road", 0))
    self.c._add_road(Road([12, 6, 14, 6], "road", 1))
    self.c._add_road(Road([14, 6, 15, 7], "road", 1))
    self.c._add_road(Road([14, 8, 15, 7], "road", 1))
    self.c._add_road(Road([14, 8, 15, 9], "road", 1))
    self.c.add_road(Road([15, 9, 17, 9], "road", 1))
    self.c._add_road(Road([14, 6, 15, 5], "road", 2))
    self.c._add_road(Road([14, 4, 15, 5], "road", 2))
    self.c._add_road(Road([14, 4, 15, 3], "road", 2))
    self.c._add_road(Road([14, 2, 15, 3], "road", 2))
    self.c.add_road(Road([12, 2, 14, 2], "road", 2))
    self.c.invasion_countdown = 3
    for tile in self.c.tiles.values():
      if tile.tile_type == "norsrc":
        tile.barbarians = 5
    self.c.hasten_invasion()  # Sets countdown to 0, adds barbarians,  and marks tiles as conquered.
    self.c.action_stack = ["dice"]

  def testInvadeNearbyTiles(self):
    self.c.next_die_roll = 4
    self.c.handle_roll_dice()

    self.assertEqual(self.c.tiles[(19, 9)].barbarians, 1)
    self.assertEqual(self.c.tiles[(10, 4)].barbarians, 0)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values() if tile.tile_type == "norsrc")
    self.assertEqual(num_barbs, 17)

    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 8
    self.c.handle_roll_dice()
    self.assertEqual(self.c.tiles[(16, 4)].barbarians, 1)
    self.assertEqual(self.c.tiles[(10, 6)].barbarians, 0)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values() if tile.tile_type == "norsrc")
    self.assertEqual(num_barbs, 16)

    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 3
    self.c.handle_roll_dice()
    self.assertEqual(self.c.tiles[(19, 11)].barbarians, 1)
    self.assertEqual(self.c.tiles[(13, 3)].barbarians, 1)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values() if tile.tile_type == "norsrc")
    self.assertEqual(num_barbs, 14)
    min_barbs = min(tile.barbarians for tile in self.c.tiles.values() if tile.tile_type == "norsrc")
    self.assertEqual(min_barbs, 4)

  def testTilesCanOnlyBeInvadedOnce(self):
    self.c.next_die_roll = 8
    self.c.handle_roll_dice()
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 10
    self.c.handle_roll_dice()
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 8
    self.c.handle_roll_dice()

    self.assertEqual(self.c.tiles[(16, 4)].barbarians, 1)
    self.assertEqual(self.c.tiles[(10, 6)].barbarians, 1)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values() if tile.tile_type == "norsrc")
    self.assertEqual(num_barbs, 18 - 3)

  def testConqueredCitiesAfterInvasion(self):
    self.c.next_die_roll = 4
    self.c.handle_roll_dice()
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 6
    self.c.handle_roll_dice()
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 8
    self.c.handle_roll_dice()
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 3
    self.c.handle_roll_dice()
    self.assertTrue(self.c.pieces[(18, 8)].conquered)
    self.assertFalse(self.c.pieces[(18, 10)].conquered)  # Touching one free tile
    self.assertFalse(self.c.pieces[(15, 3)].conquered)  # Touching one sea tile
    self.assertEqual(self.c.player_points(0, True), 1)
    self.assertEqual(self.c.player_points(2, True), 2)

  def testConqueredRoadsAfterInvasion(self):
    self.c.next_die_roll = 4
    self.c.handle_roll_dice()
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 6
    self.c.handle_roll_dice()
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 8
    self.c.handle_roll_dice()
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 3
    self.c.handle_roll_dice()
    self.assertTrue(self.c.roads[(14, 4, 15, 3)].conquered)
    self.assertTrue(self.c.roads[(17, 9, 18, 8)].conquered)
    self.assertFalse(self.c.roads[(14, 2, 15, 3)].conquered)
    self.assertTrue(self.c.roads[(17, 7, 18, 8)].conquered)

  def testLongestRoadIsRecomputedAfterConquest(self):
    self.c.next_die_roll = 4
    self.c.handle_roll_dice()
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 6
    self.c.handle_roll_dice()
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 8
    self.c.handle_roll_dice()
    self.c.action_stack = ["dice"]
    self.c.next_die_roll = 3
    self.c.handle_roll_dice()

    self.assertEqual(self.c.player_data[0].longest_route, 2)
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.assertEqual(self.c.player_data[2].longest_route, 2)

  def testNotEnoughBarbarians(self):
    for tile in self.c.tiles.values():
      if tile.tile_type == "norsrc":
        tile.barbarians = 0
    self.c.tiles[(19, 7)].barbarians = 1  # Only one barbarian left
    self.c.tiles[(16, 6)].number = 4  # Two fours next to that desert
    self.c.next_die_roll = 4
    self.c.handle_roll_dice()

    self.assertEqual(self.c.tiles[(16, 6)].barbarians, 0)
    self.assertEqual(self.c.tiles[(19, 9)].barbarians, 1)
    num_barbs = sum(tile.barbarians for tile in self.c.tiles.values() if tile.tile_type == "norsrc")
    self.assertEqual(num_barbs, 0)


class TestInvasionEdgeCases(BreakpointTestMixin):
  def setUp(self):
    super().setUp()
    # Somebody puts their starting road between the two deserts because they think it's funny.
    # According to the rules, this road should be conquered when the barbarians start gathering.
    self.c = islanders.IslandersState()
    self.c.add_player("red", "player1")
    self.c.add_player("blue", "player2")
    self.c.add_player("green", "player3")
    islanders.DesertRiders.mutate_options(self.c.options)
    islanders.DesertRiders.init(self.c)
    # TODO: we should have a helper to init a game with the default options for a scenario.
    self.c.options["foreign_island_points"].set(0)

    self.handle(0, {"type": "settle", "location": [18, 6]})
    self.handle(0, {"type": "road", "location": [18, 6, 20, 6]})
    self.handle(1, {"type": "settle", "location": [18, 8]})
    self.handle(1, {"type": "road", "location": [17, 7, 18, 8]})
    self.handle(2, {"type": "settle", "location": [15, 3]})
    self.handle(2, {"type": "road", "location": [14, 2, 15, 3]})
    self.g = islanders.IslandersGame()
    self.g.game = self.c
    self.g.scenario = "Desert Riders"
    self.c.game_phase = "main"

  def testRoadThatStartsBetweenTwoDeserts(self):
    self.c.turn_idx = 1
    self.c.action_stack.clear()
    self.c.player_data[1].cards["rsrc3"] = 5
    self.c.player_data[1].cards["rsrc5"] = 5
    self.handle(1, {"type": "city", "location": [18, 8]})

    # Each desert should now have one barbarian
    min_barbs = min(tile.barbarians for tile in self.c.tiles.values() if tile.tile_type == "norsrc")
    self.assertEqual(min_barbs, 1)
    # The road in between the two deserts should now be conquered.
    self.assertTrue(self.c.roads[(18, 6, 20, 6)].conquered)


class TestExpelBarbarians(BaseInputHandlerTest):
  TEST_FILE = "test_riders.json"

  def setUp(self):
    super().setUp()
    self.c.add_piece(islanders.Piece(18, 8, "settlement", 0))
    self.c.add_piece(islanders.Piece(15, 9, "settlement", 1))
    self.c.add_piece(islanders.Piece(15, 5, "settlement", 2))
    self.c.add_piece(islanders.Piece(15, 3, "settlement", 2))
    self.c.add_piece(islanders.Piece(15, 7, "city", 1))
    self.c.add_piece(islanders.Piece(18, 10, "city", 0))
    self.c._add_road(Road([17, 9, 18, 8], "road", 0))
    self.c._add_road(Road([17, 9, 18, 10], "road", 0))
    self.c._add_road(Road([15, 7, 17, 7], "road", 0))
    self.c._add_road(Road([17, 7, 18, 8], "road", 0))
    self.c.add_road(Road([17, 11, 18, 10], "road", 0))
    self.c._add_road(Road([12, 6, 14, 6], "road", 1))
    self.c._add_road(Road([14, 6, 15, 7], "road", 1))
    self.c._add_road(Road([14, 8, 15, 7], "road", 1))
    self.c._add_road(Road([14, 8, 15, 9], "road", 1))
    self.c.add_road(Road([15, 9, 17, 9], "road", 1))
    self.c._add_road(Road([14, 6, 15, 5], "road", 2))
    self.c._add_road(Road([14, 4, 15, 5], "road", 2))
    self.c._add_road(Road([14, 4, 15, 3], "road", 2))
    self.c._add_road(Road([14, 2, 15, 3], "road", 2))
    self.c.add_road(Road([12, 2, 14, 2], "road", 2))
    self.c.invasion_countdown = 3
    for tile in self.c.tiles.values():
      if tile.tile_type == "norsrc":
        tile.barbarians = 5
    self.c.hasten_invasion()  # Sets countdown to 0, adds barbarians,  and marks tiles as conquered.
    for dice_roll in [4, 9, 5, 6, 8, 3, 10, 2]:
      self.c.action_stack = ["dice"]
      self.c.next_die_roll = dice_roll
      self.c.handle_roll_dice()
    self.c.player_data[0].cards["knight"] += 5

  def testExpelOneBarbarian(self):
    self.assertTrue(self.c.tiles[(10, 10)].conquered)
    self.c.handle_play_dev("knight", None, 0)
    self.assertListEqual(self.c.action_stack, ["expel"])
    self.c.handle_expel([10, 10], 0)
    self.assertEqual(self.c.turn_phase, "main")
    self.assertFalse(self.c.tiles[(10, 10)].conquered)

  def testExpelFromDesert(self):
    # Maybe you do this to reclaim a city next to the desert without reclaiming other cities?
    self.assertTrue(self.c.tiles[(19, 7)].conquered)
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([19, 7], 0)
    self.assertTrue(self.c.tiles[(19, 7)].conquered)
    self.assertTrue(self.c.pieces[(18, 8)].conquered)
    self.c.played_dev = 0
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([19, 7], 0)
    self.assertFalse(self.c.tiles[(19, 7)].conquered)
    self.assertFalse(self.c.pieces[(18, 8)].conquered)

  def testExpelBarbarianReclaimsCity(self):
    self.assertTrue(self.c.tiles[(16, 10)].conquered)
    self.assertTrue(self.c.pieces[(18, 10)].conquered)
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([16, 10], 0)
    self.assertFalse(self.c.tiles[(16, 10)].conquered)
    self.assertFalse(self.c.pieces[(18, 10)].conquered)
    self.assertEqual(self.c.player_points(0, True), 2)

  def testExpelBarbarianReclaimimingLongestRoad(self):
    self.assertEqual(self.c.player_data[0].longest_route, 0)
    self.assertEqual(self.c.player_data[1].longest_route, 1)
    self.assertIsNone(self.c.longest_route_player)
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([13, 7], 0)
    self.c.played_dev = 0
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([16, 8], 0)
    self.assertEqual(self.c.player_data[0].longest_route, 3)
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.assertEqual(self.c.longest_route_player, 1)

  def testExpelBarbariansTyingLongestRoad(self):
    self.assertEqual(self.c.player_data[0].longest_route, 0)
    self.assertEqual(self.c.player_data[1].longest_route, 1)
    self.assertIsNone(self.c.longest_route_player)
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([16, 6], 0)
    self.c.played_dev = 0
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([16, 8], 0)
    self.c.played_dev = 0
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([13, 3], 0)
    self.assertEqual(self.c.player_data[1].longest_route, 4)
    self.assertEqual(self.c.player_data[2].longest_route, 3)
    self.assertIsNone(self.c.longest_route_player)
    self.c.played_dev = 0
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([13, 5], 0)
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.assertEqual(self.c.player_data[2].longest_route, 5)
    self.assertIsNone(self.c.longest_route_player)

  def testThereIsNoLargestArmy(self):
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([16, 6], 0)
    self.c.played_dev = 0
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([16, 8], 0)
    self.c.played_dev = 0
    self.c.handle_play_dev("knight", None, 0)
    self.c.handle_expel([13, 3], 0)
    self.assertEqual(self.c.player_data[0].knights_played, 0)
    self.assertEqual(self.c.player_data[1].knights_played, 0)
    self.assertEqual(self.c.player_data[2].knights_played, 0)
    self.assertIsNone(self.c.largest_army_player)


class TestBarbarianInvasion(BaseInputHandlerTest):
  TEST_FILE = "barbarian_test.json"

  def testThreeBarbariansLand(self):
    with mock.patch.object(islanders.random, "randint", side_effect=[1, 2, 3, 5, 4, 6]):
      self.handle(1, {"type": "settle", "location": [9, 7]})
    expected_tiles = [(13, 3), (13, 5), (10, 8)]
    for tile in self.c.tiles.values():
      with self.subTest(tile=tile.location):
        if tile.location in expected_tiles:
          self.assertEqual(tile.barbarians, 1)
        else:
          self.assertEqual(tile.barbarians, 0)
        self.assertFalse(tile.conquered)

  def testCityAlsoCausesInvasion(self):
    # No invasion caused by building a road
    self.handle(1, {"type": "road", "location": [2, 6, 3, 7]})
    for tile in self.c.tiles.values():
      with self.subTest(tile=tile.location):
        self.assertEqual(tile.barbarians, 0)

    # Invasion caused by upgrading to a city
    with mock.patch.object(islanders.random, "randint", side_effect=[1, 2, 3, 5, 4, 6]):
      self.handle(1, {"type": "city", "location": [0, 6]})
    expected_tiles = [(13, 3), (13, 5), (10, 8)]
    for tile in self.c.tiles.values():
      with self.subTest(tile=tile.location):
        if tile.location in expected_tiles:
          self.assertEqual(tile.barbarians, 1)
        else:
          self.assertEqual(tile.barbarians, 0)
        self.assertFalse(tile.conquered)

  def testDuplicateNumbersAreRerolled(self):
    # An eight is rolled twice - once as 3, 5 and again as 4, 4. The second one should be rerolled.
    with mock.patch.object(islanders.random, "randint", side_effect=[1, 2, 3, 5, 4, 4, 4, 6]):
      self.handle(1, {"type": "city", "location": [0, 6]})
    expected_tiles = [(13, 3), (13, 5), (10, 8)]
    for loc in expected_tiles:
      with self.subTest(tile=loc):
        self.assertEqual(self.c.tiles[loc].barbarians, 1)

  def testSevensAreRerolled(self):
    # Ignore the 7 and reroll
    with mock.patch.object(islanders.random, "randint", side_effect=[1, 2, 3, 4, 4, 4, 4, 6]):
      self.handle(1, {"type": "city", "location": [0, 6]})
    expected_tiles = [(13, 3), (13, 5), (10, 8)]
    for loc in expected_tiles:
      with self.subTest(tile=loc):
        self.assertEqual(self.c.tiles[loc].barbarians, 1)

  def testConqueredTilesAreNotRerolled(self):
    self.c.tiles[(13, 5)].barbarians = 3
    self.c.tiles[(13, 5)].conquered = True
    self.c.tiles[(13, 3)].barbarians = 2
    with mock.patch.object(islanders.random, "randint", side_effect=[1, 2, 3, 5, 4, 6]):
      self.handle(1, {"type": "city", "location": [0, 6]})
    self.assertEqual(self.c.tiles[(13, 5)].barbarians, 3)
    self.assertTrue(self.c.tiles[(13, 5)].conquered)
    self.assertEqual(self.c.tiles[(13, 3)].barbarians, 3)
    self.assertTrue(self.c.tiles[(13, 3)].conquered)
    self.assertEqual(self.c.tiles[(10, 8)].barbarians, 1)
    self.assertFalse(self.c.tiles[(10, 8)].conquered)

  def testNoMoreThanThirtyBarbarians(self):
    tiles = [(4, 2), (7, 1), (10, 2), (13, 3), (13, 5), (10, 8), (7, 9), (4, 8), (1, 7), (1, 5)]
    for loc in tiles:
      self.c.tiles[loc].barbarians = 3
      self.c.tiles[loc].conquered = True
    with mock.patch.object(islanders.random, "randint", side_effect=[1, 2, 3, 5, 4, 6]):
      self.handle(1, {"type": "city", "location": [0, 6]})
    for loc in tiles:
      with self.subTest(tile=loc):
        self.assertEqual(self.c.tiles[loc].barbarians, 3)
        self.assertTrue(self.c.tiles[loc].conquered)

  def testThirtyBarbarianLimitIncludesCaptured(self):
    self.c.player_data[0].captured_barbarians = 10
    self.c.player_data[1].captured_barbarians = 10
    self.c.player_data[2].captured_barbarians = 8
    with mock.patch.object(islanders.random, "randint", side_effect=[1, 2, 3, 5, 4, 6]):
      self.handle(1, {"type": "city", "location": [0, 6]})
    self.assertEqual(self.c.tiles[(13, 3)].barbarians, 1)
    self.assertEqual(self.c.tiles[(13, 5)].barbarians, 1)
    self.assertEqual(self.c.tiles[(10, 8)].barbarians, 0)

  def testThirtyBarbarianLimitBoardAndCaptured(self):
    self.c.player_data[0].captured_barbarians = 8
    self.c.player_data[1].captured_barbarians = 8
    self.c.player_data[2].captured_barbarians = 8
    self.c.tiles[(1, 5)].barbarians = 3
    self.c.tiles[(1, 7)].barbarians = 2
    with mock.patch.object(islanders.random, "randint", side_effect=[1, 2, 3, 5, 4, 6]):
      self.handle(1, {"type": "city", "location": [0, 6]})
    self.assertEqual(self.c.tiles[(13, 3)].barbarians, 1)
    self.assertEqual(self.c.tiles[(13, 5)].barbarians, 0)
    self.assertEqual(self.c.tiles[(10, 8)].barbarians, 0)


class TestBarbarianConquest(BaseInputHandlerTest):
  TEST_FILE = "barbarian_test.json"

  def testIsolatedSettlementsAreConquered(self):
    to_conquer = [(4, 8), (10, 2), (1, 5)]
    for loc in to_conquer:
      self.c.tiles[loc].barbarians = 2

    with mock.patch.object(islanders.random, "randint", side_effect=[3, 3, 3, 2, 4, 5]):
      self.handle(1, {"type": "city", "location": [0, 6]})
    for loc in to_conquer:
      with self.subTest(tile=loc):
        self.assertEqual(self.c.tiles[loc].barbarians, 3)
        self.assertTrue(self.c.tiles[loc].conquered)

    self.assertTrue(self.c.pieces[(3, 9)].conquered)
    self.assertTrue(self.c.pieces[(11, 1)].conquered)
    self.assertFalse(self.c.pieces[(0, 6)].conquered)

    # Also check that conquered ports no longer provide benefits
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc4"], 4)
    self.assertEqual(self.c.player_data[1].trade_ratios["rsrc4"], 3)
    self.assertEqual(self.c.player_data[2].trade_ratios["rsrc4"], 4)

  def testCastleAndDesertAreNeverConquered(self):
    to_conquer = [(10, 8), (4, 2), (7, 9)]
    for loc in to_conquer:
      self.c.tiles[loc].barbarians = 2

    with mock.patch.object(islanders.random, "randint", side_effect=[5, 5, 2, 2, 6, 5]):
      self.handle(1, {"type": "city", "location": [0, 6]})
    for loc in to_conquer:
      with self.subTest(tile=loc):
        self.assertEqual(self.c.tiles[loc].barbarians, 3)
        self.assertTrue(self.c.tiles[loc].conquered)

    self.assertFalse(self.c.pieces[(12, 8)].conquered)
    self.assertFalse(self.c.pieces[(2, 2)].conquered)

  def testRoadsAreNotConquered(self):
    to_conquer = [(10, 2), (13, 3), (13, 5)]
    for loc in to_conquer:
      self.c.tiles[loc].barbarians = 2

    with mock.patch.object(islanders.random, "randint", side_effect=[4, 5, 1, 2, 4, 4]):
      self.handle(1, {"type": "city", "location": [0, 6]})
    for loc in to_conquer:
      with self.subTest(tile=loc):
        self.assertEqual(self.c.tiles[loc].barbarians, 3)
        self.assertTrue(self.c.tiles[loc].conquered)

    self.assertTrue(self.c.pieces[(14, 4)].conquered)
    self.assertTrue(self.c.pieces[(11, 1)].conquered)
    self.assertFalse(self.c.roads[(12, 4, 14, 4)].conquered)
    self.assertEqual(self.c.player_data[2].longest_route, 1)


class TestBuildNextToConqueredTiles(BaseInputHandlerTest):
  TEST_FILE = "barbarian_test.json"

  def testCannotBuildNextToConqueredTiles(self):
    to_conquer = [(1, 5), (10, 8), (4, 8)]
    for loc in to_conquer:
      self.c.tiles[loc].barbarians = 2

    with mock.patch.object(islanders.random, "randint", side_effect=[3, 3, 3, 2, 5, 5]):
      self.handle(1, {"type": "city", "location": [0, 6]})
    with self.assertRaisesRegex(InvalidMove, "next to a conquered tile"):
      self.handle(1, {"type": "settle", "location": [9, 7]})
    with self.assertRaisesRegex(InvalidMove, "next to a conquered tile"):
      self.handle(1, {"type": "road", "location": [2, 6, 3, 5]})
    self.handle(1, {"type": "road", "location": [2, 6, 3, 7]})
    with self.assertRaisesRegex(InvalidMove, "next to a conquered tile"):
      self.handle(1, {"type": "settle", "location": [3, 7]})

  def testCanUpgradeConqueredSettlement(self):
    # The rules do not prohibit upgrading a conquered settlement to a city.
    to_conquer = [(1, 5), (1, 7), (10, 8)]
    for loc in to_conquer:
      self.c.tiles[loc].barbarians = 2

    with mock.patch.object(islanders.random, "randint", side_effect=[1, 1, 3, 3, 5, 5]):
      self.handle(1, {"type": "settle", "location": [9, 7]})
    self.handle(1, {"type": "city", "location": [0, 6]})

    # The new piece should still be conquered and not provide its port benefit.
    self.assertTrue(self.c.pieces[(0, 6)].conquered)
    self.assertEqual(self.c.player_data[1].trade_ratios["rsrc4"], 4)


class RecaptureBarbarianTest(BaseInputHandlerTest):
  TEST_FILE = "barbarian_test.json"

  def testInsufficientKnightsMeansNoBattle(self):
    locs = [(3, 1, 5, 1), (3, 3, 5, 3)]
    for loc in locs:
      self.c.knights[loc] = islanders.Knight(loc, 2, loc)
    self.c.tiles[(4, 2)].barbarians = 2
    self.handle(1, {"type": "end_turn"})
    self.assertEqual(self.c.turn_idx, 2)
    self.assertEqual(self.c.tiles[(4, 2)].barbarians, 2)
    self.assertEqual(self.c.player_data[2].captured_barbarians, 0)

  def testBattlesHappenInClockwiseOrder(self):
    locs = [(3, 1, 5, 1), (5, 1, 6, 2), (6, 2, 8, 2)]
    for loc in locs:
      self.c.knights[loc] = islanders.Knight(loc, 2, loc)
    self.c.tiles[(4, 2)].barbarians = 1
    self.c.tiles[(7, 1)].barbarians = 1
    # One barbarian on each tile, two barbarians surrounding each tile.
    # At the end of the first battle, the knight at 5, 1, 6, 2 (rotation 4) will be lost,
    # leaving not enough knights to fight the barbarians for the second battle.
    with mock.patch.object(islanders.random, "randint", new=lambda *args: 1):
      self.handle(1, {"type": "end_turn"})

    self.assertEqual(self.c.turn_idx, 2)
    self.assertEqual(self.c.tiles[(4, 2)].barbarians, 0)
    self.assertEqual(self.c.tiles[(7, 1)].barbarians, 1)
    self.assertNotIn((5, 1, 6, 2), self.c.knights)
    self.assertIn((3, 1, 5, 1), self.c.knights)
    self.assertEqual(self.c.player_data[2].captured_barbarians, 1)

  @mock.patch.object(islanders.random, "shuffle", new=lambda lst: lst.sort(reverse=True))
  def testInsufficentKnightsDoesNotPreventFutureBattle(self):
    self.c.player_data[0].cards["gold"] = 0
    self.c.player_data[1].cards["gold"] = 0
    locs = [(8, 8, 9, 9), (6, 8, 8, 8)]
    for idx, loc in enumerate(locs):
      self.c.knights[loc] = islanders.Knight(loc, idx, loc)
    self.c.tiles[(10, 8)].barbarians = 1
    self.c.tiles[(7, 9)].barbarians = 1

    with mock.patch.object(islanders.random, "randint", new=lambda *args: 1):
      self.handle(1, {"type": "end_turn"})
      self.handle(1, {"type": "end_move_knights"})

    self.assertEqual(self.c.turn_idx, 2)
    self.assertEqual(self.c.tiles[(10, 8)].barbarians, 1)
    self.assertEqual(self.c.tiles[(7, 9)].barbarians, 0)
    self.assertNotIn((8, 8, 9, 9), self.c.knights)
    self.assertIn((6, 8, 8, 8), self.c.knights)
    self.assertEqual(self.c.player_data[1].captured_barbarians, 1)
    self.assertEqual(self.c.player_data[0].captured_barbarians, 0)
    self.assertEqual(self.c.player_data[1].cards["gold"], 0)
    # Player 0 lost a knight and lost the tie-break for prisoner capture
    self.assertEqual(self.c.player_data[0].cards["gold"], 6)

  def testRecapturingRestoresPort(self):
    self.c.tiles[(10, 2)].barbarians = 3
    self.c.tiles[(10, 2)].conquered = True
    self.c.check_conquest(self.c.tiles[(10, 2)])
    self.assertTrue(self.c.pieces[(11, 1)].conquered)
    self.assertEqual(self.c.player_data[2].trade_ratios["rsrc3"], 4)

    locs = [(8, 2, 9, 1), (9, 1, 11, 1), (11, 1, 12, 2), (11, 3, 12, 2)]
    for loc in locs:
      self.c.knights[loc] = islanders.Knight(loc, 0, loc)

    self.handle(1, {"type": "end_turn"})
    self.assertEqual(self.c.turn_idx, 2)
    self.assertEqual(self.c.tiles[(10, 2)].barbarians, 0)
    self.assertFalse(self.c.pieces[(11, 1)].conquered)
    self.assertEqual(self.c.player_data[2].trade_ratios["rsrc3"], 3)


class CapturedBarbarianTest(BaseInputHandlerTest):
  TEST_FILE = "barbarian_test.json"

  @mock.patch.object(islanders.random, "randint", new=lambda *args: 3)  # Nobody loses any knights
  @mock.patch.object(islanders.random, "shuffle", new=lambda lst: lst.sort(reverse=True))
  def testCapturedBarbarianCounts(self):
    tests = [
      {"knights": [2], "barbarians": 1, "captured": [1], "gold": [0]},
      {"knights": [1, 1], "barbarians": 1, "captured": [0, 1], "gold": [3, 0]},
      {"knights": [1, 1, 1], "barbarians": 1, "captured": [0, 0, 1], "gold": [3, 3, 0]},
      {"knights": [3], "barbarians": 2, "captured": [2], "gold": [0]},
      {"knights": [2, 2], "barbarians": 2, "captured": [1, 1], "gold": [0, 0]},
      {"knights": [2, 1], "barbarians": 2, "captured": [1, 1], "gold": [0, 0]},
      {"knights": [1, 1, 1], "barbarians": 2, "captured": [0, 1, 1], "gold": [3, 0, 0]},
      {"knights": [2, 2], "barbarians": 3, "captured": [1, 2], "gold": [3, 0]},
      {"knights": [3, 2], "barbarians": 3, "captured": [2, 1], "gold": [0, 0]},
      {"knights": [2, 1, 1], "barbarians": 3, "captured": [1, 1, 1], "gold": [0, 0, 0]},
      {"knights": [2, 2, 1], "barbarians": 3, "captured": [1, 1, 1], "gold": [0, 0, 0]},
      {"knights": [1, 1, 1, 1], "barbarians": 3, "captured": [0, 1, 1, 1], "gold": [3, 0, 0, 0]},
      {"knights": [2, 1, 1, 1], "barbarians": 3, "captured": [0, 1, 1, 1], "gold": [3, 0, 0, 0]},
      {"knights": [2, 2, 1, 1], "barbarians": 3, "captured": [0, 1, 1, 1], "gold": [3, 0, 0, 0]},
    ]

    edge_locs = self.c.tiles[(7, 1)].location.get_edge_locations()
    self.c.add_player("darkviolet", "purple")

    for test in tests:
      with self.subTest(**test):
        # Put the correct number of barbarians on the tile
        self.c.tiles[(7, 1)].barbarians = test["barbarians"]

        # Clear out old knights and put in the correct number of knights per player
        self.c.knights.clear()
        i = 0
        for player_idx, knight_count in enumerate(test["knights"]):
          for _ in range(knight_count):
            self.c.knights[edge_locs[i]] = islanders.Knight(edge_locs[i], player_idx, edge_locs[i])
            i += 1

        # Remove any gold and captured barbarians the players may have left over
        for player in self.c.player_data:
          player.cards["gold"] = 0
          player.captured_barbarians = 0

        # Run the battle
        self.c.barbarian_battle(self.c.tiles[(7, 1)])

        # Assert on captured barbarians and gold
        self.assertEqual(sum(test["captured"]), test["barbarians"])
        for player_idx, player in enumerate(self.c.player_data):
          with self.subTest(player=player_idx):
            if player_idx >= len(test["captured"]):
              self.assertEqual(player.captured_barbarians, 0)
              self.assertEqual(player.cards["gold"], 0)
              continue
            self.assertEqual(player.captured_barbarians, test["captured"][player_idx])
            self.assertEqual(player.cards["gold"], test["gold"][player_idx])

  @mock.patch.object(islanders.random, "randint", new=lambda *args: 0)
  def testKnightsCountedBeforeKnightLoss(self):
    self.c.player_data[0].cards["gold"] = 0
    self.c.player_data[1].cards["gold"] = 0

    edge_locs = self.c.tiles[(7, 1)].location.get_edge_locations()
    # Player 0 will lose both knights at rotations 0 and 3. Player 1 will lose nothing.
    self.c.knights[edge_locs[0]] = islanders.Knight(edge_locs[0], 0, edge_locs[0])
    self.c.knights[edge_locs[1]] = islanders.Knight(edge_locs[1], 1, edge_locs[1])
    self.c.knights[edge_locs[3]] = islanders.Knight(edge_locs[3], 0, edge_locs[3])

    self.c.tiles[(7, 1)].barbarians = 2
    self.c.barbarian_battle(self.c.tiles[(7, 1)])

    self.assertEqual(self.c.player_data[0].captured_barbarians, 1)
    self.assertEqual(self.c.player_data[1].captured_barbarians, 1)
    self.assertEqual(self.c.player_data[0].cards["gold"], 6)  # For losing two knights.
    self.assertEqual(self.c.player_data[1].cards["gold"], 0)


class TestIntrigue(BaseInputHandlerTest):
  TEST_FILE = "barbarian_test.json"

  def setUp(self):
    super().setUp()
    self.c.dev_cards.append("intrigue")
    for player in self.c.player_data:
      player.captured_barbarians = 0
      player.cards["gold"] = 0

  def testRemoveBarbarian(self):
    locs = [(4, 2), (10, 2), (4, 8)]
    for count, loc in enumerate(locs):
      self.c.tiles[loc].barbarians = count + 1
      if count + 1 == 3:
        self.c.tiles[loc].conquered = True
        self.c.check_conquest(self.c.tiles[loc])
    self.c.handle_buy_dev(1)

    self.assertEqual(self.c.turn_phase, "intrigue")
    self.c.handle_intrigue([10, 2], 1)
    self.assertEqual(self.c.turn_phase, "main")
    self.assertEqual(self.c.tiles[(10, 2)].barbarians, 1)
    self.assertEqual(self.c.player_data[1].captured_barbarians, 1)
    self.assertEqual(self.c.player_data[1].cards["gold"], 0)

  def testInvalidLocation(self):
    self.c.tiles[(10, 2)].barbarians = 2
    self.c.handle_buy_dev(1)

    with self.assertRaisesRegex(AssertionError, "tile.*location"):
      self.c.handle_intrigue([12, 4], 1)
    with self.assertRaisesRegex(InvalidMove, "a tile with barbarians"):
      self.c.handle_intrigue([13, 5], 1)

  def testRemoveBarbarianAndRecapture(self):
    locs = [(4, 2), (10, 2), (4, 8)]
    for count, loc in enumerate(locs):
      self.c.tiles[loc].barbarians = count + 1
      if count + 1 == 3:
        self.c.tiles[loc].conquered = True
        self.c.check_conquest(self.c.tiles[loc])
    self.assertTrue(self.c.tiles[(4, 8)].conquered)
    self.c.handle_buy_dev(1)

    self.c.handle_intrigue([4, 8], 1)
    self.assertEqual(self.c.tiles[(4, 8)].barbarians, 2)
    self.assertFalse(self.c.tiles[(4, 8)].conquered)
    self.assertEqual(self.c.player_data[1].captured_barbarians, 1)
    self.assertEqual(self.c.player_data[1].cards["gold"], 0)

  def testNoBarbariansAvailable(self):
    self.c.dev_cards.extend(["treason", "intrigue"])
    num_cards = len(self.c.dev_cards)
    self.c.handle_buy_dev(1)

    self.assertEqual(self.c.turn_phase, "treason")
    self.assertEqual(len(self.c.dev_cards), num_cards - 2)

  @mock.patch.object(islanders.random, "shuffle", new=lambda cards: cards.sort())
  def testNoBarbariansAndReshuffle(self):
    self.c.dev_cards.clear()
    self.c.dev_cards.append("intrigue")
    self.c.handle_buy_dev(1)

    self.assertEqual(self.c.turn_phase, "treason")
    self.assertEqual(len(self.c.dev_cards), 25)

  @mock.patch.object(islanders.random, "shuffle")
  def testNoBarbariansMultipleReshuffles(self, mock_shuffle):
    def shuffle_with_intrigue_on_top(cards):
      cards.sort(reverse=True)
      for _ in range(4):
        cards.pop()

    mock_shuffle.side_effect = shuffle_with_intrigue_on_top
    self.c.dev_cards.clear()
    self.c.dev_cards.append("intrigue")
    self.c.handle_buy_dev(1)

    self.assertEqual(self.c.turn_phase, "knight")
    self.assertEqual(len(self.c.dev_cards), 17)


class TestTreason(BaseInputHandlerTest):
  TEST_FILE = "barbarian_test.json"

  def setUp(self):
    super().setUp()
    self.c.dev_cards.append("treason")

  def testMoveBarbarians(self):
    self.c.player_data[1].cards["gold"] = 0
    locs = [(10, 2), (4, 8)]
    for loc in locs:
      self.c.tiles[loc].barbarians = 2

    self.c.handle_buy_dev(1)
    self.assertEqual(self.c.turn_phase, "treason")
    self.c.handle_treason((10, 2), (4, 8), (4, 2), (10, 8), 1)
    for loc in locs + [(4, 2), (10, 8)]:
      with self.subTest(loc=loc):
        self.assertEqual(self.c.tiles[loc].barbarians, 1)
    self.assertEqual(self.c.player_data[1].cards["gold"], 2)

  def testMoveAndChangeConquest(self):
    locs = [(1, 5), (1, 7), (4, 8), (10, 2)]
    for idx, loc in enumerate(locs):
      self.c.tiles[loc].barbarians = 2
      if idx % 2 == 0:
        self.c.tiles[loc].barbarians = 3
        self.c.tiles[loc].conquered = True
        self.c.check_conquest(self.c.tiles[loc])

    self.assertTrue(self.c.pieces[(3, 9)].conquered)
    self.assertFalse(self.c.pieces[(11, 1)].conquered)
    self.assertFalse(self.c.pieces[(0, 6)].conquered)

    self.c.handle_buy_dev(1)
    self.c.handle_treason((1, 5), (4, 8), (1, 7), (10, 2), 1)
    self.assertFalse(self.c.tiles[(1, 5)].conquered)
    self.assertFalse(self.c.tiles[(4, 8)].conquered)
    self.assertTrue(self.c.tiles[(1, 7)].conquered)
    self.assertTrue(self.c.tiles[(10, 2)].conquered)
    self.assertFalse(self.c.pieces[(3, 9)].conquered)
    self.assertTrue(self.c.pieces[(11, 1)].conquered)
    self.assertFalse(self.c.pieces[(0, 6)].conquered)

  def testInvalidTiles(self):
    locs = [(10, 2), (4, 8)]
    for loc in locs:
      self.c.tiles[loc].barbarians = 2
    self.c.tiles[(1, 5)].barbarians = 3
    self.c.tiles[(1, 5)].conquered = True

    self.c.handle_buy_dev(1)
    with self.assertRaisesRegex(InvalidMove, "distinct tiles"):
      self.c.handle_treason((4, 8), (4, 8), (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "distinct tiles"):
      self.c.handle_treason((10, 2), (4, 8), (4, 8), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "specify both.*from"):
      self.c.handle_treason(None, (4, 8), (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "specify tile.*from"):
      self.c.handle_treason((4, 8), None, (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "specify tile.*send"):
      self.c.handle_treason((4, 8), (10, 2), None, (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "specify both.*send"):
      self.c.handle_treason((4, 8), (10, 2), (10, 8), None, 1)
    with self.assertRaisesRegex(InvalidMove, "tiles with barbarians"):
      self.c.handle_treason((7, 1), (4, 8), (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "coastal tile"):
      self.c.handle_treason((10, 2), (4, 8), (4, 2), (7, 5), 1)
    with self.assertRaisesRegex(InvalidMove, "numbered tile"):
      self.c.handle_treason((10, 2), (4, 8), (4, 2), (1, 1), 1)
    with self.assertRaisesRegex(InvalidMove, "unconquered tile"):
      self.c.handle_treason((10, 2), (4, 8), (4, 2), (1, 5), 1)

  def testEmptyBoard(self):
    self.c.handle_buy_dev(1)
    with self.assertRaisesRegex(InvalidMove, "hould not specify"):
      self.c.handle_treason((4, 8), (10, 2), (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "hould not specify"):
      self.c.handle_treason(None, (10, 2), (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "hould not specify"):
      self.c.handle_treason((4, 8), None, (4, 2), (10, 8), 1)
    self.c.handle_treason(None, None, (4, 2), (10, 8), 1)
    self.assertEqual(self.c.tiles[(4, 2)].barbarians, 1)
    self.assertEqual(self.c.tiles[(10, 8)].barbarians, 1)

  def testOneBarbarianOnBoard(self):
    self.c.tiles[(4, 8)].barbarians = 1
    self.c.handle_buy_dev(1)
    with self.assertRaisesRegex(InvalidMove, "hould not specify"):
      self.c.handle_treason((4, 8), (10, 2), (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "hould not specify"):
      self.c.handle_treason((4, 8), None, (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "specify tile.*take"):
      self.c.handle_treason(None, None, (4, 2), (10, 8), 1)
    self.c.handle_treason(None, (4, 8), (4, 2), (10, 8), 1)
    self.assertEqual(self.c.tiles[(4, 8)].barbarians, 0)
    self.assertEqual(self.c.tiles[(4, 2)].barbarians, 1)
    self.assertEqual(self.c.tiles[(10, 8)].barbarians, 1)

  def testNearlyEmptyBoardNoBarbarianSupply(self):
    self.c.tiles[(1, 5)].barbarians = 1
    for idx, player in enumerate(self.c.player_data):  # 29 barbarians gone from the supply
      player.captured_barbarians = 9 if idx == 0 else 10

    self.c.handle_buy_dev(1)
    # Because there are no barbarians left in the supply, you should not place a second barbarian.
    with self.assertRaisesRegex(InvalidMove, "not specify.*send"):
      self.c.handle_treason(None, (1, 5), (4, 2), (10, 8), 1)
    self.c.handle_treason(None, (1, 5), (4, 2), None, 1)

  def testBoardAlmostFull(self):
    self.c.player_data[1].cards["gold"] = 0
    locs = [(4, 2), (7, 1), (10, 2), (13, 3), (13, 5), (10, 8), (7, 9), (4, 8), (1, 7), (1, 5)]
    for loc in locs:  # Exactly one tile on the board with room for more barbarians.
      self.c.tiles[loc].barbarians = 3
      if loc == (1, 5):
        self.c.tiles[loc].barbarians = 0
      self.c.check_conquest(self.c.tiles[loc])

    self.c.handle_buy_dev(1)
    self.assertEqual(self.c.turn_phase, "treason")
    with self.assertRaisesRegex(InvalidMove, "hould not specify"):
      self.c.handle_treason((4, 8), (1, 5), (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "specify the tile.*from"):
      self.c.handle_treason((1, 5), None, (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "specify tile.*take"):
      self.c.handle_treason(None, None, (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "hould not specify"):
      self.c.handle_treason(None, (1, 5), (4, 2), (10, 8), 1)
    with self.assertRaisesRegex(InvalidMove, "hould not specify"):
      self.c.handle_treason(None, (1, 5), None, (4, 2), 1)
    with self.assertRaisesRegex(InvalidMove, "specify tile.*take"):
      self.c.handle_treason(None, None, None, None, 1)
    with self.assertRaisesRegex(InvalidMove, "unconquered tile"):
      self.c.handle_treason(None, (1, 7), (4, 2), None, 1)
    self.c.handle_treason(None, (4, 2), (1, 5), None, 1)
    self.assertEqual(self.c.tiles[(4, 2)].barbarians, 2)
    self.assertEqual(self.c.tiles[(1, 5)].barbarians, 1)
    self.assertEqual(self.c.player_data[1].cards["gold"], 2)

  def testBoardFull(self):
    self.c.player_data[1].cards["gold"] = 0
    locs = [(4, 2), (7, 1), (10, 2), (13, 3), (13, 5), (10, 8), (7, 9), (4, 8), (1, 7), (1, 5)]
    for loc in locs:
      self.c.tiles[loc].barbarians = 3
      self.c.check_conquest(self.c.tiles[loc])

    self.c.handle_buy_dev(1)
    self.assertEqual(self.c.turn_phase, "main")
    self.assertEqual(self.c.player_data[1].cards["gold"], 2)
    for loc in locs:
      with self.subTest(loc=loc):
        self.assertEqual(self.c.tiles[loc].barbarians, 3)


class TestTreasonCalculation(BaseInputHandlerTest):
  TEST_FILE = "barbarian_test.json"
  LOCS = ((4, 2), (7, 1), (10, 2), (13, 3), (13, 5), (10, 8), (7, 9), (4, 8), (1, 7), (1, 5))

  def setBarbarianCounts(self, empty_tiles, full_tiles, supply_count):
    partial_tiles = 10 - empty_tiles - full_tiles
    assert partial_tiles >= 0
    capture_count = 30 - full_tiles * 3 - partial_tiles * 2 - supply_count
    assert capture_count >= 0
    for loc in self.LOCS:
      if empty_tiles > 0:
        self.c.tiles[loc].barbarians = 0
        self.c.tiles[loc].conquered = False
        empty_tiles -= 1
      elif full_tiles > 0:
        self.c.tiles[loc].barbarians = 3
        self.c.tiles[loc].conquered = True
        full_tiles -= 1
      else:
        self.c.tiles[loc].barbarians = 2
        self.c.tiles[loc].conquered = False
    for idx, player in enumerate(self.c.player_data):
      player.captured_barbarians = (capture_count + idx) // 3

  def testBarbarianSourceAndDestinationCounts(self):
    tests = [
      {"empty": 10, "full": 0, "supply": 30, "srcs": 0, "dests": 2},
      {"empty": 10, "full": 0, "supply": 0, "srcs": 0, "dests": 0},
      {"empty": 10, "full": 0, "supply": 1, "srcs": 0, "dests": 1},
      {"empty": 10, "full": 0, "supply": 2, "srcs": 0, "dests": 2},
      {"empty": 9, "full": 0, "supply": 28, "srcs": 1, "dests": 2},
      {"empty": 9, "full": 1, "supply": 27, "srcs": 1, "dests": 2},
      {"empty": 9, "full": 0, "supply": 0, "srcs": 1, "dests": 1},
      {"empty": 9, "full": 0, "supply": 1, "srcs": 1, "dests": 2},
      {"empty": 8, "full": 0, "supply": 26, "srcs": 2, "dests": 2},
      {"empty": 8, "full": 0, "supply": 0, "srcs": 2, "dests": 2},
      {"empty": 8, "full": 2, "supply": 24, "srcs": 2, "dests": 2},
      {"empty": 5, "full": 5, "supply": 15, "srcs": 2, "dests": 2},
      {"empty": 2, "full": 8, "supply": 6, "srcs": 2, "dests": 2},
      {"empty": 0, "full": 8, "supply": 2, "srcs": 2, "dests": 2},
      {"empty": 1, "full": 9, "supply": 3, "srcs": 1, "dests": 1},
      {"empty": 0, "full": 9, "supply": 1, "srcs": 1, "dests": 1},
      {"empty": 0, "full": 9, "supply": 0, "srcs": 1, "dests": 1},
      {"empty": 0, "full": 10, "supply": 0, "srcs": 0, "dests": 0},
    ]
    for test in tests:
      with self.subTest(**test):
        self.setBarbarianCounts(test["empty"], test["full"], test["supply"])
        src_count, dest_count = self.c._calculate_treason_tiles()
        self.assertEqual(src_count, test["srcs"])
        self.assertEqual(dest_count, test["dests"])


class TestExtraBuildPhase(BreakpointTestMixin):
  def setUp(self):
    self.g = islanders.IslandersGame()
    self.g.connected = {"player1", "player2", "player3", "player4", "player5"}
    self.g.host = "player1"
    for u in self.g.connected:
      self.g.handle_join(u, {"name": u})
    self.g.handle_start("player1", {"options": {}})
    self.c = self.g.game

  def testNoExtraBuildDuringPlacePhase(self):
    self.handle(0, {"type": "settle", "location": [3, 3]})
    self.handle(0, {"type": "road", "location": [3, 3, 5, 3]})
    self.assertEqual(self.c.game_phase, "place1")
    self.assertEqual(self.c.turn_phase, "settle")
    self.assertEqual(self.c.turn_idx, 1)

    # Also validate that there is no special build phase after the last settlement/road.
    self.c.game_phase = "place2"
    self.c.action_stack = ["road", "settle"]
    self.c.turn_idx = 0
    self.handle(0, {"type": "settle", "location": [9, 3]})
    self.handle(0, {"type": "road", "location": [9, 3, 11, 3]})
    self.assertEqual(self.c.game_phase, "main")
    self.assertEqual(self.c.turn_phase, "dice")
    self.assertEqual(self.c.turn_idx, 0)

  def testExtraBuildActions(self):
    self.c.game_phase = "main"
    self.c.action_stack.clear()
    self.c.turn_idx = 4
    self.c.add_piece(islanders.Piece(3, 3, "settlement", 0))
    self.c._add_road(Road([3, 3, 5, 3], "road", 0))
    self.c._add_road(Road([5, 3, 6, 4], "road", 0))
    self.c.player_data[0].cards.update({"rsrc1": 3, "rsrc2": 3, "rsrc3": 5, "rsrc4": 3, "rsrc5": 5})
    self.c.player_data[4].cards.update({"rsrc1": 3, "rsrc2": 3, "rsrc3": 5, "rsrc4": 3, "rsrc5": 5})

    with self.assertRaises(islanders.NotYourTurn):
      self.handle(0, {"type": "settle", "location": [6, 4]})

    self.handle(4, {"type": "end_turn"})
    self.assertEqual(self.c.game_phase, "main")
    self.assertEqual(self.c.turn_phase, "extra_build")
    self.assertEqual(self.c.extra_build_idx, 0)
    self.handle(0, {"type": "settle", "location": [6, 4]})
    self.handle(0, {"type": "road", "location": [6, 4, 8, 4]})
    self.handle(0, {"type": "city", "location": [3, 3]})
    self.handle(0, {"type": "buy_dev"})

    with self.assertRaises(islanders.NotYourTurn):
      self.handle(0, {"type": "end_turn"})
    with self.assertRaises(islanders.NotYourTurn):
      self.handle(0, {"type": "play_dev", "card_type": "knight"})
    self.handle(0, {"type": "end_extra_build"})
    self.assertEqual(self.c.game_phase, "main")
    self.assertEqual(self.c.turn_phase, "extra_build")
    self.assertEqual(self.c.extra_build_idx, 1)

    with self.assertRaises(islanders.NotYourTurn):
      self.handle(4, {"type": "buy_dev"})

  def testLastExtraBuild(self):
    self.c.game_phase = "main"
    self.c.action_stack = ["extra_build"]
    self.c.turn_idx = 4
    self.c.extra_build_idx = 3

    self.handle(3, {"type": "end_extra_build"})
    self.assertEqual(self.c.game_phase, "main")
    self.assertEqual(self.c.turn_phase, "dice")
    self.assertIsNone(self.c.extra_build_idx)
    self.assertEqual(self.c.turn_idx, 0)


class TestUnstartedGame(unittest.TestCase):
  def setUp(self):
    self.c = islanders.IslandersGame()

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
      self.assertIsInstance(self.c.player_sessions[key], islanders.Player)
    self.assertEqual(self.c.host, "one")
    self.c.disconnect_user("two")
    self.assertCountEqual(self.c.player_sessions.keys(), ["one", "three"])
    self.c.connect_user("four")
    self.c.handle_join("four", {"name": "player4"})
    self.assertCountEqual(self.c.player_sessions.keys(), ["one", "four", "three"])

  def testRejoin(self):
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.handle_join("one", {"name": "player1", "color": "red"})
    self.c.handle_join("two", {"name": "player2", "color": "blue"})
    self.c.handle_join("three", {"name": "player3", "color": "limegreen"})
    self.assertSetEqual(
      {p.color for p in self.c.player_sessions.values()}, {"red", "blue", "limegreen"}
    )
    self.c.handle_join("three", {"name": "3player", "color": "saddlebrown"})
    self.assertSetEqual(
      {p.color for p in self.c.player_sessions.values()}, {"red", "blue", "saddlebrown"}
    )
    self.assertSetEqual(
      {p.name for p in self.c.player_sessions.values()}, {"player1", "player2", "3player"}
    )

  def testChooseBadScenario(self):
    self.assertIsNone(self.c.game)
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.connect_user("four")
    with self.assertRaises(KeyError):
      self.c.handle_change_scenario("one", {})
    with self.assertRaisesRegex(InvalidMove, "Unknown scenario"):
      self.c.handle_change_scenario("one", {"scenario": "nsaoeu"})

  def testStartGame(self):
    self.assertIsNone(self.c.game)
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.connect_user("four")
    with self.assertRaisesRegex(InvalidMove, "at least two players"):
      self.c.handle_start("one", {"options": {"Scenario": "Standard Map"}})

    self.c.handle_join("one", {"name": "player1"})
    self.c.handle_join("two", {"name": "player2"})
    self.c.handle_join("three", {"name": "player3"})
    self.c.handle_join("four", {"name": "player4"})
    with self.assertRaisesRegex(InvalidMove, "not the host"):
      self.c.handle_start("two", {"options": {}})
    self.assertIsNone(self.c.game)

    self.c.handle_start("one", {"options": {}})
    self.assertIsNotNone(self.c.game)
    self.assertIsNone(self.c.host)
    self.assertGreater(len(self.c.game.tiles.keys()), 0)

    with self.assertRaisesRegex(InvalidMove, "already started"):
      self.c.handle_start("one", {"options": {}})
    with self.assertRaisesRegex(islanders.InvalidPlayer, "already started"):
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
    self.c.handle_start(self.c.host, {"options": {}})

    self.assertIsNotNone(self.c.game)
    self.assertEqual(len(self.c.game.player_data), 2)
    self.assertCountEqual(self.c.player_sessions.keys(), ["two", "four"])
    self.assertEqual(self.c.game.player_data[self.c.player_sessions["two"]].name, "player2")
    self.assertEqual(self.c.game.player_data[self.c.player_sessions["four"]].name, "player4")
    self.assertDictEqual(self.c.game.discard_players, {})
    self.assertDictEqual(self.c.game.counter_offers, {})


class TestGameOptions(unittest.TestCase):
  def setUp(self):
    self.c = islanders.IslandersGame()

  def testInitialState(self):
    basic_options = islanders.Options()
    self.assertCountEqual(self.c.choices.keys(), basic_options.keys())
    for key, val in self.c.choices.items():
      self.assertDictEqual(val.__dict__, basic_options[key].__dict__)
    self.assertEqual(self.c.scenario, "Standard Map")

  def testOptions(self):
    self.c.scenario = "Beginner's Map"
    json_for_player = json.loads(self.c.for_player(None))
    option_data = json_for_player["options"]
    self.assertIn("debug", option_data)
    self.assertEqual(option_data["debug"]["name"], "Debug")
    self.assertFalse(option_data["debug"]["value"])
    self.assertIsNone(option_data["debug"]["choices"])
    self.assertIn("extra_build", option_data)
    self.assertEqual(option_data["extra_build"]["name"], "5-6 Players")
    self.assertFalse(option_data["extra_build"]["value"])

  def testModifyOptions(self):
    self.c.host = "a"
    self.c.handle_change_scenario("a", {"scenario": "Test Map"})
    self.c.handle_select_option("a", {"options": {"debug": True, "friendly_robber": True}})
    self.assertEqual(self.c.scenario, "Test Map")
    self.assertTrue(self.c.choices.debug)
    self.assertTrue(self.c.choices.friendly_robber)
    self.assertFalse(self.c.choices.seafarers)

    self.c.handle_change_scenario("a", {"scenario": "Beginner's Map"})
    self.assertEqual(self.c.scenario, "Beginner's Map")
    self.assertTrue(self.c.choices.debug)
    self.assertTrue(self.c.choices.friendly_robber)
    self.c.handle_select_option("a", {"options": {"debug": False}})
    self.assertEqual(self.c.scenario, "Beginner's Map")
    self.assertFalse(self.c.choices.debug)
    self.assertTrue(self.c.choices.friendly_robber)
    self.assertFalse(self.c.choices.seafarers)

    self.c.handle_change_scenario("a", {"scenario": "Standard Map"})
    self.assertEqual(self.c.scenario, "Standard Map")
    # Friendly robber should be reset to default because the default changed.
    self.assertFalse(self.c.choices.friendly_robber)
    self.assertFalse(self.c.choices.debug)
    self.assertFalse(self.c.choices.seafarers)

    self.c.handle_change_scenario("a", {"scenario": "The Four Islands"})
    self.assertEqual(self.c.scenario, "The Four Islands")
    # Should set the option to its default even if it wasn't in the provided options.
    self.assertFalse(self.c.choices.friendly_robber)
    self.assertFalse(self.c.choices.debug)
    self.assertTrue(self.c.choices.seafarers)

    self.c.handle_select_option("a", {"options": {"seafarers": False}})
    # You cannot override a forced option.
    self.assertTrue(self.c.choices.seafarers)

  def testStartWithOptions(self):
    self.c.connect_user("one")
    self.c.connect_user("two")
    self.c.connect_user("three")
    self.c.handle_join("one", {"name": "player1"})
    self.c.handle_join("two", {"name": "player2"})
    self.c.handle_join("three", {"name": "player3"})

    self.c.handle_select_option("one", {"options": {"debug": True}})
    # Completely change the options before starting the game; make sure they're honored.
    self.c.handle_start("one", {"options": {"debug": False, "friendly_robber": True}})
    self.assertIsNotNone(self.c.game)
    self.assertTrue(self.c.game.options.friendly_robber)
    self.assertFalse(self.c.game.options.debug)

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

    self.c.handle_change_scenario("one", {"scenario": "Standard Map"})
    self.assertTrue(self.c.choices.extra_build)

    self.c.disconnect_user("two")
    self.assertFalse(self.c.choices.extra_build)

    self.c.handle_start("one", {"options": {}})
    self.assertFalse(self.c.game.options.extra_build)

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

    self.c.handle_change_scenario("one", {"scenario": "Standard Map"})
    self.assertFalse(self.c.choices.extra_build)

    self.c.handle_join("five", {"name": "player5"})
    self.assertTrue(self.c.choices.extra_build)

    self.c.handle_start("one", {"options": {}})
    self.assertTrue(self.c.game.options.extra_build)


if __name__ == "__main__":
  unittest.main()
