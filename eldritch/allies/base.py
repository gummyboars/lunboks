from eldritch import events
from eldritch.cards import Card, MAX_TYPES


class FortuneTeller(Card):
  def __init__(self):
    super().__init__("Fortune Teller", None, "allies", {}, {"luck": 2})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and self.handle in event.kept:
      return events.Gain(owner, {"clues": 2})
    return None


class TravelingSalesman(Card):
  def __init__(self):
    super().__init__("Traveling Salesman", None, "allies", {}, {"sneak": 1, "will": 1})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and self.handle in event.kept:
      return events.Draw(owner, "common", 1)
    return None


class PoliceDetective(Card):
  def __init__(self):
    super().__init__("Police Detective", None, "allies", {}, {"fight": 1, "lore": 1})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and self.handle in event.kept:
      return events.Draw(owner, "spells", 1)
    return None


class Thief(Card):
  def __init__(self):
    super().__init__("Thief", None, "allies", {}, {"sneak": 2})

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and self.handle in event.kept:
      return events.Draw(owner, "unique", 1)
    return None


class StatIncreaser(Card):
  def __init__(self, name, stat):
    assert stat in MAX_TYPES
    super().__init__(name, None, "allies", {}, {stat: 1})
    self.stat = stat[4:]

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and self.handle in event.kept:
      return events.Gain(owner, {self.stat: 1})
    if isinstance(event, events.DiscardNamed) and event.discarded == self:
      return events.CapStatsAtMax(owner)
    if isinstance(event, events.DiscardSpecific) and self in event.discarded:
      return events.CapStatsAtMax(owner)
    return None

  def get_usable_interrupt(self, event, owner, state):
    if not self.is_usable(event, owner, state):
      return None
    restore = events.Gain(owner, {self.stat: float("inf")})
    discard = events.DiscardSpecific(owner, [self])
    return events.Sequence([restore, discard], owner)

  def is_usable(self, event, owner, state):
    """Determines whether this is usable.

    when can you discard this?
    - when adjusting sliders (maybe so that you can use some spell during upkeep)
    --- interrupt SliderInput (if not done and prev is Upkeep)
    - during city movement
    --- interrupt CityMovement (if not done)
    - between fighting different monsters - or any fight/evade/combat choice
    --- interrupt a not-done MonsterChoice
    --- interrupt a not-done FightOrEvadeChoice
    - other world movement
    --- interrupt ForceMovement (if not done and prev is Movement)
    - before returning from another world
    --- interrupt GateChoice (if not done and chain is Return <- Movement)
    - before you draw a card:
    --- interrupt DrawEncounter (if chain is Encounter <- EncounterPhase)
    --- interrupt GateEncounter (if chain is OtherWorldPhase)
    --- interrupt DrawMythosCard (if prev event is Mythos)
    - before your encounter (other)
    --- interrupt Travel event (if prev is EncounterPhase)
    --- interrupt CardSpendChoice (if chain is Sequence <- EncounterPhase)
    --- interrupt MultipleChoice (if chain is GateCloseAttempt <- EncounterPhase)
    """
    prev_event = None
    if len(state.event_stack) > 1:
      prev_event = state.event_stack[-2]
    if event.is_done():
      return False
    if isinstance(event, events.DrawMythosCard) and isinstance(prev_event, events.Mythos):
      return True
    if getattr(event, "character", None) != owner:
      return False
    choice_interrupts = (events.SliderInput, events.CityMovement)
    if isinstance(event, choice_interrupts):
      return True
    fight_interrupts = (events.MonsterChoice, events.FightOrEvadeChoice, events.CombatChoice)
    if isinstance(event, fight_interrupts) and state.turn_phase == "movement":
      return True
    if isinstance(event, events.ForceMovement) and isinstance(prev_event, events.Movement):
      return True
    if isinstance(event, events.Travel) and isinstance(prev_event, events.EncounterPhase):
      return True
    if isinstance(event, events.GateEncounter) and isinstance(prev_event, events.OtherWorldPhase):
      if not event.cards and not event.draw:
        return True
    if len(state.event_stack) <= 2:
      return False
    prev_prev = state.event_stack[-3]
    if isinstance(event, events.GateChoice):
      if isinstance(prev_event, events.Return) and isinstance(prev_prev, events.Movement):
        return True
    if isinstance(event, events.DrawEncounter):
      if isinstance(prev_event, events.Encounter) and isinstance(prev_prev, events.EncounterPhase):
        return True
    if isinstance(event, events.CardSpendChoice):
      if isinstance(prev_event, events.Sequence) and isinstance(prev_prev, events.EncounterPhase):
        return True
    if isinstance(event, events.MultipleChoice) and isinstance(prev_event, events.GateCloseAttempt):
      if isinstance(prev_prev, events.EncounterPhase):
        return True
    return False


class ArmWrestler(StatIncreaser):
  def __init__(self):
    super().__init__("Arm Wrestler", "max_stamina")


class Dog(StatIncreaser):
  def __init__(self):
    super().__init__("Dog", "max_sanity")


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


def CreateAllies():
  return [
    ally()
    for ally in [
      FortuneTeller,
      TravelingSalesman,
      PoliceDetective,
      Thief,
      BraveGuy,
      PoliceInspector,
      ArmWrestler,
      VisitingPainter,
      ToughGuy,
      OldProfessor,
      Dog,
    ]
  ]
