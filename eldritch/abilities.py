from eldritch import assets
from eldritch import events


class BonusSkill(assets.Card):

  def __init__(self, name, idx, check_type):
    assert check_type in assets.CHECK_TYPES
    super().__init__(name, idx, "skills", {}, {check_type: 1})
    self.check_type = check_type

  def _check_matches(self, check_type):
    return check_type == self.check_type or assets.SUB_CHECKS.get(check_type) == self.check_type

  def get_interrupt(self, event, owner, state):
    if not isinstance(event, events.BonusDiceRoll):
      return None
    if len(state.event_stack) < 2 or not isinstance(state.event_stack[-2], events.Check):
      return None
    if event.character != owner or not self._check_matches(state.event_stack[-2].check_type):
      return None
    return events.AddExtraDie(owner, event)


class RerollSkill(assets.Card):

  def __init__(self, name, idx, check_type):
    assert check_type in assets.SUB_CHECKS
    super().__init__(name, idx, "skills", {}, {})
    self.check_type = check_type

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, events.SpendChoice) or event.character != owner or event.is_done():
      return None
    if len(state.event_stack) < 2 or not isinstance(state.event_stack[-2], events.Check):
      return None
    if self.exhausted or state.event_stack[-2].check_type != self.check_type:
      return None
    return events.Sequence(
        [events.ExhaustAsset(owner, self), events.RerollCheck(owner, state.event_stack[-2])], owner,
    )


def Speed(idx):
  return BonusSkill("Speed", idx, "speed")


def Sneak(idx):
  return BonusSkill('Sneak', idx, "sneak")


def Fight(idx):
  return BonusSkill("Fight", idx, "fight")


def Will(idx):
  return BonusSkill("Will", idx, "will")


def Lore(idx):
  return BonusSkill("Lore", idx, "lore")


def Luck(idx):
  return BonusSkill("Luck", idx, "luck")


def Stealth(idx):
  return RerollSkill("Stealth", idx, "evade")


def Marksman(idx):
  return RerollSkill("Marksman", idx, "combat")


def Bravery(idx):
  return RerollSkill("Bravery", idx, "horror")


def ExpertOccultist(idx):
  return RerollSkill("Expert Occultist", idx, "spell")


def CreateSkills():
  skills = []
  skill_list = [Speed, Sneak, Fight, Will, Lore, Luck, Stealth, Marksman, Bravery, ExpertOccultist]
  for skill in skill_list:
    skills.extend([skill(0), skill(1)])
  return skills


class FluxStabilizer(assets.Asset):

  def __init__(self):
    super().__init__("Flux Stabilizer")


class Medicine(assets.Asset):

  def __init__(self):
    super().__init__("Medicine")

  def get_usable_trigger(self, event, owner, state):
    if not isinstance(event, events.UpkeepActions):
      return None
    return self.get_usable(event, owner, state)

  def get_usable_interrupt(self, event, owner, state):
    if not isinstance(event, (events.UpkeepActions, events.SliderInput)):
      return None
    return self.get_usable(event, owner, state)

  def get_usable(self, event, owner, state):
    if self.exhausted:
      return None
    if event.character != owner:
      return None
    neighbors = [char for char in state.characters if char.place == owner.place]
    eligible = [char for char in neighbors if char.stamina < char.max_stamina(state)]
    if not eligible:
      return None
    gains = {idx: events.Gain(char, {"stamina": 1}) for idx, char in enumerate(eligible)}
    gains[len(eligible)] = events.Nothing()
    choice = events.MultipleChoice(
        owner, "Choose a character to heal", [char.name for char in eligible] + ["nobody"])
    cond = events.Conditional(owner, choice, "choice_index", gains)
    return events.Sequence([events.ExhaustAsset(owner, self), choice, cond], owner)
