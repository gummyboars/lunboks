#!/usr/bin/env python3

from collections import Counter
import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from game import InvalidMove
from powerplant import cities
from powerplant.materials import Resource
from powerplant import plants
from powerplant import powerplant


def SampleCities(_):
  # Triangle of cities A-B-C, connected to triangle of cities D-E-F
  mapping = {
    "RED": cities.City("RED", cities.Color.RED),
    "BLUE": cities.City("BLUE", cities.Color.BLUE),
    "YELLOW": cities.City("YELLOW", cities.Color.YELLOW),
    "PURPLE": cities.City("PURPLE", cities.Color.PURPLE),
    "CYAN": cities.City("CYAN", cities.Color.CYAN),
    "BROWN": cities.City("BROWN", cities.Color.BROWN),
  }
  cities.connect(mapping, "RED", "BLUE", 4)
  cities.connect(mapping, "RED", "YELLOW", 8)
  cities.connect(mapping, "BLUE", "YELLOW", 0)
  cities.connect(mapping, "PURPLE", "CYAN", 5)
  cities.connect(mapping, "PURPLE", "BROWN", 7)
  cities.connect(mapping, "CYAN", "BROWN", 9)
  cities.connect(mapping, "RED", "PURPLE", 11)
  cities.connect(mapping, "BLUE", "CYAN", 16)
  cities.connect(mapping, "YELLOW", "BROWN", 15)
  return mapping


def SamplePlants(_):
  return [
    plants.Plant(cost=4, resource=Resource.COAL, intake=2, output=1),
    plants.Plant(cost=8, resource=Resource.COAL, intake=3, output=2),
    plants.Plant(cost=10, resource=Resource.COAL, intake=2, output=2),
    plants.Plant(cost=3, resource=Resource.OIL, intake=2, output=1),
    plants.Plant(cost=7, resource=Resource.OIL, intake=3, output=2),
    plants.Plant(cost=9, resource=Resource.OIL, intake=1, output=1),
    plants.Plant(cost=5, resource=Resource.HYBRID, intake=2, output=1),
    plants.Plant(cost=6, resource=Resource.GAS, intake=1, output=1),
    plants.Plant(cost=11, resource=Resource.URANIUM, intake=1, output=2),
    plants.Plant(cost=13, resource=Resource.GREEN, intake=0, output=1),
    plants.Plant(cost=11, resource=Resource.GREEN, intake=0, output=1, plus=True),
    plants.Plant(cost=12, resource=Resource.HYBRID, intake=2, output=2),
    plants.Plant(cost=17, resource=Resource.URANIUM, intake=1, output=2),
  ]


class OrderTest(unittest.TestCase):
  def testPlantOrdering(self):
    plantlist = SamplePlants(None)
    plantlist.sort()
    self.assertListEqual(
      [3, 4, 5, 6, 7, 8, 9, 10, 11, 11, 12, 13, 17], [plant.cost for plant in plantlist]
    )
    self.assertFalse(plantlist[8].plus)
    self.assertTrue(plantlist[9].plus)


class BaseBaseTest(unittest.TestCase):
  NUM_PLAYERS = 5  # Carefully chosen to not throw out any power plants to start the game.

  def setUp(self):
    colors = sorted(list(powerplant.PowerPlantGame.COLORS))
    players = [powerplant.Player(name=f"p{x}", color=colors[x]) for x in range(self.NUM_PLAYERS)]
    with mock.patch.object(cities, "CreateCities", new=SampleCities):
      with mock.patch.object(plants, "CreatePlants", new=SamplePlants):
        self.game = powerplant.GameState(players, "Germany", "old")


class RegionConnectionTest(BaseBaseTest):
  def testConnectivity(self):
    self.game.handle_region("red")
    self.assertSetEqual(self.game.colors, {cities.Color.RED})
    self.assertTrue(self.game.is_connected(cities.Color.BLUE))
    self.assertTrue(self.game.is_connected(cities.Color.YELLOW))
    self.assertTrue(self.game.is_connected(cities.Color.PURPLE))
    self.assertFalse(self.game.is_connected(cities.Color.CYAN))
    self.assertFalse(self.game.is_connected(cities.Color.BROWN))

    with self.assertRaisesRegex(InvalidMove, "contiguous"):
      self.game.handle_region("cyan")
    self.assertSetEqual(self.game.colors, {cities.Color.RED})  # Check nothing changed

    self.game.handle_region("blue")
    self.assertSetEqual(self.game.colors, {cities.Color.RED, cities.Color.BLUE})
    self.assertTrue(self.game.is_connected(cities.Color.BLUE))
    self.assertTrue(self.game.is_connected(cities.Color.YELLOW))
    self.assertTrue(self.game.is_connected(cities.Color.PURPLE))
    self.assertTrue(self.game.is_connected(cities.Color.CYAN))
    self.assertFalse(self.game.is_connected(cities.Color.BROWN))

    self.game.handle_region("cyan")
    self.assertSetEqual(self.game.colors, {cities.Color.RED, cities.Color.BLUE, cities.Color.CYAN})
    self.assertTrue(self.game.is_connected(cities.Color.BLUE))
    self.assertTrue(self.game.is_connected(cities.Color.YELLOW))
    self.assertTrue(self.game.is_connected(cities.Color.PURPLE))
    self.assertTrue(self.game.is_connected(cities.Color.CYAN))
    self.assertTrue(self.game.is_connected(cities.Color.BROWN))

  def testDuplicateAndErronousRegins(self):
    self.game.handle_region("red")
    with self.assertRaisesRegex(InvalidMove, "already.*chosen"):
      self.game.handle_region("red")
    with self.assertRaisesRegex(InvalidMove, "Unknown"):
      self.game.handle_region("green")
    self.game.handle_region("blue")
    self.game.handle_region("cyan")
    self.game.handle_region("yellow")
    self.game.handle_region("purple")
    with self.assertRaisesRegex(InvalidMove, "already.*determined"):
      self.game.handle_region("brown")

  def testAnyRegionIsConnectedWhenNoneHaveBeenChosen(self):
    for color in cities.Color:
      with self.subTest(color=color):
        self.assertTrue(self.game.is_connected(color))


class BaseTest(BaseBaseTest):
  def setUp(self):
    super().setUp()
    for color in ["red", "blue", "cyan", "purple", "yellow"]:
      self.game.handle_region(color)

  # Convenience functions to iterate through the returned generator.
  def handle_bid(self, bid, plant_idx):
    list(self.game.handle_bid(bid, plant_idx))

  def remove_plant(self, plant):
    list(self.game.remove_plant(plant))

  def handle_confirm(self):
    list(self.game.handle_confirm())

  def handle_burn(self, resource_counts):
    list(self.game.handle_burn(resource_counts))

  def handle(self, player_idx, data):
    ret = self.game.handle(player_idx, data)
    if ret:
      list(ret)


class RemovePlantTest(BaseTest):
  def testCycleLowestPlant(self):
    self.assertEqual(len(self.game.market), 8)
    old_plants = self.game.plants[:]
    lowest = self.game.market[0]

    self.remove_plant(lowest)
    self.assertEqual(len(self.game.market), 8)
    plant_numbers = [plant.cost for plant in self.game.market]
    self.assertListEqual(plant_numbers, sorted(plant_numbers))
    self.assertEqual(len(self.game.plants), len(old_plants) - 1)
    self.assertNotIn(lowest, self.game.market)
    self.assertNotIn(lowest, self.game.plants)


