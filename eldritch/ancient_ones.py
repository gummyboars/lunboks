import abc
from typing import Optional, TYPE_CHECKING, Union

from eldritch import events, places, characters, monsters, values, mythos
from eldritch.events import AncientOneAttack
from eldritch.characters import Character

if TYPE_CHECKING:
  from eldritch.eldritch import GameState


class AncientOne(mythos.GlobalEffect, metaclass=abc.ABCMeta):
  # pylint: disable=unused-argument
  def __init__(
      self, name: str, max_doom: int, attributes: set, combat_rating: Union[int, float]
  ):
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
  def has_attribute(self, attribute, state, char: Optional[Character]):
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


class SquidFace(AncientOne):
  def __init__(self):
    super().__init__("Squid Face", 13, set(), -6)

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Cultist):
      return {"horrordifficulty": -2, "horrordamage": 2}.get(attribute, 0)
    if isinstance(thing, characters.Character):
      return {"max_sanity": -1, "max_stamina": -1}.get(attribute, 0)
    return super().get_modifier(thing, attribute, state)

  def attack(self, state):
    self.doom = min(self.doom + 1, self.max_doom)
    return AncientOneAttack([
        # TODO: Each character lowers max sanity or stamina
        events.AddDoom()
    ])

  def setup(self, state: "GameState"):
    for char in state.characters:
      char.sanity = char.max_sanity(state)
      char.stamina = char.max_stamina(state)


class YellowKing(AncientOne):
  def __init__(self):
    # TODO: change this to always have a combat rating equal to the terror level
    super().__init__("The Yellow King", 13, {"physical resistance"}, 0)
    self.luck_modifier = 1

  def awaken(self, state):
    self._combat_rating = state.terror

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Cultist):
      return {"combatdifficulty": -3}.get(attribute, 0)
    if isinstance(thing, events.GateCloseAttempt) and attribute == "seal_clues":
      return 3
    return super().get_modifier(thing, attribute, state)

  def get_override(self, thing, attribute):
    if isinstance(thing, monsters.Cultist) and attribute == "flying":
      return True
    return super().get_override(thing, attribute)

  def attack(self, state):
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      check = events.Check(char, "luck", self.luck_modifier, name=self.name)
      checks.append(
          events.PassFail(char, check, events.Nothing(), events.Loss(char, {"sanity": 2}))
      )
    return AncientOneAttack(checks)

  def escalate(self, state):
    self.luck_modifier -= 1


class ChaosGod(AncientOne):
  def __init__(self):
    super().__init__("God of Chaos", 14, set(), float("-inf"))

  def awaken(self, state):
    state.game_stage = "defeat"  # TODO: do we want to do this through an event?

  def attack(self, state):
    return AncientOneAttack([])

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Maniac):
      return {"toughness": 1}.get(attribute, 0)
    return super().get_modifier(thing, attribute, state)

  def json_repr(self, state):
    data = super().json_repr(state)
    data["combat_rating"] = "-\u221E"
    return data


class Wendigo(AncientOne):
  def __init__(self):
    super().__init__("Wendigo", 11, set(), -3)
    self.fight_modifier = 1

  def get_interrupt(self, event, state):
    # TODO: Discard weather cards
    if isinstance(event, events.ActivateEnvironment) and event.env.environment_type == "weather":
      return events.CancelEvent(event)
    return None

  def get_trigger(self, event, state):
    losses = []
    if isinstance(event, events.Mythos):
      for char in state.characters:
        if isinstance(char.place, places.Street):
          losses.append(events.Loss(char, {"stamina": 1}))
      return events.Sequence(losses)
    if isinstance(event, events.Awaken):
      # TODO: Roll a die for each item, discard on a failure
      pass
    return None

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Cultist):
      return {"toughness": 2}.get(attribute, 0)
    return super().get_modifier(thing, attribute, state)

  def attack(self, state):
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      check = events.Check(char, "fight", self.fight_modifier, name=self.name)
      checks.append(
          events.PassFail(char, check, events.Nothing(), events.Loss(char, {"stamina": 2}))
      )
    return AncientOneAttack(checks)

  def escalate(self, state):
    self.fight_modifier -= 1


