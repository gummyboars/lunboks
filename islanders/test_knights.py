#!/usr/bin/env python3

import collections
import os
import sys
import unittest

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from islanders import islanders
from islanders.islanders import InvalidMove, Road
from islanders.test_islanders import BaseInputHandlerTest

# pylint: disable=protected-access


class TestBuyKnight(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)

  def testBuyKnight(self):
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.c.handle_place_knight([6, 4], 0)
    self.assertIn((6, 4), self.c.knights)
    self.assertEqual(self.c.knights[(6, 4)].player, 0)
    self.assertEqual(self.c.knights[(6, 4)].strength, 1)
    self.assertEqual(self.c.knights[(6, 4)].movement, 0)  # Movement is for the other type of knight
    self.assertFalse(self.c.knights[(6, 4)].active)
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)

    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc5": 1})

  def testCannotBuyKnightOnSettlement(self):
    with self.assertRaisesRegex(InvalidMove, "on an empty corner"):
      self.c.handle_place_knight([8, 4], 0)
    self.assertNotIn((8, 4), self.c.knights)

  def testKnightsMustBeAttachedToRoads(self):
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle_place_knight([5, 3], 0)
    self.assertNotIn((5, 3), self.c.knights)

  def testKnightsCannotBePlacedOnShips(self):
    self.c.options["seafarers"].force(True)
    self.c.add_road(Road([8, 4, 9, 5], "ship", 0))
    with self.assertRaisesRegex(InvalidMove, "next to one of your roads"):
      self.c.handle_place_knight([9, 5], 0)
    self.assertNotIn((9, 5), self.c.knights)

  def testBuyingKnightUpdatesLongestRoute(self):
    self.c.add_road(Road([5, 5, 6, 4], "road", 1))
    self.c.add_road(Road([5, 3, 6, 4], "road", 1))
    self.assertEqual(self.c.player_data[1].longest_route, 3)
    self.c.handle_place_knight([6, 4], 0)
    self.assertEqual(self.c.player_data[1].longest_route, 2)

  def testMaxAvailableKnights(self):
    self.c.add_knight(islanders.Knight((5, 3), 0, (5, 3), strength=1))
    self.c.add_knight(islanders.Knight((6, 2), 0, (6, 2), strength=1))
    with self.assertRaisesRegex(InvalidMove, "knights remaining"):
      self.c.handle_place_knight([6, 4], 0)


class TestPromoteKnight(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)

  def testPromoteKnight(self):
    self.c.add_knight(islanders.Knight((6, 4), 0, (6, 4), strength=1))
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertEqual(self.c.knights[(6, 4)].strength, 1)
    self.c.handle_promote_knight([6, 4], 0)
    self.assertEqual(self.c.knights[(6, 4)].strength, 2)
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc1": 1, "rsrc5": 1})
    self.assertFalse(self.c.knights[(6, 4)].active)

  def testPromotionDoesNotChangeActiveStatus(self):
    self.c.add_knight(islanders.Knight((6, 4), 0, (6, 4), strength=1, active=True))
    self.c.handle_promote_knight([6, 4], 0)
    self.assertTrue(self.c.knights[(6, 4)].active)
    self.assertEqual(self.c.knights[(6, 4)].strength, 2)

  def testMaxKnightPromotion(self):
    self.c.add_knight(islanders.Knight((6, 4), 0, (6, 4), strength=3))
    with self.assertRaisesRegex(InvalidMove, "promote knights beyond"):
      self.c.handle_promote_knight([6, 4], 0)
    self.assertEqual(self.c.knights[(6, 4)].strength, 3)

  def testMaxOnePromotionPerTurn(self):
    self.c.add_knight(islanders.Knight((6, 4), 0, (6, 4), strength=1))
    self.c.handle_promote_knight([6, 4], 0)
    with self.assertRaisesRegex(InvalidMove, "promote.*more than once per turn"):
      self.c.handle_promote_knight([6, 4], 0)

  def testMaxAvailableKnights(self):
    self.c.add_knight(islanders.Knight((2, 4), 0, (2, 4), strength=3))
    self.c.add_knight(islanders.Knight((3, 3), 0, (3, 3), strength=3))
    self.c.add_knight(islanders.Knight((5, 3), 0, (5, 3), strength=2))
    self.c.add_knight(islanders.Knight((6, 2), 0, (6, 2), strength=2))
    self.c.add_knight(islanders.Knight((6, 4), 0, (6, 4), strength=1))
    with self.assertRaisesRegex(InvalidMove, "knights remaining"):
      self.c.handle_promote_knight([6, 4], 0)
    with self.assertRaisesRegex(InvalidMove, "knights remaining"):
      self.c.handle_promote_knight([6, 2], 0)

  def testMustPromoteOwnKnight(self):
    self.c.add_knight(islanders.Knight((6, 4), 1, (6, 4), strength=1))
    with self.assertRaisesRegex(InvalidMove, "your own knight"):
      self.c.handle_promote_knight([6, 4], 0)

  def testInvalidInput(self):
    self.c.add_knight(islanders.Knight((6, 4), 0, (6, 4), strength=1))
    with self.assertRaisesRegex(InvalidMove, "tuple of size 2"):
      self.c.handle_promote_knight([6], 0)
    with self.assertRaisesRegex(InvalidMove, "do not have a knight there"):
      self.c.handle_promote_knight([8, 4], 0)


