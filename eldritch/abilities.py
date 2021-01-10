import eldritch.assets as assets
import eldritch.events as events


class BonusSkill(assets.Card):

  def __init__(self, name, check_type):
    assert check_type in assets.CHECK_TYPES
    super(BonusSkill, self).__init__(name, "skills", {}, {check_type: 1})
    self.check_type = check_type

  def _check_matches(self, check_type):
    return check_type == self.check_type or assets.SUB_CHECKS.get(check_type) == self.check_type

  def get_interrupt(self, event, owner, state):
    if not isinstance(event, events.SpendClue) or not isinstance(event.check, events.Check):
      return None
    if event.character != owner or not self._check_matches(event.check.check_type):
      return None
    return events.AddExtraDie(owner, event.dice)


class RerollSkill(assets.Card):

  def __init__(self, name, check_type):
    assert check_type in assets.SUB_CHECKS
    super(RerollSkill, self).__init__(name, "skills", {}, {})
    self.check_type = check_type

  def get_usable_trigger(self, event, owner, state):
    if not isinstance(event, events.Check) or event.character != owner:
      return None
    if self.exhausted or event.check_type != self.check_type:
      return None
    return events.Sequence([events.ExhaustAsset(owner, self), events.RerollCheck(owner, event)])


def Speed():
  return BonusSkill("Speed", "speed")
def Sneak():
  return BonusSkill("Sneak", "sneak")
def Fight():
  return BonusSkill("Fight", "fight")
def Will():
  return BonusSkill("Will", "will")
def Lore():
  return BonusSkill("Lore", "lore")
def Luck():
  return BonusSkill("Luck", "luck")
def Stealth():
  return RerollSkill("Stealth", "evade")
def Marksman():
  return RerollSkill("Marksman", "combat")
def Bravery():
  return RerollSkill("Bravery", "horror")
def ExportOccultist():
  return RerollSkill("Export Occultist", "spell")


class Medicine(assets.Asset):

  def __init__(self):
    super(Medicine, self).__init__("Medicine")

  def get_usable_trigger(self, event, owner, state):
    if self.exhausted:
      return None
    if state.turn_phase != "upkeep" or state.characters[state.turn_idx] != owner:
      return None
    neighbors = [char for char in state.characters if char.location == owner.location]
    eligible = [char for char in neigbors if char.stamina < char.max_stamina]
    if not eligible:
      return None
    gains = [events.Gain(char, {"stamina": 1}) for char in eligible]
    choice = events.MultipleChoice(
        owner,
        "Choose a character to heal",
        [char.name for char in eligible] + ["nobody"],
        gains + [events.Nothing()],
    )
    return events.Sequence([events.ExhaustAsset(owner, self), choice])
