#!/usr/bin/env python3

import collections
import os
import sys
import unittest

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from islanders.islanders import (
  InvalidMove,
  InvalidInput,
  Piece,
  CornerLocation,
  Knight,
  NotYourTurn,
  Road,
  TileLocation,
)
from islanders.test_islanders import BaseInputHandlerTest


class AlchemistTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.action_stack.append("dice")
    self.c.player_data[0].cards["alchemist"] = 1

  def testPlayAndGetResources(self):
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    selection = {"red": 3, "white": 2}
    self.handle(0, {"type": "play_dev", "card_type": "alchemist", "selection": selection})

    self.assertEqual(self.c.turn_phase, "main")
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {"rsrc4": 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"alchemist": 1})
    self.assertEqual(self.c.dice_roll, (3, 2))

  def testPlayAndMoveRobber(self):
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    selection = {"red": 3, "white": 4}
    self.handle(0, {"type": "play_dev", "card_type": "alchemist", "selection": selection})

    self.assertEqual(self.c.turn_phase, "discard")
    self.assertEqual(self.c.action_stack, ["rob", "robber", "discard"])
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"alchemist": 1})
    self.assertEqual(self.c.dice_roll, (3, 4))

  def testInvalidInputs(self):
    data = {"type": "play_dev", "card_type": "alchemist"}
    with self.assertRaisesRegex(InvalidMove, "Invalid dice selection"):
      self.handle(0, {"selection": 7, **data})
    with self.assertRaisesRegex(InvalidMove, "Invalid dice selection"):
      self.handle(0, {"selection": [3, 4], **data})
    with self.assertRaisesRegex(InvalidMove, "Invalid dice selection"):
      self.handle(0, {"selection": {"red": 3, "white": 3, "blue": 3}, **data})
    with self.assertRaisesRegex(InvalidMove, "Invalid dice selection"):
      self.handle(0, {"selection": {"red": 3.5, "white": 3.5}, **data})
    with self.assertRaisesRegex(InvalidInput, "between 1 and 6"):
      self.handle(0, {"selection": {"red": 0, "white": 0}, **data})

  def testCannotPlayDuringMainPhase(self):
    self.c.action_stack.pop()
    selection = {"red": 3, "white": 4}
    with self.assertRaisesRegex(InvalidMove, "before rolling the dice"):
      self.handle(0, {"type": "play_dev", "card_type": "alchemist", "selection": selection})

  def testCannotPlayWithoutCard(self):
    self.c.player_data[0].cards["alchemist"] = 0
    selection = {"red": 3, "white": 4}
    with self.assertRaisesRegex(InvalidMove, "do not have any alchemist"):
      self.handle(0, {"type": "play_dev", "card_type": "alchemist", "selection": selection})


class EngineerTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.player_data[0].cards["engineer"] = 1
    self.c.pieces[(8, 4)].piece_type = "city"
    self.c.options["city_walls"].force(True)

  def testCannotPlayAsDevCard(self):
    with self.assertRaisesRegex(InvalidMove, "play that card while building"):
      self.handle(0, {"type": "play_dev", "card_type": "engineer", "selection": [8, 4]})

  def testBuildCityWalls(self):
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.handle(0, {"type": "walls", "selection": ["engineer"], "location": [8, 4]})
    self.assertTrue(self.c.pieces[(8, 4)].walls)
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"engineer": 1})

  def testCannotPlayWithoutCard(self):
    self.c.player_data[0].cards["engineer"] = 0
    with self.assertRaisesRegex(InvalidMove, "would need an extra 1 {engineer}"):
      self.handle(0, {"type": "walls", "selection": ["engineer"], "location": [8, 4]})

  def testInvalidInputs(self):
    with self.assertRaisesRegex(InvalidInput, "Selection must be"):
      self.handle(0, {"type": "walls", "selection": "engineer", "location": [8, 4]})
    with self.assertRaisesRegex(InvalidInput, "Invalid selection"):
      self.handle(0, {"type": "walls", "selection": ["engineer", "engineer"], "location": [8, 4]})
    with self.assertRaisesRegex(InvalidInput, "Invalid selection"):
      self.handle(0, {"type": "walls", "selection": ["alchemist"], "location": [8, 4]})


class MedicineTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.player_data[0].cards["medicine"] = 2

  def testCannotPlayAsDevCard(self):
    with self.assertRaisesRegex(InvalidMove, "play that card while building"):
      self.handle(0, {"type": "play_dev", "card_type": "medicine", "selection": [8, 4]})

  def testBuildCity(self):
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.handle(0, {"type": "city", "selection": ["medicine"], "location": [8, 4]})
    self.assertEqual(self.c.pieces[(8, 4)].piece_type, "city")
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"medicine": 1, "rsrc5": 2, "rsrc3": 1})

  def testCannotUseTwoAtOnce(self):
    with self.assertRaisesRegex(InvalidInput, "Invalid selection"):
      self.handle(0, {"type": "city", "selection": ["medicine", "medicine"], "location": [8, 4]})

  def testCannotPlayWithoutCard(self):
    self.c.player_data[0].cards["medicine"] = 0
    with self.assertRaisesRegex(InvalidMove, "would need an extra 1 {medicine}"):
      self.handle(0, {"type": "city", "selection": ["medicine"], "location": [8, 4]})

  def testInvalidInputs(self):
    with self.assertRaisesRegex(InvalidInput, "Selection must be"):
      self.handle(0, {"type": "city", "selection": "medicine", "location": [8, 4]})
    with self.assertRaisesRegex(InvalidInput, "Invalid selection"):
      self.handle(0, {"type": "city", "selection": ["engineer"], "location": [8, 4]})


class InventorTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.player_data[0].cards["inventor"] = 1
    self.data = {"type": "play_dev", "card_type": "inventor"}

  def testSwitchTwo(self):
    self.handle(0, {"location": [7, 3], "selection": [7, 5], **self.data})
    self.assertEqual(self.c.tiles[(7, 3)].number, 5)
    self.assertEqual(self.c.tiles[(7, 5)].number, 9)
    self.assertEqual(self.c.player_data[0].cards["inventor"], 0)

  def testInvalidInput(self):
    with self.assertRaisesRegex(InvalidMove, "tuple of size 2"):
      self.handle(0, {"selection": [7, 5], **self.data})
    with self.assertRaisesRegex(InvalidMove, "tuple of size 2"):
      self.handle(0, {"location": [7, 5], **self.data})

  def testInvalidTiles(self):
    with self.assertRaisesRegex(InvalidMove, "cannot choose 2, 6"):
      self.handle(0, {"location": [4, 4], "selection": [7, 5], **self.data})
    with self.assertRaisesRegex(InvalidMove, "must choose numbered land"):
      self.handle(0, {"location": [4, 2], "selection": [7, 5], **self.data})
    self.c.tiles[(4, 6)].number = None
    with self.assertRaisesRegex(InvalidMove, "must choose numbered land"):
      self.handle(0, {"location": [4, 6], "selection": [7, 5], **self.data})
    with self.assertRaisesRegex(InvalidMove, "distinct tiles"):
      self.handle(0, {"selection": [7, 5], "location": [7, 5], **self.data})