class AuctionTest(BaseTest):
  def setUp(self):
    super().setUp()
    self.game.turn_order = [3, 0, 4, 1, 2]
    self.game.auction_idx = 3

  def testInvalidBids(self):
    self.assertListEqual([plant.cost for plant in self.game.market], [3, 4, 5, 6, 7, 8, 9, 10])
    self.assertIsNone(self.game.auction_plant_idx)
    self.assertIsNone(self.game.auction_bid)

    with self.assertRaisesRegex(InvalidMove, "Invalid plant"):
      self.handle_bid(10, -1)
    with self.assertRaisesRegex(InvalidMove, "Invalid plant"):
      self.handle_bid(10, 8)
    with self.assertRaisesRegex(InvalidMove, "Invalid plant"):
      self.handle_bid(10, "pi")

    with self.assertRaisesRegex(InvalidMove, "positive integral"):
      self.handle_bid(3.5, 0)
    with self.assertRaisesRegex(InvalidMove, "positive integral"):
      self.handle_bid("pi", 0)

    with self.assertRaisesRegex(InvalidMove, "at least"):
      self.handle_bid(2, 0)
    with self.assertRaisesRegex(InvalidMove, "future market"):
      self.handle_bid(7, 4)

    self.game.players[3].money = 2
    with self.assertRaisesRegex(InvalidMove, "have enough money"):
      self.handle_bid(3, 0)

  def testBidOnePlantAtATime(self):
    self.handle_bid(3, 0)
    with self.assertRaisesRegex(InvalidMove, "wait until"):
      self.handle_bid(4, 1)

  def testPlayerGetsPlant(self):
    self.handle_bid(3, 0)
    for _ in range(4):
      self.handle_bid(None, 0)

    self.assertEqual(len(self.game.players[3].plants), 1)
    self.assertEqual(self.game.players[3].plants[0].cost, 3)
    self.assertEqual(self.game.players[3].money, 47)
    for other in [0, 1, 2, 4]:
      self.assertListEqual(self.game.players[other].plants, [])
      self.assertEqual(self.game.players[other].money, 50)

  def testCanBidAgainAfterLosingPlant(self):
    self.handle_bid(3, 0)
    for _ in range(2):  # Players 0 and 4 pass
      self.handle_bid(None, 0)

    self.assertSetEqual(self.game.auction_passed, {0, 4})
    self.assertDictEqual(self.game.auction_bought, {})
    self.handle_bid(4, 0)
    self.assertEqual(self.game.auction_bid, 4)

    with self.assertRaisesRegex(InvalidMove, "more than"):
      self.handle_bid(4, 0)
    self.handle_bid(5, 0)

    self.handle_bid(None, 0)  # Player 3 passes
    self.handle_bid(7, 0)  # Player 1 bids a lot
    self.assertEqual(self.game.auction_bid, 7)
    self.assertSetEqual(self.game.auction_passed, {0, 3, 4})
    self.assertDictEqual(self.game.auction_bought, {})

    self.handle_bid(None, 0)  # Player 2 passes
    self.assertEqual(len(self.game.players[1].plants), 1)
    self.assertEqual(self.game.players[1].plants[0].cost, 3)
    self.assertEqual(self.game.players[1].money, 43)
    for other in [0, 2, 3, 4]:
      self.assertListEqual(self.game.players[other].plants, [])
      self.assertEqual(self.game.players[other].money, 50)

    self.assertDictEqual(self.game.auction_bought, {1: True})
    # Everything else should reset
    self.assertSetEqual(self.game.auction_passed, set())
    self.assertIsNone(self.game.auction_plant_idx)
    self.assertIsNone(self.game.auction_bid)

    # The player first in turn order should get to bid again.
    self.assertEqual(self.game.auction_idx, 3)
    self.assertListEqual([plant.cost for plant in self.game.market][:7], [4, 5, 6, 7, 8, 9, 10])
    self.handle_bid(4, 0)
    for _ in range(3):  # Only 3 players have to pass now
      self.handle_bid(None, 0)
    self.assertEqual(len(self.game.players[3].plants), 1)
    self.assertEqual(self.game.players[3].plants[0].cost, 4)
    self.assertEqual(self.game.players[3].money, 46)
    self.assertListEqual([plant.cost for plant in self.game.market][:6], [5, 6, 7, 8, 9, 10])

    self.assertDictEqual(self.game.auction_bought, {3: True, 1: True})
    self.assertIsNone(self.game.auction_bid)
    self.assertIsNone(self.game.auction_plant_idx)
    self.assertSetEqual(self.game.auction_passed, set())

  def testFirstRoundMustBuy(self):
    self.assertTrue(self.game.first_round)
    with self.assertRaisesRegex(InvalidMove, "first round"):
      self.handle_bid(None, 0)
    self.assertEqual(self.game.auction_idx, 3)
    self.assertDictEqual(self.game.auction_bought, {})
    self.assertSetEqual(self.game.auction_passed, set())

    self.game.first_round = False
    self.handle_bid(None, 0)
    self.assertEqual(self.game.auction_idx, 0)
    self.assertDictEqual(self.game.auction_bought, {3: False})
    self.assertSetEqual(self.game.auction_passed, set())

    self.handle_bid(None, 0)
    self.assertEqual(self.game.auction_idx, 4)
    self.assertDictEqual(self.game.auction_bought, {3: False, 0: False})
    self.assertSetEqual(self.game.auction_passed, set())

  def testAllPlayersBuy(self):
    self.assertTrue(self.game.first_round)
    self.handle_bid(4, 1)
    for _ in range(3):
      self.handle_bid(None, None)  # It's valid to not pass the plant number when passing
    self.handle_bid(5, 1)
    self.handle_bid(7, 1)
    self.handle_bid(None, 1)
    self.assertDictEqual(self.game.auction_bought, {3: True})
    self.assertListEqual([plant.cost for plant in self.game.market][:7], [3, 5, 6, 7, 8, 9, 10])

    self.handle_bid(5, 1)
    self.handle_bid(6, 1)
    for _ in range(3):
      self.handle_bid(None, 1)
    self.assertDictEqual(self.game.auction_bought, {3: True, 4: True})
    self.assertListEqual([plant.cost for plant in self.game.market][:6], [3, 6, 7, 8, 9, 10])

    self.handle_bid(8, 3)
    for _ in range(2):
      self.handle_bid(None, 3)
    self.assertDictEqual(self.game.auction_bought, {3: True, 4: True, 0: True})
    self.assertListEqual([plant.cost for plant in self.game.market][:5], [3, 6, 7, 9, 10])

    self.handle_bid(9, 3)
    self.handle_bid(None, 3)
    self.assertDictEqual(self.game.auction_bought, {3: True, 0: True, 4: True, 1: True})
    self.assertListEqual([plant.cost for plant in self.game.market][:4], [3, 6, 7, 10])

    self.handle_bid(10, 3)
    # The auction has now finished
    self.assertEqual(self.game.phase_idx, self.game.PHASES.index(powerplant.TurnPhase.MATERIALS))
    self.assertFalse(self.game.first_round)

    self.assertListEqual([plant.cost for plant in self.game.market], [3, 6, 7, 11, 11, 12, 13, 17])

    plantlist = {3: 4, 4: 5, 0: 8, 1: 9, 2: 10}
    for player, cost in plantlist.items():
      self.assertEqual(len(self.game.players[player].plants), 1)
      self.assertEqual(self.game.players[player].plants[0].cost, cost)

  def testAllPlayersPass(self):
    self.game.first_round = False
    for _ in range(5):
      self.handle_bid(None, None)
    self.assertEqual(self.game.phase_idx, self.game.PHASES.index(powerplant.TurnPhase.MATERIALS))

    # Throw out the lowest cost plant if nobody bought one.
    self.assertListEqual([plant.cost for plant in self.game.market], [4, 5, 6, 7, 8, 9, 10, 13])

  def testMostPlayersPass(self):
    self.game.first_round = False
    for _ in range(4):
      self.handle_bid(None, None)
    self.handle_bid(6, 3)
    self.assertEqual(self.game.phase_idx, self.game.PHASES.index(powerplant.TurnPhase.MATERIALS))

    # Don't throw out any plants.
    self.assertListEqual([plant.cost for plant in self.game.market], [3, 4, 5, 7, 8, 9, 10, 13])


class Stage3AuctionTest(BaseTest):
  def setUp(self):
    super().setUp()
    self.game.turn_order = [3, 0, 4, 1, 2]
    self.game.auction_idx = 3
    self.game.stage_idx = 2
    self.game.first_round = False
    back = self.game.market.pop()
    second_back = self.game.market.pop()
    self.game.plants = [second_back, back] + self.game.plants

  def testCanBidAnyPlant(self):
    self.handle_bid(8, 5)
    for _ in range(4):
      self.handle_bid(None, None)

    self.assertEqual(len(self.game.players[3].plants), 1)
    self.assertEqual(self.game.players[3].plants[0].cost, 8)

    self.assertListEqual([plant.cost for plant in self.game.market], [3, 4, 5, 6, 7, 9])

  def testAllPlayersPass(self):
    for _ in range(5):
      self.handle_bid(None, None)
    self.assertEqual(self.game.phase_idx, self.game.PHASES.index(powerplant.TurnPhase.MATERIALS))

    # Throw out the lowest cost plant if nobody bought one.
    self.assertListEqual([plant.cost for plant in self.game.market], [4, 5, 6, 7, 8, 9])


