import collections
from typing import TYPE_CHECKING, Optional

from eldritch import events

if TYPE_CHECKING:
  from eldritch.eldritch import GameState


CHECK_TYPES = {"speed", "sneak", "fight", "will", "lore", "luck"}
SUB_CHECKS = {"evade": "sneak", "combat": "fight", "horror": "will", "spell": "lore"}
COMBAT_SUBTYPES = {"physical", "magical"}
MAX_TYPES = {"max_sanity", "max_stamina"}


class Asset:
  # pylint: disable=unused-argument

  JSON_ATTRS = frozenset(
    {"name", "handle", "active", "exhausted", "hands", "in_use", "max_tokens", "tokens"}
  )

  def __init__(self, name, idx=None):
    self._name = name
    self._idx = idx
    self._exhausted = False
    self.tokens = {}
    self.max_tokens = {}

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

  def get_bonus(self, check_type, attributes, owner, state: Optional["GameState"]):
    return 0

  @property
  def bonuses(self):
    bonuses = {
      check: self.get_bonus(check, None, None, None) for check in CHECK_TYPES | SUB_CHECKS.keys()
    }
    bonuses["combat"] = sum(
      self.get_bonus(check, None, None, None) for check in {"combat"} | COMBAT_SUBTYPES
    )
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

  def get_spend_amount(self, event, owner, state):
    return None

  def get_spend_event(self, owner):
    return events.Nothing()

  def get_max_token_event(self, token_type, owner):
    return events.Nothing()

  def get_zero_tokens_event(self, token_type, owner):
    return events.Nothing()

  def json_repr(self):
    return {attr: getattr(self, attr, None) for attr in self.JSON_ATTRS}

  @classmethod
  def parse_json(cls, data):
    pass  # TODO


class Card(Asset):
  DECKS = frozenset({"common", "unique", "spells", "skills", "allies", "tradables", "specials"})
  VALID_BONUS_TYPES = CHECK_TYPES | SUB_CHECKS.keys() | COMBAT_SUBTYPES | MAX_TYPES
  VALID_BONUS_TYPES |= {f"{ct}_check" for ct in CHECK_TYPES | SUB_CHECKS.keys()}

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

  def get_bonus(self, check_type, attributes, owner, state: Optional["GameState"]):
    bonus = self.passive_bonuses[check_type]
    if self.active:
      bonus += self.active_bonuses[check_type]
    return bonus
