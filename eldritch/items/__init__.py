from eldritch.assets import Deputy, Blessing, Curse, Retainer, BankLoan, BadCredit, LodgeMembership
from .base import Item, Weapon, OneshotWeapon, Tome
from .common import *
from .unique import *
from .spells import *
from .deputy import PatrolWagon, DeputysRevolver


def CreateTradables():
  return [DeputysRevolver(), PatrolWagon()]


def CreateSpecials():
  return (
      [Deputy()]
      + [
          card(i) for i in range(12)
          for card in [Blessing, Curse, Retainer, BankLoan, BadCredit, LodgeMembership]
      ]
  )