class DiscardPlantTest(BaseTest):
  def setUp(self):
    super().setUp()
    self.game.turn_order = [3, 0, 4, 1, 2]
    self.game.auction_idx = 3
    for _ in range(3):  # Grant the player plants 3, 4, and 5
      self.game.players[3].plants.append(self.game.market[0])
      self.remove_plant(self.game.market[0])
    self.game.players[3].plants[0].storage.update({Resource.OIL: 2})
    self.game.players[3].plants[1].storage.update({Resource.COAL: 2})
    self.game.players[3].plants[2].storage.update({Resource.COAL: 1, Resource.OIL: 1})

  def testDiscardAPlant(self):
    self.handle_bid(8, 2)
    for _ in range(4):
      self.handle_bid(None, None)
    self.assertEqual(len(self.game.players[3].plants), 4)
    self.assertEqual(self.game.auction_discard_idx, 3)
    self.assertEqual(self.game.auction_idx, 0)

    with self.assertRaisesRegex(InvalidMove, "Waiting.*discard"):
      self.handle(0, {"type": "bid", "bid": 9, "plant": 2})
    with self.assertRaisesRegex(InvalidMove, "must.*discard"):
      self.handle(3, {"type": "bid", "bid": 9, "plant": 2})
    with self.assertRaisesRegex(InvalidMove, "Waiting.*discard"):
      self.handle(0, {"type": "discard", "plant": 0})

    self.handle(3, {"type": "discard", "plant": 0})
    self.assertIsNone(self.game.auction_discard_idx)
    self.assertEqual(self.game.auction_idx, 0)
    self.assertIsNone(self.game.auction_bid)
    self.assertIsNone(self.game.auction_plant_idx)

    self.assertEqual([plant.cost for plant in self.game.players[3].plants], [4, 5, 8])
    self.assertDictEqual(self.game.players[3].plants[0].storage, {Resource.COAL: 2})
    self.assertDictEqual(
      self.game.players[3].plants[1].storage, {Resource.OIL: 1, Resource.COAL: 1}
    )
    self.assertDictEqual(self.game.players[3].plants[2].storage, {})

  def testShuffleBeforeDiscarding(self):
    self.handle_bid(8, 2)
    for _ in range(4):
      self.handle_bid(None, None)
    self.assertEqual(len(self.game.players[3].plants), 4)
    self.assertEqual(self.game.auction_discard_idx, 3)

    self.handle(3, {"type": "shuffle", "resource": "coal", "source": 1, "dest": 3})
    self.handle(3, {"type": "shuffle", "resource": "coal", "source": 3, "dest": 2})
    self.handle(3, {"type": "shuffle", "resource": "coal", "source": 1, "dest": 3})
    self.handle(3, {"type": "discard", "plant": 1})

    self.assertEqual([plant.cost for plant in self.game.players[3].plants], [3, 5, 8])
    self.assertDictEqual(self.game.players[3].plants[0].storage, {Resource.OIL: 2})
    self.assertDictEqual(
      self.game.players[3].plants[1].storage, {Resource.OIL: 1, Resource.COAL: 2}
    )
    self.assertDictEqual(self.game.players[3].plants[2].storage, {Resource.COAL: 1})

  def testCannotDiscardPurchasedPlant(self):
    self.handle_bid(8, 2)
    for _ in range(4):
      self.handle_bid(None, None)
    self.assertEqual(len(self.game.players[3].plants), 4)
    self.assertEqual(self.game.auction_discard_idx, 3)

    with self.assertRaisesRegex(InvalidMove, "just bought"):
      self.handle(3, {"type": "discard", "plant": 3})

  def testInvalidDiscarding(self):
    self.handle_bid(8, 2)
    for _ in range(4):
      self.handle_bid(None, None)
    self.assertEqual(len(self.game.players[3].plants), 4)
    self.assertEqual(self.game.auction_discard_idx, 3)

    with self.assertRaisesRegex(InvalidMove, "Invalid plant"):
      self.handle(3, {"type": "discard"})
    with self.assertRaisesRegex(InvalidMove, "Invalid plant"):
      self.handle(3, {"type": "discard", "plant": -1})
    with self.assertRaisesRegex(InvalidMove, "Invalid plant"):
      self.handle(3, {"type": "discard", "plant": "x"})


class BuyResourcesTest(BaseTest):
  def setUp(self):
    super().setUp()
    self.game.players[0].money = 15
    for _ in range(2):  # Grant the player plants 3 and 4 (coal and oil).
      self.game.players[0].plants.append(self.game.market[0])
      self.remove_plant(self.game.market[0])
    self.game.phase_idx = self.game.PHASES.index(powerplant.TurnPhase.MATERIALS)

  def testCanBuyResources(self):
    self.game.handle_buy("coal", 1)
    self.assertDictEqual(self.game.pending_buy, {Resource.COAL: 1})
    self.assertEqual(self.game.pending_spend, 1)

    self.game.handle_buy("coal", 3)
    self.assertDictEqual(self.game.pending_buy, {Resource.COAL: 4})
    self.assertEqual(self.game.pending_spend, 5)

    self.game.handle_buy("oil", 1)
    self.assertDictEqual(self.game.pending_buy, {Resource.COAL: 4, Resource.OIL: 1})
    self.assertEqual(self.game.pending_spend, 8)
    stored = sum([Counter(plant.storage) for plant in self.game.players[0].plants], Counter())
    self.assertFalse(stored)

    self.handle_confirm()
    self.assertDictEqual(self.game.pending_buy, {})
    self.assertEqual(self.game.pending_spend, 0)
    stored = sum([Counter(plant.storage) for plant in self.game.players[0].plants], Counter())
    self.assertDictEqual(stored, {Resource.COAL: 4, Resource.OIL: 1})

  def testCanReset(self):
    self.game.handle_buy("coal", 3)
    self.assertEqual(self.game.pending_spend, 3)

    self.game.handle_buy("oil", 1)
    self.assertDictEqual(self.game.pending_buy, {Resource.COAL: 3, Resource.OIL: 1})
    self.assertEqual(self.game.pending_spend, 6)

    self.game.handle_reset()
    self.assertDictEqual(self.game.pending_buy, {})
    self.assertEqual(self.game.pending_spend, 0)

  def testCannotBuyResourcesWithNoStorage(self):
    with self.assertRaisesRegex(InvalidMove, "storage"):
      self.game.handle_buy("gas", 1)

    with self.assertRaisesRegex(InvalidMove, "storage"):
      self.game.handle_buy("coal", 5)

    self.assertDictEqual(self.game.pending_buy, {})
    self.assertEqual(self.game.pending_spend, 0)

  def testInsufficientMoney(self):
    self.game.handle_buy("coal", 3)
    self.assertEqual(self.game.pending_spend, 3)
    self.game.handle_buy("oil", 3)
    self.assertEqual(self.game.pending_spend, 12)

    with self.assertRaisesRegex(InvalidMove, "would need"):
      self.game.handle_buy("oil", 1)

  def testCannotBuyMoreThanExists(self):
    self.game.resources[Resource.COAL] = 2
    self.game.players[0].money = 50

    self.game.handle_buy("coal", 2)
    self.assertEqual(self.game.pending_spend, 16)
    with self.assertRaisesRegex(InvalidMove, "available"):
      self.game.handle_buy("coal", 1)
    self.assertDictEqual(self.game.pending_buy, {Resource.COAL: 2})
    self.assertEqual(self.game.pending_spend, 16)

  def testCanAllocateCoalToHybrids(self):
    hybrid = self.game.market[0]
    self.remove_plant(hybrid)
    self.game.players[0].plants.append(hybrid)
    self.game.players[0].money = 50

    self.game.handle_buy("coal", 8)
    self.assertEqual(self.game.pending_spend, 15)

    with self.assertRaisesRegex(InvalidMove, "storage"):
      self.game.handle_buy("coal", 1)

    self.handle_confirm()
    self.assertDictEqual(self.game.pending_buy, {})
    self.assertEqual(self.game.pending_spend, 0)
    self.assertDictEqual(self.game.players[0].plants[0].storage, {})
    self.assertDictEqual(self.game.players[0].plants[1].storage, {Resource.COAL: 4})
    self.assertDictEqual(self.game.players[0].plants[2].storage, {Resource.COAL: 4})

  def testCanAllocateOilToHybrids(self):
    hybrid = self.game.market[0]
    self.remove_plant(hybrid)
    self.game.players[0].plants.append(hybrid)
    self.game.players[0].money = 50

    self.game.handle_buy("oil", 8)
    self.assertEqual(self.game.pending_spend, 31)

    with self.assertRaisesRegex(InvalidMove, "storage"):
      self.game.handle_buy("oil", 1)

    self.handle_confirm()
    self.assertDictEqual(self.game.pending_buy, {})
    self.assertEqual(self.game.pending_spend, 0)
    self.assertDictEqual(self.game.players[0].plants[0].storage, {Resource.OIL: 4})
    self.assertDictEqual(self.game.players[0].plants[1].storage, {})
    self.assertDictEqual(self.game.players[0].plants[2].storage, {Resource.OIL: 4})

  def testHybridsCanHoldBothResourceTypes(self):
    hybrid = self.game.market[0]
    self.remove_plant(hybrid)
    self.game.players[0].plants.append(hybrid)
    self.game.players[0].money = 50

    self.game.handle_buy("oil", 6)
    self.assertEqual(self.game.pending_spend, 21)
    self.game.handle_buy("coal", 6)
    self.assertEqual(self.game.pending_spend, 30)

    with self.assertRaisesRegex(InvalidMove, "storage"):
      self.game.handle_buy("oil", 1)
    with self.assertRaisesRegex(InvalidMove, "storage"):
      self.game.handle_buy("coal", 1)

    self.handle_confirm()
    self.assertDictEqual(self.game.pending_buy, {})
    self.assertEqual(self.game.pending_spend, 0)
    self.assertDictEqual(self.game.players[0].plants[0].storage, {Resource.OIL: 4})
    self.assertDictEqual(self.game.players[0].plants[1].storage, {Resource.COAL: 4})
    self.assertDictEqual(
      self.game.players[0].plants[2].storage, {Resource.OIL: 2, Resource.COAL: 2}
    )

  def testInvalidResources(self):
    with self.assertRaisesRegex(InvalidMove, "Unknown"):
      self.game.handle_buy("trash", 1)
    with self.assertRaisesRegex(InvalidMove, "cannot buy"):
      self.game.handle_buy("green", 1)
    with self.assertRaisesRegex(InvalidMove, "cannot buy"):
      self.game.handle_buy("hybrid", 1)

  def testInvalidBuy(self):
    with self.assertRaisesRegex(InvalidMove, "positive integer"):
      self.game.handle_buy("coal", 0)
    with self.assertRaisesRegex(InvalidMove, "positive integer"):
      self.game.handle_buy("coal", -1)
    with self.assertRaisesRegex(InvalidMove, "positive integer"):
      self.game.handle_buy("coal", 1.5)
    with self.assertRaisesRegex(InvalidMove, "positive integer"):
      self.game.handle_buy("coal", "some")


