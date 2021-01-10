import abc
import collections

import eldritch.events as events


CHECK_TYPES = {"speed", "sneak", "fight", "will", "lore", "luck"}
SUB_CHECKS = {"evade": "sneak", "combat": "fight", "horror": "will", "spell": "lore"}


class Asset(metaclass=abc.ABCMeta):

  def __init__(self, name):
    self._name = name
    self._exhausted = False

  @property
  def name(self):
    return self._name

  @property
  def exhausted(self):
    return self._exhausted

  def get_bonus(self, check_type):
    return 0

  def get_interrupt(self, event, owner, state):
    return None

  def get_usable_interrupt(self, event, owner, state):
    return None

  def get_trigger(self, event, owner, state):
    return None

  def get_usable_trigger(self, event, owner, state):
    return None


class Card(Asset):

  DECKS = {"common", "unique", "spells", "skills", "allies"}

  def __init__(self, name, deck, active_bonuses, passive_bonuses):
    assert deck in self.DECKS
    assert not ((active_bonuses.keys() | passive_bonuses.keys()) - CHECK_TYPES - SUB_CHECKS.keys())
    super(Card, self).__init__(name)
    self.deck = deck
    self.active_bonuses = collections.defaultdict(int)
    self.active_bonuses.update(active_bonuses)
    self.passive_bonuses = collections.defaultdict(int)
    self.passive_bonuses.update(passive_bonuses)
    self._active = False

  def json_repr(self):
    output = {}
    output.update(self.__dict__)
    return output

  @classmethod
  def parse_json(cls, data):
    pass  # TODO

  @property
  def active(self):
    return self._active

  def get_bonus(self, check_type):
    if self.active:
      return self.active_bonuses[check_type] + self.passive_bonuses[check_type]
    return self.passive_bonuses[check_type]