class GainTwoTestMixin:
  def setUp(self):
    super().setUp()
    self.c.player_data[0].cards[self.CARD] = 2
    self.c.tiles[(7, 3)].tile_type = self.RESOURCE
    self.c.tiles[(4, 4)].tile_type = "norsrc"
    self.c.options["knights"].force(True)

  def testPlayAndGain(self):
    for piece_type in ["settlement", "city"]:
      with self.subTest(piece_type=piece_type):
        self.c.pieces[(8, 4)].piece_type = piece_type
        old_rsrcs = collections.Counter(self.c.player_data[0].cards)
        self.handle(0, {"type": "play_dev", "card_type": self.CARD})

        new_rsrcs = collections.Counter(self.c.player_data[0].cards)
        self.assertDictEqual(new_rsrcs - old_rsrcs, {self.RESOURCE: 2})
        self.assertDictEqual(old_rsrcs - new_rsrcs, {self.CARD: 1})

  def testGainIsPerTileNotPerPiece(self):
    self.c.add_piece(Piece(5, 3, "settlement", 0))
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.handle(0, {"type": "play_dev", "card_type": self.CARD})

    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {self.RESOURCE: 2})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {self.CARD: 1})

  def testOnePieceCanGainFromMultipleTiles(self):
    self.c.tiles[(7, 5)].tile_type = self.RESOURCE
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.handle(0, {"type": "play_dev", "card_type": self.CARD})

    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {self.RESOURCE: 4})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {self.CARD: 1})

  def testDepleteBank(self):
    self.c.player_data[0].cards[self.RESOURCE] = 0
    self.c.player_data[1].cards[self.RESOURCE] = 18
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.handle(0, {"type": "play_dev", "card_type": self.CARD})

    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {self.RESOURCE: 1})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {self.CARD: 1})

  def testCannotPlayWithoutEffect(self):
    self.c.tiles[(7, 3)].tile_type = "norsrc"
    with self.assertRaisesRegex(InvalidMove, "have no settlements/cities next to"):
      self.handle(0, {"type": "play_dev", "card_type": self.CARD})


class IrrigationTest(GainTwoTestMixin, BaseInputHandlerTest):
  CARD = "irrigation"
  RESOURCE = "rsrc3"


class MiningTest(GainTwoTestMixin, BaseInputHandlerTest):
  CARD = "mining"
  RESOURCE = "rsrc5"


class SmithTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.player_data[0].cards["smith"] = 2
    self.add_knight((6, 4), 0)

  def add_knight(self, loc, player, strength=1):
    location = CornerLocation(*loc)
    self.c.knights[location] = Knight(location, player, location, strength=strength)

  def testOnlyOneKnight(self):
    self.assertEqual(self.c.knights[(6, 4)].strength, 1)
    self.handle(0, {"type": "play_dev", "card_type": "smith", "location": [6, 4]})
    self.assertEqual(self.c.knights[(6, 4)].strength, 2)
    self.assertEqual(self.c.player_data[0].cards["smith"], 1)

  def testTwoKnights(self):
    self.add_knight((3, 3), 0)
    data = {"type": "play_dev", "card_type": "smith"}
    with self.assertRaisesRegex(InvalidMove, "same knight twice"):
      self.handle(0, {"location": [6, 4], "selection": [6, 4], **data})

    self.handle(0, {"location": [6, 4], "selection": [3, 3], **data})
    self.assertEqual(self.c.knights[(6, 4)].strength, 2)
    self.assertEqual(self.c.knights[(3, 3)].strength, 2)
    self.assertEqual(self.c.player_data[0].cards["smith"], 1)

  def testInvalidSelections(self):
    self.add_knight((3, 3), 1)
    self.c.knights[(6, 4)].strength = 3
    with self.assertRaisesRegex(InvalidMove, "tuple of size 2"):
      self.handle(0, {"type": "play_dev", "card_type": "smith"})
    with self.assertRaisesRegex(InvalidMove, "do not have a knight there"):
      self.handle(0, {"type": "play_dev", "card_type": "smith", "location": [2, 4]})
    with self.assertRaisesRegex(InvalidMove, "your own knights"):
      self.handle(0, {"type": "play_dev", "card_type": "smith", "location": [3, 3]})
    with self.assertRaisesRegex(InvalidMove, "promote knights beyond"):
      self.handle(0, {"type": "play_dev", "card_type": "smith", "location": [6, 4]})

  def testCannotDoublePromote(self):
    self.handle(0, {"type": "play_dev", "card_type": "smith", "location": [6, 4]})
    with self.assertRaisesRegex(InvalidMove, "once per turn"):
      self.handle(0, {"type": "play_dev", "card_type": "smith", "location": [6, 4]})

  def testNoKnightsAvailableAtThatStrength(self):
    self.add_knight((3, 3), 0, 2)
    self.add_knight((5, 3), 0, 2)
    with self.assertRaisesRegex(InvalidMove, "insufficient.*knights remaining"):
      self.handle(0, {"type": "play_dev", "card_type": "smith", "location": [6, 4]})

  def testRemainingKnightsAvailableAtThatStrength(self):
    self.add_knight((3, 3), 0, 1)
    self.add_knight((5, 3), 0, 2)
    data = {"type": "play_dev", "card_type": "smith"}
    # Cannot promote two knights to strength 2 because one is already in use.
    with self.assertRaisesRegex(InvalidMove, "insufficient.*knights remaining"):
      self.handle(0, {"location": [6, 4], "selection": [3, 3], **data})

  def testCanChainPromote(self):
    self.add_knight((3, 3), 0, 2)
    self.add_knight((5, 3), 0, 2)
    data = {"type": "play_dev", "card_type": "smith"}
    self.handle(0, {"location": [6, 4], "selection": [3, 3], **data})
    self.assertEqual(self.c.knights[(6, 4)].strength, 2)
    self.assertEqual(self.c.knights[(3, 3)].strength, 3)
    self.assertEqual(self.c.player_data[0].cards["smith"], 1)


class BishopTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["pirate"].force(True)
    self.c.options["knights"].force(True)
    self.c.add_player("limegreen", "Bob")
    self.c.player_data[2].cards["bishop"] = 1
    self.c.turn_idx = 2

  def testPlayBishop(self):
    self.handle(2, {"type": "play_dev", "card_type": "bishop"})
    self.assertEqual(self.c.action_stack, ["roball", "robber"])
    p0_count = sum(self.c.player_data[0].cards.values())
    p1_count = sum(self.c.player_data[1].cards.values())
    self.handle(2, {"location": [7, 5], "type": "robber"})
    self.assertEqual(sum(self.c.player_data[0].cards.values()), p0_count - 1)
    self.assertEqual(sum(self.c.player_data[1].cards.values()), p1_count - 1)
    self.assertEqual(sum(self.c.player_data[2].cards.values()), 2)
    self.assertEqual(self.c.turn_phase, "main")

  def testPlayBishopOnePlayer(self):
    self.handle(2, {"type": "play_dev", "card_type": "bishop"})
    p0_count = sum(self.c.player_data[0].cards.values())
    p1_count = sum(self.c.player_data[1].cards.values())
    self.handle(2, {"location": [7, 3], "type": "robber"})
    self.assertEqual(sum(self.c.player_data[0].cards.values()), p0_count - 1)
    self.assertEqual(sum(self.c.player_data[1].cards.values()), p1_count)
    self.assertEqual(sum(self.c.player_data[2].cards.values()), 1)
    self.assertEqual(self.c.turn_phase, "main")

  def testBishopCannotMovePirate(self):
    self.handle(2, {"type": "play_dev", "card_type": "bishop"})
    with self.assertRaisesRegex(InvalidMove, "cannot move the pirate"):
      self.handle(2, {"location": [10, 4], "type": "pirate"})


class DiplomatTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.options["seafarers"].force(True)
    self.c.player_data[0].cards["diplomat"] = 1
    self.play_diplomat = {"type": "play_dev", "card_type": "diplomat"}

  def testRemoveOpponentRoad(self):
    self.handle(0, {"type": "play_dev", "card_type": "diplomat", "location": [5, 5, 6, 6]})
    self.assertNotIn((5, 5, 6, 6), self.c.roads)

  def testRemoveOwnRoad(self):
    self.handle(0, {"type": "play_dev", "card_type": "diplomat", "location": [6, 4, 8, 4]})
    self.assertIn((5, 5, 6, 6), self.c.roads)
    self.assertNotIn((6, 4, 8, 4), self.c.roads)

  def testMoveOwnRoad(self):
    self.handle(0, {"location": [6, 4, 8, 4], "selection": [8, 4, 9, 5], **self.play_diplomat})
    self.assertNotIn((6, 4, 8, 4), self.c.roads)
    self.assertIn((8, 4, 9, 5), self.c.roads)
    self.assertEqual(self.c.roads[(8, 4, 9, 5)].player, 0)

  def testMovingRoadClaimsTreasure(self):
    self.c.treasures[CornerLocation(9, 5)] = "collect1"
    self.handle(0, {"location": [6, 4, 8, 4], "selection": [8, 4, 9, 5], **self.play_diplomat})
    self.assertNotIn((6, 4, 8, 4), self.c.roads)
    self.assertIn((8, 4, 9, 5), self.c.roads)
    self.assertEqual(self.c.roads[(8, 4, 9, 5)].player, 0)
    self.assertEqual(self.c.turn_phase, "collect1")

  def testMovingRoadDiscovers(self):
    self.c.tiles[(10, 6)].tile_type = "discover"
    self.c.discoverable_tiles = ["rsrc5"]
    self.c.discoverable_numbers = [5]
    self.handle(0, {"location": [6, 4, 8, 4], "selection": [8, 4, 9, 5], **self.play_diplomat})
    self.assertNotIn((6, 4, 8, 4), self.c.roads)
    self.assertIn((8, 4, 9, 5), self.c.roads)
    self.assertEqual(self.c.roads[(8, 4, 9, 5)].player, 0)
    self.assertEqual(self.c.tiles[(10, 6)].tile_type, "rsrc5")
    self.assertEqual(self.c.tiles[(10, 6)].number, 5)

  def testMovingRoadDoesntConcedeLongestRoute(self):
    self.c.add_road(Road([5, 3, 6, 4], "road", 0))
    self.c.add_road(Road([3, 3, 5, 3], "road", 0))
    self.c.add_road(Road([2, 4, 3, 3], "road", 0))
    self.c.add_road(Road([2, 4, 3, 5], "road", 0))

    self.c.add_road(Road([5, 7, 6, 6], "road", 1))
    self.c.add_road(Road([3, 7, 5, 7], "road", 1))
    self.c.add_road(Road([2, 6, 3, 7], "road", 1))
    self.c.add_road(Road([2, 6, 3, 5], "road", 1))

    self.assertEqual(self.c.longest_route_player, 0)
    self.assertEqual(self.c.player_data[0].longest_route, 5)
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.handle(0, {"location": [2, 4, 3, 5], "selection": [8, 4, 9, 5], **self.play_diplomat})
    self.assertEqual(self.c.longest_route_player, 0)
    self.assertEqual(self.c.player_data[0].longest_route, 5)
    self.assertEqual(self.c.player_data[1].longest_route, 5)

  def testMoveOwnShip(self):
    self.c.add_road(Road([8, 4, 9, 5], "ship", 0))
    self.handle(0, {"location": [8, 4, 9, 5], "selection": [8, 4, 9, 3], **self.play_diplomat})
    self.assertNotIn((8, 4, 9, 5), self.c.roads)
    self.assertIn((8, 4, 9, 3), self.c.roads)
    self.assertEqual(self.c.roads[(8, 4, 9, 3)].player, 0)
    self.assertEqual(self.c.roads[(8, 4, 9, 3)].road_type, "ship")

  def testInvalidRoadMoves(self):
    with self.assertRaisesRegex(InvalidMove, "cannot move another player"):
      self.handle(0, {"location": [5, 5, 6, 6], "selection": [8, 4, 9, 5], **self.play_diplomat})
    with self.assertRaisesRegex(InvalidMove, "on top of an existing"):
      self.handle(0, {"location": [6, 4, 8, 4], "selection": [6, 4, 8, 4], **self.play_diplomat})
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.handle(0, {"location": [6, 4, 8, 4], "selection": [5, 5, 6, 4], **self.play_diplomat})
    with self.assertRaisesRegex(InvalidMove, "must choose a valid"):
      self.handle(0, {"type": "play_dev", "card_type": "diplomat", "location": [8, 4, 9, 5]})

  def testCanOnlyMoveOpenRoads(self):
    self.c.add_road(Road([5, 3, 6, 4], "road", 0))
    with self.assertRaisesRegex(InvalidMove, "from the end of a route"):
      self.handle(0, {"type": "play_dev", "card_type": "diplomat", "location": [6, 4, 8, 4]})

    self.c.add_piece(Piece(5, 3, "settlement", 0))
    with self.assertRaisesRegex(InvalidMove, "road that connects"):
      self.handle(0, {"type": "play_dev", "card_type": "diplomat", "location": [5, 3, 6, 4]})

  def testRoadCannotBecomeShip(self):
    self.c.add_road(Road([8, 4, 9, 5], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "must be connected"):
      self.handle(0, {"location": [6, 4, 8, 4], "selection": [8, 6, 9, 5], **self.play_diplomat})


class DefectorTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.player_data[0].cards["defector"] = 1
    self.c.add_player("limegreen", "Bob")
    self.add_knight((6, 6), 1)

  def add_knight(self, loc, player, strength=1):
    location = CornerLocation(*loc)
    self.c.knights[location] = Knight(location, player, location, strength=strength)

  def testPlayDefector(self):
    self.handle(0, {"type": "play_dev", "card_type": "defector", "selection": 1})
    self.assertEqual(self.c.action_stack, ["adopt", "defect"])
    self.assertEqual(self.c.affected_player, 1)
    self.assertEqual(self.c.player_data[0].cards["defector"], 0)

  def testInvalidSelections(self):
    with self.assertRaisesRegex(InvalidInput, "Invalid player"):
      self.handle(0, {"type": "play_dev", "card_type": "defector", "selection": -1})
    with self.assertRaisesRegex(InvalidMove, "at least one knight"):
      self.handle(0, {"type": "play_dev", "card_type": "defector", "selection": 2})
    with self.assertRaisesRegex(InvalidMove, "cannot choose yourself"):
      self.handle(0, {"type": "play_dev", "card_type": "defector", "selection": 0})


class DefectTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.add_knight((6, 6), 1)
    self.c.affected_player = 1
    self.c.action_stack.extend(["adopt", "defect"])

  def add_knight(self, loc, player, strength=1):
    location = CornerLocation(*loc)
    self.c.knights[location] = Knight(location, player, location, strength=strength)

  def testDefect(self):
    self.handle(1, {"type": "defect", "location": [6, 6]})
    self.assertEqual(self.c.turn_phase, "adopt")
    self.assertNotIn((6, 6), self.c.knights)
    self.assertEqual(self.c.displaced_knight.player, 1)
    self.assertEqual(self.c.displaced_knight.strength, 1)
    self.assertIsNone(self.c.affected_player)

  def testDefectingKnightRecalculatesLongestRoad(self):
    self.c.knights[(6, 6)].player = 0
    self.c.affected_player = 0

    self.c.add_player("green", "Player3")
    self.c.add_piece(Piece(5, 3, "settlement", 2))
    self.c.add_road(Road([5, 3, 6, 4], "road", 2))
    self.c.add_road(Road([5, 5, 6, 4], "road", 2))
    self.c.add_road(Road([5, 3, 6, 2], "road", 2))
    self.c.add_road(Road([6, 2, 8, 2], "road", 2))
    self.c.add_road(Road([8, 2, 9, 3], "road", 2))
    self.c.add_road(Road([5, 7, 6, 6], "road", 1))
    self.c.add_road(Road([3, 7, 5, 7], "road", 1))
    self.c.add_road(Road([2, 6, 3, 7], "road", 1))
    self.c.add_road(Road([2, 6, 3, 5], "road", 1))
    self.c.add_road(Road([2, 4, 3, 5], "road", 1))
    self.c.add_road(Road([8, 4, 9, 5], "road", 0))
    self.c.add_road(Road([8, 6, 9, 5], "road", 0))
    self.c.add_road(Road([6, 6, 8, 6], "road", 0))

    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.assertEqual(self.c.player_data[2].longest_route, 5)
    # Player 2 got longest route first, so they still have it despite the tie.
    self.assertEqual(self.c.longest_route_player, 2)

    self.handle(0, {"type": "defect", "location": [6, 6]})
    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertEqual(self.c.player_data[1].longest_route, 6)
    self.assertEqual(self.c.player_data[2].longest_route, 5)
    self.assertEqual(self.c.longest_route_player, 1)

  def testInvalidDefections(self):
    self.add_knight((6, 4), 0)
    with self.assertRaisesRegex(InvalidMove, "tuple of size 2"):
      self.handle(1, {"type": "defect", "location": 0})
    with self.assertRaisesRegex(InvalidMove, "do not have a knight there"):
      self.handle(1, {"type": "defect", "location": [5, 5]})
    with self.assertRaisesRegex(InvalidMove, "one of your own knights"):
      self.handle(1, {"type": "defect", "location": [6, 4]})
    with self.assertRaisesRegex(NotYourTurn, "Waiting"):
      self.handle(0, {"type": "defect", "location": [6, 6]})


class AdoptTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.add_knight((6, 6), 1)
    self.c.affected_player = 1
    self.c.action_stack.extend(["adopt", "defect"])

  def add_knight(self, loc, player, strength=1):
    location = CornerLocation(*loc)
    self.c.knights[location] = Knight(location, player, location, strength=strength)

  def testAdopt(self):
    self.handle(1, {"type": "defect", "location": [6, 6]})
    self.handle(0, {"type": "adopt", "location": [6, 4]})
    self.assertEqual(self.c.turn_phase, "main")
    self.assertIn((6, 4), self.c.knights)
    self.assertEqual(self.c.knights[(6, 4)].player, 0)
    self.assertEqual(self.c.knights[(6, 4)].strength, 1)
    self.assertIsNone(self.c.displaced_knight)

  def testInvalidAdoptions(self):
    self.handle(1, {"type": "defect", "location": [6, 6]})
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.handle(0, {"type": "adopt", "location": [6, 6]})
    with self.assertRaisesRegex(InvalidMove, "choose an empty corner"):
      self.handle(0, {"type": "adopt", "location": [8, 4]})
    with self.assertRaisesRegex(InvalidMove, "tuple of size 2"):
      self.handle(0, {"type": "adopt"})
    with self.assertRaisesRegex(NotYourTurn, "not your turn"):
      self.handle(1, {"type": "adopt", "location": [6, 6]})

  def testAdoptedKnightCanBeUsedImmediately(self):
    self.c.robber = TileLocation(7, 3)
    self.c.knights[(6, 6)].active = True
    self.handle(1, {"type": "defect", "location": [6, 6]})
    self.handle(0, {"type": "adopt", "location": [6, 4]})
    self.assertEqual(self.c.turn_phase, "main")
    self.assertIn((6, 4), self.c.knights)
    self.assertTrue(self.c.knights[(6, 4)].active)
    self.c.handle_chase([7, 3], [6, 4], 0)

  def testAdoptStrongerKnight(self):
    self.c.knights[(6, 6)].strength = 2
    self.handle(1, {"type": "defect", "location": [6, 6]})
    self.handle(0, {"type": "adopt", "location": [6, 4]})
    self.assertEqual(self.c.knights[(6, 4)].strength, 2)
    self.assertEqual(self.c.turn_phase, "main")
    self.assertIsNone(self.c.displaced_knight)

  def testAdoptWithoutAvailableKnights(self):
    self.add_knight((5, 3), 0, strength=3)
    self.add_knight((3, 3), 0, strength=3)
    self.c.knights[(6, 6)].strength = 3
    self.handle(1, {"type": "defect", "location": [6, 6]})
    self.handle(0, {"type": "adopt", "location": [6, 4]})
    self.assertEqual(self.c.knights[(6, 4)].strength, 1)
    self.assertEqual(self.c.turn_phase, "main")
    self.assertIsNone(self.c.displaced_knight)

  def testAdoptWithoutAnyAvailableKnights(self):
    self.add_knight((5, 3), 0, strength=1)
    self.add_knight((3, 3), 0, strength=1)
    self.handle(1, {"type": "defect", "location": [6, 6]})
    self.assertEqual(self.c.turn_phase, "main")
    self.assertEqual(len([k for k in self.c.knights.values() if k.player == 0]), 2)
    self.assertIsNone(self.c.displaced_knight)

  def testAdoptWithoutAnyAvailableCorners(self):
    self.add_knight((6, 4), 0, strength=1)
    self.handle(1, {"type": "defect", "location": [6, 6]})
    self.assertEqual(self.c.turn_phase, "main")
    self.assertEqual(len([k for k in self.c.knights.values() if k.player == 0]), 1)
    self.assertIsNone(self.c.displaced_knight)

  def testAdoptedKnightRecalculatesLongestRoad(self):
    self.c.add_player("green", "Player3")
    self.c.add_piece(Piece(5, 3, "settlement", 2))
    self.c.add_road(Road([5, 3, 6, 4], "road", 2))
    self.c.add_road(Road([5, 5, 6, 4], "road", 2))
    self.c.add_road(Road([5, 3, 6, 2], "road", 2))
    self.c.add_road(Road([6, 2, 8, 2], "road", 2))
    self.c.add_road(Road([8, 2, 9, 3], "road", 2))
    self.c.add_road(Road([5, 7, 6, 6], "road", 1))
    self.c.add_road(Road([3, 7, 5, 7], "road", 1))
    self.c.add_road(Road([2, 6, 3, 7], "road", 1))
    self.c.add_road(Road([2, 6, 3, 5], "road", 1))
    self.c.add_road(Road([8, 4, 9, 5], "road", 0))
    self.c.add_road(Road([8, 6, 9, 5], "road", 0))
    self.c.add_road(Road([6, 6, 8, 6], "road", 0))

    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.assertEqual(self.c.player_data[2].longest_route, 5)
    self.assertEqual(self.c.longest_route_player, 2)

    self.handle(1, {"type": "defect", "location": [6, 6]})
    self.assertEqual(self.c.longest_route_player, 2)

    self.handle(0, {"type": "adopt", "location": [6, 4]})
    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.assertEqual(self.c.player_data[2].longest_route, 4)
    self.assertEqual(self.c.longest_route_player, 1)


class DeceptionTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.player_data[0].cards["deception"] = 1
    self.c.add_road(Road([5, 5, 6, 4], "road", 1))
    self.add_knight((6, 4), 1, strength=3)

  def add_knight(self, loc, player, strength=1):
    location = CornerLocation(*loc)
    self.c.knights[location] = Knight(location, player, location, strength=strength)

  def testForceDisplace(self):
    self.handle(0, {"type": "play_dev", "card_type": "deception", "location": [6, 4]})
    self.assertEqual(self.c.turn_phase, "displace")
    self.assertEqual(self.c.displaced_knight.player, 1)
    self.assertEqual(self.c.player_data[0].cards["deception"], 0)
    self.assertNotIn((6, 4), self.c.knights)

  def testNoPlaceForDisplacedKnight(self):
    self.add_knight((6, 6), 1)
    self.handle(0, {"type": "play_dev", "card_type": "deception", "location": [6, 4]})
    self.assertEqual(self.c.turn_phase, "main")
    self.assertIsNone(self.c.displaced_knight)
    self.assertNotIn((6, 4), self.c.knights)

  def testDisplacedKnightUpdatesLongestRoad(self):
    self.c.add_road(Road([5, 3, 6, 4], "road", 0))
    self.c.add_road(Road([5, 3, 6, 2], "road", 0))
    self.c.add_road(Road([6, 2, 8, 2], "road", 0))
    self.c.add_road(Road([8, 2, 9, 3], "road", 0))
    self.assertEqual(self.c.player_data[0].longest_route, 4)

    self.handle(0, {"type": "play_dev", "card_type": "deception", "location": [6, 4]})
    self.assertEqual(self.c.player_data[0].longest_route, 5)
    self.assertEqual(self.c.longest_route_player, 0)

  def testInvalidDisplacements(self):
    self.add_knight((6, 6), 1)
    self.c.add_road(Road([8, 4, 9, 3], "road", 0))
    self.add_knight((9, 3), 0)
    with self.assertRaisesRegex(InvalidMove, "tuple of size 2"):
      self.handle(0, {"type": "play_dev", "card_type": "deception"})
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads or ships"):
      self.handle(0, {"type": "play_dev", "card_type": "deception", "location": [6, 6]})
    with self.assertRaisesRegex(InvalidMove, "cannot choose your own knight"):
      self.handle(0, {"type": "play_dev", "card_type": "deception", "location": [9, 3]})

    self.c.roads[(5, 5, 6, 4)].player = 0
    with self.assertRaisesRegex(InvalidMove, "must choose a knight"):
      self.handle(0, {"type": "play_dev", "card_type": "deception", "location": [5, 5]})


class SaboteurTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.add_player("limegreen", "Bob")
    self.c.player_data[2].cards["saboteur"] = 1
    self.c.add_piece(Piece(2, 4, "settlement", 2))
    self.c.turn_idx = 2

  def testPlayersDiscard(self):
    self.handle(2, {"type": "play_dev", "card_type": "saboteur"})
    self.assertEqual(self.c.turn_phase, "discard")
    self.assertDictEqual(self.c.discard_players, {0: 5, 1: 7})

  def testDiscardWithLessThanSeven(self):
    self.c.player_data[0].cards.clear()
    self.c.player_data[0].cards["rsrc3"] = 4
    self.handle(2, {"type": "play_dev", "card_type": "saboteur"})
    self.assertEqual(self.c.turn_phase, "discard")
    self.assertDictEqual(self.c.discard_players, {0: 2, 1: 7})

  def testSelfNotAffected(self):
    self.c.player_data[2].cards["rsrc3"] = 8
    self.handle(2, {"type": "play_dev", "card_type": "saboteur"})
    self.assertEqual(self.c.turn_phase, "discard")
    self.assertNotIn(2, self.c.discard_players)

  def testPlayersWithFewerPointsUnaffected(self):
    self.c.pieces[(2, 4)].piece_type = "city"
    self.c.pieces[(8, 4)].piece_type = "city"
    self.handle(2, {"type": "play_dev", "card_type": "saboteur"})
    self.assertEqual(self.c.turn_phase, "discard")
    self.assertNotIn(1, self.c.discard_players)
    self.assertIn(0, self.c.discard_players)

  def testNoAffectedPlayers(self):
    self.c.player_data[2].cards["rsrc3"] = 8
    self.c.pieces[(2, 4)].piece_type = "city"
    with self.assertRaisesRegex(InvalidMove, "no players"):
      self.handle(2, {"type": "play_dev", "card_type": "saboteur"})


class SpyTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.add_player("limegreen", "Bob")
    self.c.player_data[0].cards.update({"warlord": 1, "irrigation": 1})
    self.c.player_data[1].cards.update({"mining": 2, "constitution": 1})
    self.c.player_data[2].cards.update({"spy": 1})
    self.c.turn_idx = 2

  def testStealACard(self):
    self.handle(2, {"type": "play_dev", "card_type": "spy", "selection": 1})
    self.assertEqual(self.c.turn_phase, "spy")
    self.assertEqual(self.c.affected_player, 1)

    self.handle(2, {"type": "steal", "selection": {"mining": 1}})
    self.assertEqual(self.c.player_data[1].cards["mining"], 1)
    self.assertEqual(self.c.player_data[2].cards["mining"], 1)
    self.assertEqual(self.c.player_data[2].cards["spy"], 0)
    self.assertEqual(self.c.turn_phase, "main")

  def testStealingWorksAfterChangingYourMind(self):
    """Handle the player selecting one card, deselecting it, and then selecting another."""
    self.handle(2, {"type": "play_dev", "card_type": "spy", "selection": 1})

    self.handle(2, {"type": "steal", "selection": {"mining": 1, "constitution": 0}})
    self.assertEqual(self.c.player_data[1].cards["mining"], 1)
    self.assertEqual(self.c.player_data[1].cards["constitution"], 1)
    self.assertEqual(self.c.player_data[2].cards["mining"], 1)
    self.assertEqual(self.c.player_data[2].cards["constitution"], 0)
    self.assertEqual(self.c.player_data[2].cards["spy"], 0)
    self.assertEqual(self.c.turn_phase, "main")

  def testInvalidPlayerSelection(self):
    self.c.player_data[1].cards["mining"] = 0
    with self.assertRaisesRegex(InvalidMove, "steal from a player with progress cards"):
      self.handle(2, {"type": "play_dev", "card_type": "spy", "selection": 1})
    with self.assertRaisesRegex(InvalidMove, "cannot choose yourself"):
      self.handle(2, {"type": "play_dev", "card_type": "spy", "selection": 2})
    with self.assertRaisesRegex(InvalidInput, "Invalid player"):
      self.handle(2, {"type": "play_dev", "card_type": "spy"})

  def testInvalidCardSteal(self):
    self.handle(2, {"type": "play_dev", "card_type": "spy", "selection": 1})
    self.assertEqual(self.c.turn_phase, "spy")
    self.assertEqual(self.c.affected_player, 1)

    with self.assertRaisesRegex(InvalidMove, "that player does not have"):
      self.handle(2, {"type": "steal", "selection": {"warlord": 1}})
    with self.assertRaisesRegex(InvalidMove, "Invalid card selection"):
      self.handle(2, {"type": "steal", "selection": {"rsrc3": 1}})
    with self.assertRaisesRegex(InvalidMove, "Invalid card selection"):
      self.handle(2, {"type": "steal", "selection": {"printer": 1}})
    with self.assertRaisesRegex(InvalidMove, "select exactly 1"):
      self.handle(2, {"type": "steal", "selection": {"mining": 2}})


class WarlordTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.player_data[0].cards["warlord"] = 1
    self.add_knight((6, 4), 0)
    self.add_knight((5, 3), 0)

  def add_knight(self, loc, player, strength=1):
    location = CornerLocation(*loc)
    self.c.knights[location] = Knight(location, player, location, strength=strength)

  def testActivateAll(self):
    self.assertFalse(self.c.knights[(6, 4)].active)
    self.assertFalse(self.c.knights[(5, 3)].active)
    self.handle(0, {"type": "play_dev", "card_type": "warlord"})
    self.assertTrue(self.c.knights[(6, 4)].active)
    self.assertTrue(self.c.knights[(5, 3)].active)
    self.assertIn((6, 4), self.c.activated_this_turn)
    self.assertIn((5, 3), self.c.activated_this_turn)
    self.assertEqual(self.c.player_data[0].cards["warlord"], 0)

  def testActivateOnlyOwn(self):
    self.c.knights[(5, 3)].player = 1
    self.handle(0, {"type": "play_dev", "card_type": "warlord"})
    self.assertTrue(self.c.knights[(6, 4)].active)
    self.assertFalse(self.c.knights[(5, 3)].active)

  def testDontReactivate(self):
    self.c.knights[(5, 3)].active = True
    self.handle(0, {"type": "play_dev", "card_type": "warlord"})
    self.assertTrue(self.c.knights[(6, 4)].active)
    self.assertTrue(self.c.knights[(5, 3)].active)
    self.assertIn((6, 4), self.c.activated_this_turn)
    self.assertNotIn((5, 3), self.c.activated_this_turn)

  def testNoKnights(self):
    self.c.knights.clear()
    with self.assertRaisesRegex(InvalidMove, "have no knights"):
      self.handle(0, {"type": "play_dev", "card_type": "warlord"})


class WeddingTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.add_player("limegreen", "Bob")
    self.c.player_data[2].cards["wedding"] = 1
    self.c.player_data[2].cards["roadbuilding"] = 1
    self.c.turn_idx = 2

  def testGetTwoFromEachOpponent(self):
    self.handle(2, {"type": "play_dev", "card_type": "wedding"})
    self.assertEqual(self.c.turn_phase, "donate")
    self.assertDictEqual(self.c.discard_players, {0: 2, 1: 2})
    with self.assertRaisesRegex(InvalidMove, "cannot play.*right now"):
      self.handle(2, {"type": "play_dev", "card_type": "roadbuilding"})

    self.handle(0, {"type": "discard", "selection": {"rsrc1": 2}})
    self.assertDictEqual(self.c.discard_players, {1: 2})

    with self.assertRaisesRegex(InvalidMove, "Invalid resource selection"):
      self.handle(1, {"type": "discard"})
    with self.assertRaisesRegex(InvalidMove, "Invalid resource selection"):
      self.handle(1, {"type": "discard", "selection": {"gold": 2}})
    with self.assertRaisesRegex(InvalidMove, "must donate 2"):
      self.handle(1, {"type": "discard", "selection": {"rsrc1": 1}})
    with self.assertRaisesRegex(InvalidMove, "need an extra 1"):
      self.handle(1, {"type": "discard", "selection": {"rsrc4": 2}})

    self.handle(1, {"type": "discard", "selection": {"rsrc2": 2}})
    self.assertEqual(self.c.turn_phase, "main")
    self.assertDictEqual(self.c.discard_players, {})
    self.assertEqual(self.c.player_data[2].cards["rsrc1"], 2)
    self.assertEqual(self.c.player_data[2].cards["rsrc2"], 2)
    self.assertEqual(self.c.player_data[2].cards["wedding"], 0)

  def testOpponentWithoutCards(self):
    self.c.player_data[0].cards.clear()
    self.c.player_data[0].cards["gold"] = 3  # Gold cannot be donated
    self.c.player_data[0].cards["roadbuilding"] = 1  # Progress cards cannot be donated
    self.c.player_data[1].cards.clear()
    self.c.player_data[1].cards["rsrc3"] = 1

    self.handle(2, {"type": "play_dev", "card_type": "wedding"})
    self.assertEqual(self.c.turn_phase, "donate")
    self.assertDictEqual(self.c.discard_players, {1: 1})
    self.handle(1, {"type": "discard", "selection": {"rsrc3": 1}})
    self.assertEqual(self.c.turn_phase, "main")
    self.assertEqual(self.c.player_data[2].cards["rsrc3"], 1)
    self.assertEqual(self.c.player_data[2].cards["wedding"], 0)

  def testOpponentHasFewerVictoryPoints(self):
    self.c.add_piece(Piece(2, 4, "settlement", 2))
    self.c.pieces[(8, 4)].piece_type = "city"

    self.handle(2, {"type": "play_dev", "card_type": "wedding"})
    self.assertEqual(self.c.turn_phase, "donate")
    # Player 1 has the same number of points and therefore does not have to donate.
    self.assertDictEqual(self.c.discard_players, {0: 2})

  def testNoEligibleOpponents(self):
    self.c.add_piece(Piece(2, 4, "settlement", 2))
    self.c.pieces[(8, 4)].piece_type = "city"
    self.c.player_data[0].cards.clear()

    with self.assertRaisesRegex(InvalidMove, "no eligible players"):
      self.handle(2, {"type": "play_dev", "card_type": "wedding"})
    self.assertEqual(self.c.turn_phase, "main")
    self.assertDictEqual(self.c.discard_players, {})
    self.assertEqual(self.c.player_data[2].cards["wedding"], 1)


class PeddlerTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.add_player("limegreen", "Bob")
    self.c.player_data[0].cards.update({"warlord": 1, "irrigation": 1})
    self.c.player_data[1].cards.update({"mining": 2})
    self.c.player_data[2].cards.update({"peddler": 1})
    self.c.turn_idx = 2

  def testStealACard(self):
    self.handle(2, {"type": "play_dev", "card_type": "peddler", "selection": 1})
    self.assertEqual(self.c.turn_phase, "peddler")
    self.assertEqual(self.c.affected_player, 1)

    old_count = self.c.player_data[1].cards["rsrc1"]
    self.handle(2, {"type": "steal", "selection": {"rsrc1": 2}})
    self.assertEqual(self.c.player_data[1].cards["rsrc1"], old_count - 2)
    self.assertEqual(self.c.player_data[2].cards["rsrc1"], 2)
    self.assertEqual(self.c.player_data[2].cards["spy"], 0)
    self.assertEqual(self.c.turn_phase, "main")

  def testInvalidPlayerSelection(self):
    self.c.add_piece(Piece(5, 3, "settlement", 2))
    self.c.pieces[(5, 5)].piece_type = "city"
    self.c.player_data[1].cards.clear()
    with self.assertRaisesRegex(InvalidMove, "steal from a player with at least one card"):
      self.handle(2, {"type": "play_dev", "card_type": "peddler", "selection": 1})
    with self.assertRaisesRegex(InvalidMove, "who has more victory points"):
      self.handle(2, {"type": "play_dev", "card_type": "peddler", "selection": 0})
    with self.assertRaisesRegex(InvalidMove, "cannot choose yourself"):
      self.handle(2, {"type": "play_dev", "card_type": "peddler", "selection": 2})
    with self.assertRaisesRegex(InvalidInput, "Invalid player"):
      self.handle(2, {"type": "play_dev", "card_type": "peddler"})

  def testInvalidCardSteal(self):
    self.handle(2, {"type": "play_dev", "card_type": "peddler", "selection": 1})
    self.assertEqual(self.c.turn_phase, "peddler")
    self.assertEqual(self.c.affected_player, 1)

    with self.assertRaisesRegex(InvalidMove, "that player does not have"):
      self.handle(2, {"type": "steal", "selection": {"rsrc4": 2}})
    with self.assertRaisesRegex(InvalidMove, "Invalid card selection"):
      self.handle(2, {"type": "steal", "selection": {"mining": 2}})
    with self.assertRaisesRegex(InvalidMove, "select exactly 2"):
      self.handle(2, {"type": "steal", "selection": {"rsrc4": 1}})

  def testOnlyOneCardRemaining(self):
    self.c.player_data[1].cards.clear()
    self.c.player_data[1].cards["mining"] = 2
    self.c.player_data[1].cards["rsrc4"] = 1

    self.handle(2, {"type": "play_dev", "card_type": "peddler", "selection": 1})
    with self.assertRaisesRegex(InvalidMove, "select exactly 1"):
      self.handle(2, {"type": "steal", "selection": {"rsrc4": 2}})
    self.handle(2, {"type": "steal", "selection": {"rsrc4": 1}})
    self.assertEqual(self.c.player_data[1].cards["rsrc4"], 0)
    self.assertEqual(self.c.player_data[2].cards["rsrc4"], 1)
    self.assertEqual(self.c.player_data[2].cards["spy"], 0)


class MerchantTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.player_data[0].cards["merchant"] = 2
    self.c.player_data[1].cards["merchant"] = 1
    self.c.options["knights"].force(True)

  def testTradeRatios(self):
    self.assertEqual(self.c._get_ratios(0)["rsrc1"], 2)
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 3)
    self.handle(0, {"type": "play_dev", "card_type": "merchant", "location": [7, 3]})
    self.assertEqual(self.c._get_ratios(0)["rsrc1"], 2)
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 2)
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc3"], 3)
    self.assertEqual(self.c.player_points(0, True), 2)
    # Make sure the trade ratio is shown in the UI so the player gets the right trades.
    data = self.c.for_player(0)
    self.assertEqual(data["player_data"][0]["trade_ratios"]["rsrc3"], 2)
    # Make sure the updated trade ratio only applies to the player with the merchant
    p1_data = self.c.for_player(1)
    self.assertEqual(p1_data["player_data"][1]["trade_ratios"]["rsrc3"], 4)

  def testUseTwice(self):
    self.assertEqual(self.c._get_ratios(0)["rsrc1"], 2)
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 3)
    self.assertEqual(self.c._get_ratios(0)["rsrc4"], 3)
    self.handle(0, {"type": "play_dev", "card_type": "merchant", "location": [7, 3]})
    self.handle(0, {"type": "play_dev", "card_type": "merchant", "location": [7, 5]})
    self.assertEqual(self.c._get_ratios(0)["rsrc1"], 2)
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 3)
    self.assertEqual(self.c._get_ratios(0)["rsrc4"], 2)
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc3"], 3)
    self.assertEqual(self.c.player_points(0, True), 2)

  def testMustUseNextToOwnPiece(self):
    with self.assertRaisesRegex(InvalidMove, "next to one of your"):
      self.handle(0, {"type": "play_dev", "card_type": "merchant", "location": [4, 4]})

  def testInvalidInputs(self):
    with self.assertRaisesRegex(InvalidMove, "tuple of size 2"):
      self.handle(0, {"type": "play_dev", "card_type": "merchant"})
    with self.assertRaisesRegex(InvalidMove, "land tile"):
      self.handle(0, {"type": "play_dev", "card_type": "merchant", "location": [10, 2]})

  def testStolenByAnotherPlayer(self):
    self.handle(0, {"type": "play_dev", "card_type": "merchant", "location": [7, 3]})
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 2)
    self.c.handle_end_turn()
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 2)
    self.assertEqual(self.c.player_points(0, True), 2)

    self.c.action_stack.clear()
    self.assertEqual(self.c._get_ratios(1)["rsrc1"], 4)
    self.handle(1, {"type": "play_dev", "card_type": "merchant", "location": [4, 6]})
    self.assertEqual(self.c._get_ratios(1)["rsrc1"], 2)
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 3)
    self.assertEqual(self.c.player_points(0, True), 1)
    self.assertEqual(self.c.player_points(1, True), 2)


