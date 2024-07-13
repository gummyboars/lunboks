import typing

from eldritch import assets
from eldritch import events
from eldritch import places

if typing.TYPE_CHECKING:
  from eldritch.eldritch import GameState


class Streetwise(assets.Asset):
  def __init__(self):
    super().__init__("Streetwise")

  def get_interrupt(self, event, owner, state):
    if (
        isinstance(event, events.EvadeRound)
        and event.character == owner
        and isinstance(owner.place, places.Street)
    ):
      return events.PassEvadeRound(event)
    return None


class BlessedIsTheChild(assets.Asset):
  def __init__(self):
    super().__init__("Blessed is the Child")

  def get_interrupt(self, event, owner, state):
    if (
        isinstance(event, (events.Arrested, events.Curse))
        and event.character == owner
        and "Elder Sign" in [p.name for p in owner.poseessions]
    ):
      return events.CancelEvent(event)
    return None


class Minor(assets.Asset):
  def __init__(self):
    # Minor, Not Miner
    super().__init__("Minor")

  def get_interrupt(self, event, owner, state):
    if event.character == owner and isinstance(event, events.TakeBankLoan):
      return events.CancelEvent(event)
    return None
