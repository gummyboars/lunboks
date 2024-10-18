# pylint: disable=useless-import-alias
from typing import List
from eldritch.assets import (
  Asset as Asset,
  Card as Card,
  Deputy as Deputy,
  Blessing as Blessing,
  Curse as Curse,
  Retainer as Retainer,
  BankLoan as BankLoan,
  BadCredit as BadCredit,
  LodgeMembership as LodgeMembership,
  BonusToAllChecks as BonusToAllChecks,
  StaminaDecrease as StaminaDecrease,
  SanityDecrease as SanityDecrease,
)
from eldritch.expansions.seaside.abilities import TeamPlayerBonus as TeamPlayerBonus
from .base import Item as Item, Weapon as Weapon, OneshotWeapon as OneshotWeapon, Tome as Tome
from .common import *
from .unique import *
from .spells import *
from .deputy import PatrolWagon as PatrolWagon, DeputysRevolver as DeputysRevolver


def CreateTradables():
  return [DeputysRevolver(), PatrolWagon()]


def CreateSpecials():
  cards = [
    Blessing,
    Curse,
    Retainer,
    BankLoan,
    BadCredit,
    LodgeMembership,
    StaminaDecrease,
    SanityDecrease,
  ]
  ret: List[Asset] = [Deputy(), TeamPlayerBonus(0)] + [card(i) for i in range(12) for card in cards]
  ret.extend([BonusToAllChecks("Voice Bonus", i) for i in range(12)])
  return ret
