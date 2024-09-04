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
      # Allow Spy to keep the lore slider from the last turn for spellcasting
      # TODO: change the order such that the slider input happens earlier.
      return events.MoveSliders(
        owner, {slider + "_slider": 0 for slider in owner.sliders() if "lore" not in slider}
      )
    return None

  def get_bonus(self, check_type, attributes, owner, state: typing.Optional["GameState"]):
    if check_type == "abnormal_focus":
      return 5
    return 0


class BreakingTheLimits(assets.Asset):
  def __init__(self):
    super().__init__("Breaking the Limits")
    self.tokens["sanity"] = 0
    self.tokens["stamina"] = 0

  def get_interrupt(self, event, owner, state):
    if isinstance(event, events.Upkeep) and event.character == owner:
      return events.Sequence(
        [
          events.RemoveToken(self, "sanity", owner, self.tokens["sanity"]),
          events.RemoveToken(self, "stamina", owner, self.tokens["stamina"]),
        ],
        owner,
      )
    return None

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.SliderInput) or event.is_done() or event.character != owner:
      return None
    if sum(self.tokens.values()) >= 3 or (owner.stamina == 1 and owner.sanity == 1):
      return None
    prereq = values.FlexibleRangeSpendPrerequisite(
      ["sanity", "stamina"], 1, 3 - sum(self.tokens.values()), character=owner
    )
    spend = events.SpendChoice(
      owner, prompt="Break the limits?", choices=["No", "Yes"], spends=[None, prereq]
    )

    return events.Sequence(
      [spend, events.AddTokenMap(self, values.Calculation(spend, "spend_map"), owner)], owner
    )

  def get_bonus(self, check_type, attributes, owner, state):
    if check_type == "abnormal_focus":
      return sum(self.tokens.values())
    return 0


class Synergy(assets.Asset):
  def __init__(self):
    super().__init__("Synergy")

  def get_bonus(
    self,
    check_type,
    attributes,
    owner: characters.BaseCharacter,
    state: typing.Optional["GameState"],
  ):
    # TODO: Call Stack enforcement to guard against infinite loops.
    if state is None:
      return 0
    n_allies = len([ally for ally in owner.possessions if getattr(ally, "deck", None) == "allies"])
    n_in_same_place = len(
      [char for char in state.characters if char != owner and char.place == owner.place]
    )
    if n_allies == 0 and n_in_same_place == 0:
      return 0
    if check_type in assets.CHECK_TYPES:
      return 1
    return 0


class TeamPlayer(assets.Asset):
  def __init__(self):
    super().__init__("Team Player")

  def get_interrupt(self, event, owner, state):
    in_same_place = [
      char for char in state.characters if char != owner and char.place == owner.place
    ]
    if (
      not isinstance(event, events.SliderInput)
      or event.character != owner
      or event.is_done()
      or self.exhausted
      or not in_same_place
    ):
      return None
    choice = events.MultipleChoice(
      owner,
      "Grant another player +1 bonus to all skill checks until the end of the turn?",
      ["None"] + [char.name for char in in_same_place],
    )
    results = {
      0: events.Nothing(),
      **{
        i: events.DrawSpecific(char, "specials", "Team Player Bonus")
        for i, char in enumerate(in_same_place, start=1)
      },
    }
    cond = events.Conditional(owner, choice, "choice_index", results)
    return events.Sequence([choice, cond, events.ExhaustAsset(owner, self)], owner)


class TeamPlayerBonus(assets.Card):
  def __init__(self, idx):
    super().__init__("Team Player Bonus", idx, "specials", {}, {})

  def get_bonus(self, check_type, attributes, owner, state: typing.Optional["GameState"]):
    if (
      state is not None
      and len(state.event_stack) > 0
      and isinstance(state.event_stack[-1], events.Check)
      and check_type in assets.CHECK_TYPES
    ):
      return 1
    return 0

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.Mythos) and event.is_done():
      return events.DiscardSpecific(owner, [self])
    return None


class ThickSkulledCombat(events.Combat):
  def resolve(self, state):
    # Horror check
    if (
      self.monster.difficulty("horror", state, self.character) is not None
      and self.horror is None
      and (self.evade is not None or self.combat is not None)
      and any(
        [
          getattr(self.evade, "evaded", None) is False,
          getattr(self.combat, "defeated", None) is False,
        ]
      )
    ):
      self._setup_horror(state)
    if self.horror is not None:
      return_early = self._do_horror(state)
      if return_early:
        return

    # Combat or flee choice.
    self._do_combat_or_evade(state)


class ThickSkulled(assets.Asset):
  def __init__(self):
    super().__init__("Thick Skulled")

  def get_interrupt(self, event, owner, state):
    if (
      isinstance(event, events.Combat)
      and not isinstance(event, ThickSkulledCombat)
      and event.character == owner
    ):
      return events.Sequence(
        [events.CancelEvent(event), ThickSkulledCombat(event.character, event.monster)]
      )
    return None