class TestActivateKnight(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.add_knight(islanders.Knight((6, 4), 0, (6, 4), strength=1))

  def testActivateKnight(self):
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertFalse(self.c.knights[(6, 4)].active)
    self.c.handle_activate_knight([6, 4], 0)
    self.assertTrue(self.c.knights[(6, 4)].active)
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)

    self.assertDictEqual(new_rsrcs - old_rsrcs, {})
    self.assertDictEqual(old_rsrcs - new_rsrcs, {"rsrc3": 1})

  def testCannotDoubleActivateKnight(self):
    self.c.knights[(6, 4)].active = True
    old_rsrcs = collections.Counter(self.c.player_data[0].cards)
    with self.assertRaisesRegex(InvalidMove, "already active"):
      self.c.handle_activate_knight([6, 4], 0)
    new_rsrcs = collections.Counter(self.c.player_data[0].cards)
    self.assertDictEqual(old_rsrcs - new_rsrcs, {})

  def testMustActivateOwnKnight(self):
    self.c.knights[(6, 4)].player = 1
    with self.assertRaisesRegex(InvalidMove, "your own knights"):
      self.c.handle_activate_knight([6, 4], 0)

  def testInvalidInput(self):
    with self.assertRaisesRegex(InvalidMove, "tuple of size 2"):
      self.c.handle_activate_knight([6], 0)
    with self.assertRaisesRegex(InvalidMove, "do not have a knight there"):
      self.c.handle_activate_knight([8, 4], 0)


