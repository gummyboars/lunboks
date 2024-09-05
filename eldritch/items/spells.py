import operator

from eldritch import events
from eldritch import monsters
from eldritch import places
from eldritch import values
from .base import Item

__all__ = [
  "Spell",
  "CreateSpells",
  "BindMonster",
  "DreadCurse",
  "EnchantWeapon",
  "FindGate",
  "FleshWard",
  "Heal",
  "Mists",
  "RedSign",
  "Shrivelling",
  "Voice",
  "Wither",
]


def CreateSpells():
  counts = {
    BindMonster: 2,
    DreadCurse: 4,
    EnchantWeapon: 3,
    FindGate: 4,
    FleshWard: 4,
    Heal: 3,
    Mists: 4,
    RedSign: 2,
    Shrivelling: 5,
    Voice: 3,
    Wither: 6,
  }
  spells = []
  for item, count in counts.items():
    spells.extend([item(idx) for idx in range(count)])
  return spells


class Spell(Item):
  combat = False

  def __init__(self, name, idx, active_bonuses, hands, difficulty, sanity_cost):
    super().__init__(name, idx, "spells", active_bonuses, {}, hands, None)
    self.difficulty = difficulty
    self._sanity_cost = sanity_cost
    self.in_use = False
    self.deactivatable = False
    self.choice = None
    self.check = None

  def get_difficulty(self, state):
    return self.difficulty

  def get_required_successes(self, state):  # pylint: disable=unused-argument
    return 1

  def hands_used(self):
    return self.hands if self.in_use else 0

  def get_cast_event(self, owner, state):  # pylint: disable=unused-argument
    return events.Nothing()

  def sanity_cost(self, state):
    return max(self._sanity_cost + state.get_modifier(self, "sanity_cost"), 0)


class CombatSpell(Spell):
  combat = True

  def is_combat(self, event, owner):
    if getattr(event, "character", None) != owner:
      return False
    if isinstance(event, events.CombatChoice) and not event.is_resolved():
      return True
    # May cast even before making the decision to fight or evade. TODO: this is hacky/fragile.
    if isinstance(event, events.MultipleChoice) and hasattr(event, "monster"):
      if not event.is_resolved():
        return True
    return False

  def get_usable_interrupt(self, event, owner, state):
    if not self.is_combat(event, owner):
      return None
    if self.in_use:
      if self.deactivatable:
        return events.DeactivateSpell(owner, self)
      return None
    if self.exhausted or owner.sanity < self.sanity_cost(state):
      return None
    hands_available = owner.hands_available()
    if isinstance(event, events.CombatChoice):
      hands_available -= event.hands_used()
    if hands_available < self.hands:
      return None
    return events.CastSpell(owner, self)

  def get_trigger(self, event, owner, state):
    if not self.in_use:
      return None
    if isinstance(event, (events.CombatRound, events.EvadeRound)) and event.character == owner:
      return events.MarkDeactivatable(owner, self)
    return None

  def get_cast_event(self, owner, state):
    return events.ActivateItem(owner, self)

  def activate(self):
    pass

  def deactivate(self):
    pass


def Wither(idx):
  return CombatSpell("Wither", idx, {"magical": 3}, 1, 0, 0)


def Shrivelling(idx):
  return CombatSpell("Shrivelling", idx, {"magical": 6}, 1, -1, 1)


def DreadCurse(idx):
  return CombatSpell("Dread Curse", idx, {"magical": 9}, 2, -2, 2)


class BindMonster(CombatSpell):
  def __init__(self, idx):
    super().__init__("Bind Monster", idx, {}, 2, 4, 2)
    self.combat_round = None

  def get_required_successes(self, state):
    self.combat_round = state.event_stack[-2].combat_round
    # CombatRound[-3] > CombatChoice[-2] > CastSpell[-1]
    return self.combat_round.monster.toughness(state, self.combat_round.character)

  def get_usable_interrupt(self, event, owner, state):
    if (
      isinstance(event, events.CombatChoice)
      and event.combat_round is not None
      and isinstance(event.combat_round.monster, monsters.Monster)
    ):
      return super().get_usable_interrupt(event, owner, state)
    return None

  def get_cast_event(self, owner, state):
    return events.Sequence(
      [events.DiscardSpecific(owner, [self]), events.PassCombatRound(self.combat_round)], owner
    )


