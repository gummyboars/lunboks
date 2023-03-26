import abc
from eldritch import events
from eldritch import assets
from eldritch import characters


class StoryResult(assets.Card, metaclass=abc.ABCMeta):
  @abc.abstractmethod
  def __init__(self, name, passive_bonuses=None):
    super().__init__(
        name, None, "specials", active_bonuses={}, passive_bonuses=passive_bonuses or {}
    )

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.KeepDrawn) and event.drawn == [self]:
      print("Triggering on", event, owner, state)
      return self.get_create_event(owner)
    return None

  def get_create_event(self, owner: characters.Character):
    return events.Nothing()


class Story(assets.Card, metaclass=abc.ABCMeta):
  @abc.abstractmethod
  def __init__(self, name, pass_result, fail_result):
    super().__init__(name, None, "specials", active_bonuses={}, passive_bonuses={})
    self.results = {True: pass_result, False: fail_result}

  @abc.abstractmethod
  def get_pass_asset(self) -> StoryResult:
    pass

  @abc.abstractmethod
  def get_fail_asset(self) -> StoryResult:
    pass

  def advance_story(self, character, pass_story):
    return events.Sequence([
      events.DiscardSpecific(character, [self]),
      events.DrawSpecific(character, "specials", self.results[pass_story])
    ])


class SweetDreams(StoryResult):
  def __init__(self):
    super().__init__("Sweet Dreams", passive_bonuses={"speed": 1, "luck": 1})


class LivingNightmare(StoryResult):
  def __init__(self):
    super().__init__("Living Nightmare")

  def get_create_event(self, owner: characters.Character):
    allies = [
      ally
      for ally in owner.possessions
      if getattr(ally, "deck", None) == "allies" and ally.name != "Dog"
    ]
    return events.DiscardSpecific(owner, allies)

  def get_interrupt(self, event, owner, state):
    if not getattr(event, "character", None) == owner:
      return
    if (
        (isinstance(event, events.KeepDrawn)
         and (getattr(event.drawn, "deck", None) == "allies"))
        or (isinstance(event, (events.DrawNamed, events.DrawItems)) and event.deck == "allies")
    ):
      return events.CancelEvent(event)
    return


class PowerfulNightmares(Story):
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
    elif (
      isinstance(event, events.AddDoom)
      and state.ancient_one.doom >= 5
    ):
      return self.advance_story(owner, False)
    return None

  def get_pass_asset(self) -> StoryResult:
      return SweetDreams()

  def get_fail_asset(self) -> StoryResult:
    return LivingNightmare()


def CreateStories():
  return [
    SweetDreams(), LivingNightmare(), PowerfulNightmares()
  ]