class BlackPharaoh(AncientOne):
  def __init__(self):
    super().__init__("The Thousand Masks", 11, {"magical resistance"}, -4)
    self.lore_modifier = 1
    # TODO: Add masks to monster cup

  def get_override(self, thing, attribute):
    if isinstance(thing, monsters.Cultist) and attribute == "endless":
      return True
    return super().get_override(thing, attribute)

  def get_trigger(self, event, state):
    if not isinstance(event, events.Awaken):
      return None
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      has_clues = values.AttributePrerequisite(char, "clues", 1, "at least")
      checks.append(events.PassFail(char, has_clues, events.Nothing(), events.Devoured(char)))
    return events.Sequence(checks)

  def attack(self, state):
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      check = events.Check(char, "lore", self.lore_modifier, name=self.name)
      has_clues = values.AttributePrerequisite(char, "clues", 1, "at least")
      checks.append(
          events.Sequence([
              events.PassFail(char, check, events.Nothing(), events.Loss(char, {"clues": 1})),
              events.PassFail(char, has_clues, events.Nothing(), events.Devoured(char))
          ], char)

      )
    return AncientOneAttack(checks)

  def escalate(self, state):
    self.lore_modifier -= 1


class BlackGoat(AncientOne):
  def __init__(self):
    super().__init__("Black Goat of the Woods", 12, {"physical immunity"}, -5)
    self.sneak_modifier = 1

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Monster) and attribute == "toughness":
      return 1
    return super().get_modifier(thing, attribute, state)

  def get_override(self, thing, attribute):
    if thing.name == "Tentacle Tree" and attribute == "endless":
      return True
    return super().get_override(thing, attribute)

  def get_trigger(self, event, state):
    if not isinstance(event, (events.Awaken, events.AncientOneAttack)):
      return None
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      has_trophies = values.AttributePrerequisite(char, "n_monster_trophies", 1, "at least")
      checks.append(events.PassFail(char, has_trophies, events.Nothing(), events.Devoured(char)))
    return events.Sequence(checks)

  def attack(self, state):
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      check = events.Check(char, "sneak", self.sneak_modifier, name=self.name)
      checks.append(
          events.PassFail(
              char, check, events.Nothing(),
              events.BinarySpend(
                  char, "monsters", 1, "Lose one monster trophy or be devoured",
                  "Spend", "Be Devoured",
                  events.Nothing(), events.Devoured(char)
              )
          )
      )
    return AncientOneAttack(checks)

  def escalate(self, state):
    self.sneak_modifier -= 1


class SerpentGod(AncientOne):
  def __init__(self):
    super().__init__("Serpent God", 10, set(), -3)
    self.speed_modifier = 1

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Cultist):
      if attribute == "combat_difficulty":
        return -1
      if attribute == "combat_damage":
        return 3
    return 0

  def get_trigger(self, event, state):
    if isinstance(event, events.LostInTimeAndSpace):
      return events.AddDoom()
    if (
        isinstance(event, events.PassCombatRound)
        and isinstance(event.combat_round.monster, monsters.Cultist)
    ):
      return events.AddDoom(character=event.character)
    if isinstance(event, events.Awaken):
      per_character = []
      for char in state.characters:
        assert isinstance(char, characters.Character)
        if char.gone:
          continue
        if char.bless_curse == -1:
          per_character.append(events.Devoured(char))
        else:
          per_character.append(events.Curse(char))
      return events.Sequence(per_character)

    return None

  def attack(self, state):
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      check = events.Check(char, "speed", self.speed_modifier, name=self.name)
      checks.append(
          events.PassFail(
              char, check,
              events.Nothing(), events.Loss(char, {"sanity": 1, "stamina": 1})
          )
      )
    return AncientOneAttack(checks)

  def escalate(self, state):
    self.speed_modifier -= 1


class SpaceBubbles(AncientOne):
  def __init__(self):
    super().__init__("Space Bubbles", 12, {"magical immunity"}, -5)
    self.will_modifier = 1

  def get_trigger(self, event, state):
    if isinstance(event, events.Awaken):
      to_devour = []
      for char in state.characters:
        assert isinstance(char, characters.Character)
        if char.n_gate_trophies == 0:
          to_devour.append(events.Devoured(char))
      return events.Sequence(to_devour)
    if isinstance(event, events.LostInTimeAndSpace):
      return events.Devoured(event.character)
    return None

  def attack(self, state):
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      check = events.Check(char, "speed", self.will_modifier, name=self.name)
      checks.append(
          events.PassFail(
              char, check,
              events.Nothing(),
              events.BinarySpend(
                  char, "gates", 1, "Lose one gate trophy or be devoured",
                  "Lose", "Be Devoured",
                  events.Nothing(), events.Devoured(char)
              )
          )
      )
    return AncientOneAttack(checks)

  def escalate(self, state):
    self.will_modifier -= 1

  def get_override(self, thing, attribute):
    if isinstance(thing, monsters.Cultist) and attribute == "magical immunity":
      return True
    return None

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Cultist) and attribute == "combat_difficulty":
      return -2
    return 0




def AncientOnes():
  ancients = [
    SquidFace, YellowKing, ChaosGod, Wendigo, BlackPharaoh, BlackGoat, SerpentGod, SpaceBubbles
  ]
  return {ancient().name: ancient() for ancient in ancients}
