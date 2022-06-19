from eldritch import events
from .base import Weapon, OneshotWeapon

__all__ = [
    "CreateUnique", "EnchantedKnife", "EnchantedBlade", "HolyWater", "MagicLamp", "MagicPowder",
    "SwordOfGlory"
]


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


def EnchantedKnife(idx):
  return Weapon("Enchanted Knife", idx, "unique", {"magical": 3}, {}, 1, 5)


def EnchantedBlade(idx):
  return Weapon("Enchanted Blade", idx, "unique", {"magical": 4}, {}, 1, 6)


def HolyWater(idx):
  return OneshotWeapon("Holy Water", idx, "unique", {"magical": 6}, {}, 2, 4)


def MagicLamp(idx):
  return Weapon("Magic Lamp", idx, "unique", {"magical": 5}, {}, 2, 7)


class MagicPowder(Weapon):
  def __init__(self, idx):
    super().__init__("Magic Powder", idx, "unique", {"magical": 9}, {}, 2, 6)

  def get_trigger(self, event, owner, state):
    if not isinstance(event, events.Check) or event.check_type != "combat":
      return None
    if event.character != owner or not self.active:
      return None
    return events.Sequence([
        events.DiscardSpecific(event.character, [self]),
        events.Loss(event.character, {"sanity": 1}),
    ], event.character
    )


def SwordOfGlory(idx):
  return Weapon("Sword of Glory", idx, "unique", {"magical": 6}, {}, 2, 8)
