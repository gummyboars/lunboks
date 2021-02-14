import abc
import collections

import eldritch.events as events


CHECK_TYPES = {"speed", "sneak", "fight", "will", "lore", "luck"}
SUB_CHECKS = {"evade": "sneak", "combat": "fight", "horror": "will", "spell": "lore"}


class Asset(metaclass=abc.ABCMeta):

  JSON_ATTRS = {"name", "active", "exhausted", "hands", "bonuses"}

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

  @property
  def bonuses(self):
    return {check: self.get_bonus(check) for check in CHECK_TYPES | SUB_CHECKS.keys()}

  def get_interrupt(self, event, owner, state):
    return None

  def get_usable_interrupt(self, event, owner, state):
    return None

  def get_trigger(self, event, owner, state):
    return None

  def get_usable_trigger(self, event, owner, state):
    return None

  def json_repr(self):
    return {attr: getattr(self, attr, None) for attr in self.JSON_ATTRS}

  @classmethod
  def parse_json(cls, data):
    pass  # TODO


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

  @property
  def active(self):
    return self._active

  def get_bonus(self, check_type):
    bonus = self.passive_bonuses[check_type]
    if self.active:
      bonus += self.active_bonuses[check_type]
    return bonus


# TODO: drawing things when these allies join you
def FortuneTeller():
  return Card("Fortune Teller", "allies", {}, {"luck": 2})
def TravelingSalesman():
  return Card("Traveling Salesman", "allies", {}, {"sneak": 1, "will": 1})
def PoliceDetective():
  return Card("Police Detective", "allies", {}, {"fight": 1, "lore": 1})
def Thief():
  return Card("Thief", "allies", {}, {"sneak": 2})
def BraveGuy():
  return Card("Brave Guy", "allies", {}, {"speed": 2})
def Mortician():
  return Card("Mortician", "allies", {}, {"will": 2})
def ArmWrestler():
  return Card("Arm Wrestler", "allies", {}, {})  # TODO: maximum stamina
def VisitingPainter():
  return Card("Visiting Painter", "allies", {}, {"speed": 1, "luck": 1})
def ToughGuy():
  return Card("Tough Guy", "allies", {}, {"fight": 2})
def OldProfessor():
  return Card("Old Professor", "allies", {}, {"lore": 2})
def Dog():
  return Card("Dog", "allies", {}, {})  # TODO: maximum sanity
