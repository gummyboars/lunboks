import eldritch.events as events


class EncounterCard(object):

  def __init__(self, name, encounter_creators):
    self.name = name
    self.encounters = {}
    for location_name, encounter_creator in encounter_creators.items():
      self.add_encounter(location_name, encounter_creator)

  def add_encounter(self, location_name, encounter_creator):
    self.encounters[location_name] = encounter_creator

  # TODO: fixed encounters
  def encounter_event(self, character, location_name):
    if location_name not in self.encounters:
      print(f"TODO: missing encounters for {self.name} at {location_name}")
      return events.Nothing()
    return self.encounters[location_name](character)


def Diner1(char):
  return events.Nothing() # TODO numeric choice
def Diner2(char):
  return events.DrawSpecific(char, "common", "Food")
def Diner3(char):
  adj = events.GainOrLoss(char, {"stamina": 2}, {"dollars": 1})
  choice = events.BinaryChoice(char, "Pay $1 for pie?", "Pay $1", "Go Hungry", adj, events.Nothing());
  prereq = events.AttributePrerequisite(char, "dollars", 1, "at least")
  return events.PassFail(char, prereq, choice, events.Nothing())
def Diner4(char):
  gain = events.Gain(char, {"dollars": 5})
  check = events.Check(char, "will", -2)
  return events.PassFail(char, check, gain, events.Nothing())
def Diner5(char):
  bless = events.Bless(char)
  curse = events.Curse(char)
  check = events.Check(char, "luck", -1)
  return events.PassFail(char, check, bless, curse)
def Diner6(char):
  loss = events.Loss(char, {"stamina": 2})
  check = events.Check(char, "luck", -1)
  return events.PassFail(char, check, events.Nothing(), loss)
def Diner7(char):
  move = events.ForceMovement(char, "Easttown")
  die = events.DiceRoll(char, 1)
  gain = events.Gain(char, {"dollars": die})
  check = events.Check(char, "sneak", -1)
  return events.PassFail(char, check, events.Sequence([die, gain]), move)

def Roadhouse1(char):
  # TODO: this prerequisite should account for characters that can spend clues in other ways, such
  # as by discarding a research materials, or by using the violinist's clues, etc.
  prereq = events.AttributePrerequisite(char, "clues", 3, "at least")
  spend = events.Loss(char, {"clues": 3})
  # TODO: prerequisite of the ally being in the deck.
  draw = events.DrawSpecific(char, "allies", "Traveling Salesman")
  take = events.Sequence([spend, draw], char)
  nothing = events.Nothing()
  choice = events.BinaryChoice(char, "Spend 3 clues for an ally?", "Yes", "No", take, nothing)
  return events.PassFail(char, prereq, choice, nothing)
def Roadhouse2(char):
  check = events.Check(char, "luck", -1)
  gain = events.Gain(char, {"dollars": 5})
  dollar_loss = events.Loss(char, {"dollars": 3})
  stamina_loss = events.Loss(char, {"stamina": 1})
  move = events.ForceMovement(char, "Easttown")
  prereq = events.AttributePrerequisite(char, "dollars", 3, "at least")
  loss = events.PassFail(char, prereq, dollar_loss, events.Sequence([stamina_loss, move], char))
  return events.PassFail(char, check, gain, loss)
def Roadhouse3(char):
  return events.DrawSpecific(char, "common", "Whiskey")
def Roadhouse4(char):
  return events.Nothing() # TODO buying stuff
def Roadhouse5(char):
  return events.Nothing() # TODO monster cup
def Roadhouse6(char):
  check = events.Check(char, "will", -1)
  clues = events.Gain(char, {"clues": 2})
  move = events.ForceMovement(char, "Easttown")
  dollars_stolen = events.Loss(char, {"dollars": float("inf")})
  # TODO: allow the character to choose an item to be stolen instead, but this needs to be
  # conditional on a prerequisite of the character having at least one item.
  return events.PassFail(char, check, clues, events.Sequence([move, dollars_stolen], char))
def Roadhouse7(char):
  loss = events.Loss(char, {"dollars": float("inf")})
  check = events.Check(char, "luck", -1)
  return events.PassFail(char, check, events.Nothing(), loss)

def Police1(char):
  check = events.Check(char, "will", -1)
  gain = events.Gain(char, {"clues": 1})
  move = events.ForceMovement(char, "Easttown")
  loss = events.Loss(char, {"sanity": 1})
  return events.PassFail(char, check, gain, events.Sequence([move, loss], char))
def Police2(char):
  check = events.Check(char, "luck", -1)
  loss = events.Loss(char, {"stamina": 2})
  return events.PassFail(char, check, events.Nothing(), loss)
