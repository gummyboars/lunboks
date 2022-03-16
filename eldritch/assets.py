import abc
import collections

from eldritch import events


CHECK_TYPES = {"speed", "sneak", "fight", "will", "lore", "luck"}
SUB_CHECKS = {"evade": "sneak", "combat": "fight", "horror": "will", "spell": "lore"}
COMBAT_SUBTYPES = {"physical", "magical"}


class Asset(metaclass=abc.ABCMeta):

  # pylint: disable=unused-argument

  JSON_ATTRS = {"name", "handle", "active", "exhausted", "hands", "bonuses"}

  def __init__(self, name, idx=None):
    self._name = name
    self._idx = idx
    self._exhausted = False

  @property
  def name(self):
    return self._name

  @property
  def handle(self):
    if self._idx is None:
      return self._name
    return f"{self._name}{self._idx}"

  @property
  def exhausted(self):
    return self._exhausted

  def get_bonus(self, check_type, attributes):
    return 0

  @property
  def bonuses(self):
    bonuses = {check: self.get_bonus(check, None) for check in CHECK_TYPES | SUB_CHECKS.keys()}
    bonuses["combat"] = sum([
        self.get_bonus(check, None) for check in {"combat", "physical", "magical"}])
    return bonuses

  def get_modifier(self, other, attribute):
    return None

  def get_override(self, other, attribute):
    return None

  def get_interrupt(self, event, owner, state):
    return None

  def get_usable_interrupt(self, event, owner, state):
    return None

  def get_trigger(self, event, owner, state):
    return None

  def get_usable_trigger(self, event, owner, state):
    return None

  def get_spend_event(self, owner):
    return events.Nothing()

  def json_repr(self):
    return {attr: getattr(self, attr, None) for attr in self.JSON_ATTRS}

  @classmethod
  def parse_json(cls, data):
    pass  # TODO


class Card(Asset):

  DECKS = {"common", "unique", "spells", "skills", "allies", "tradables", "specials"}
  VALID_BONUS_TYPES = CHECK_TYPES | SUB_CHECKS.keys() | COMBAT_SUBTYPES

  def __init__(self, name, idx, deck, active_bonuses, passive_bonuses):
    assert deck in self.DECKS
    assert not (active_bonuses.keys() | passive_bonuses.keys()) - self.VALID_BONUS_TYPES
    super().__init__(name, idx)
    self.deck = deck
    self.active_bonuses = collections.defaultdict(int)
    self.active_bonuses.update(active_bonuses)
    self.passive_bonuses = collections.defaultdict(int)
    self.passive_bonuses.update(passive_bonuses)
    self._active = False
    self.losable = True

  @property
  def active(self):
    return self._active

  def get_bonus(self, check_type, attributes):
    bonus = self.passive_bonuses[check_type]
    if self.active:
      bonus += self.active_bonuses[check_type]
    return bonus


# TODO: drawing things when these allies join you
def FortuneTeller():
  return Card("Fortune Teller", None, "allies", {}, {"luck": 2})


def TravelingSalesman():
  return Card("Traveling Salesman", None, "allies", {}, {"sneak": 1, "will": 1})


def PoliceDetective():
  return Card("Police Detective", None, "allies", {}, {"fight": 1, "lore": 1})


def Thief():
  return Card("Thief", None, "allies", {}, {"sneak": 2})


def ArmWrestler():
  return Card("Arm Wrestler", None, "allies", {}, {})  # TODO: maximum stamina


def Dog():
  return Card("Dog", None, "allies", {}, {})  # TODO: maximum sanity


class BraveGuy(Card):

  def __init__(self):
    super().__init__("Brave Guy", None, "allies", {}, {"speed": 2})

  def get_override(self, other, attribute):
    if attribute == "nightmarish":
      return False
    return None


class PoliceInspector(Card):

  def __init__(self):
    super().__init__("Police Inspector", None, "allies", {}, {"will": 2})

  def get_override(self, other, attribute):
    if attribute == "endless":
      return False
    return None


class VisitingPainter(Card):

  def __init__(self):
    super().__init__("Visiting Painter", None, "allies", {}, {"speed": 1, "luck": 1})

  def get_override(self, other, attribute):
    if attribute == "physical resistance":
      return False
    return None


class OldProfessor(Card):

  def __init__(self):
    super().__init__("Old Professor", None, "allies", {}, {"lore": 2})

  def get_override(self, other, attribute):
    if attribute == "magical resistance":
      return False
    return None


class ToughGuy(Card):

  def __init__(self):
    super().__init__("Tough Guy", None, "allies", {}, {"fight": 2})

  def get_override(self, other, attribute):
    if attribute == "overwhelming":
      return False
    return None


class Deputy(Card):

  def __init__(self):
    super().__init__("Deputy", None, "specials", {}, {})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.UpkeepActions) and event.character == owner:
      return events.Gain(owner, {"dollars": 1})
    if isinstance(event, events.KeepDrawn) and self.name in event.kept:
      return events.Sequence([
          events.DrawSpecific(owner, "tradables", "Deputy's Revolver"),
          events.DrawSpecific(owner, "tradables", "Patrol Wagon"),
      ], owner)
    return None


def CreateAllies():
  return [
      ally() for ally in [
          FortuneTeller, TravelingSalesman, PoliceDetective, Thief, BraveGuy,
          PoliceInspector, ArmWrestler, VisitingPainter, ToughGuy, OldProfessor, Dog,
      ]
  ]
