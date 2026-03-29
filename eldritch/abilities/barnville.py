from eldritch import cards as assets
from eldritch import events, mythos, values


class WitchBlood(assets.Asset):
  def __init__(self):
    super().__init__("Witch Blood")

  def get_usable_interrupt(self, event, owner, state):
    if (
      isinstance(event, events.Upkeep)
      and (event.character == owner)
      # When the story succeeds, an additional use is allowed
      and self.tokens["stamina"] < 1 + owner.get_modifier(None, "max_witch_blood")
    ):
      return WitchBloodInvocation(owner)
    return None


class WitchBloodInvocation(events.Sequence):
  # This is its own class so the story, when passed, can detect it and reward.
  def __init__(self, character):
    super().__init__(
      [events.RemoveDoom(character), events.AddToken(self, "stamina", character)],
      character=character,
    )


class ThirdEye(assets.Asset):
  def __init__(self):
    super().__init__("Third Eye")

  def get_modifier(self, other, attribute):
    if attribute in ("spell_hands_available", "total_hands_available"):
      return 1
    return 0


class Leadership(assets.Asset):
  def __init__(self):
    super().__init__("Leadership")

  def get_usable_interrupt(self, event, owner, state):
    if isinstance(event, events.GainOrLoss) and not self.exhausted:
      san_stam = {"sanity", "stamina"}
      exhaust = events.ExhaustAsset(owner, self)
      san_prevent = events.Sequence(
        [events.LossPrevention(owner, event, "sanity", 1), exhaust], owner
      )
      stam_prevent = events.Sequence(
        [events.LossPrevention(owner, event, "stamina", 1), exhaust], owner
      )
      if set(event.losses).intersection(san_stam) == {"sanity"}:
        return san_prevent
      if set(event.losses).intersection(san_stam) == {"stamina"}:
        return stam_prevent
      if set(event.losses).intersection(san_stam) == {"stamina", "sanity"}:
        message = (f"What kind of loss to prevent to [{event.character}]?",)
        return events.BinaryChoice(owner, message, "Sanity", "Stamina", san_prevent, stam_prevent)
    return None


class Precognition(assets.Asset):
  def __init__(self):
    super().__init__("Precognition")

  def get_usable_trigger(self, event, owner, state):
    if (
      (len(state.event_stack) > 1)
      and isinstance(state.event_stack[-2], events.Mythos)
      and isinstance(event, events.DrawMythosCard)
      and not isinstance(event.card, mythos.core.ShuffleMythos)
    ):
      new_mythos = events.CancelEvent(event)
      spend = values.ExactSpendPrerequisite({"clues": 2})
      choice = events.SpendChoice(owner, "Draw a new mythos?", ["Yes", "No"], spends=[spend, None])
      cond = events.Conditional(owner, choice, "choice_index", {0: new_mythos, 1: events.Nothing()})
      return events.Sequence([choice, cond], owner)
    return None


def CreateAbilities():
  abilities = [WitchBlood(), ThirdEye(), Precognition()]
  return {ability.name: ability for ability in abilities}