def Police3(char):
  check = events.Check(char, "will", -1)
  gain = events.Gain(char, {"clues": 2})
  return events.PassFail(char, check, gain, events.Nothing())
def Police4(char):
  check = events.Check(char, "luck", -1)
  draw = events.DrawSpecific(char, "common", ".38 Revolver")
  return events.PassFail(char, check, draw, events.Nothing())
def Police5(char):
  return events.Nothing()  # TODO discarding all weapons
def Police6(char):
  check = events.Check(char, "luck", -2)
  draw = events.Draw(char, "unique", 1)
  return events.PassFail(char, check, draw, events.Nothing())
def Police7(char):
  check = events.Check(char, "sneak", 0)
  draw = events.DrawSpecific(char, "common", "Research Materials")
  return events.PassFail(char, check, draw, events.Nothing())

def Lodge1(char):
  check = events.Check(char, "lore", -1)
  draw = events.Draw(char, "spells", 2)
  return events.PassFail(char, check, draw, events.Nothing())

def Witch2(char):
  check = events.Check(char, "luck", -1)
  draw = events.Draw(char, "unique", 1)
  return events.PassFail(char, check, draw, events.Nothing())

def Store5(char):
  check = events.Check(char, "will", -2)
  draw = events.Draw(char, "common", 3)
  return events.PassFail(char, check, draw, events.Nothing())

def Society4(char):
  check = events.Check(char, "luck", -1)
  skill = events.Sequence([events.Draw(char, "skills", 1), events.Delayed(char)], char)
  cond = events.Conditional(char, check, "successes", {0: events.Nothing(), 2: skill})
  return events.Sequence([check, cond], char)

def Administration7(char):
  check = events.Check(char, "will", -2)
  gain = events.Gain(char, {"dollars": 8})
  arrest = events.Arrested(char)
  return events.PassFail(char, check, gain, arrest)

def Asylum1(char):
  check = events.Check(char, "lore", 0)
  roll0 = events.GainOrLoss(char, {"clues": 1}, {"sanity": 1})
  roll1 = events.Gain(char, {"clues": 2})
  roll3 = events.Gain(char, {"clues": 3})
  cond = events.Conditional(char, check, "successes", {0: roll0, 1: roll1, 3: roll3})
  return events.Sequence([check, cond], char)
def Asylum2(char):
  check = events.Check(char, "speed", -1)
  item = events.Draw(char, "unique", 1)
  move = events.ForceMovement(char, "Downtown")
  return events.PassFail(char, check, item, move)
def Asylum3(char):
  check = events.Check(char, "sneak", -1)
  escape = events.ForceMovement(char, "Downtown")
  arrested = events.Arrested(char)
  return events.PassFail(char, check, escape, arrested)
def Asylum4(char):
  check = events.Check(char, "lore", -1)
  spell = events.Draw(char, "spells", 1)
  return events.PassFail(char, check, spell, events.Nothing())
def Asylum5(char):
  check = events.Check(char, "will", -1)
  lose = events.Nothing() #TODO: Oh dear...so many choices
  skill = events.Draw(char, "skills", 1)
  cond = events.Conditional(char, check, "successes", {0: lose, 2: skill})
  return events.Sequence([check, cond], char)
def Asylum6(char):
  check = events.Check(char, "lore", -2)
  gain = events.Gain(char, {"clues": 2})
  loss = events.Loss(char, {"stamina": 1})
  return events.PassFail(char, check, gain, loss)
def Asylum7(char):
  check = events.Check(char, "fight", -2)
  stamina = events.Gain(char, {"stamina": 2})
  rest = events.Sequence([stamina, events.LoseTurn(char)], char)
  fight = events.PassFail(char, check, events.Nothing(), rest)
  return events.BinaryChoice(char, "Do you resist?", "Yes", "No", fight, rest)

def Bank1(char):
  return events.Nothing() # TODO: implement location choice
def Bank2(char):
  check = events.Check(char, "luck", -1)
  spend = events.Loss(char, {"dollars": 2})
  common = events.Draw(char, "common", 1)
  unique = events.Draw(char, "unique", 1)
  cond = events.Conditional(char, check, "successes", {0: common, 1: unique})
  prereq = events.AttributePrerequisite(char, "dollars", 2, "at least")
  nothing = events.Nothing()
  choice = events.BinaryChoice(
                              char, "Pay $2 for man's last possession?",
                              "Pay $2",
                              "Let man and his family go hungry", 
                              events.Sequence([spend, check, cond], char), nothing)
  return events.PassFail(char, prereq, choice, nothing)
def Bank3(char):
  prep = events.CombatChoice(char, "Choose weapons to fight the bank robbers")
  check = events.Check(char, "combat", -1)
  robbed = events.Loss(char, {"dollars": char.dollars})
  nothing = events.Nothing()
  cond = events.Conditional(char, check, "successes", {0: robbed, 1: nothing})
  return events.Sequence([prep, check, cond], char)