class BuyHybridResourcesTest(BaseTest):
  def setUp(self):
    super().setUp()
    # Grant the player plants 5 and 9 (hybrid and oil).
    self.game.players[0].plants.append(self.game.market[2])
    self.remove_plant(self.game.market[2])
    self.remove_plant(self.game.market[0])
    self.remove_plant(self.game.market[0])
    self.game.players[0].plants.append(self.game.market[3])
    self.remove_plant(self.game.market[3])
    self.game.phase_idx = self.game.PHASES.index(powerplant.TurnPhase.MATERIALS)

  def testBuyOil(self):
    self.assertEqual([plant.cost for plant in self.game.players[0].plants], [5, 9])
    self.game.players[0].plants[0].storage.update({Resource.COAL: 2})
    self.game.handle_buy("oil", 3)
    self.handle_confirm()

    self.assertDictEqual(
      self.game.players[0].plants[0].storage, {Resource.COAL: 2, Resource.OIL: 1}
    )
    self.assertDictEqual(self.game.players[0].plants[1].storage, {Resource.OIL: 2})

  def testBuyCoalThenOil(self):
    self.game.handle_buy("coal", 2)
    self.game.handle_buy("oil", 3)
    self.handle_confirm()

    self.assertDictEqual(
      self.game.players[0].plants[0].storage, {Resource.COAL: 2, Resource.OIL: 1}
    )
    self.assertDictEqual(self.game.players[0].plants[1].storage, {Resource.OIL: 2})

  def testBuyOilThenCoal(self):
    self.game.handle_buy("oil", 3)
    self.game.handle_buy("coal", 2)
    self.handle_confirm()

    self.assertDictEqual(
      self.game.players[0].plants[0].storage, {Resource.COAL: 2, Resource.OIL: 1}
    )
    self.assertDictEqual(self.game.players[0].plants[1].storage, {Resource.OIL: 2})

  def testBuyThenShuffleBeforeConfirm(self):
    self.game.players[0].plants[1].storage.update({Resource.OIL: 2})
    self.game.handle_buy("coal", 3)
    self.game.handle_shuffle(0, "oil", 1, 0)
    self.game.handle_shuffle(0, "oil", 1, 0)
    # We had room for 3 coal when we decided to buy it, but now that we've moved 2 oil over to
    # our hybrid plant, we no longer have enough room to complete our purchase.
    with self.assertRaisesRegex(InvalidMove, "storage"):
      self.handle_confirm()
    self.game.handle_shuffle(0, "oil", 0, 1)
    self.game.handle_shuffle(0, "oil", 0, 1)
    self.handle_confirm()

  def testOverBuyCoalAndOil(self):
    # Tests to make sure we correctly track remaining capacity on hybrid plants.
    self.game.players[0].plants = [
      plants.Plant(cost=5, resource=Resource.HYBRID, intake=2, output=1),
      plants.Plant(cost=12, resource=Resource.HYBRID, intake=2, output=2),
    ]
    self.game.handle_buy("coal", 4)
    self.game.handle_buy("oil", 4)
    self.handle_confirm()

    self.assertDictEqual(self.game.players[0].plants[0].storage, {Resource.COAL: 4})
    self.assertDictEqual(self.game.players[0].plants[1].storage, {Resource.OIL: 4})


class BuildTest(BaseTest):
  def setUp(self):
    super().setUp()
    self.game.phase_idx = self.game.PHASES.index(powerplant.TurnPhase.BUILDING)
    self.game.turn_idx = 2

  def testFirstBuild(self):
    self.game.handle_build("RED")
    self.assertListEqual(self.game.pending_build, ["RED"])
    self.assertEqual(self.game.pending_spend, 10)

  def testCannotBuildTwiceInSameCity(self):
    self.game.stage_idx = 2
    self.game.cities["RED"].occupants = [2]
    with self.assertRaisesRegex(InvalidMove, "already in RED"):
      self.game.handle_build("RED")
    self.assertListEqual(self.game.pending_build, [])
    self.assertEqual(self.game.pending_spend, 0)

  def testConnectionCost(self):
    self.game.handle_build("RED")
    self.assertListEqual(self.game.pending_build, ["RED"])
    self.assertEqual(self.game.pending_spend, 10)
    self.game.handle_build("BLUE")
    self.assertListEqual(self.game.pending_build, ["RED", "BLUE"])
    self.assertEqual(self.game.pending_spend, 24)

    self.handle_confirm()
    self.assertListEqual(self.game.pending_build, [])
    self.assertEqual(self.game.pending_spend, 0)
    self.assertListEqual(self.game.cities["RED"].occupants, [2])
    self.assertListEqual(self.game.cities["BLUE"].occupants, [2])
    self.assertListEqual(self.game.cities["YELLOW"].occupants, [])  # Just making sure.

  def testTransitiveConnectionCost(self):
    self.game.handle_build("RED")
    self.assertListEqual(self.game.pending_build, ["RED"])
    self.assertEqual(self.game.pending_spend, 10)
    self.game.handle_build("YELLOW")
    self.assertListEqual(self.game.pending_build, ["RED", "YELLOW"])
    # Connect to yellow cheaper through blue. red -> yellow is 8, but red -> blue -> yellow is 4.
    self.assertEqual(self.game.pending_spend, 24)

  def testChoosesBestConnection(self):
    self.game.handle_build("RED")
    self.assertEqual(self.game.pending_spend, 10)
    self.game.handle_build("PURPLE")
    self.assertEqual(self.game.pending_spend, 31)
    self.game.handle_build("CYAN")
    self.assertEqual(self.game.pending_spend, 46)

  def testStage1NoMultipleOccupants(self):
    self.game.handle_build("RED")
    self.handle_confirm()

    self.assertEqual(self.game.turn_idx, 1)
    with self.assertRaisesRegex(InvalidMove, "only be occupied by 1"):
      self.game.handle_build("RED")
    self.assertListEqual(self.game.pending_build, [])
    self.assertEqual(self.game.pending_spend, 0)

    self.game.turn_idx = 2  # Make sure the original builder can't do this either
    with self.assertRaisesRegex(InvalidMove, "only be occupied by 1"):
      self.game.handle_build("RED")

  def testConnectionCostNotFromOtherPlayers(self):
    self.game.handle_build("RED")
    self.handle_confirm()

    self.assertEqual(self.game.turn_idx, 1)
    self.game.handle_build("CYAN")
    self.assertEqual(self.game.pending_spend, 10)
    self.game.handle_build("PURPLE")
    self.assertEqual(self.game.pending_spend, 25)

  def testTooExpensive(self):
    self.game.players[2].money = 30
    self.game.handle_build("RED")
    self.assertEqual(self.game.pending_spend, 10)
    with self.assertRaisesRegex(InvalidMove, "need at least 21"):
      self.game.handle_build("PURPLE")

  def testCanReset(self):
    self.game.handle_build("RED")
    self.game.handle_build("BLUE")
    self.assertEqual(self.game.pending_spend, 24)

    self.game.handle_reset()
    self.assertListEqual(self.game.pending_build, [])
    self.assertEqual(self.game.pending_spend, 0)
    self.game.handle_build("BLUE")
    self.game.handle_build("YELLOW")
    self.assertEqual(self.game.pending_spend, 20)

    self.handle_confirm()
    self.assertListEqual(self.game.pending_build, [])
    self.assertEqual(self.game.pending_spend, 0)
    self.assertListEqual(self.game.cities["RED"].occupants, [])

  def testCanRemoveFromPending(self):
    self.game.handle_build("RED")
    self.game.handle_build("BLUE")
    self.game.handle_build("PURPLE")
    self.assertEqual(self.game.pending_spend, 45)

    self.game.handle_build("BLUE")
    self.assertEqual(self.game.pending_spend, 31)

    self.game.handle_build("YELLOW")
    self.game.handle_build("PURPLE")
    self.assertEqual(self.game.pending_spend, 24)
    self.assertCountEqual(self.game.pending_build, ["RED", "YELLOW"])

    self.game.handle_build("RED")
    self.game.handle_build("YELLOW")
    self.assertEqual(self.game.pending_spend, 0)
    self.assertCountEqual(self.game.pending_build, [])

  def testBuildRemovesLowCostPlants(self):
    self.game.players[2].money = 200
    self.assertEqual(self.game.market[0].cost, 3)
    self.assertEqual(self.game.market[1].cost, 4)
    self.assertEqual(self.game.market[2].cost, 5)

    self.game.handle_build("RED")
    self.game.handle_build("BLUE")
    self.game.handle_build("YELLOW")
    self.game.handle_build("CYAN")
    self.handle_confirm()

    self.assertEqual(len(self.game.market), 8)
    self.assertNotIn(3, [plant.cost for plant in self.game.market])
    self.assertNotIn(3, [plant.cost for plant in self.game.plants])
    self.assertNotIn(4, [plant.cost for plant in self.game.market])
    self.assertNotIn(4, [plant.cost for plant in self.game.plants])

  def testStage2DoesNotStartEarly(self):
    self.game.stage_2_count = 3
    self.game.turn_idx = 1
    self.game.handle_build("RED")
    self.game.handle_build("BLUE")
    self.game.handle_build("YELLOW")
    self.handle_confirm()

    self.assertTrue(self.game.begin_stage_2)
    self.assertEqual(self.game.stage_idx, 0)

    self.assertEqual(self.game.turn_idx, 0)
    with self.assertRaisesRegex(InvalidMove, "only be occupied by 1"):
      self.game.handle_build("RED")
    self.game.handle_build("CYAN")
    self.handle_confirm()

    self.assertTrue(self.game.begin_stage_2)
    self.assertEqual(self.game.stage_idx, 1)


