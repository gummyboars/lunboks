import typing

from eldritch import assets
from eldritch import characters
from eldritch import events
from eldritch import values

if typing.TYPE_CHECKING:
  from eldritch.eldritch import GameState


class AbnormalFocus(assets.Asset):
  def __init__(self):
    super().__init__("Abnormal Focus")

  def get_interrupt(self, event, owner: characters.BaseCharacter, state):
    if isinstance(event, events.Upkeep) and event.character == owner:
      return events.MoveSliders(owner, {slider + "_slider": 0 for slider in owner.sliders()})
    return None


class BreakingTheLimits(assets.Asset):
  def __init__(self):
    super().__init__("Breaking the Limits")
    self.tokens["sanity"] = 0
    self.tokens["stamina"] = 0

  def get_interrupt(self, event, owner, state):
    if isinstance(event, events.Upkeep) and event.character == owner:
      return events.Sequence([
          events.RemoveToken(self, "sanity", owner, self.tokens["sanity"]),
          events.RemoveToken(self, "stamina", owner, self.tokens["stamina"]),
      ], owner)
    return None

  def get_usable_interrupt(self, event, owner, state):
    if (
        not isinstance(event, events.SliderInput)
        or event.character != owner
        or self.get_bonus("abnormal_focus", None, owner, state) >= 3
        or (owner.stamina == 1 and owner.sanity == 1)
    ):
      return None
    spend = events.SpendChoice(
        owner, prompt="Break the limits?",
        choices=["No", "Yes"],
        spends=[None, values.FlexibleRangeSpendPrerequisite(["sanity", "stamina"], 1, 3)]
    )

    return events.Sequence([
        spend,
        events.AddTokenMap(self, values.Calculation(spend, "spend_map"), owner)
    ], owner)

  def get_bonus(self, check_type, attributes, owner, state):
    if check_type == "abnormal_focus":
      return sum(self.tokens.values())
    return 0


class Synergy(assets.Asset):
  def __init__(self):
    super().__init__("Synergy")

  def get_bonus(
      self, check_type, attributes, owner: characters.BaseCharacter, state: "GameState"
  ):
    n_allies = len([ally for ally in owner.possessions if ally.deck == "allies"])
    n_in_same_place = len(
        [char for char in state.characters if char != owner and char.place == owner.place]
    )
    if n_allies == 0 and n_in_same_place == 0:
      return 0
    if check_type in (assets.CHECK_TYPES | assets.SUB_CHECKS.keys()):
      return 1
    return 0


class TeamPlayer(assets.Asset):
  def __init__(self):
    super().__init__("Team Player")

  def get_usable_interrupt(self, event, owner, state):
    in_same_place = [
        char for char in state.characters if char != owner and char.place == owner.place
    ]
    if not isinstance(event, events.Upkeep) or not event.character == owner:
      return None
    choice = events.MultipleChoice(
        owner,
        "Grant another player +1 bonus to all skill checks until the end of the turn?",
        ["None"] + [char.name for char in in_same_place]
    )
    cond = events.Conditional(
        owner, choice, "choice_index",
        {0: events.Nothing, **{
            i: events.DrawSpecific(char, "specials", "Team Player Bonus")
            for i, char in enumerate(in_same_place, start=1)
        }}
    )
    return events.Sequence(owner, [choice, cond])


class TeamPlayerBonus(assets.Card):
  def __init__(self, idx):
    super().__init__(
        "Team Player Bonus", idx, "specials", {},
        passive_bonuses={check: 1 for check in assets.CHECK_TYPES | assets.SUB_CHECKS.keys()}
    )

  def get_interrupt(self, event, owner, state):
    if isinstance(event, events.Upkeep) and event.character == owner:
      return events.DiscardSpecific(owner, self)
    return None