class EnchantWeapon(CombatSpell):
  def __init__(self, idx):
    super().__init__("Enchant Weapon", idx, {}, 0, 0, 1)
    self.weapon = None
    self.active_change = 0
    self.passive_change = 0

  def get_usable_interrupt(self, event, owner, state):
    interrupt = super().get_usable_interrupt(event, owner, state)
    if not isinstance(interrupt, events.CastSpell):
      return interrupt

    # Instead of immediately casting the spell, ask the user to make a choice. If they have no
    # valid choices (or if they choose nothing), then don't cast the spell at all.
    spend = values.ExactSpendPrerequisite({"sanity": self.sanity_cost(state)})
    choice = events.SinglePhysicalWeaponChoice(
      owner, "Choose a physical weapon to enchant", spend=spend
    )
    return events.CastSpell(owner, self, choice=choice)

  def get_interrupt(self, event, owner, state):
    if (
      isinstance(event, (events.DiscardSpecific, events.DiscardNamed))
      and event.character == owner
      and event.discarded
      and (
        self in event.discarded
        if hasattr(event.discarded, "__contains__")
        else self == event.discarded
      )
    ):
      # TODO: Should we figure out a way to have the effect last until the end of combat?
      # The only way I can think of to lose an item during combat is the Elder Thing, which is not
      # resistant. Plus, the rules are non-specific as to whether discarding a spell makes its
      # effect go away.
      return events.DeactivateSpell(owner, self)
    return super().get_interrupt(event, owner, state)

  def activate(self):
    assert self.choice.is_resolved()
    assert len(self.choice.chosen) == 1
    self.weapon = self.choice.chosen[0]
    self.active_change = self.weapon.active_bonuses["physical"]
    self.passive_change = self.weapon.passive_bonuses["physical"]
    self.weapon.active_bonuses["physical"] -= self.active_change
    self.weapon.active_bonuses["magical"] += self.active_change
    self.weapon.passive_bonuses["physical"] -= self.passive_change
    self.weapon.passive_bonuses["magical"] += self.passive_change

  def deactivate(self):
    if self.weapon is None:
      return
    self.weapon.active_bonuses["physical"] += self.active_change
    self.weapon.active_bonuses["magical"] -= self.active_change
    self.weapon.passive_bonuses["physical"] += self.passive_change
    self.weapon.passive_bonuses["magical"] -= self.passive_change
    self.active_change = 0
    self.passive_change = 0
    self.weapon = None


class FleshWard(Spell):
  def __init__(self, idx):
    super().__init__("Flesh Ward", idx, {}, 0, -2, 1)
    self.loss = None

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.Awaken):
      return events.DiscardSpecific(owner, [self])
    return None

  def get_usable_interrupt(self, event, owner, state):
    if (
      not isinstance(event, events.GainOrLoss)
      or event.character != owner
      or "stamina" not in event.losses
      or owner.sanity < self.sanity_cost(state)
      or self.exhausted
    ):
      return None
    stam_loss = event.losses["stamina"]
    if values.Calculation(left=stam_loss, operand=operator.le, right=0).value(state):
      return None
    self.loss = event
    return events.CastSpell(owner, self)

  def get_cast_event(self, owner, state):
    return events.LossPrevention(self, self.loss, "stamina", float("inf"))


class Heal(Spell):
  def __init__(self, idx):
    super().__init__("Heal", idx, {}, 0, 1, 1)

  def get_usable_interrupt(self, event, owner, state):
    if not self.exhausted and isinstance(event, events.SliderInput) and event.character == owner:
      if not event.is_done():
        return events.CastSpell(owner, self)
    return None

  def get_cast_event(self, owner, state):
    neighbors = [char for char in state.characters if char.place == owner.place]
    gains = {
      idx: events.Gain(char, {"stamina": self.check.successes})
      for idx, char in enumerate(neighbors)
    }
    choice = events.MultipleChoice(
      owner, "Choose a character to heal", [char.name for char in neighbors]
    )
    cond = events.Conditional(owner, choice, "choice_index", gains)
    return events.Sequence([choice, cond], owner)


