from eldritch.assets import Deputy
from .base import Item, Weapon, OneshotWeapon, Tome
from .common import *
from .unique import *
from .spells import *
from .deputy import PatrolWagon, DeputysRevolver


def CreateTradables():
  return [DeputysRevolver(), PatrolWagon()]


def CreateSpecials():
  return [Deputy()]