class BuildOutsidePlayAreaTest(BaseBaseTest):
  def setUp(self):
    super().setUp()
    for color in ["red", "purple", "cyan", "yellow", "brown"]:
      self.game.handle_region(color)
    self.game.phase_idx = self.game.PHASES.index(powerplant.TurnPhase.BUILDING)
    self.game.turn_idx = 2

  def testCannotBuildOutsidePlayArea(self):
    with self.assertRaisesRegex(InvalidMove, "Unknown city"):
      self.game.handle_build("BLUE")

  def testCannotConnectOutsidePlayArea(self):
    self.game.handle_build("RED")
    self.assertEqual(self.game.pending_spend, 10)
    self.game.handle_build("YELLOW")
    # If we were able to connect to yellow through blue, the connection cost would be 4 instead.
    self.assertEqual(self.game.pending_spend, 28)


class MultiBuildTest(BaseTest):
  def setUp(self):
    super().setUp()
    self.game.phase_idx = self.game.PHASES.index(powerplant.TurnPhase.BUILDING)
    self.game.turn_idx = 2
    self.game.stage_idx = 1

  def testCanBuildSecond(self):
    self.game.handle_build("RED")
    self.handle_confirm()

    self.assertEqual(self.game.turn_idx, 1)
    self.game.handle_build("RED")
    self.assertListEqual(self.game.pending_build, ["RED"])
    self.assertEqual(self.game.pending_spend, 15)
    self.handle_confirm()

    self.assertEqual(self.game.turn_idx, 0)
    with self.assertRaisesRegex(InvalidMove, "only be occupied by 2"):
      self.game.handle_build("RED")

    self.assertListEqual(self.game.cities["RED"].occupants, [2, 1])

  def testCanBuildThird(self):
    self.game.stage_idx = 2
    self.game.turn_idx = 3
    self.game.handle_build("RED")
    self.handle_confirm()

    self.assertEqual(self.game.turn_idx, 2)
    self.game.handle_build("RED")
    self.handle_confirm()

    self.assertEqual(self.game.turn_idx, 1)
    self.game.handle_build("RED")
    self.assertEqual(self.game.pending_spend, 20)
    self.handle_confirm()

    self.assertEqual(self.game.turn_idx, 0)
    with self.assertRaisesRegex(InvalidMove, "only be occupied by 3"):
      self.game.handle_build("RED")


class ShuffleResourcesTest(BaseTest):
  def setUp(self):
    super().setUp()
    self.game.players[0].plants = [
      plants.Plant(cost=5, resource=Resource.HYBRID, intake=2, output=1),
      plants.Plant(cost=12, resource=Resource.HYBRID, intake=2, output=2),
    ]
    self.game.players[1].plants = [
      plants.Plant(cost=6, resource=Resource.GAS, intake=1, output=1),
      plants.Plant(cost=11, resource=Resource.URANIUM, intake=1, output=2),
      plants.Plant(cost=13, resource=Resource.GREEN, intake=0, output=1),
    ]
    self.game.players[2].plants = [
      plants.Plant(cost=4, resource=Resource.COAL, intake=2, output=1),
      plants.Plant(cost=8, resource=Resource.COAL, intake=3, output=2),
      plants.Plant(cost=10, resource=Resource.COAL, intake=2, output=2),
    ]
    self.game.turn_idx = 0
    self.game.players[0].plants[0].storage.update({Resource.COAL: 2, Resource.OIL: 2})
    self.game.players[0].plants[1].storage.update({Resource.COAL: 2, Resource.OIL: 2})
    self.game.players[1].plants[0].storage.update({Resource.GAS: 1})
    self.game.players[1].plants[1].storage.update({Resource.URANIUM: 1})
    self.game.players[2].plants[0].storage.update({Resource.COAL: 2})
    self.game.players[2].plants[2].storage.update({Resource.COAL: 2})

  def testCanShuffleSameResource(self):
    self.game.handle_shuffle(2, "coal", 0, 1)
    self.assertDictEqual(self.game.players[2].plants[0].storage, {Resource.COAL: 1})
    self.assertDictEqual(self.game.players[2].plants[1].storage, {Resource.COAL: 1})
    self.game.handle_shuffle(2, "coal", 0, 2)
    self.assertDictEqual(self.game.players[2].plants[0].storage, {Resource.COAL: 0})
    self.assertDictEqual(self.game.players[2].plants[2].storage, {Resource.COAL: 3})
    self.game.handle_shuffle(2, "coal", 2, 1)
    self.assertDictEqual(self.game.players[2].plants[1].storage, {Resource.COAL: 2})
    self.assertDictEqual(self.game.players[2].plants[2].storage, {Resource.COAL: 2})

  def testCannotShuffleOtherResources(self):
    with self.assertRaisesRegex(InvalidMove, "cannot store"):
      self.game.handle_shuffle(1, "gas", 0, 1)
    with self.assertRaisesRegex(InvalidMove, "cannot store"):
      self.game.handle_shuffle(1, "uranium", 1, 0)
    with self.assertRaisesRegex(InvalidMove, "cannot store"):
      self.game.handle_shuffle(1, "gas", 0, 2)
    self.assertDictEqual(self.game.players[1].plants[0].storage, {Resource.GAS: 1})
    self.assertDictEqual(self.game.players[1].plants[1].storage, {Resource.URANIUM: 1})
    self.assertDictEqual(self.game.players[1].plants[2].storage, {})

  def testCanSwapBetweenFullPlants(self):
    player = self.game.players[0]
    self.game.handle_shuffle(0, "coal", 0, 1)
    self.assertDictEqual(player.plants[0].storage, {Resource.COAL: 1, Resource.OIL: 3})
    self.assertDictEqual(player.plants[1].storage, {Resource.COAL: 3, Resource.OIL: 1})
    self.game.handle_shuffle(0, "oil", 1, 0)
    self.assertDictEqual(player.plants[0].storage, {Resource.COAL: 0, Resource.OIL: 4})
    self.assertDictEqual(player.plants[1].storage, {Resource.COAL: 4, Resource.OIL: 0})

  def testCannotMakeMeaninglessSwap(self):
    player = self.game.players[0]
    player.plants.append(plants.Plant(cost=3, resource=Resource.OIL, intake=2, output=1))
    player.plants[2].storage.update({Resource.OIL: 4})
    with self.assertRaisesRegex(InvalidMove, "Cannot swap"):
      self.game.handle_shuffle(0, "oil", 2, 0)
    with self.assertRaisesRegex(InvalidMove, "is full"):
      self.game.handle_shuffle(0, "oil", 0, 2)

  def testSwapToSamePlant(self):
    # Meaningless, but also harmless.
    self.assertEqual(self.game.players[2].plants[2].storage[Resource.COAL], 2)
    self.game.handle_shuffle(2, "coal", 2, 2)
    self.assertEqual(self.game.players[2].plants[2].storage[Resource.COAL], 2)

  def testSwapToOrFromInvalidPlant(self):
    with self.assertRaisesRegex(InvalidMove, "Invalid destination plant"):
      self.game.handle_shuffle(0, "coal", 0, 2)
    with self.assertRaisesRegex(InvalidMove, "Invalid source plant"):
      self.game.handle_shuffle(0, "coal", 2, 0)
    with self.assertRaisesRegex(InvalidMove, "Invalid source plant"):
      self.game.handle_shuffle(0, "coal", -1, 0)

  def testSwapInvalidResource(self):
    with self.assertRaisesRegex(InvalidMove, "Invalid resource"):
      self.game.handle_shuffle(0, "x", 0, 1)
    with self.assertRaisesRegex(InvalidMove, "do not have any"):
      self.game.handle_shuffle(0, "gas", 0, 1)


