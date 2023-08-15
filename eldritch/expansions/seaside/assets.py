from eldritch import assets
from eldritch import events


class BreakingTheLimits(assets.Asset):
  def __init__(self):
    super().__init__("Breaking the Limits")

  def get_interrupt(self, event, owner, state):
    if isinstance(event, events.Upkeep) and event.character == owner:
      return events.Sequence([
        events.RemoveToken(self, "sanity", owner, self.tokens['sanity']),
        events.RemoveToken(self, "stamina", owner, self.tokens['stamina']),
        ], owner)
    return None

  def get_bonus(self, check_type, attributes):
    if check_type == "abnormal_focus":
      return sum(self.tokens.values())
    return 0

