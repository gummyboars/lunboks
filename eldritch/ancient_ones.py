import abc

from eldritch import events, places
from eldritch.monsters import Monster


class AncientOne(metclass=abc.ABCMeta):
  def __init__(self):
    self.doom = 0
    self.combat_difficulty = 0
    self.attributes = []

  def get_interrupts(self, owner, state):
    return []

  def get_modifier(self, thing, attribute):
    return 0

  def awaken(self, state):
    return []

  @abc.abstractmethod
  def attack(self, state):
    raise NotImplementedError


class SquidFace(AncientOne):
  def __init__(self):
    super(AncientOne, self).__init__()
    self.name = "SquidFace"
    self.max_doom = 13
    self.combat_difficulty = -6

  def get_modifier(self, thing, attribute):
    if isinstance(thing, Monster) and thing.name == "Cultist":
      return {'horror': -2, 'horror_damage': 2}.get(attribute, 0)
    if isinstance(thing, characters.Character):
      return {'maximum_sanity': -1, 'maximum_stamina': -1}
    return 0

  def attack(self, state):
    self.doom = min(self.doom + 1, self.max_doom)
    # TODO: Each character lowers max sanity or stamina


class YellowKing(AncientOne):
  def __init__(self):
    super(AncientOne, self).__init__()
    self.name = "The Yellow King"
    self.attributes = ['physical resistance']
    self.combat_difficulty = None
    self.luck_modifier = 1

  def awaken(self, state):
    self.combat_difficulty = state.terror

  def get_modifier(self, thing, attribute):
    if isinstance(thing, Monster) and thing.name == "Cultist":
      return {'combat_difficulty': -2, 'movement': 'flying'}.get(attribute, 0)
    if isinstance(thing, events.GateCloseAttempt):
      return 3
    return 0

  def attack(self, state):
    for char in state.characters:
      check = events.Check(char, "luck", self.luck_modifier)
      state.event_stack.append(
        events.PassFail(char, check, events.Nothing(), events.Loss(char, {'sanity': 2}))
      )
    self.luck_modifier -= 1


class ChaosGod(AncientOne):
  def __init__(self):
    super(AncientOne, self).__init__()
    self.name = "God of Chaos"
    self.max_doom = 14

  def awaken(self, state):
    state.game_stage = "defeat"

  def get_modifier(self, thing, attribute):
    if isinstance(thing, Monster) and thing.name == "Maniac":
      return {'toughness': 1}.get(attribute, 0)

class Wendigo(AncientOne):
  def __init__(self):
    super(AncientOne, self).__init__()
    self.name = "Wendigo"
    self.max_doom = 11
    self.combat_difficulty = -3
    self.fight_modifier = 1

  def get_interrupts(self, owner, state):
    if isinstance(owner, events.EndMovement) and isinstance(owner.character.place, places.StreetPlace):
      return [events.Loss(owner.character, {'stamina': 1})]
    #TODO: Discard weather cards
    return []

  def get_modifier(self, thing, attribute):
    if isinstance(thing, Monster) and thing.name == "Cultist":
      return {'toughness': 2}.get(attribute, 0)

  def awaken(self, state):
    #TODO: Roll a die for each item, discard on a failure
    pass

  def attack(self, state):
    for char in state.characters:
      check = events.Check(char, "fight", self.fight_modifier)
      state.event_stack.append(
          events.PassFail(char, check, events.Nothing(), events.Loss(char, {'stamina': 2}))
      )
    self.fight_modifier -= 1

class BlackPharaoh(AncientOne):
  def __init__(self):
    super(AncientOne, self).__init__()
    self.max_doom = 11
    self.attributes = ['magical resistance']
    self.combat_difficulty = -4
    self.lore_modifier = 1

  def get_modifier(self, thing, attribute):
    if isinstance(thing, Monster) and thing.name == "Cultist":
     return {'attribute': 'endless'}.get(attribute, 0)
    return 0

  def awaken(self, state):
    for char in state.characters:
      if char.clues == 0:
        pass
        # state.event_stack.append(events.Devoured(char))

  def attack(self, state):
    for char in state.characters:
      check = events.Check(char, "lore", self.lore_modifier)
      has_clues = events.AttributePrerequisite(char, "clues", "at least", 1)
      state.event_stack.append(
          events.Sequence([
            events.PassFail(char, check, events.Nothing(), events.Loss(char, {'stamina': 2})),
            events.PassFail(char, has_clues, events.Nothing(), events.Nothing())
            #TODO: Devoured if no clue tokens
            ], char)

      )
    self.lore_modifier -= 1