class AdvanceStageTest(unittest.TestCase):
  def setUpGame(self, num):
    colors = sorted(list(powerplant.PowerPlantGame.COLORS))
    players = [powerplant.Player(name=f"p{x}", color=colors[x], money=999) for x in range(num)]
    game = powerplant.GameState(players, "Germany", "old")
    # Replace plants with plants numbered > 14 to avoid cycling out small plants.
    plants_to_own = [plant for plant in plants.OldPlants() if plant.cost <= 14]
    plants_to_use = [plant for plant in plants.OldPlants() if plant.cost > 14]
    plants_to_use.sort()
    game.market = plants_to_use[:8]
    game.plants = plants_to_use[8:]
    game.plants.append(plants.Plant(powerplant.STAGE_3_COST, Resource.GREEN, 0, 0))
    for idx in range(num):
      game.players[idx].plants.append(plants_to_own[idx])

    for color in ["red", "blue", "cyan", "purple", "yellow"]:
      if len(game.colors) >= game.to_choose:
        break
      game.handle_region(color)
    game.phase_idx = game.PHASES.index(powerplant.TurnPhase.BUILDING)
    game.turn_idx = 0
    game.stage_idx = 0
    game.first_round = False
    game.turn_order = list(range(num))
    return game

  def handle(self, game, player_idx, data):
    ret = game.handle(player_idx, data)
    if ret:
      list(ret)

  def testAdvanceToSecondStage(self):
    player_to_count = {2: 10, 3: 7, 6: 6}
    for num, count in player_to_count.items():
      with self.subTest(num_players=num):
        game = self.setUpGame(num)

        to_build = [
          "ESSEN",
          "DUISBURG",
          "DUSSELDORF",
          "DORTMUND",
          "MUNSTER",
          "KOLN",
          "OSNABRUCK",
          "AACHEN",
          "BREMEN",
          "CUXHAVEN",
        ]
        # Build count-1 cities first.
        for i in range(count - 1):
          self.handle(game, 0, {"type": "build", "city": to_build[i]})
        self.handle(game, 0, {"type": "confirm"})

        self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.BUREAUCRACY)
        self.assertEqual(game.stage_idx, 0)
        self.assertFalse(game.begin_stage_2)
        self.assertFalse(game.begin_stage_3)
        self.assertEqual(game.market[0].cost, 15)

        # Go through one turn.
        for idx in range(num):
          self.handle(game, idx, {"type": "burn", "counts": [None]})

        self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.AUCTION)
        for idx in range(num):
          self.handle(game, game.turn_order[idx], {"type": "bid", "bid": None, "plant": None})
        self.assertEqual(game.market[0].cost, 16)
        self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.MATERIALS)
        for idx in range(num):
          self.handle(game, game.turn_order[num - idx - 1], {"type": "confirm"})
        self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.BUILDING)
        for idx in range(num - 1):
          self.handle(game, game.turn_order[num - idx - 1], {"type": "confirm"})

        # Build the last city to trigger the next stage.
        self.handle(game, 0, {"type": "build", "city": to_build[count - 1]})
        self.handle(game, 0, {"type": "confirm"})
        self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.BUREAUCRACY)
        self.assertEqual(game.stage_idx, 1)
        self.assertTrue(game.begin_stage_2)
        self.assertFalse(game.begin_stage_3)

        # Should remove the lowest cost plant once. Note that because nobody bought a power
        # plant, plant 15 was removed from the market, so plant 16 will be removed for stage 2.
        self.assertEqual(game.market[0].cost, 17)

  def testAdvanceToThirdStageDuringAuction(self):
    num = 4
    game = self.setUpGame(num)
    game.stage_idx = 1  # Start in stage 2
    game.begin_stage_2 = True
    game.plants = game.plants[-1:] + game.plants[:-1]  # Put stage 3 on top.

    game.phase_idx = game.PHASES.index(powerplant.TurnPhase.AUCTION)
    self.handle(game, 0, {"type": "bid", "bid": 15, "plant": 0})
    # All other players pass on this plant.
    for idx in range(1, num):
      self.handle(game, game.turn_order[idx], {"type": "bid", "bid": None, "plant": 0})
    self.assertEqual(game.market[-1].cost, powerplant.STAGE_3_COST)
    self.assertTrue(game.begin_stage_3)
    self.assertEqual(game.stage_idx, 1)  # Still more bidding to be done.

    # Finish the auction phase.
    for idx in range(1, num):
      self.handle(game, game.turn_order[idx], {"type": "bid", "bid": None, "plant": None})
    self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.MATERIALS)
    self.assertTrue(game.begin_stage_3)
    self.assertEqual(game.stage_idx, 2)  # Now that we're in the next phase, stage 3 has begun.

    self.assertEqual(len(game.market), 6)
    self.assertEqual(game.market[0].cost, 17)  # Discard the lowest numbered plant once for stage 3.
    self.assertEqual(game.market[-1].cost, 22)

  def testAdvanceToThirdStageDuringBuilding(self):
    num = 4
    game = self.setUpGame(num)
    game.stage_idx = 1  # Start in stage 2
    game.begin_stage_2 = True
    self.assertEqual(game.resources["gas"], 6)
    game.plants = game.plants[-1:] + game.plants[:-1]  # Put stage 3 on top.
    game.market[0] = plants.Plant(1, Resource.GREEN, 0, 0)  # Doesn't matter as long as it costs 1.
    self.assertEqual(game.market[1].cost, 16)

    game.phase_idx = game.PHASES.index(powerplant.TurnPhase.BUILDING)
    self.handle(game, 0, {"type": "build", "city": "ESSEN"})
    self.handle(game, 0, {"type": "confirm"})
    self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.BUREAUCRACY)
    self.assertTrue(game.begin_stage_3)
    self.assertEqual(game.stage_idx, 2)

    self.assertEqual(len(game.market), 6)
    self.assertEqual(game.market[0].cost, 17)
    self.assertEqual(game.market[-1].cost, 22)

    # Go through bureaucracy and make sure the resupply is correct.
    for idx in range(num):
      self.handle(game, idx, {"type": "burn", "counts": [None]})

    self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.AUCTION)
    self.assertEqual(game.resources["gas"], 10)  # Resupplies at 4 in stage 3.

  def testAdvanceToThirdStageDuringBureaucracy(self):
    num = 4
    game = self.setUpGame(num)
    game.stage_idx = 1  # Start in stage 2
    game.begin_stage_2 = True
    self.assertEqual(game.resources["gas"], 6)
    game.plants = game.plants[-1:] + game.plants[:-1]  # Put stage 3 on top.
    self.assertEqual(game.market[-1].cost, 22)

    game.phase_idx = game.PHASES.index(powerplant.TurnPhase.BUREAUCRACY)
    for idx in range(num):
      self.handle(game, idx, {"type": "burn", "counts": [None]})
    self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.AUCTION)

    # When the largest plant is put on the bottom, stage 3 should come out.
    # Remove the lowest numbered plant (15), so 16 is now the lowest number.
    self.assertEqual(len(game.market), 6)
    self.assertEqual(game.market[0].cost, 16)
    self.assertEqual(game.market[-1].cost, 21)
    self.assertTrue(game.begin_stage_3)
    self.assertEqual(game.stage_idx, 2)

  def testAdvanceToThirdStageThenSecondStageDuringBuilding(self):
    num = 4
    game = self.setUpGame(num)
    game.stage_idx = 0  # Start in stage 1
    game.turn_idx = 1
    self.assertEqual(game.resources["gas"], 6)
    game.plants = game.plants[-1:] + game.plants[:-1]  # Put stage 3 on top.
    # We will have one player build to 6, and the next player build to 7. The first one will
    # discard plant 6, and bring stage 3 into play. The second one will trigger stage 2.
    game.market[0] = plants.Plant(6, Resource.GREEN, 0, 0)
    self.assertEqual(game.market[1].cost, 16)

    game.phase_idx = game.PHASES.index(powerplant.TurnPhase.BUILDING)

    # One player builds 6, forcing plant 6 to be discarded. Stage 3 card comes out.
    to_build = ["ESSEN", "DUISBURG", "DUSSELDORF", "DORTMUND", "MUNSTER", "KOLN"]
    for idx in range(6):
      self.handle(game, 1, {"type": "build", "city": to_build[idx]})
    self.handle(game, 1, {"type": "confirm"})
    self.assertFalse(game.begin_stage_2)
    self.assertTrue(game.begin_stage_3)
    self.assertEqual(len(game.market), 6)  # Should remove smallest plant and stage 3 card.
    self.assertEqual(game.stage_idx, 0)  # Should not start until next phase.

    # Next player builds 7, triggering stage 2.
    to_build = ["FLENSBURG", "KIEL", "HAMBURG", "CUXHAVEN", "BREMEN", "HANNOVER", "OSNABRUCK"]
    for idx in range(7):
      self.handle(game, 0, {"type": "build", "city": to_build[idx]})
    self.handle(game, 0, {"type": "confirm"})
    self.assertTrue(game.begin_stage_2)
    self.assertTrue(game.begin_stage_3)
    self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.BUREAUCRACY)
    self.assertEqual(len(game.market), 6)
    self.assertEqual(game.stage_idx, 2)

    # Go through bureaucracy and make sure the resupply is correct.
    for idx in range(num):
      self.handle(game, idx, {"type": "burn", "counts": [None]})

    self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.AUCTION)
    self.assertEqual(game.resources["gas"], 10)  # Resupplies at 4 in stage 3.

  def testAdvanceToSecondStageThenThirdStageDuringBuilding(self):
    num = 4
    game = self.setUpGame(num)
    game.stage_idx = 0  # Start in stage 1
    game.turn_idx = 1
    self.assertEqual(game.resources["gas"], 6)
    game.plants = game.plants[-1:] + game.plants[:-1]  # Put stage 3 on top.
    # We will have one player build to 7, and the next player build to 8. The first one will
    # trigger stage 2. The second one will discard plant 8, and bring stage 3 into play.
    game.market[0] = plants.Plant(8, Resource.GREEN, 0, 0)
    self.assertEqual(game.market[1].cost, 16)

    game.phase_idx = game.PHASES.index(powerplant.TurnPhase.BUILDING)

    # One player builds 7, triggering stage 2.
    to_build = ["FLENSBURG", "KIEL", "HAMBURG", "CUXHAVEN", "BREMEN", "HANNOVER", "OSNABRUCK"]
    for idx in range(7):
      self.handle(game, 1, {"type": "build", "city": to_build[idx]})
    self.handle(game, 1, {"type": "confirm"})
    self.assertTrue(game.begin_stage_2)
    self.assertFalse(game.begin_stage_3)
    self.assertEqual(len(game.market), 8)
    self.assertEqual(game.stage_idx, 0)

    # Next player builds 8, forcing plant 8 to be discarded. Stage 3 card comes out.
    to_build = ["ESSEN", "DUISBURG", "DUSSELDORF", "DORTMUND", "MUNSTER", "KOLN", "AACHEN", "TRIER"]
    for idx in range(8):
      self.handle(game, 0, {"type": "build", "city": to_build[idx]})
    self.handle(game, 0, {"type": "confirm"})
    self.assertEqual(len(game.market), 6)
    self.assertTrue(game.begin_stage_2)
    self.assertTrue(game.begin_stage_3)
    self.assertEqual(game.stage_idx, 2)

    # Go through bureaucracy and make sure the resupply is correct.
    for idx in range(num):
      self.handle(game, idx, {"type": "burn", "counts": [None]})

    self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.AUCTION)
    self.assertEqual(game.resources["gas"], 10)  # Resupplies at 4 in stage 3.

  def testAdvanceToSecondStageThenThirdStageDuringBureaucracy(self):
    num = 4
    game = self.setUpGame(num)
    game.stage_idx = 0  # Start in stage 1
    game.turn_idx = 1
    self.assertEqual(game.resources["gas"], 6)
    game.plants = game.plants[-1:] + game.plants[:-1]  # Put stage 3 on top.
    # We will have one player build to 7, triggering stage 2. During bureaucracy, the lowest
    # numbered plant will be removed (this happens once when we move to stage 2), bringing the
    # stage 3 card into play.
    self.assertEqual(game.market[0].cost, 15)

    game.phase_idx = game.PHASES.index(powerplant.TurnPhase.BUILDING)

    # One player builds 7, triggering stage 2.
    to_build = ["FLENSBURG", "KIEL", "HAMBURG", "CUXHAVEN", "BREMEN", "HANNOVER", "OSNABRUCK"]
    for idx in range(7):
      self.handle(game, 1, {"type": "build", "city": to_build[idx]})
    self.handle(game, 1, {"type": "confirm"})
    self.assertTrue(game.begin_stage_2)
    self.assertFalse(game.begin_stage_3)
    self.assertEqual(len(game.market), 8)
    self.assertEqual(game.market[0].cost, 15)  # Do not remove lowest cost plant until next phase.
    # Stage 3 card should not have come out yet.
    self.assertNotEqual(game.market[-1].cost, powerplant.STAGE_3_COST)
    self.assertEqual(game.stage_idx, 0)  # Not done with this phase yet.

    self.handle(game, 0, {"type": "confirm"})
    self.assertTrue(game.begin_stage_2)
    self.assertTrue(game.begin_stage_3)
    self.assertEqual(game.stage_idx, 1)  # Stage 3 starts at the end of bureaucracy.

    for idx in range(num):
      self.handle(game, idx, {"type": "burn", "counts": [None]})

    self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.AUCTION)
    self.assertEqual(game.resources["gas"], 9)  # Resupplies at 3 in stage 2.
    self.assertEqual(game.stage_idx, 2)  # Bureaucracy is over, stage 3 should start.

  def testAdvanceToThirdStageEarly(self):
    num = 4
    game = self.setUpGame(num)
    game.stage_idx = 0  # Start in stage 1
    game.turn_idx = 0
    self.assertEqual(game.resources["gas"], 6)
    game.plants = game.plants[-1:] + game.plants[:-1]  # Put stage 3 on top.

    game.phase_idx = game.PHASES.index(powerplant.TurnPhase.BUREAUCRACY)
    for idx in range(num):
      self.handle(game, idx, {"type": "burn", "counts": [None]})

    self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.AUCTION)
    self.assertFalse(game.begin_stage_2)
    self.assertTrue(game.begin_stage_3)
    self.assertEqual(len(game.market), 6)
    self.assertEqual(game.stage_idx, 2)

    for idx in range(num):
      self.handle(game, game.turn_order[idx], {"type": "bid", "bid": None, "plant": None})
    self.assertEqual(game.market[0].cost, 17)
    self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.MATERIALS)
    for idx in range(num):
      self.handle(game, game.turn_order[num - idx - 1], {"type": "confirm"})
    self.assertIs(game.PHASES[game.phase_idx], powerplant.TurnPhase.BUILDING)

    for idx in range(num - 1):
      self.handle(game, game.turn_order[num - idx - 1], {"type": "confirm"})
    to_build = ["FLENSBURG", "KIEL", "HAMBURG", "CUXHAVEN", "BREMEN", "HANNOVER", "OSNABRUCK"]
    for idx in range(7):
      self.handle(game, game.turn_order[0], {"type": "build", "city": to_build[idx]})
    self.handle(game, game.turn_order[0], {"type": "confirm"})

    self.assertFalse(game.begin_stage_2)
    self.assertTrue(game.begin_stage_3)
    self.assertEqual(game.stage_idx, 2)
    self.assertEqual(len(game.market), 6)


