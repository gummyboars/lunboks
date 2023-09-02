import abc
from eldritch import assets
from eldritch import characters
from eldritch import events
from eldritch import gates
from eldritch import monsters
from eldritch import values


class StoryResult(assets.Card, metaclass=abc.ABCMeta):
  @abc.abstractmethod
  def __init__(self, name, passive_bonuses=None):
    super().__init__(
        name, None, "specials", active_bonuses={}, passive_bonuses=passive_bonuses or {}
    )

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and event.drawn == [self]:
      return self.get_in_play_event(owner)
    return None

  def get_in_play_event(self, owner: characters.Character):  # pylint: disable=unused-argument
    return events.Nothing()


class Story(assets.Card, metaclass=abc.ABCMeta):
  @abc.abstractmethod
  def __init__(self, name, pass_result, fail_result):
    super().__init__(name, None, "specials", active_bonuses={}, passive_bonuses={})
    self.results = {True: pass_result, False: fail_result}

  def advance_story(self, character, pass_story):
    return events.Sequence([
        events.DiscardSpecific(character, [self]),
        events.DrawSpecific(character, "specials", self.results[pass_story])
    ], character)


class DrifterStoryPass(StoryResult):
  def __init__(self):
    super().__init__("Sweet Dreams", passive_bonuses={"speed": 1, "luck": 1})


class DrifterStoryFail(StoryResult):
  def __init__(self):
    super().__init__("Living Nightmare")

  def get_in_play_event(self, owner: characters.Character):
    allies = [
        ally
        for ally in owner.possessions
        if getattr(ally, "deck", None) == "allies" and ally.name != "Dog"
    ]
    return events.DiscardSpecific(owner, allies)

  def get_interrupt(self, event, owner, state):
    if (
        getattr(event, "character", None) == owner
        and isinstance(event, events.KeepDrawn)
        and event.draw
        and event.draw.drawn
        and getattr(event.draw.drawn[0], "deck", None) == "allies"
    ):
      return events.CancelEvent(event)
    return super().get_interrupt(event, owner, state)


class DrifterStory(Story):
  def __init__(self):
    super().__init__(
        "Powerful Nightmares", "Sweet Dreams", "Living Nightmare"
    )

  def get_trigger(self, event, owner, state):
    if (
        isinstance(event, events.TakeGateTrophy)
        and (event.character == owner)
        and (event.gate.name == "Dreamlands")
    ):
      return self.advance_story(owner, True)
    if (
        isinstance(event, events.AddDoom)
        and state.ancient_one.doom >= 5
    ):
      return self.advance_story(owner, False)
    return super().get_trigger(event, owner, state)


class GangsterStoryPass(StoryResult):
  def __init__(self):
    super().__init__("This One's for Louis", {"max_sanity": 1})

  def get_in_play_event(self, owner: characters.Character):
    return events.Gain(owner, {"sanity": 1}, self)

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.ForceTakeTrophy) and event.character == owner:
      return events.Gain(owner, {"sanity": 1}, self)
    return super().get_trigger(event, owner, state)


class GangsterStoryFail(StoryResult):
  def __init__(self):
    super().__init__("Crime Doesn't Pay")

  def get_in_play_event(self, owner: characters.Character):
    return events.Loss(owner, {"dollars": owner.dollars})

  def get_interrupt(self, event, owner, state):
    if (
        isinstance(event, events.GainOrLoss)
        and event.character == owner
        and "dollars" in event.gains
    ):
      return events.GainOrLossPrevention(self, event, "dollars", float("inf"), "gains")
    return None


class GangsterStory(Story):
  def __init__(self):
    super().__init__("For a Friend", "This One's for Louis", "Crime Doesn't Pay")

  def get_trigger(self, event, owner: characters.Character, state):
    n_trophies = len([t for t in owner.trophies if isinstance(t, monsters.Monster)])
    if isinstance(event, events.ForceTakeTrophy) and n_trophies >= 5:
      return self.advance_story(owner, True)
    if (
        isinstance(event, events.GainOrLoss)
        and (event.character == owner)
        and (event.gains.get("dollars", 0) >= 5)
    ):
      return self.advance_story(owner, False)
    return super().get_trigger(event, owner, state)