class ConvoyTest(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.player_data[0].cards["convoy"] = 2
    self.c.options["knights"].force(True)

  def testTradeRatios(self):
    self.assertEqual(self.c._get_ratios(0)["rsrc1"], 2)
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 3)
    self.handle(0, {"type": "play_dev", "card_type": "convoy", "selection": {"rsrc3": 1}})
    self.assertEqual(self.c._get_ratios(0)["rsrc1"], 2)
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 2)
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc3"], 3)  # Not permanently changed
    # Must also make its way to the UI so that the interface gives this option
    data = self.c.for_player(0)
    self.assertEqual(data["player_data"][0]["trade_ratios"]["rsrc3"], 2)
    # Also make sure this applies only to the player who played the convoy.
    p1_data = self.c.for_player(1)
    self.assertEqual(p1_data["player_data"][1]["trade_ratios"]["rsrc3"], 4)

    self.c.handle_end_turn()
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 3)
    data = self.c.for_player(0)
    self.assertEqual(data["player_data"][0]["trade_ratios"]["rsrc3"], 3)

  def testUseTwoOnTheSameTurn(self):
    self.assertEqual(self.c._get_ratios(0)["rsrc1"], 2)
    self.assertEqual(self.c._get_ratios(0)["rsrc2"], 3)
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 3)
    self.handle(0, {"type": "play_dev", "card_type": "convoy", "selection": {"rsrc3": 1}})
    self.handle(0, {"type": "play_dev", "card_type": "convoy", "selection": {"rsrc2": 1}})
    self.assertEqual(self.c._get_ratios(0)["rsrc1"], 2)
    self.assertEqual(self.c._get_ratios(0)["rsrc2"], 2)
    self.assertEqual(self.c._get_ratios(0)["rsrc3"], 2)
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc3"], 3)
    self.assertEqual(self.c.player_data[0].trade_ratios["rsrc2"], 3)

  def testInvalidInputs(self):
    with self.assertRaisesRegex(InvalidMove, "exactly one resource"):
      data = {"type": "play_dev", "card_type": "convoy", "selection": {"rsrc3": 1, "rsrc2": 1}}
      self.handle(0, data)
    with self.assertRaisesRegex(InvalidMove, "exactly one resource"):
      self.handle(0, {"type": "play_dev", "card_type": "convoy", "selection": {}})
    with self.assertRaisesRegex(InvalidMove, "Invalid resource selection"):
      self.handle(0, {"type": "play_dev", "card_type": "convoy"})
    with self.assertRaisesRegex(InvalidMove, "exactly one resource"):
      self.handle(0, {"type": "play_dev", "card_type": "convoy", "selection": {"rsrc2": 2}})