class Mists(Spell):
  def __init__(self, idx):
    super().__init__("Mists", idx, {}, 0, None, 0)
    self.evade = None

  def get_usable_interrupt(self, event, owner, state):
    if event.is_done() or self.exhausted or getattr(event, "character", None) != owner:
      return None
    # TODO: be able to cast Mists on an EvadeCheck
    if isinstance(event, events.EvadeRound) and not event.check:
      self.difficulty = event.monster.difficulty("evade", state, owner)
      self.evade = event
      return events.CastSpell(owner, self)
    if (
      isinstance(event, events.SpendChoice)
      and len(state.event_stack) >= 3
      and isinstance(state.event_stack[-2], events.Check)
      and isinstance(state.event_stack[-3], events.EvadeRound)
      and not state.event_stack[-3].is_done()
    ):
      self.evade = state.event_stack[-3]
      self.difficulty = self.evade.monster.difficulty("evade", state, owner)
      return events.CastSpell(owner, self)
    return None

  def get_cast_event(self, owner, state):
    return events.PassEvadeRound(self.evade)


class RedSign(CombatSpell):
  INVALID_ATTRIBUTES = frozenset({"magical immunity", "elusive", "mask", "spawn"})

  def __init__(self, idx):
    super().__init__("Red Sign", idx, {}, 1, -1, 1)

  def get_usable_interrupt(self, event, owner, state):
    interrupt = super().get_usable_interrupt(event, owner, state)
    if not isinstance(interrupt, events.CastSpell):
      return interrupt

    if not isinstance(getattr(event, "monster", None), monsters.Monster):
      return None
    attributes = sorted(event.monster.attributes(state, owner) - self.INVALID_ATTRIBUTES)
    if not attributes and event.monster.toughness(state, event.character) == 1:
      return None
    choices = attributes + ["none", "Cancel"]
    spend = values.ExactSpendPrerequisite({"sanity": self.sanity_cost(state)})
    spends = [spend] * (len(choices) - 1) + [None]
    choice = events.SpendChoice(owner, "Choose an ability to ignore", choices, spends=spends)
    return events.CastSpell(owner, self, choice=choice)

  def get_modifier(self, other, attribute):
    if self.active and attribute == "toughness":
      return -1
    return None

  def get_override(self, other, attribute):
    if self.active and self.choice is not None and attribute == self.choice.choice:
      return False
    return None


class Voice(Spell):
  def __init__(self, idx):
    super().__init__("Voice", idx, {}, 0, -1, 1)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.SliderInput) or event.character != owner or event.is_done():
      return None
    if self.exhausted or owner.sanity < self.sanity_cost(state):
      return None
    return events.CastSpell(owner, self)

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.Mythos) and self.active:
      return events.DeactivateSpell(owner, self)
    return None

  def get_cast_event(self, owner, state):
    return events.DrawSpecific(owner, "specials", "Voice Bonus")


class FindGate(Spell):
  def __init__(self, idx):
    super().__init__("Find Gate", idx, {}, 0, -1, 1)

  def movement_in_other_world(self, owner, state):
    if state.turn_phase != "movement" or state.characters[state.turn_idx] != owner:
      return False
    if not isinstance(owner.place, places.OtherWorld):  # noqa: SIM103
      return False
    return True

  def get_usable_interrupt(self, event, owner, state):
    if self.exhausted or owner.sanity < self.sanity_cost(state):
      return None
    if not self.movement_in_other_world(owner, state):
      return None
    if not isinstance(event, events.ForceMovement):
      return None
    return events.CastSpell(owner, self)

  def get_usable_trigger(self, event, owner, state):
    if self.exhausted or owner.sanity < self.sanity_cost(state):
      return None
    if not self.movement_in_other_world(owner, state):
      return None
    # Note: you can travel into another world during the movement phase by failing a combat check
    # against certain types of monsters.
    if not isinstance(event, (events.Travel, events.ForceMovement)):
      return None
    # Food for thought: should we have a SpendMixin for GateChoice so that you only get one choice?
    return events.CastSpell(owner, self)

  def get_cast_event(self, owner, state):
    if len(state.event_stack) > 1 and isinstance(state.event_stack[-2], events.ForceMovement):
      return events.Sequence(
        [events.Return(owner, owner.place.info.name), events.CancelEvent(state.event_stack[-2])],
        owner,
      )
    return events.Return(owner, owner.place.info.name)