class NunStoryPass(StoryResult):
  def __init__(self):
    super().__init__("Fear No Evil")

  def get_interrupt(self, event, owner, state):
    if isinstance(event, events.Curse) and event.character == owner:
      return events.CancelEvent(event)
    return super().get_interrupt(event, owner, state)

  def get_usable_trigger(self, event, owner, state):
    if isinstance(event, events.DiceRoll) and state.turn_phase == "upkeep":
      # Note: I see nothing that says it has to be one of her dice
      choice = events.MultipleChoice(owner, "Choose a die to reroll", event.roll[:])
      chosen = values.Calculation(choice, "choice_index")
      return events.Sequence([
          events.ExhaustAsset(owner, self),
          choice,
          events.RerollSpecificDice(event.character, event, chosen),
      ], owner)
    return None

  def get_trigger(self, event, owner, state):
    # Once per turn, not technically "exhaust to ..."
    if (
      self.exhausted
      and isinstance(event, events.Mythos)
      and event.is_done()
    ):
      return events.RefreshAsset(owner, self)

  def get_in_play_event(self, owner: characters.Character):
    return events.Bless(owner)


class NunStoryFail(StoryResult):
  def __init__(self):
    super().__init__("I Shall Not Want")

  def get_in_play_event(self, owner: characters.Character):
    return events.Sequence([
        events.DiscardNamed(owner, "Curse"),
        events.Bless(owner)
    ], owner)


class NunStory(Story):
  def __init__(self):
    super().__init__("He Is My Shepherd", "Fear No Evil", "I Shall Not Want")
    self.max_tokens["clue"] = 2
    self.tokens["clue"] = 0

  def get_max_token_event(self, token_type, owner):
    if token_type == "clue":
      return self.advance_story(owner, True)
    return events.Nothing()

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.Bless):
      return events.AddToken(self, "clue", owner)
    if (
        isinstance(event, events.BlessCurse)
        and (event.character == owner)
        and event.is_resolved()
        and values.ItemNameCount(owner, "Curse").value(state) == 1
    ):
      return self.advance_story(owner, False)
    return super().get_trigger(event, owner, state)


class PhotographerStoryPass(StoryResult):
  def __init__(self):
    super().__init__("There's Your Proof")

  def get_in_play_event(self, owner: characters.Character):
    return events.DrawSpecific(owner, "specials", "Retainer")

  def get_interrupt(self, event, owner, state):
    if (
        isinstance(event, events.AddToken)
        and event.character == owner
        and event.token_type == "must_roll"
        and event.asset.name == "Retainer"
    ):
      return events.CancelEvent(event)
    return None


class PhotographerStoryFail(StoryResult):
  def __init__(self):
    super().__init__("The Film Is Ruined")

  def get_in_play_event(self, owner: characters.Character):
    return events.DiscardNamed(owner, "Retainer")

  def get_override(self, other, attribute):
    if isinstance(other, (assets.BankLoan, assets.Retainer)) and attribute == "can_keep":
      return False
    return None


class PhotographerStory(Story):
  def __init__(self):
    super().__init__("A Thousand Words", "There's Your Proof", "The Film is Ruined")

  def get_trigger(self, event, owner, state):
    if len([t for t in owner.trophies if isinstance(t, gates.Gate)]) >= 2:
      return self.advance_story(owner, True)
    if owner.clues >= 5:
      return self.advance_story(owner, False)
    return None


class PsychologistStoryPass(StoryResult):
  def __init__(self):
    super().__init__("Cured")

  def get_interrupt(self, event, owner, state):
    return events.Sequence([
        events.Bless(owner),
        events.Gain(owner, {"clues": 3})
    ])


class PsychologistStoryFail(StoryResult):
  def __init__(self):
    super().__init__("Followed", {"sneak": -1})


