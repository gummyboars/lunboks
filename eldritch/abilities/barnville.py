from eldritch import cards as assets
from eldritch import events


class WitchBlood(assets.Asset):
    def __init__(self):
        super().__init__("Witch Blood")

    def get_interrupt(self, )

class ThirdEye(assets.Asset):
    def __init__(self):
        super().__init__("Third Eye")

class Precognition(assets.Asset):
  def __init__(self):
    super().__init__("Precognition")

  def get_trigger(self, event, owner, state):
    if isinstance(event, events.DrawMythosCard) and not isinstance(
      event.card, mythos.ShuffleMythos
    ):
      new_mythos = events.Nothing()
      spend = values.ExactSpendPrerequisite({"clues": 2})
      choice = events.SpendChoice(
        char, "Draw a new mythos?", ["Yes", "No"], spends=[spend, None]
      )
      cond = events.Conditional(char, choice, "choice_index", {0: new_mythos, 1: events.Nothing()})
      seq = events.Sequence([choice, cond], char)
      return seq
