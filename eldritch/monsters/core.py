from eldritch import events


class MonsterCup:
  def __init__(self):
    self.name = "cup"

  def json_repr(self):
    return self.name


class Monster:
  MOVEMENTS = ("unique", "flying", "stalker", "aquatic", "fast", "stationary", "normal")
  DIMENSIONS = frozenset(
    {"circle", "triangle", "moon", "hex", "square", "diamond", "star", "slash", "plus"}
  )
  DIFFICULTIES = frozenset({"horror", "combat", "evade"})
  DAMAGES = frozenset({"horror", "combat"})
  ATTRIBUTES = frozenset(
    {
      "magical resistance",
      "magical immunity",
      "physical resistance",
      "physical immunity",
      "undead",
      "ambush",
      "elusive",
      "endless",
      "mask",
      "spawn",
    }
  )
  ALL_ATTRIBUTES = ATTRIBUTES | {"nightmarish", "overwhelming"}

  def __init__(
    self, name, movement, dimension, ratings, damages, toughness, attributes=None, bypass=None
  ):
    if attributes is None:
      attributes = set()
    if bypass is None:
      bypass = {}
    assert movement in self.MOVEMENTS
    assert dimension in self.DIMENSIONS
    assert not {"evade", "combat"} - ratings.keys()
    assert not ratings.keys() - self.DIFFICULTIES
    assert not damages.keys() - self.DAMAGES
    assert not damages.keys() - ratings.keys()
    assert not attributes - self.ATTRIBUTES
    assert not bypass.keys() - damages.keys()
    assert len(attributes & {"magical resistance", "magical immunity"}) < 2
    assert len(attributes & {"physical resistance", "physical immunity"}) < 2
    self.name = name
    self._movement = movement
    self.dimension = dimension
    self.difficulties = ratings
    self.damages = damages
    self._toughness = toughness
    self._attributes = attributes
    self.bypass = bypass
    if "combat" in bypass:
      self._attributes.add("overwhelming")
    if "horror" in bypass:
      self._attributes.add("nightmarish")
    self.idx = None
    self.place = None

  def __repr__(self):
    if self.place is None:
      return f"<Monster: {self.name} {id(self)} at nowhere>"
    return f"<Monster: {self.name} {id(self)} at {self.place}>"

  @property
  def handle(self):
    if self.idx is None:
      return self.name
    return f"{self.name}{self.idx}"

  @property
  def visual_name(self):
    return self.handle

  def json_repr(self, state, char):
    return {
      "name": self.name,
      "handle": self.handle,
      "movement": self.movement(state),
      "dimension": self.dimension,
      "idx": self.idx,
      "place": getattr(self.place, "name", None),
      "horror_difficulty": self.difficulty("horror", state, char),
      "horror_damage": self.damage("horror", state, char),
      "horror_bypass": self.bypass_damage("horror", state),
      "combat_difficulty": self.difficulty("combat", state, char),
      "combat_damage": self.damage("combat", state, char),
      "combat_bypass": self.bypass_damage("combat", state),
      "toughness": self.toughness(state, char),
      "attributes": sorted(self.attributes(state, char)),
    }

  def difficulty(self, check_type, state, char):
    state_modifier = state.get_modifier(self, check_type + "difficulty") or 0
    char_modifier = char.get_modifier(self, check_type + "difficulty") or 0 if char else 0
    if state_modifier or char_modifier:
      return (self.difficulties.get(check_type) or 0) + state_modifier + char_modifier
    return self.difficulties.get(check_type)

  def damage(self, check_type, state, char):
    state_modifier = state.get_modifier(self, check_type + "damage") or 0
    char_modifier = char.get_modifier(self, check_type + "damage") or 0 if char else 0
    if state_modifier or char_modifier:
      return max((self.damages.get(check_type) or 0) + state_modifier + char_modifier, 0)
    return self.damages.get(check_type)

  def bypass_damage(self, check_type, state):  # pylint: disable=unused-argument
    return self.bypass.get(check_type)

  def toughness(self, state, char):
    state_modifier = state.get_modifier(self, "toughness")
    char_modifier = char.get_modifier(self, "toughness") if char else 0
    return max(self._toughness + (state_modifier or 0) + (char_modifier or 0), 1)

  def attributes(self, state, char):
    attrs = set()
    for attr in self.ALL_ATTRIBUTES:
      if self.has_attribute(attr, state, char):
        attrs.add(attr)
    return attrs

  def has_attribute(self, attribute, state, char):
    state_override = state.get_override(self, attribute)
    char_override = char.get_override(self, attribute) if char else None
    # Prefer specific overrides (at the item level) over general ones (environment, ancient one).
    if char_override is not None:
      return char_override
    if state_override is not None:
      return state_override
    return attribute in self._attributes or attribute == self._movement

  def movement(self, state):
    for movement in self.MOVEMENTS:
      if self.has_attribute(movement, state, None):
        return movement
    return "normal"

  def get_interrupt(self, event, state):
    endless = self.has_attribute("endless", state, event.character)
    if isinstance(event, events.TakeTrophy) and endless:
      # TODO: Should this be coded into TakeTrophy instead?
      cup = events.ReturnToCup(handles=[self.handle], character=event.character)
      return events.Sequence([events.CancelEvent(event), cup], event.character)
    return None

  def get_trigger(self, event, state):  # pylint: disable=unused-argument
    return None


class EventMonster(Monster):
  """A pseudo-monster used for events like Bank3, Hospital2, and Graveyard3."""

  def __init__(self, name, rating, pass_event, fail_event, toughness=1, attributes=None):
    super().__init__(
      name, "normal", "moon", {"evade": 0, **rating}, {"combat": 0}, toughness, attributes or set()
    )
    self.pass_event = pass_event
    self.fail_event = fail_event

  @property
  def visual_name(self):
    return None

  def get_interrupt(self, event, state):
    if isinstance(event, events.TakeTrophy):
      return events.CancelEvent(event)
    return super().get_interrupt(event, state)

  def get_trigger(self, event, state):
    if isinstance(event, events.PassCombatRound):
      return self.pass_event

    if (
      (not isinstance(event, events.CombatRound))
      or event.check is None
      or not event.check.is_done()
    ):
      return None

    if not event.check.success:
      return self.fail_event
    return None