class PsychologistStory(Story):
  def __init__(self):
    super().__init__("Final Analysis", "Cured", "Followed")

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.GainOrLoss) and owner.clues >= 6:
      return self.advance_story(owner, False)
    return None

  def get_usable_interrupt(self, event, owner: characters.Character, state):
    if (
        isinstance(event, events.Upkeep)
        and event.character == owner
        and owner.place.name == "Asylum"
    ):
      choice = events.SpendChoice(
          owner,
          "Spend $15 to finish story?",
          ["No", "Yes"],
          spends=[None, values.ExactSpendPrerequisite({"dollars": 15})]
      )

      result = events.Conditional(owner, choice, "choice_idx", {1: self.advance_story(owner, True)})
      return events.Sequence([choice, result], owner)
    return None


class SalesmanStoryPass(StoryResult):
  def __init__(self):
    super().__init__("Jackpot")

  def get_in_play_event(self, owner: characters.Character):
    return events.Gain(owner, {"dollars": 15}, self)

  def get_usable_interrupt(self, event, owner, state):
    if (
        isinstance(event, events.Upkeep)
        and event.character == owner
        and not self.exhausted
    ):
      choice = events.SpendChoice(
          owner, "Spend $3 for 1 clue token?",
          ["No", "Yes"],
          spends=[None, values.ExactSpendPrerequisite({"dollars": 3})]
      )
      cond = events.Conditional(owner, choice, "choice_idx", {1: events.Gain(owner, {"clues": 1})})
      return events.Sequence([choice, cond], owner)
    return None


class SalesmanStoryFail(StoryResult):
  def __init__(self):
    super().__init__("Greed")

  def get_in_play_event(self, owner: characters.Character):
    return events.Curse(owner)

  def get_interrupt(self, event, owner: characters.Character, state):
    if isinstance(event, events.Bless) and event.character == owner and owner.dollars > 0:
      return events.CancelEvent(event)
    if (
        isinstance(event, events.GainOrLoss)
        and event.character == owner
        and event.gains.get("dollars", 0) > 0
        and owner.bless_curse == 1
    ):
      return events.Curse(owner)
    return None


class SalesmanStory(Story):
  def __init__(self):
    super().__init__("Old Money", "Jackpot", "Greed")

  def get_trigger(self, event, owner: characters.Character, state):
    if owner.clues >= 5:
      return self.advance_story(owner, True)
    if len([t for t in owner.trophies if isinstance(t, monsters.Monster)]) >= 3:
      return self.advance_story(owner, False)
    return None


class ScientistStoryPass(StoryResult):
  def __init__(self):
    super().__init__("It's Working!")

  def get_modifier(self, other, attribute):
    if attribute == "gate_limit":
      return 1
    return 0

  def get_in_play_event(self, owner: characters.Character):
    return events.AddGlobalEffect(self)

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.Devoured) and event.character == owner:
      return events.RemoveGlobalEffect(self)
    # Any other conditions when their story could go away?
    return None


class ScientistStoryFail(StoryResult):
  def __init__(self):
    super().__init__("This Is No Good")

  def get_override(self, other, attribute):
    if isinstance(other, events.GateCloseAttempt) and attribute == "can_spend_clues":
      return False
    return None


class ScientistStory(Story):
  def __init__(self):
    super().__init__("Resonance", "It's Working!", "This Is No Good")

  def get_trigger(self, event, owner, state):
    if len([t for t in owner.trophies if isinstance(t, gates.Gate)]) >= 2:
      return self.advance_story(owner, True)
    if state.ancient_one.doom >= 6:
      return self.advance_story(owner, False)
    return None


def CreateStories():
  return [
      DrifterStoryPass(), DrifterStoryFail(), DrifterStory(),
      GangsterStoryPass(), GangsterStoryFail(), GangsterStory(),
      NunStoryPass(), NunStoryFail(), NunStory(),
      # Don't add stories that don't have tests
      # PhotographerStoryPass(), PhotographerStoryFail(), PhotographerStory(),
      # PsychologistStoryPass(), PsychologistStoryFail(), PsychologistStory(),
      # SalesmanStoryPass(), SalesmanStoryFail(), SalesmanStory(),
      # ScientistStoryPass(), ScientistStoryFail(), ScientistStory(),
  ]
