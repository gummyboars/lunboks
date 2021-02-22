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
  prereq = events.AttributePrerequisite(char, "dollars", 1, "at least")
  dollar_choice = events.MultipleChoice(
      char, "How many dollars do you want to pay?", [x for x in range(0, min(char.dollars+1, 7))])
  spend = events.Loss(char, {"dollars": dollar_choice})
  gain = events.SplitGain(char, "stamina", "sanity", dollar_choice)
  spend_and_gain = events.Sequence([dollar_choice, spend, gain], char)
  return events.PassFail(char, prereq, spend_and_gain, events.Nothing())
def Diner2(char):
  return events.DrawSpecific(char, "common", "Food")
def Diner3(char):
  adj = events.GainOrLoss(char, {"stamina": 2}, {"dollars": 1})
  choice = events.BinaryChoice(char, "Pay $1 for pie?", "Pay $1", "Go Hungry", adj, events.Nothing())
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

def Administration1(char):
  check = events.Check(char, "lore", -1)
  dollars = events.Gain(char, {"dollars": 5})
  return events.PassFail(char, check, dollars, events.Nothing())
def Administration2(char):
  return events.Gain(char, {"clues": 1})
def Administration3(char):
  check =  events.Check(char, "will", -1)
  retainer = events.StatusChange(char, "retainer")
  return events.PassFail(char, check, retainer, events.Nothing())
def Administration4(char):
  check = events.Check(char, "lore", -2)
  spell = events.Draw(char, "spells", 1)
  curse = events.Curse(char)
  assist =  events.PassFail(char, check, spell, curse)
  return events.BinaryChoice(
    char,"Help the professor and his students?", "Yes", "No", assist, events.Nothing())
def Administration5(char):
  move = events.ForceMovement(char, "Asylum")
  encounter = events.Nothing()
  return events.Sequence([move, encounter], char)
def Administration6(char):
  # Administration 6 is identical to Administration 1
  return Administration1(char)
def Administration7(char):
  check = events.Check(char, "will", -2)
  gain = events.Gain(char, {"dollars": 8})
  arrest = events.Arrested(char)
  deceive = events.PassFail(char, check, gain, arrest)
  return events.BinaryChoice(char, "Carry on Deception?", "Yes", "No", deceive, events.Nothing())

def Library1(char):
  check = events.Check(char, "will", -1)
  tome = events.Draw(char, "unique", 1) # TODO: this is actually draw the first tome
  move = events.ForceMovement(char, "University")
  return events.PassFail(char, check, tome, move)
def Library2(char):
  check = events.Check(char, "will", 0)
  move = events.ForceMovement(char, "University")
  spell = events.Draw(char, "spells", 2)
  unique = events.Draw(char, "unique", 1)
  cond = events.Conditional(char, check, "successes", {0: move, 1: spell, 2: unique})
  return events.Sequence([check, cond], char)
def Library3(char):
  check = events.Check(char, "lore", -2)
  die = events.DiceRoll(char, 1)
  gain = events.Gain(char, {"clues": die})
  loss = events.Loss(char, {"stamina": 2, "sanity": 2})
  return events.PassFail(char, check, events.Sequence([die, gain], char), loss)
def Library4(char):
  return events.Nothing() # TODO: GO TO DREAMLANDS!! DO NOT PASS GO! but do return here
def Library5(char):
  return events.Loss(char, {"sanity": 1})
def Library6(char):
  prereq = events.AttributePrerequisite(char, "dollars", 4, "at least")
  pay = events.Loss(char, {"dollars": 4})
  move = events.ForceMovement(char, "University")
  return events.PassFail(char, prereq, pay, move)
def Library7(char):
  check = events.Check(char, "luck", -2)
  money = events.Gain(char, {"dollars": 5})
  return events.PassFail(char, check, money, events.Nothing())

def Science1(char):
  return events.Bless(char)
def Science2(char):
  spell = events.Draw(char, "spells", 1)
  check = events.Check(char, "fight", -1)
  lose = events.Nothing() # TODO: lose an item of your choice
  fight = events.PassFail(char, check, events.Nothing(), lose)
  return events.Sequence([spell, fight], char) 
def Science3(char):
  prereq = events.AttributePrerequisite(char, "dollars", 2, "less than") # TODO: the money is a lie, it's actually number of spells
  unique = events.Draw(char, "unique", 1)
  move = events.ForceMovement(char, "University")
  return events.PassFail(char, prereq, events.Sequence([unique, move], char), events.Nothing())
