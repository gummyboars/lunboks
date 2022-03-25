import abc

from eldritch import events, places, characters, monsters, values, mythos
from eldritch.events import AncientOneAttack, AncientOneAwaken


class AncientOne(mythos.GlobalEffect, metaclass=abc.ABCMeta):
  # pylint: disable=unused-argument
  def __init__(self, name, max_doom, attributes, combat_rating):
    self.name = name
    self.max_doom = max_doom
    self.doom = 0
    self.combat_rating = combat_rating
    self.attributes = attributes

  def awaken(self, state):
    return AncientOneAwaken([])

  @abc.abstractmethod
  def attack(self, state):
    raise NotImplementedError

  def json_repr(self):
    return {
        "name": self.name,
        "doom": self.doom,
        "max_doom": self.max_doom,
    }


class DummyAncient(AncientOne):
  def __init__(self):
    super().__init__("Dummy", 10, set(), 0)

  def attack(self, state):
    return AncientOneAttack([])


class SquidFace(AncientOne):
  def __init__(self):
    super().__init__("Squid Face", 13, set(), -6)

  def get_modifier(self, thing, attribute):
    if isinstance(thing, monsters.Cultist):
      return {"horrordifficulty": -2, "horrordamage": 2}.get(attribute, 0)
    if isinstance(thing, characters.Character):
      return {"max_sanity": -1, "max_stamina": -1}.get(attribute, 0)
    return super().get_modifier(thing, attribute)

  def attack(self, state):
    self.doom = min(self.doom + 1, self.max_doom)
    return AncientOneAttack([
        # TODO: Each character lowers max sanity or stamina
        events.AddDoom()
    ])


class YellowKing(AncientOne):
  def __init__(self):
    super().__init__("The Yellow King", 13, {"physical resistance"}, None)
    self.luck_modifier = 1

  def awaken(self, state):
    self.combat_rating = state.terror
    return AncientOneAwaken([])

  def get_modifier(self, thing, attribute):
    if isinstance(thing, monsters.Cultist):
      return {"combatdifficulty": -3}.get(attribute, 0)
    if isinstance(thing, events.GateCloseAttempt) and attribute == "seal_clues":
      return 3
    return super().get_modifier(thing, attribute)

  def get_override(self, thing, attribute):
    if isinstance(thing, monsters.Cultist) and attribute == "flying":
      return True
    return super().get_override(thing, attribute)

  def attack(self, state):
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      check = events.Check(char, "luck", self.luck_modifier)
      checks.append(
          events.PassFail(char, check, events.Nothing(), events.Loss(char, {"sanity": 2}))
      )
    self.luck_modifier -= 1  # TODO: make this an Event to allow it to be canceled
    return AncientOneAttack(checks)


class ChaosGod(AncientOne):
  def __init__(self):
    super().__init__("God of Chaos", 14, set(), float("-inf"))

  def awaken(self, state):
    state.game_stage = "defeat"
    return AncientOneAwaken([])

  def attack(self, state):
    return AncientOneAttack([])

  def get_modifier(self, thing, attribute):
    if isinstance(thing, monsters.Maniac):
      return {"toughness": 1}.get(attribute, 0)
    return super().get_modifier(thing, attribute)


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
    return None

  def get_modifier(self, thing, attribute):
    if isinstance(thing, monsters.Cultist):
      return {"toughness": 2}.get(attribute, 0)
    return super().get_modifier(thing, attribute)

  def awaken(self, state):
    # TODO: Roll a die for each item, discard on a failure
    return AncientOneAwaken([])

  def attack(self, state):
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      check = events.Check(char, "fight", self.fight_modifier)
      checks.append(
          events.PassFail(char, check, events.Nothing(), events.Loss(char, {"stamina": 2}))
      )
    self.fight_modifier -= 1  # TODO: make this an Event to allow it to be canceled
    return AncientOneAttack(checks)


class BlackPharaoh(AncientOne):
  def __init__(self):
    super().__init__("The Thousand Masks", 11, {"magical resistance"}, -4)
    self.lore_modifier = 1
    # TODO: Add masks to monster cup

  def get_override(self, thing, attribute):
    if isinstance(thing, monsters.Cultist) and attribute == "endless":
      return True
    return super().get_override(thing, attribute)

  def awaken(self, state):
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      has_clues = values.AttributePrerequisite(char, "clues", 1, "at least")
      checks.append(
          events.PassFail(
              char, has_clues, events.Nothing(), events.Nothing()
          )  # TODO: Devoured if no clue tokens
      )
    return AncientOneAwaken(checks)

  def attack(self, state):
    checks = []
    for char in state.characters:
      if char.gone:
        continue
      check = events.Check(char, "lore", self.lore_modifier)
      has_clues = values.AttributePrerequisite(char, "clues", "at least", 1)
      checks.append(
          events.Sequence([
              events.PassFail(char, check, events.Nothing(), events.Loss(char, {"clues": 1})),
              events.PassFail(char, has_clues, events.Nothing(), events.Nothing())
              # TODO: Devoured if no clue tokens
          ], char)

      )
    self.lore_modifier -= 1  # TODO: make this an Event to allow it to be canceled
    return AncientOneAttack(checks)


def AncientOnes():
  ancients = [SquidFace, YellowKing, ChaosGod, Wendigo, BlackPharaoh]
  return {ancient().name: ancient() for ancient in ancients}
