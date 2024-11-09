from eldritch.abilities import base
from eldritch.abilities import clifftown
from eldritch.abilities import seaside


def CreateAbilities(expansions):
  abilities = base.CreateAbilities()
  if "clifftown" in expansions:
    abilities.update(clifftown.CreateAbilities())
  if "seaside" in expansions:
    abilities.update(seaside.CreateAbilities())
  return abilities