def Science4(char):
  stamina = events.Loss(char, {"stamina": 2})
  ally = events.DrawSpecific(char, "allies", "Arm Wrestler") # TODO: prereq on the ally being in the deck
  return events.BinaryChoice(char, "Arm Wrestle?", "Yes", "No", events.Sequence([stamina, ally], char), events.Nothing())
def Science5(char):
  check = events.Check(char, "luck", 0)
  die = events.DiceRoll(char, 1)
  win = events.SplitGain(char, "stamina", "sanity", die)
  coffee = events.Gain(char, {"stamina": 1})
  return events.PassFail(char, check, events.Sequence([die, win], char), coffee)
def Science6(char):
  check = events.Check(char, "luck", -1)
  success = events.Nothing() # TODO: OH NO!!  Pick a new investigator...
  return events.PassFail(char, check, success, events.Nothing())
def Science7(char):
  check = events.Check(char, "lore", -2)
  die = events.DiceRoll(char, 1)
  stamina = events.Loss(char, {"stamina": die})
  close_gates = events.Nothing() # TODO: close all of the gates!
  move = events.ForceMovement(char, "Hospital")
  fail = events.Sequence([die, stamina, move], char)
  helping = events.PassFail(char, check, close_gates, fail)
  return events.BinaryChoice(char, "Offer to help?", "Yes", "No", helping, events.Nothing())

def Train3(char):
  return events.SplitGain(char, "stamina", "sanity", 2)

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
  loss = events.Nothing()  #TODO: Choose an item to lose
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

def Docks1(char):
  check = events.Check(char, "luck", -1)
  spell = events.Draw(char, "spells", 1)
  return events.PassFail(char, check, spell, events.Nothing())
def Docks2(char):
  # TODO: you should just be able to draw two items
  item1 = events.Draw(char, "common", 1)
  item2 = events.Draw(char, "common", 1)
  items = events.Sequence([item1, item2], char)
  check = events.Check(char, "luck", -1)
  success = events.Nothing()
  fail = events.Arrested(char)
  passfail = events.PassFail(char, check, success, fail)
  return events.Sequence([items, passfail], char)
def Docks3(char):
  check = events.Check(char, "fight", 0)
  dollars = events.Gain(char, {"dollars": 3}) # TODO: This is really dollars * number of successes
  move = events.ForceMovement(char, "Merchant")
  stamina = events.Loss(char, {"stamina": 1})
  cond= events.Conditional(char, check, "successes", {0: events.Sequence([stamina, move], char), 1: dollars})
  return events.Sequence([check, cond], char)
def Docks4(char):
  check = events.Check(char, "will", -1)
  item = events.Draw(char, "unique", 1)
  success = events.Sequence([events.Loss(char, {"sanity": 1}), item], char)
  fail = events.Sequence([events.Loss(char, {"sanity": 2}), item], char)
  return events.PassFail(char, check, success, fail)
def Docks5(char):
  check = events.Check(char, "speed", -1)
  loss = events.Loss(char, {"sanity": 1})
  return events.PassFail(char, check, events.Nothing(), loss)
def Docks6(char):
  check = events.Check(char, "will", 1)
  lost = events.Nothing() # TODO: Oh No, what time is it?  Where am I?  I'm lost in Time AND Space!
  return events.PassFail(char, check, events.Nothing(), lost)
def Docks7(char):
  check = events.Check(char, "luck", -1)
  draw = events.Draw(char, "common", 1)
  struggle = events.Loss(char, {"stamina": 3, "sanity": 1})
  return events.PassFail(char, check, draw, struggle)

def Unnamable1(char):
  loss = events.Loss(char, {"sanity": 2})
  # TODO: add prerequisite of ally being in deck
  ally = events.DrawSpecific(char, "allies", "Brave Guy")
  listen = events.Sequence([loss, ally], char)
  return events.BinaryChoice(char, "Listen to the tale?", "Yes", "No", listen, events.Nothing())
def Unnamable2(char):
  check = events.Check(char, "lore", -1)
  spell = events.Draw(char, "spells", 1)
  clues = events.Gain(char, {"clues": 2})
  delayed = events.Delayed(char)
  read = events.PassFail(char, check, spell, events.Sequence([clues, delayed], char))
  return events.BinaryChoice(char, "Read the manuscript?", "Yes", "No", read, events.Nothing())