def Bank4(char):
  check = events.Check(char, "luck", -2)
  bless = events.Bless(char)
  curse = events.Curse(char)
  return events.PassFail(char, check, bless, curse)
def Bank5(char):
  check = events.Check(char, "speed", -1)
  gain = events.Gain(char, {"dollars": 2})
  return events.PassFail(char, check, gain, events.Nothing())
def Bank6(char):
  return events.Loss(char, {"sanity": 1})
def Bank7(char):
  return events.GainOrLoss(char, {"dollars": 5}, {"sanity": 1})

def Square1(char):
  return events.Gain(char, {"stamina": 1})
def Square2(char):
  check = events.Check(char, "will", -1)
  # TODO: prerequisite ally being in the deck, otherwise two clue tokens
  ally = events.DrawSpecific(char, "allies", "Fortune Teller")
  return events.PassFail(char, check, ally, events.Nothing())
def Square3(char):
  check = events.Check(char, "will", -1)
  loss = events.Loss(char, {"sanity": 1, "stamina": 1})
  return events.PassFail(char, check, events.Nothing(), loss)
def Square4(char):
  check = events.Check(char, "luck", -2)
  loss = event.Nothing()  #TODO: Choose an item to lose
  return events.PassFail(char, check, events.Nothing(), loss)
def Square5(char):
  check = events.Check(char, "fight", -1)
  move = events.ForceMovement(char, "Downtown")
  return events.PassFail(char, check, events.Nothing(), move)
def Square6(char):
  check = events.Check(char, "luck", -1)
  stamina = events.Loss(char, {"stamina": 1})
  lose = events.Sequence([stamina, events.Curse(char)], char)
  buy = events.Nothing() #TODO: Buying stuff
  interact = events.PassFail(char, check, buy, lose)
  return events.BinaryChoice(char, "Interact with the gypsies?", "Yes", "No", interact, events.Nothing())
def Square7(char):
  check = events.Check(char, "luck", -1)
  draw = events.Draw(char, "spells", 1)
  gain = events.GainOrLoss(char, {"clues": 2}, {"stamina": 1})
  success = events.Sequence([draw, gain], char)
  fail = events.Nothing() # TODO: RUN!!! It's a GATE!
  return events.PassFail(char, check, success, fail)

def CreateEncounterCards():
  return {
      "Downtown": [
        EncounterCard("Downtown1", {"Asylum": Asylum1, "Bank": Bank1, "Square": Square1}),
        EncounterCard("Downtown2", {"Asylum": Asylum2, "Bank": Bank2, "Square": Square2}),
        EncounterCard("Downtown3", {"Asylum": Asylum3, "Bank": Bank3, "Square": Square3}),
        EncounterCard("Downtown4", {"Asylum": Asylum4, "Bank": Bank4, "Square": Square4}),
        EncounterCard("Downtown5", {"Asylum": Asylum5, "Bank": Bank5, "Square": Square5}),
        EncounterCard("Donwtown6", {"Asylum": Asylum6, "Bank": Bank6, "Square": Square6}),
        EncounterCard("Donwtown7", {"Asylum": Asylum7, "Bank": Bank7, "Square": Square7})
      ],
      "Easttown": [
        EncounterCard("Easttown1", {"Diner": Diner1, "Roadhouse": Roadhouse1, "Police": Police1}),
        EncounterCard("Easttown2", {"Diner": Diner2, "Roadhouse": Roadhouse2, "Police": Police2}),
        EncounterCard("Easttown3", {"Diner": Diner3, "Roadhouse": Roadhouse3, "Police": Police3}),
        EncounterCard("Easttown4", {"Diner": Diner4, "Roadhouse": Roadhouse4, "Police": Police4}),
        EncounterCard("Easttown5", {"Diner": Diner5, "Roadhouse": Roadhouse5, "Police": Police5}),
        EncounterCard("Easttown6", {"Diner": Diner6, "Roadhouse": Roadhouse6, "Police": Police6}),
        EncounterCard("Easttown7", {"Diner": Diner7, "Roadhouse": Roadhouse7, "Police": Police7}),
      ],
      "FrenchHill": [
        EncounterCard("FrenchHill1", {"Lodge": Lodge1}),
        EncounterCard("FrenchHill2", {"Witch": Witch2}),
      ],
      "Rivertown": [
        EncounterCard("Rivertown5", {"Store": Store5}),
      ],
      "University": [
        EncounterCard("University7", {"Administration": Administration7}),
      ],
      "Southside": [
        EncounterCard("Southside4", {"Society": Society4}),
      ]
  }
