from eldritch.assets import Deputy
from .base import Item, Weapon, OneshotWeapon, Tome
from .common import (
    AncientTome, Automatic45, Axe, DarkCloak,
    Derringer18, Revolver38, Dynamite,
    TommyGun, Food, ResearchMaterials,
    Rifle, Shotgun, CavalrySaber, Whiskey, Knife, Lantern,
    Bullwhip, Cross)

from .unique import (
    HolyWater, EnchantedBlade, EnchantedKnife, MagicLamp, MagicPowder, SwordOfGlory
)
from .spells import (BindMonster, DreadCurse, EnchantWeapon,
                     FindGate, FleshWard, Heal, Mists, RedSign,
                     Shrivelling, Voice, Wither)
from .deputy import PatrolWagon, DeputysRevolver


def CreateCommon():
  common = []
  for item in [
      AncientTome, Automatic45, DarkCloak, Derringer18, Revolver38, Dynamite, Rifle, Shotgun,
      TommyGun, Food, ResearchMaterials, Bullwhip, Cross, CavalrySaber, Knife, Whiskey, Axe,
      Lantern,
  ]:
    common.extend([item(0), item(1)])
  return common


def CreateUnique():
  counts = {
      HolyWater: 4,
      EnchantedBlade: 2,
      EnchantedKnife: 2,
      MagicLamp: 1,
      MagicPowder: 2,
      SwordOfGlory: 1,
  }
  uniques = []
  for item, count in counts.items():
    uniques.extend([item(idx) for idx in range(count)])
  return uniques


def CreateSpells():
  counts = {
      BindMonster: 2,
      DreadCurse: 4,
      EnchantWeapon: 3,
      FindGate: 4,
      FleshWard: 4,
      # Heal: 3,  TODO: add heal to the spell pool when it does not stall upkeep in tests
      Mists: 4,
      RedSign: 2,
      Shrivelling: 5,
      Voice: 3,
      Wither: 6,
  }
  spells = []
  for item, count in counts.items():
    spells.extend([item(idx) for idx in range(count)])
  return spells


def CreateTradables():
  return [DeputysRevolver(), PatrolWagon()]


def CreateSpecials():
  return [Deputy()]