def Unnamable3(char):
  # TODO: WHAT IS THAT THING??? IT LOOKS LIKE A GATE!
  return events.Nothing()
def Unnamable4(char):
  check = events.Check(char, "speed", -1)
  move = events.ForceMovement(char, "Merchant")
  loss = events.Loss(char, {"stamina": 2})
  return events.PassFail(char, check, move, loss)
def Unnamable5(char):
  check = events.Check(char, "luck", -1)
  unique = events.Draw(char, "unique", 1)
  loss = events.Loss(char, {"sanity": 1, "stamina": 2})
  return events.PassFail(char, check, unique, loss)
def Unnamable6(char):
  check = events.Check(char, "speed", -1)
  lost = events.Nothing() #TODO: I'm stuck inside a clock and I'm somewhere around Mars?
  return events.PassFail(char, check, events.Nothing(), lost)
def Unnamable7(char):
  check = events.Check(char, "luck", -1)
  unique = events.Draw(char, "unique", 1)
  return events.PassFail(char, check, unique, events.Nothing())

def Isle1(char):
  spell = events.Draw(char, "spells", 1)
  loss = events.Loss(char, {"sanity": 1})
  return events.Sequence([spell, loss], char)
def Isle2(char):
  check = events.Check(char, "sneak", -1)
  # TODO add prerequisite for Ally in deck
  ally = events.DrawSpecific(char, "allies", "Mortician")
  return events.PassFail(char, check, ally, events.Nothing())
def Isle3(char):
  stamina = events.Loss(char, {"stamina": 1})
  check = events.Check(char, "will", -1)
  sanity = events.Loss(char, {"sanity": 1})
  will = events.PassFail(char, check, events.Nothing(), sanity)
  return events.Sequence([stamina, will], char)
def Isle4(char):
  check = events.Check(char, "will", -1)
  return events.PassFail(char, check, events.Nothing(), events.Curse(char))
def Isle5(char):
  check = events.Check(char, "will", -2)
  sanity = events.Loss(char, {"sanity": 3})
  return events.PassFail(char, check, events.Nothing(), sanity)
def Isle6(char):
  return events.GainOrLoss(char, {"clues": 1}, {"sanity": 1})
def Isle7(char):
  check = events.Check(char, "sneak", -1)
  clues = events.Gain(char, {"clues": 2})
  return events.PassFail(char, check, clues, events.Nothing())

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
      "Merchant": [
        EncounterCard("Merchant1", {"Docks": Docks1, "Unnamable": Unnamable1, "Isle": Isle1}),
        EncounterCard("Merchant2", {"Docks": Docks2, "Unnamable": Unnamable2, "Isle": Isle2}),
        EncounterCard("Merchant3", {"Docks": Docks3, "Unnamable": Unnamable3, "Isle": Isle3}),
        EncounterCard("Merchant4", {"Docks": Docks4, "Unnamable": Unnamable4, "Isle": Isle4}),
        EncounterCard("Merchant5", {"Docks": Docks5, "Unnamable": Unnamable5, "Isle": Isle5}),
        EncounterCard("Merchant6", {"Docks": Docks6, "Unnamable": Unnamable6, "Isle": Isle6}),
        EncounterCard("Merchant7", {"Docks": Docks7, "Unnamable": Unnamable7, "Isle": Isle7}),
      ],      
      "Northside": [
        EncounterCard("Northside3", {"Train": Train3}),
      ],
      "Rivertown": [
        EncounterCard("Rivertown5", {"Store": Store5}),
      ],
      "Southside": [
        EncounterCard("Southside4", {"Society": Society4}),
      ],
      "University": [
        EncounterCard("University1", {"Administration": Administration1, "Library": Library1, "Science": Science1}),
        EncounterCard("University2", {"Administration": Administration2, "Library": Library2, "Science": Science2}),
        EncounterCard("University3", {"Administration": Administration3, "Library": Library3, "Science": Science3}),
        EncounterCard("University4", {"Administration": Administration4, "Library": Library4, "Science": Science4}),
        EncounterCard("University5", {"Administration": Administration5, "Library": Library5, "Science": Science5}),
        EncounterCard("University6", {"Administration": Administration6, "Library": Library6, "Science": Science6}),
        EncounterCard("University7", {"Administration": Administration7, "Library": Library7, "Science": Science7}),
      ],
  }
