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
      and "Elder Sign" in [p.name for p in owner.possessions]
    ):
      return events.CancelEvent(event)
    return None


class Minor(assets.Asset):
  def __init__(self):
    # Minor, Not Miner
    super().__init__("Minor")

  def get_interrupt(self, event, owner, state):
    if isinstance(event, events.TakeBankLoan) and event.character == owner:
      return events.CancelEvent(event)
    return None

  def get_override(self, other, attribute):
    if attribute == "can_get_bank_loan":
      return False
    return None