class BureaucracyTest(BaseTest):
  def setUp(self):
    colors = sorted(list(powerplant.PowerPlantGame.COLORS))
    players = [powerplant.Player(name=f"p{x}", color=colors[x], money=0) for x in range(4)]
    with mock.patch.object(plants, "CreatePlants", new=SamplePlants):
      self.game = powerplant.GameState(players, "Germany", "old")
    for color in ["red", "blue", "cyan", "brown"]:
      self.game.handle_region(color)
    self.game.phase_idx = self.game.PHASES.index(powerplant.TurnPhase.BUREAUCRACY)
    self.game.turn_order = [1, 2, 0, 3]
    self.game.turn_idx = 1
    self.game.stage_idx = 1

    # We will violate the constraint on number of players in a city, but that's not being tested.
    player_counts = {0: 4, 1: 3, 2: 4, 3: 2}
    names = ["ESSEN", "MUNSTER", "KOLN", "AACHEN", "TRIER", "KASSEL", "BREMEN", "HAMBURG", "LUBECK"]
    for player_idx, count in player_counts.items():
      for idx in range(count):
        self.game.cities[names[idx]].occupants.append(player_idx)

    self.game.players[0].plants.append(plants.Plant(4, Resource.COAL, 2, 1))
    self.game.players[0].plants.append(plants.Plant(10, Resource.COAL, 2, 2))
    self.game.players[0].plants.append(plants.Plant(13, Resource.GREEN, 0, 1))
    self.game.players[0].plants[0].storage.update({Resource.COAL: 4})
    self.game.players[0].plants[1].storage.update({Resource.COAL: 2})

    self.game.players[1].plants.append(plants.Plant(5, Resource.HYBRID, 2, 1))
    self.game.players[1].plants.append(plants.Plant(12, Resource.HYBRID, 2, 2))
    self.game.players[1].plants[0].storage.update({Resource.COAL: 2, Resource.OIL: 2})
    self.game.players[1].plants[1].storage.update({Resource.COAL: 1, Resource.OIL: 1})

    self.game.players[2].plants.append(plants.Plant(6, Resource.GAS, 1, 1))
    self.game.players[2].plants.append(plants.Plant(11, Resource.URANIUM, 1, 2))
    self.game.players[2].plants.append(plants.Plant(13, Resource.GREEN, 0, 1))
    self.game.players[2].plants[0].storage.update({Resource.GAS: 2})
    self.game.players[2].plants[1].storage.update({Resource.URANIUM: 2})

    self.game.players[3].plants.append(plants.Plant(8, Resource.COAL, 3, 2))
    self.game.players[3].plants.append(plants.Plant(16, Resource.OIL, 2, 3))
    self.game.players[3].plants[0].storage.update({Resource.COAL: 2})
    self.game.players[3].plants[1].storage.update({Resource.OIL: 2})

    self.game.resources = {Resource.COAL: 3, Resource.OIL: 5, Resource.GAS: 4, Resource.URANIUM: 2}


