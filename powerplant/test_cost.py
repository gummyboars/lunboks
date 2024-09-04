#!/usr/bin/env python3

import os
import sys
import unittest

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from powerplant import cities
from powerplant import cost


class TestCosts(unittest.TestCase):
  def testNoCities(self):
    germany = cities.Germany()
    self.assertEqual(cost.total_cost(germany, 0, []), 0)
    germany["BERLIN"].occupants.append(0)
    self.assertEqual(cost.total_cost(germany, 0, []), 0)

  def testInitialCosts(self):
    germany = cities.Germany()
    self.assertEqual(cost.total_cost(germany, 0, ["HAMBURG", "LUBECK", "KIEL"]), 10)
    self.assertEqual(cost.total_cost(germany, 0, ["BREMEN", "LUBECK", "KIEL"]), 21)

  def testCostFromOneCity(self):
    germany = cities.Germany()
    germany["FLENSBURG"].occupants.append(0)
    self.assertEqual(cost.total_cost(germany, 0, ["HAMBURG", "LUBECK", "KIEL"]), 14)
    self.assertEqual(cost.total_cost(germany, 0, ["BREMEN", "LUBECK", "KIEL"]), 25)

  def testCostFromMultipleCities(self):
    germany = cities.Germany()
    germany["MUNSTER"].occupants.append(0)
    germany["AACHEN"].occupants.append(0)
    self.assertEqual(cost.total_cost(germany, 0, ["ESSEN", "DUSSELDORF", "KOLN", "DORTMUND"]), 12)
    self.assertEqual(cost.total_cost(germany, 0, ["DUSSELDORF"]), 8)
    self.assertEqual(cost.total_cost(germany, 0, ["KASSEL", "TRIER"]), 39)
    self.assertEqual(cost.total_cost(germany, 0, ["OSNABRUCK", "KOLN"]), 14)

  def testOtherPlayersDoNotAffectCost(self):
    germany = cities.Germany()
    germany["BERLIN"].occupants.append(0)
    germany["MAGDEBURG"].occupants.append(1)
    self.assertEqual(cost.total_cost(germany, 0, ["LEIPZIG"]), 17)


if __name__ == "__main__":
  unittest.main()
