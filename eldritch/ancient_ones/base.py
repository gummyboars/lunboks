from typing import TYPE_CHECKING

from eldritch import events, places, values
from eldritch.ancient_ones.core import AncientOne
from eldritch.gates import Gate
from eldritch.events import AncientOneAttack
from eldritch.characters import BaseCharacter
from eldritch.monsters import base as monsters
from eldritch.monsters.core import Monster

if TYPE_CHECKING:
  from eldritch.eldritch import GameState


class SquidFace(AncientOne):
  def __init__(self):
    super().__init__("Squid Face", 13, set(), -6)

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Cultist):
      return {"horrordifficulty": -2, "horrordamage": 2}.get(attribute, 0)
    if isinstance(thing, BaseCharacter) and state.game_stage != "awakened":
      return {"max_sanity": -1, "max_stamina": -1}.get(attribute, 0)
    return super().get_modifier(thing, attribute, state)

  def attack(self, state):
    attack = []
    prompt = "Lower your max sanity or stamina?"
    for char in state.characters:
      if char.gone:
        continue
      sanity = events.DrawSpecific(char, "specials", "Sanity Decrease")
      stamina = events.DrawSpecific(char, "specials", "Stamina Decrease")
      attack.append(events.BinaryChoice(char, prompt, "Sanity", "Stamina", sanity, stamina))
    attack.append(events.AddDoom())
    return AncientOneAttack(attack)

  def setup(self, state: "GameState"):
    for char in state.characters:
      char.sanity = char.max_sanity(state)
      char.stamina = char.max_stamina(state)


class YellowKing(AncientOne):
  def __init__(self):
    super().__init__("The Yellow King", 13, {"physical resistance"}, 0)
    self.luck_modifier = 1

  def awaken(self, state):
    self._combat_rating = -state.terror

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Cultist):
      return {"combatdifficulty": -3}.get(attribute, 0)
    if isinstance(thing, Gate) and attribute == "seal_clues":
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
    state.game_stage = "defeat"
    state.event_log.append(events.EventLog("The ancient one devoured the world.", False))

  def attack(self, state):
    return AncientOneAttack([])

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Maniac):
      return {"toughness": 1}.get(attribute, 0)
    return super().get_modifier(thing, attribute, state)

  def json_repr(self, state):
    data = super().json_repr(state)
    data["combat_rating"] = "-\u221e"
    return data


class Wendigo(AncientOne):
  def __init__(self):
    super().__init__("Wendigo", 11, set(), -3)
    self.fight_modifier = 1

  def get_interrupt(self, event, state):
    if isinstance(event, events.ActivateEnvironment) and event.env.environment_type == "weather":
      return events.CancelEvent(event)
    return None

  def get_trigger(self, event, state):
    losses = []
    if isinstance(event, events.Mythos):
      for char in state.characters:
        if isinstance(char.place, places.Street):
          losses.append(events.Loss(char, {"stamina": 1}))  # noqa: PERF401
      return events.Sequence(losses)
    if isinstance(event, events.Awaken):
      for char in state.characters:
        if char.gone:
          continue
        for pos in char.possessions:
          if getattr(pos, "deck", "") not in ("common", "unique", "spells", "tradables"):
            continue
          if not getattr(pos, "losable", True):
            continue
          roll = events.DiceRoll(char, 1, name=pos.handle)
          discard = events.DiscardSpecific(char, [pos])
          cond = events.Conditional(char, roll, "successes", {0: discard, 1: events.Nothing()})
          losses.extend([roll, cond])
      return events.Sequence(losses)
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
      seq = [
        events.PassFail(char, check, events.Nothing(), events.Loss(char, {"clues": 1})),
        events.PassFail(char, has_clues, events.Nothing(), events.Devoured(char)),
      ]
      checks.append(events.Sequence(seq, char))
    return AncientOneAttack(checks)

  def escalate(self, state):
    self.lore_modifier -= 1


class BlackGoat(AncientOne):
  def __init__(self):
    super().__init__("Black Goat of the Woods", 12, {"physical immunity"}, -5)
    self.sneak_modifier = 1

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, Monster) and attribute == "toughness":
      return 1
    return super().get_modifier(thing, attribute, state)

  def get_override(self, thing, attribute):
    if getattr(thing, "name", None) == "Tentacle Tree" and attribute == "endless":
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
      prompt = "Lose one monster trophy or be devoured"
      spend = events.BinarySpend(
        char, "monsters", 1, prompt, "Spend", "Be Devoured", events.Nothing(), events.Devoured(char)
      )
      checks.append(events.PassFail(char, check, events.Nothing(), spend))
    return AncientOneAttack(checks)

  def escalate(self, state):
    self.sneak_modifier -= 1


class SerpentGod(AncientOne):
  def __init__(self):
    super().__init__("Serpent God", 10, set(), -3)
    self.speed_modifier = 1

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Cultist):
      if attribute == "combatdifficulty":
        return -1
      if attribute == "combatdamage":
        return 3
    return 0

  def get_trigger(self, event, state):
    if isinstance(event, events.LostInTimeAndSpace):
      return events.AddDoom()
    if isinstance(event, events.PassCombatRound) and isinstance(
      event.combat_round.monster, monsters.Cultist
    ):
      return events.AddDoom(character=event.character)
    if isinstance(event, events.Awaken):
      per_character = []
      for char in state.characters:
        assert isinstance(char, BaseCharacter)
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
      loss = events.Loss(char, {"sanity": 1, "stamina": 1})
      checks.append(events.PassFail(char, check, events.Nothing(), loss))
    return AncientOneAttack(checks)

  def escalate(self, state):
    self.speed_modifier -= 1


class SpaceBubbles(AncientOne):
  def __init__(self):
    super().__init__("Space Bubbles", 12, {"magical immunity"}, -5)
    self.will_modifier = 1

  def get_trigger(self, event, state):
    if isinstance(event, (events.Awaken, events.AncientOneAttack)):
      to_devour = []
      for char in state.characters:
        assert isinstance(char, BaseCharacter)
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
      check = events.Check(char, "will", self.will_modifier, name=self.name)
      prompt = "Lose one gate trophy or be devoured"
      spend = events.BinarySpend(
        char, "gates", 1, prompt, "Lose", "Be Devoured", events.Nothing(), events.Devoured(char)
      )
      checks.append(events.PassFail(char, check, events.Nothing(), spend))
    return AncientOneAttack(checks)

  def escalate(self, state):
    self.will_modifier -= 1

  def get_override(self, thing, attribute):
    if isinstance(thing, monsters.Cultist) and attribute == "magical immunity":
      return True
    return None

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Cultist) and attribute == "combatdifficulty":
      return -2
    if isinstance(thing, Gate) and attribute == "difficulty":
      return 1
    return 0


def AncientOnes():
  ancients = [
    SquidFace,
    YellowKing,
    ChaosGod,
    Wendigo,
    BlackPharaoh,
    BlackGoat,
    SerpentGod,
    SpaceBubbles,
  ]
  return {ancient().name: ancient() for ancient in ancients}
