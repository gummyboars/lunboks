from typing import List

from eldritch.assets import Asset, Deputy, Blessing, Curse, Retainer, BankLoan, BadCredit, \
    LodgeMembership
from .base import Item, Weapon, OneshotWeapon, Tome
from .common import *
from .unique import *
from .spells import *
from .deputy import PatrolWagon, DeputysRevolver
from eldritch.expansions.seaside.abilities import TeamPlayerBonus


def CreateTradables():
  return [DeputysRevolver(), PatrolWagon()]


def CreateSpecials():
  ret: List[Asset] = (
      [Deputy(), TeamPlayerBonus(0)]
      + [
          card(i) for i in range(12)
          for card in [Blessing, Curse, Retainer, BankLoan, BadCredit, LodgeMembership]
      ]
  )

  return ret