class TestKnightMovement(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.add_knight(islanders.Knight((6, 4), 0, (6, 4), strength=2, active=True))
    self.c.add_road(islanders.Road([5, 3, 6, 4], "road", 0))

  def testMoveKnightAlongRoads(self):
    self.c.handle_move_knight([6, 4], [5, 3], 0)
    self.assertIn((5, 3), self.c.knights)
    self.assertNotIn((6, 4), self.c.knights)
    self.assertFalse(self.c.knights[(5, 3)].active)
    self.assertEqual(self.c.knights[(5, 3)].strength, 2)

  def testCannotMoveInactiveKnight(self):
    self.c.knights[(6, 4)].active = False
    with self.assertRaisesRegex(InvalidMove, "must activate"):
      self.c.handle_move_knight([6, 4], [5, 3], 0)

  def testCannotMoveActivatedThisTurn(self):
    self.c.activated_this_turn.append((6, 4))
    with self.assertRaisesRegex(InvalidMove, "activated this turn"):
      self.c.handle_move_knight([6, 4], [5, 3], 0)

  def testDestinationCannotBeSource(self):
    with self.assertRaisesRegex(InvalidMove, "to a different location"):
      self.c.handle_move_knight([6, 4], [6, 4], 0)

  def testMoveKnightPastOwnPieces(self):
    self.c.add_road(islanders.Road([8, 4, 9, 5], "road", 0))
    self.c.add_road(islanders.Road([8, 6, 9, 5], "road", 0))
    self.c.add_knight(islanders.Knight((9, 5), 0, (9, 5), strength=1))
    self.c.handle_move_knight([6, 4], [8, 6], 0)

  def testCannotPlaceOnAnotherKnight(self):
    self.c.add_road(islanders.Road([8, 4, 9, 5], "road", 0))
    self.c.add_road(islanders.Road([8, 6, 9, 5], "road", 0))
    self.c.add_knight(islanders.Knight((8, 6), 0, (8, 6), strength=1))
    with self.assertRaisesRegex(InvalidMove, "on top of another knight"):
      self.c.handle_move_knight([6, 4], [8, 6], 0)

  def testCannotPlaceOnSettlement(self):
    with self.assertRaisesRegex(InvalidMove, "on a settlement"):
      self.c.handle_move_knight([6, 4], [8, 4], 0)

  def testCannotMoveKnightPastOpponentsPieces(self):
    self.c.add_road(islanders.Road([3, 3, 5, 3], "road", 0))
    self.c.add_road(islanders.Road([5, 5, 6, 4], "road", 0))
    self.c.add_road(islanders.Road([3, 5, 5, 5], "road", 0))
    self.c.add_knight(islanders.Knight((5, 3), 1, (5, 3), strength=1))
    with self.assertRaisesRegex(InvalidMove, "cannot reach"):
      self.c.handle_move_knight([6, 4], [3, 5], 0)
    with self.assertRaisesRegex(InvalidMove, "cannot reach"):
      self.c.handle_move_knight([6, 4], [3, 3], 0)

  def testMovedKnightCannotBePromotedAgain(self):
    self.c.knights[(6, 4)].strength = 1
    self.c.handle_promote_knight([6, 4], 0)
    self.c.handle_move_knight([6, 4], [5, 3], 0)
    with self.assertRaisesRegex(InvalidMove, "more than once per turn"):
      self.c.handle_promote_knight([5, 3], 0)
    self.assertEqual(self.c.knights[(5, 3)].strength, 2)

  def testMovingKnightToALocationWhereOneWasPreviouslyPromoted(self):
    self.c.add_road(islanders.Road([8, 4, 9, 5], "road", 0))
    self.c.add_knight(islanders.Knight((9, 5), 0, (9, 5), strength=1, active=True))
    self.c.handle_promote_knight([6, 4], 0)
    self.c.handle_move_knight([6, 4], [5, 3], 0)
    self.c.handle_move_knight([9, 5], [6, 4], 0)
    self.c.handle_promote_knight([6, 4], 0)

  def testCannotDisplaceEqualKnight(self):
    self.c.add_piece(islanders.Piece(2, 4, "settlement", 1))
    self.c.add_road(islanders.Road([2, 4, 3, 3], "road", 1))
    self.c.add_road(islanders.Road([3, 3, 5, 3], "road", 1))
    self.c.add_knight(islanders.Knight((5, 3), 1, (5, 3), strength=2, active=True))
    with self.assertRaisesRegex(InvalidMove, "cannot displace"):
      self.c.handle_move_knight([6, 4], [5, 3], 0)

  def testCanDisplaceWeakerKnight(self):
    self.c.add_piece(islanders.Piece(2, 4, "settlement", 1))
    self.c.add_road(islanders.Road([2, 4, 3, 3], "road", 1))
    self.c.add_road(islanders.Road([3, 3, 5, 3], "road", 1))
    self.c.add_knight(islanders.Knight((5, 3), 1, (5, 3), strength=1, active=True))
    self.c.handle_move_knight([6, 4], [5, 3], 0)
    self.assertEqual(self.c.turn_phase, "displace")
    self.assertIsNotNone(self.c.displaced_knight)
    self.assertEqual(self.c.displaced_knight.location, (5, 3))
    self.assertEqual(self.c.displaced_knight.player, 1)
    self.assertTrue(self.c.displaced_knight.active)

  def testMovingKnightRecalculatesLongestRoute(self):
    self.c.add_player("green", "Player3")
    self.c.add_piece(islanders.Piece(5, 3, "settlement", 2))
    self.c.add_road(islanders.Road([5, 3, 6, 4], "road", 2))
    self.c.add_road(islanders.Road([5, 5, 6, 4], "road", 2))
    self.c.add_road(islanders.Road([3, 3, 5, 3], "road", 2))
    self.c.add_road(islanders.Road([2, 4, 3, 3], "road", 2))
    self.c.add_road(islanders.Road([2, 4, 3, 5], "road", 2))
    self.c.add_road(islanders.Road([5, 7, 6, 6], "road", 1))
    self.c.add_road(islanders.Road([3, 7, 5, 7], "road", 1))
    self.c.add_road(islanders.Road([2, 6, 3, 7], "road", 1))
    self.c.add_road(islanders.Road([2, 6, 3, 5], "road", 1))
    self.c.add_road(islanders.Road([8, 4, 9, 5], "road", 0))
    self.c.add_road(islanders.Road([8, 6, 9, 5], "road", 0))
    self.c.add_road(islanders.Road([6, 6, 8, 6], "road", 0))

    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertEqual(self.c.player_data[1].longest_route, 5)
    self.assertEqual(self.c.player_data[2].longest_route, 4)
    self.assertEqual(self.c.longest_route_player, 1)

    self.c.handle_move_knight([6, 4], [6, 6], 0)
    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertEqual(self.c.player_data[1].longest_route, 4)
    self.assertEqual(self.c.player_data[2].longest_route, 5)
    self.assertEqual(self.c.longest_route_player, 2)

  def testKnightCanMoveOntoShips(self):
    pass  # TODO

  def testMovingKnightRedoesMovableCalculations(self):
    pass  # TODO


class TestDisplacedKnight(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.add_road(islanders.Road([5, 5, 6, 4], "road", 1))
    self.c.add_road(islanders.Road([5, 3, 6, 4], "road", 1))
    self.c.add_knight(islanders.Knight((6, 4), 1, (6, 4), strength=1, active=True))
    self.c.add_road(islanders.Road([8, 4, 9, 5], "road", 0))
    self.c.add_knight(islanders.Knight((9, 5), 0, (9, 5), strength=2, active=True))

  def testMoveDisplacedKnight(self):
    self.c.handle_move_knight([9, 5], [6, 4], 0)
    self.assertEqual(self.c.turn_phase, "displace")
    self.assertEqual(self.c.displaced_knight.location, (6, 4))
    self.assertTrue(self.c.displaced_knight.active)

    self.c.handle_displace([6, 6], 1)
    self.assertIsNone(self.c.displaced_knight)
    self.assertEqual(self.c.knights[(6, 6)].location, (6, 6))
    self.assertTrue(self.c.knights[(6, 6)].active)
    self.assertEqual(self.c.turn_phase, "main")

  def testDisplacedWithNoDestination(self):
    self.c.roads.pop((5, 5, 6, 6))
    self.c.roads.pop((5, 3, 6, 4))
    self.c.handle_move_knight([9, 5], [6, 4], 0)
    self.assertEqual(self.c.turn_phase, "main")
    self.assertIsNone(self.c.displaced_knight)
    self.assertEqual(self.c.knights[(6, 4)].player, 0)

  def testDisplacedWithOnlyOccupiedDestinations(self):
    self.c.add_knight(islanders.Knight((6, 6), 0, (6, 6), strength=1))
    self.c.add_knight(islanders.Knight((5, 3), 1, (5, 3), strength=1, active=True))
    self.c.handle_move_knight([9, 5], [6, 4], 0)
    self.assertEqual(self.c.turn_phase, "main")
    self.assertIsNone(self.c.displaced_knight)
    self.assertEqual(self.c.knights[(6, 4)].player, 0)

  def testMustDisplaceToEmptyCorner(self):
    self.c.add_knight(islanders.Knight((5, 3), 1, (5, 3), strength=1, active=True))
    self.c.handle_move_knight([9, 5], [6, 4], 0)
    self.assertEqual(self.c.turn_phase, "displace")
    with self.assertRaisesRegex(InvalidMove, "empty corner"):
      self.c.handle_displace([5, 3], 1)
    with self.assertRaisesRegex(InvalidMove, "empty corner"):
      self.c.handle_displace([5, 5], 1)

  def testMustMoveWithinSameRoadNetwork(self):
    self.c.add_piece(islanders.Piece(3, 3, "settlement", 1))
    self.c.add_road(islanders.Road([2, 4, 3, 3], "road", 1))
    self.c.handle_move_knight([9, 5], [6, 4], 0)
    self.assertEqual(self.c.turn_phase, "displace")
    with self.assertRaisesRegex(InvalidMove, "cannot reach that location"):
      self.c.handle_displace([2, 4], 1)
    self.c.handle_displace([5, 3], 1)

  def testDisplacedKnightAlsoUpdatesLongestRoad(self):
    self.c.add_road(islanders.Road([8, 6, 9, 5], "road", 0))
    self.c.add_road(islanders.Road([6, 6, 8, 6], "road", 0))
    self.c.add_road(islanders.Road([5, 7, 6, 6], "road", 0))
    self.assertEqual(self.c.player_data[0].longest_route, 5)
    self.assertEqual(self.c.player_data[1].longest_route, 3)
    self.assertEqual(self.c.longest_route_player, 0)

    self.c.handle_move_knight([9, 5], [6, 4], 0)
    self.c.handle_displace([6, 6], 1)
    self.assertEqual(self.c.player_data[0].longest_route, 4)
    self.assertEqual(self.c.player_data[1].longest_route, 2)
    self.assertIsNone(self.c.longest_route_player)

  def testOtherPlayersCannotPlayDuringDisplace(self):
    self.c.handle_move_knight([9, 5], [6, 4], 0)
    with self.assertRaisesRegex(islanders.NotYourTurn, "Waiting.*displaced"):
      self.handle(0, {"type": "promote", "location": [6, 4]})


class TestChaseRobber(BaseInputHandlerTest):
  def setUp(self):
    super().setUp()
    self.c.options["knights"].force(True)
    self.c.add_road(islanders.Road([5, 3, 6, 4], "road", 0))
    self.c.add_knight(islanders.Knight((5, 3), 0, (5, 3), strength=1, active=True))
    self.c.robber = islanders.TileLocation(7, 3)

  def testChaseRobber(self):
    self.c.handle_chase([7, 3], [5, 3], 0)
    self.assertEqual(self.c.action_stack[-1], "robber")
    self.assertEqual(self.c.action_stack[0], "rob")
    self.assertIn((5, 3), self.c.knights)
    self.assertFalse(self.c.knights[(5, 3)].active)

  def testMustChaseTheRobbersLocation(self):
    with self.assertRaisesRegex(InvalidMove, "must choose the robber"):
      self.c.handle_chase([4, 4], [5, 3], 0)

  def testMustBeNextToChasedRobber(self):
    self.c.robber = islanders.TileLocation(7, 5)
    with self.assertRaisesRegex(InvalidMove, "must be next to"):
      self.c.handle_chase([7, 5], [5, 3], 0)

  def testMustBeActivatedToChase(self):
    self.c.knights[(5, 3)].active = False
    with self.assertRaisesRegex(InvalidMove, "must activate"):
      self.c.handle_chase([7, 3], [5, 3], 0)

  def testCannotChaseOnActivationTurn(self):
    self.c.knights[(5, 3)].active = False
    self.c.handle_activate_knight([5, 3], 0)
    with self.assertRaisesRegex(InvalidMove, "activated this turn"):
      self.c.handle_chase([7, 3], [5, 3], 0)

  def testMustUseOwnKnight(self):
    self.c.knights[(5, 3)].player = 1
    with self.assertRaisesRegex(InvalidMove, "your own knight"):
      self.c.handle_chase([7, 3], [5, 3], 0)

  def testCanChasePirate(self):
    self.c.options["pirate"].force(True)
    self.c.options["seafarers"].force(True)
    self.c.pirate = islanders.TileLocation(4, 2)
    self.c.handle_chase([4, 2], [5, 3], 0)
    self.assertEqual(self.c.turn_phase, "robber")
    self.c.handle_pirate(0, [7, 7])
    self.assertEqual(self.c.turn_phase, "main")

  def testCannotMoveRobberIfChasedPirate(self):
    self.c.options["pirate"].force(True)
    self.c.options["seafarers"].force(True)
    self.c.pirate = islanders.TileLocation(4, 2)
    self.c.handle_chase([4, 2], [5, 3], 0)
    self.assertEqual(self.c.turn_phase, "robber")
    with self.assertRaisesRegex(InvalidMove, "must move the robber"):
      self.c.handle_robber([4, 6], 0)

  def testCannotMovePirateIfChasedRobber(self):
    self.c.options["pirate"].force(True)
    self.c.options["seafarers"].force(True)
    self.c.pirate = islanders.TileLocation(4, 2)
    self.c.handle_chase([7, 3], [5, 3], 0)
    self.assertEqual(self.c.turn_phase, "robber")
    with self.assertRaisesRegex(InvalidMove, "must move the pirate"):
      self.c.handle_pirate(0, [4, 8])


if __name__ == "__main__":
  unittest.main()