class GuildTest(BaseInputHandlerTest):
  """Test for just the variations on the monopoly rules from cities and knights."""

  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.add_player("limegreen", "Bob")
    self.c.player_data[2].cards["guild"] = 1
    self.c.turn_idx = 2

  def testUseGuild(self):
    self.c.player_data[0].cards["rsrc3"] = 3
    self.c.player_data[1].cards["rsrc3"] = 4
    self.handle(2, {"type": "play_dev", "card_type": "guild", "selection": {"rsrc3": 1}})
    self.assertEqual(self.c.player_data[2].cards["rsrc3"], 4)
    self.assertEqual(self.c.player_data[0].cards["rsrc3"], 1)
    self.assertEqual(self.c.player_data[1].cards["rsrc3"], 2)

  def testUseGuildLimitedCards(self):
    self.c.player_data[0].cards["rsrc3"] = 1
    self.c.player_data[1].cards["rsrc3"] = 0
    self.handle(2, {"type": "play_dev", "card_type": "guild", "selection": {"rsrc3": 1}})
    self.assertEqual(self.c.player_data[2].cards["rsrc3"], 1)
    self.assertEqual(self.c.player_data[0].cards["rsrc3"], 0)
    self.assertEqual(self.c.player_data[1].cards["rsrc3"], 0)


if __name__ == "__main__":
  unittest.main()
