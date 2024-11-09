# pylint: disable=useless-import-alias

from eldritch.characters import base
from eldritch.characters import clifftown
from eldritch.characters import seaside
from eldritch.characters.core import BaseCharacter as BaseCharacter
from eldritch.characters.core import Character as Character


def CreateCharacters(expansions):
  chars = base.CreateCharacters()
  if "clifftown" in expansions:
    chars.update(clifftown.CreateCharacters())
  if "seaside" in expansions:
    chars.update(seaside.CreateCharacters())
  return chars