class BurnTest(BureaucracyTest):
  def testNormalBurn(self):
    self.handle_burn([{"coal": 2}, {"coal": 1, "oil": 1}])
    self.handle_burn([{"gas": 1}, {"uranium": 1}, {}])
    self.handle_burn([{"coal": 2}, {"coal": 2}, {}])
    self.handle_burn([None, {"oil": 2}])

    self.assertDictEqual(self.game.players[1].plants[0].storage, {Resource.OIL: 2})
    self.assertDictEqual(self.game.players[1].plants[1].storage, {})
    self.assertDictEqual(self.game.players[2].plants[0].storage, {Resource.GAS: 1})
    self.assertDictEqual(self.game.players[2].plants[1].storage, {Resource.URANIUM: 1})
    self.assertDictEqual(self.game.players[2].plants[2].storage, {})
    self.assertDictEqual(self.game.players[0].plants[0].storage, {Resource.COAL: 2})
    self.assertDictEqual(self.game.players[0].plants[1].storage, {})
    self.assertDictEqual(self.game.players[0].plants[2].storage, {})
    self.assertDictEqual(self.game.players[3].plants[0].storage, {Resource.COAL: 2})
    self.assertDictEqual(self.game.players[3].plants[1].storage, {})

    expected_powered = {1: 3, 2: 4, 0: 4, 3: 2}
    for player_idx, expected in expected_powered.items():
      with self.subTest(player=player_idx):
        self.assertEqual(powerplant.PAYMENTS.index(self.game.players[player_idx].money), expected)

  def testUnderBurn(self):
    self.handle_burn([{"coal": 1, "oil": 1}, None])
    self.handle_burn([{"gas": 1}, None, None])
    self.handle_burn([None, {"coal": 2}, {}])
    self.handle_burn([None, {"oil": 2}])

    players = self.game.players
    self.assertDictEqual(players[1].plants[0].storage, {Resource.OIL: 1, Resource.COAL: 1})
    self.assertDictEqual(players[1].plants[1].storage, {Resource.OIL: 1, Resource.COAL: 1})
    self.assertDictEqual(players[2].plants[0].storage, {Resource.GAS: 1})
    self.assertDictEqual(players[2].plants[1].storage, {Resource.URANIUM: 2})
    self.assertDictEqual(players[2].plants[2].storage, {})
    self.assertDictEqual(players[0].plants[0].storage, {Resource.COAL: 4})
    self.assertDictEqual(players[0].plants[1].storage, {})
    self.assertDictEqual(players[0].plants[2].storage, {})
    self.assertDictEqual(players[3].plants[0].storage, {Resource.COAL: 2})
    self.assertDictEqual(players[3].plants[1].storage, {})

    expected_powered = {1: 1, 2: 1, 0: 3, 3: 2}
    for player_idx, expected in expected_powered.items():
      with self.subTest(player=player_idx):
        self.assertEqual(powerplant.PAYMENTS.index(self.game.players[player_idx].money), expected)

  def testCycleLargestPlant(self):
    self.assertListEqual([plant.cost for plant in self.game.market], [3, 4, 5, 6, 7, 8, 9, 10])
    self.handle_burn([None, None])
    self.handle_burn([None, None, None])
    self.handle_burn([None, None, None])
    self.handle_burn([None, None])
    self.assertListEqual([plant.cost for plant in self.game.market], [3, 4, 5, 6, 7, 8, 9, 13])
    self.assertEqual(self.game.plants[-1].cost, 10)

  def testCycleSmallestPlant(self):
    self.game.stage_idx = 2
    self.game.market.pop()
    self.game.market.pop()
    self.assertListEqual([plant.cost for plant in self.game.market], [3, 4, 5, 6, 7, 8])
    orig_len = len(self.game.plants)
    self.handle_burn([None, None])
    self.handle_burn([None, None, None])
    self.handle_burn([None, None, None])
    self.handle_burn([None, None])
    self.assertListEqual([plant.cost for plant in self.game.market], [4, 5, 6, 7, 8, 13])
    self.assertEqual(len(self.game.plants), orig_len - 1)

  def testNoPlantsLeft(self):
    self.game.stage_idx = 2
    self.game.market.clear()
    self.game.plants.clear()
    self.handle_burn([None, None])
    self.handle_burn([None, None, None])
    self.handle_burn([None, None, None])
    self.handle_burn([None, None])

  def testCorrectBurnAmounts(self):
    with self.assertRaisesRegex(InvalidMove, "exact number"):
      self.handle_burn([{"coal": 1}, {"coal": 1, "oil": 1}])
    with self.assertRaisesRegex(InvalidMove, "exact number"):
      self.handle_burn([{"coal": 2, "oil": 2}, {"coal": 1, "oil": 1}])

  def testCannotBurnMoreThanYouHave(self):
    with self.assertRaisesRegex(InvalidMove, "are on your plants"):
      self.handle_burn([{"coal": 2}, {"coal": 2}])

  def testInvalidBurn(self):
    with self.assertRaisesRegex(InvalidMove, "Invalid resource counts"):
      self.handle_burn(None)
    with self.assertRaisesRegex(InvalidMove, "Invalid resource counts"):
      self.handle_burn(["coal", "oil"])
    with self.assertRaisesRegex(InvalidMove, "each plant"):
      self.handle_burn([None, None, None])

  def testInvalidCounts(self):
    with self.assertRaisesRegex(InvalidMove, "Invalid resource in"):
      self.handle_burn([{"oil": 2}, {"trash": 2}])
    with self.assertRaisesRegex(InvalidMove, "Invalid resource in"):
      self.handle_burn([{"coal": 2}, {"trash": 2}])
    with self.assertRaisesRegex(InvalidMove, "on your plants"):
      self.handle_burn([{"oil": 2}, {"hybrid": 2}])
    with self.assertRaisesRegex(InvalidMove, "on your plants"):
      self.handle_burn([{"oil": 2}, {"oil": 2}])

    with self.assertRaisesRegex(InvalidMove, "positive integral"):
      self.handle_burn([{"oil": 2}, {"oil": 0}])
    with self.assertRaisesRegex(InvalidMove, "positive integral"):
      self.handle_burn([{"oil": 1.5}, {"oil": 1.5}])
    with self.assertRaisesRegex(InvalidMove, "exact number"):
      self.handle_burn([{"oil": 2}, {"oil": 1}])
    with self.assertRaisesRegex(InvalidMove, "exact number"):
      self.handle_burn([{"oil": 2, "coal": 2}, {"coal": 1, "oil": 1}])


class ResupplyTest(BureaucracyTest):
  def testStage1(self):
    self.game.stage_idx = 0
    orig = Counter(self.game.resources)
    self.handle_burn([{"coal": 2}, {"coal": 1, "oil": 1}])
    self.handle_burn([{"gas": 1}, {"uranium": 1}, {}])
    self.handle_burn([{"coal": 2}, {"coal": 2}, {}])
    self.handle_burn([None, {"oil": 2}])
    self.assertEqual(self.game.phase_idx, self.game.PHASES.index(powerplant.TurnPhase.AUCTION))

    updated = Counter(self.game.resources)
    diff = updated - orig
    expected = {Resource.COAL: 5, Resource.OIL: 3, Resource.GAS: 2, Resource.URANIUM: 1}
    self.assertDictEqual(diff, expected)

  def testStage2(self):
    self.game.stage_idx = 1
    orig = Counter(self.game.resources)
    self.handle_burn([{"coal": 2}, {"coal": 1, "oil": 1}])
    self.handle_burn([{"gas": 1}, {"uranium": 1}, {}])
    self.handle_burn([{"coal": 2}, {"coal": 2}, {}])
    self.handle_burn([None, {"oil": 2}])
    self.assertEqual(self.game.phase_idx, self.game.PHASES.index(powerplant.TurnPhase.AUCTION))

    updated = Counter(self.game.resources)
    diff = updated - orig
    expected = {Resource.COAL: 6, Resource.OIL: 4, Resource.GAS: 3, Resource.URANIUM: 2}
    self.assertDictEqual(diff, expected)

  def testStage3(self):
    self.game.stage_idx = 2
    orig = Counter(self.game.resources)
    self.handle_burn([{"coal": 2}, {"coal": 1, "oil": 1}])
    self.handle_burn([{"gas": 1}, {"uranium": 1}, {}])
    self.handle_burn([{"coal": 2}, {"coal": 2}, {}])
    self.handle_burn([None, {"oil": 2}])
    self.assertEqual(self.game.phase_idx, self.game.PHASES.index(powerplant.TurnPhase.AUCTION))

    updated = Counter(self.game.resources)
    diff = updated - orig
    expected = {Resource.COAL: 4, Resource.OIL: 5, Resource.GAS: 4, Resource.URANIUM: 2}
    self.assertDictEqual(diff, expected)

  def testDoesNotOverSupply(self):
    self.game.stage_idx = 0
    # Have everyone burn nothing. Resources remaining on plants: 11 coal, 5 oil, 2 gas, 2 uranium
    orig = Counter({Resource.COAL: 11, Resource.OIL: 16, Resource.GAS: 21, Resource.URANIUM: 9})
    self.game.resources.update(orig)
    self.handle_burn([None, None])
    self.handle_burn([None, None, None])
    self.handle_burn([None, None, None])
    self.handle_burn([None, None])
    self.assertEqual(self.game.phase_idx, self.game.PHASES.index(powerplant.TurnPhase.AUCTION))

    updated = Counter(self.game.resources)
    diff = updated - orig
    expected = {Resource.COAL: 2, Resource.OIL: 3, Resource.GAS: 1, Resource.URANIUM: 1}
    self.assertDictEqual(diff, expected)


if __name__ == "__main__":
  unittest.main()
