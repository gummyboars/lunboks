from eldritch import cards as assets
from eldritch import events
from eldritch import values


class FluxStabilizer(assets.Asset):
  def __init__(self):
    super().__init__("Flux Stabilizer")


class GuardianAngel(assets.Asset):
  def __init__(self):
    super().__init__("Guardian Angel")

  def get_interrupt(self, event, owner, state):
    if not isinstance(event, events.LostInTimeAndSpace) or event.character != owner:
      return None

    dest = events.ForceMovement(owner, "Church")

    if len(state.event_stack) > 1:
      parent = state.event_stack[-2]
      if isinstance(parent, events.InsaneOrUnconscious) and parent.attribute == "stamina":
        dest = events.ForceMovement(owner, "Hospital")
      elif isinstance(parent, events.InsaneOrUnconscious) and parent.attribute == "sanity":
        dest = events.ForceMovement(owner, "Asylum")

    return events.Sequence([events.CancelEvent(event), dest], owner)


class ExtraDraw(assets.Asset):
  def __init__(self, name, draw_type, deck, attribute="draw_count"):
    super().__init__(name)
    self.draw_type = draw_type
    # Special note: do not name this attribute "deck". Otherwise, this ability will be returned
    # to that deck when the investigator is devoured. Also, other bad things will happen.
    self.deck_name = deck
    self.attribute = attribute

  def get_interrupt(self, event, owner, state):
    if not isinstance(event, self.draw_type):
      return None
    if event.character != owner:
      return None
    if self.deck_name is not None and event.deck != self.deck_name:
      return None
    return events.ChangeCount(event, self.attribute, 1)


def Studious():
  return ExtraDraw("Studious", events.DrawItems, "skills")


def ShrewdDealer():
  return ExtraDraw("Shrewd Dealer", events.DrawItems, "common")


def HometownAdvantage():
  return ExtraDraw("Hometown Advantage", events.DrawEncounter, None, "count")


def MagicalGift():
  return ExtraDraw("Magical Gift", events.DrawItems, "spells")


def PsychicSensitivity():
  return ExtraDraw("Psychic Sensitivity", events.GateEncounter, None)


def Archaeology():
  return ExtraDraw("Archaeology", events.DrawItems, "unique")


class Prevention(assets.Asset):
  def __init__(self, name, attribute):
    super().__init__(name)
    self.attribute = attribute

  def get_interrupt(self, event, owner, state):
    if not isinstance(event, events.GainOrLoss) or owner != event.character:
      return None
    if isinstance(event.losses.get(self.attribute), values.Value):
      if event.losses[self.attribute].value(state) < 1:
        return None
    elif event.losses.get(self.attribute, 0) < 1:
      return None
    return events.LossPrevention(self, event, self.attribute, 1)


def StrongMind():
  return Prevention("Strong Mind", "sanity")


def StrongBody():
  return Prevention("Strong Body", "stamina")


class TrustFund(assets.Asset):
  def __init__(self):
    super().__init__("Trust Fund")

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.RefreshAssets) and event.character == owner:
      return events.Gain(owner, {"dollars": 1})
    return None


class Hunches(assets.Asset):
  def __init__(self):
    super().__init__("Hunches")

  def get_interrupt(self, event, owner, state):
    if not isinstance(event, events.BonusDiceRoll) or event.character != owner:
      return None
    if len(state.event_stack) < 2 or not isinstance(state.event_stack[-2], events.Check):
      return None
    return events.AddExtraDie(owner, event)


class Research(assets.Asset):
  def __init__(self):
    super().__init__("Research")

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.SpendChoice) or event.is_done() or self.exhausted:
      return None
    if len(state.event_stack) < 2 or not isinstance(state.event_stack[-2], events.Check):
      return None
    bad_dice = values.UnsuccessfulDice(state.event_stack[-2])
    reroll = events.RerollSpecific(state.event_stack[-2].character, state.event_stack[-2], bad_dice)
    return events.Sequence([events.ExhaustAsset(owner, self), reroll], owner)


class Scrounge(assets.Asset):
  def __init__(self):
    super().__init__("Scrounge")

  def get_interrupt(self, event, owner, state):
    if not isinstance(event, events.DrawItems):
      return None
    if event.character != owner or event.deck not in ["common", "unique", "spells"]:
      return None
    return events.ScroungeItems(owner, event)


class UpkeepRestoreStat(assets.Asset):
  def __init__(self, name, stat, verb):
    super().__init__(name)
    self.stat = stat
    self.verb = verb

  def get_usable_interrupt(self, event, owner, state):
    if event.is_done() or not isinstance(event, events.SliderInput):
      return None
    if self.exhausted:
      return None
    if event.character != owner:
      return None
    neighbors = [char for char in state.characters if char.place == owner.place]
    eligible = [
      char
      for char in neighbors
      if getattr(char, self.stat) < getattr(char, "max_" + self.stat)(state)
    ]
    if not eligible:
      return None
    gains = {
      idx: events.Gain(char, {self.stat: 1}, source=self) for idx, char in enumerate(eligible)
    }
    gains[len(eligible)] = events.Nothing()
    prompt = f"Choose a character to {self.verb}"
    choice = events.MultipleChoice(owner, prompt, [char.name for char in eligible] + ["Cancel"])
    cond = events.Conditional(owner, choice, "choice_index", gains)
    exhaust_result = {0: events.ExhaustAsset(owner, self), len(eligible): events.Nothing()}
    exhaust = events.Conditional(owner, choice, "choice_index", exhaust_result)
    return events.Sequence([choice, exhaust, cond], owner)


def Physician():
  return UpkeepRestoreStat("Physician", "stamina", "heal")


def Psychology():
  return UpkeepRestoreStat("Psychology", "sanity", "treat")


def CreateAbilities():
  abilities = [
    FluxStabilizer(),
    Studious(),
    ShrewdDealer(),
    HometownAdvantage(),
    MagicalGift(),
    PsychicSensitivity(),
    Archaeology(),
    StrongMind(),
    StrongBody(),
    TrustFund(),
    Hunches(),
    Physician(),
    Psychology(),
    Research(),
    Scrounge(),
    GuardianAngel(),
  ]
  return {ability.name: ability for ability in abilities}
