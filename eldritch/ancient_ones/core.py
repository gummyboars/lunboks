import abc
from typing import Optional, Union

from eldritch.monsters import core as monsters
from eldritch.mythos.core import GlobalEffect
from eldritch.events import AncientOneAttack
from eldritch.characters import BaseCharacter


class AncientOne(GlobalEffect, metaclass=abc.ABCMeta):
  # pylint: disable=unused-argument
  def __init__(self, name: str, max_doom: int, attributes: set, combat_rating: Union[int, float]):
    self.name = name
    self.max_doom = max_doom
    self.doom = 0
    self.health = None
    self._combat_rating = combat_rating
    self._attributes = attributes

  def awaken(self, state):
    pass

  @abc.abstractmethod
  def attack(self, state):
    raise NotImplementedError

  def escalate(self, state):
    pass

  def setup(self, state):
    pass

  # TODO: dedup with monster
  def attributes(self, state, char):
    attrs = set()
    for attr in monsters.Monster.ALL_ATTRIBUTES:
      if self.has_attribute(attr, state, char):
        attrs.add(attr)
    return attrs

  # TODO: dedup with monster
  def has_attribute(self, attribute, state, char: Optional[BaseCharacter]):
    state_override = state.get_override(self, attribute)
    char_override = char.get_override(self, attribute) if char else None
    # Prefer specific overrides (at the item level) over general ones (environment, ancient one).
    if char_override is not None:
      return char_override
    if state_override is not None:
      return state_override
    return attribute in self._attributes

  def combat_rating(self, state, char):
    state_modifier = state.get_modifier(self, "combatdifficulty") or 0
    char_modifier = (char.get_modifier(self, "combatdifficulty") or 0) if char is not None else 0
    return self._combat_rating + state_modifier + char_modifier

  def json_repr(self, state):
    return {
      "name": self.name,
      "doom": self.doom,
      "max_doom": self.max_doom,
      "health": self.health,
      "attributes": sorted(self.attributes(state, None)),
      "combat_rating": self.combat_rating(state, None),
    }


class DummyAncient(AncientOne):
  def __init__(self):
    super().__init__("Dummy", 10, set(), 0)

  def attack(self, state):
    return AncientOneAttack([])
