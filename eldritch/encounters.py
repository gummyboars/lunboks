import eldritch.events as events
import eldritch.items as items
import eldritch.places as places


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
  draw2 = events.Sequence([events.Draw(char, "common", 1), events.Draw(char, "common", 1)], char)
  draw = events.GainAllyOrReward(char, "Traveling Salesman", draw2)
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
def Lodge2(char):
  check = events.Check(char, "fight", -1)
  draw = events.Draw(char, "unique", 1)
  ally = events.GainAllyOrReward(char, "Thief", draw)
  return events.PassFail(char, check, ally, events.Nothing())
def Lodge3(char):
  check = events.Check(char, "luck", -1)
  curse = events.BlessCurse(char, False)
  return events.PassFail(char, check, events.Nothing(), curse)
def Lodge4(char):
  prereq = events.AttributePrerequisite(char, "dollars", 3, "at least")
  pay = events.Loss(char, {"dollars": 3})
  check = events.Check(char, "will", -1)
  damage = events.Loss(char, {"stamina": 2})
  membership = events.MembershipChange(char, True)
  move = events.ForceMovement(char, "FrenchHill")
  resist = events.PassFail(char, check, move, events.Sequence([damage, move]))
  choice = events.BinaryChoice(char, "Join the Lodge?", "Yes", "No",
                               events.Sequence([pay, membership], char), resist)
  return events.PassFail(char, prereq, choice, resist)
def Lodge5(char):
  check = events.Check(char, "lore", -1)
  gain = events.Gain(char, {"clues": 3})
  loss = events.Loss(char, {"clues": float("inf")})
  move = events.ForceMovement(char, "FrenchHill")
  return events.PassFail(char, check, gain, events.Sequence([loss, move], char))
def Lodge6(char):
  # Hey, it has the same text!
  return Lodge4(char)
def Lodge7(char):
  check = events.Check(char, "sneak", -2)
  common1 = events.Draw(char, 'common', 1)
  common2 = events.Draw(char, 'common', 1)
  unique1 = events.Draw(char, "unique", 1)
  unique2 = events.Draw(char, "unique", 1)
  rolls = events.DiceRoll(char, 2)
  two_common = events.Sequence([common1, common2], char)
  two_unique = events.Sequence([unique1, unique2], char)
  one_each = events.Sequence([common1, unique1], char)
  cond = events.Conditional(
    char, rolls, "successes", { 0: two_common, 1: one_each, 2: two_unique, }
  )
  return events.PassFail(char, check, events.Sequence([rolls, cond], char), events.Nothing())

def Sanctum1(char):
  check = events.Check(char, "luck", -2)
  gain = events.Draw(char, "unique", float("inf"))
  return events.PassFail(char, check, gain, events.Nothing())
def Sanctum2(char):
  check = events.Check(char, "luck", -1)
  spend = events.Loss(char, {"sanity": 1})
  success = events.Nothing() # TODO: claim a monster on the board as a trophy
  nothing = events.Nothing()
  seq = events.Sequence([
    spend, events.PassFail(char, check, success, nothing)
  ])
  choice = events.BinaryChoice(char, "Cast a banishment spell?", "Yes", "No", seq, nothing)
  return choice
def Sanctum3(char):
  choice = events.MultipleChoice(
    char, "How many sanity do you want to trade for clues?", list(range(min(char.sanity, 3)+1))
  )
  gain = events.GainOrLoss(char, {"clues": choice}, {"sanity": choice})
  return events.Sequence([choice, gain], char)
def Sanctum4(char):
  prereq = events.AttributePrerequisite(char, "dollars", 3, "at least")
  dues = events.Loss(char, {"dollars": 3})
  dreams = events.Loss(char, {"sanity": 2})
  membership = events.MembershipChange(char, False)
  decline = events.Sequence([membership, dreams], char)
  return events.PassFail(
    char,
    prereq,
    events.BinaryChoice(char, "Pay your dues?", "Spend $3", "Decline", dues, decline),
    decline
  )
def Sanctum5(char):
  check = events.Check(char, "luck", -2)
  curse = events.BlessCurse(char, False)
  return events.PassFail(char, check, events.Nothing(), curse)
def Sanctum6(char):
  return events.Nothing() #TODO: A monster appears
def Sanctum7(char):
  prereq = events.AttributePrerequisite(char, "clues", 2, "at least")
  check = events.Check(char, "lore", -2)
  close = events.Nothing() # TODO: Close a gate
  nothing = events.Nothing()
  cost = events.Loss(char, {"clues": 2, "sanity": 1})
  ceremony = events.PassFail(char, check, close, nothing)
  seq = events.Sequence([cost, ceremony], char)
  participate = events.BinaryChoice(char, "Participate in a gating ceremony?", "Yes", "No", seq, nothing)
  return events.PassFail(char, prereq, participate, nothing)

def Witch1(char):
  ally = events.DrawSpecific(char, "allies", "Police Detective") # TODO: prereq on the ally being in the deck
  check = events.Check(char, "lore", -1)
  return events.PassFail(char, check, ally, events.Nothing())
def Witch2(char):
  check = events.Check(char, "luck", -1)
  draw = events.Draw(char, "unique", 1)
  return events.PassFail(char, check, draw, events.Nothing())
def Witch3(char):
  check = events.Check(char, "luck", 0)
  cond = events.Conditional(
    char, check, "successes",
    {
      0: events.Loss(char, {'sanity': 3}),
      1: events.Delayed(char),
      2: events.Loss(char, {'stamina': 1}),
      3: events.Gain(char, {'stamina': 3})
    }
  )
  return events.Sequence([check, cond], char)
def Witch4(char):
  return events.Loss(char, {"sanity": 1})
def Witch5(char):
  return events.OpenGate("Witch")
def Witch6(char):
  die = events.DiceRoll(char, 1)
  gain = events.GainOrLoss(char, {"clues": die}, {"sanity": die})
  return events.Sequence([die, gain], char)
def Witch7(char):
  check = events.Check(char, "will", -2)
  spell = events.Draw(char, "spells", 1)
  n_items_to_lose = int(len(char.possessions)//2)
  #TODO: Lose half your items properly
  loss_choice = events.ItemCountChoice(
      char, "Which items are you missing when you wake up?", n_items_to_lose
  )
  loss = events.Sequence([
    loss_choice,
    #TODO: Lose items that you chose
  ])
  return events.PassFail(char, check, spell, loss)

def Cave1(char):
  check = events.Check(char, "luck", 0)
  san_loss = events.Loss(char, {'sanity': 1})
  monster = events.Sequence(
    [
      san_loss,
      # TODO: Implement a monster appears
    ], char
  )
  draw = events.Draw(char, "common", 1)
  cond = events.Conditional(char, check, "successes", {0: monster, 1: san_loss, 2: draw})
  return events.Sequence([check, cond], char)
def Cave2(char):
  return events.Loss(char, {"sanity": 1})
def Cave3(char):
  check = events.Check(char, "speed", -1)
  return events.PassFail(char, check, events.Nothing(), events.Loss(char, {"stamina":1}))
def Cave4(char):
  # TODO: A monster appears
  return events.Nothing()
def Cave5(char):
  check = events.Check(char, "lore", -2)
  return events.PassFail(
    char,
    check,
    events.Nothing(),
    events.Sequence([events.Loss(char, {'stamina': 1}), events.Delayed(char)], char)
  )
def Cave6(char):
  prereq = events.ItemPrerequisite(char, "Whiskey")
  check = events.Check(char, "luck", -2)
  ally = events.GainAllyOrReward(char, "Tough Guy", events.Draw(char, "common", draw_count=1, target_type=items.Weapon))
  give_whiskey = events.DiscardNamed(char, "Whiskey")
  gain = events.PassFail(char, check, ally, events.Nothing())
  seq = events.Sequence([give_whiskey, ally], char)
  choose_give_food = events.BinaryChoice(char, "Discard whiskey to pass automatically?", "Yes", "No", seq, gain)
  return events.PassFail(char, prereq, choose_give_food, gain)
def Cave7(char):
  check = events.Check(char, "luck", 0)
  evil = events.Loss(char, {"sanity": 1, "stamina": 1})
  diary = events.GainOrLoss(char, gains={'clues': 1}, losses={'sanity': 1})
  tome = events.Draw(char, "unique", 1) # TODO: this is actually draw the first tome
  cond = events.Conditional(char, check, "successes", {0: evil, 1: diary, 2: tome})
  read = events.Sequence([check, cond], char)
  return events.BinaryChoice(char, "Do you read the book?", "Yes", "No", read, events.Nothing())


def Store1(char):
  return events.Gain(char, {"dollars": 1})
def Store2(char):
  return events.Nothing()
def Store3(char):
  #TODO: Sell any common item for twice the price
  return events.Nothing()
def Store4(char):
  return events.Loss(char, {"sanity": 1})
def Store5(char):
  check = events.Check(char, "will", -2)
  draw = events.Draw(char, "common", 3)
  return events.PassFail(char, check, draw, events.Nothing())
def Store6(char):
  prereq = events.AttributePrerequisite(char, "dollars", 1, "at least")
  check = events.Check(char, "lore", -2)
  pay = events.Loss(char, {'dollars': 1})
  guess = events.PassFail(char, check, events.Gain(char, {'dollars': 5}), events.Nothing())
  do_guess = events.Sequence([pay, guess], char)
  choose_guess = events.BinaryChoice(
    char, "Pay $1 to guess how many beans the jar contains?", "Yes", "No", do_guess, events.Nothing()
  )
  return events.PassFail(char, prereq, choose_guess, events.Nothing())
def Store7(char):
  return events.Draw(char, "common", 1)

def Graveyard1(char):
  #TODO: A monster appears
  return events.Nothing()
def Graveyard2(char):
  check = events.Check(char, "lore", -1)
  fail = events.ForceMovement(char, "Rivertown")
  succeed = events.GainOrLoss(char, gains={'clues': 1}, losses={'sanity': 1})
  return events.PassFail(char, check, succeed, fail)
def Graveyard3(char):
  check = events.Check(char, "combat", -2)
  victory = events.Sequence([events.Draw(char, 'unique', 1), events.Gain(char, {'clues': 1})])
  damage = events.DiceRoll(char, 1)
  defeat = events.Loss(char, {'stamina': damage})
  return events.PassFail(char, check, victory, events.Sequence([damage, defeat], char))
def Graveyard4(char):
  #TODO: Trade monster trophies for Painter
  return events.Nothing()
def Graveyard5(char):
  check = events.Check(char, 'luck', -2)
  #TODO: You may move to any location
  move = events.Nothing()
  clues = events.Gain(char, {"clues": 2})
  rubbings = events.Sequence([clues, move], char)
  return events.PassFail(char, check, rubbings, events.Nothing())
def Graveyard6(char):
  return events.Gain(char, {"sanity": 2})
def Graveyard7(char):
  return events.Nothing()

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
  move = events.ForceMovement(char, "Dreamlands1")
  # TODO: don't hard-code.
  enc = events.GateEncounter(char, "Dreamlands", {"blue", "green", "red", "yellow"})
  ret = events.ForceMovement(char, "Library")
  return events.Sequence([move, enc, ret], char)
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
  ally = events.GainAllyOrReward(char, "Arm Wrestler", events.Gain(char, {"dollars": 5}))
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

def Shop1(char):
  check = events.Check(char, "luck", -2)
  curse = events.Curse(char)
  return events.PassFail(char, check, events.Nothing(), curse)
def Shop2(char):
  check = events.Check(char, "fight", -1)
  move = events.ForceMovement(char, "Abyss1")
  enc = events.GateEncounter(char, "Abyss", {"blue", "red"})  # TODO: don't hard-code.
  ret = events.ForceMovement(char, "Shop")
  abyss = events.Sequence([move, enc, ret], char)
  return events.PassFail(char, check, events.Nothing(), abyss)
def Shop3(char):
  common = events.Nothing() # TODO: search through the common deck and purchase any item
  unique = events.Nothing() # TODO: search through the unique deck and purchase any item
  choice = events.BinaryChoice(char, "Purchase a Common or Unique item?",
                              "Common", "Unique", common, unique)
  return choice
def Shop4(char):
  check = events.Check(char, "luck",-1)
  prereq = events.AttributePrerequisite(char, "dollars", 1, "at least") # TODO: This is actually a check that you an item
  loss = events.Nothing() # TODO: Lose one item of your choice
  newEvent = events.Nothing() # TODO: draw a new encounter
  fail = events.PassFail(char, prereq, loss, newEvent)
  return events.PassFail(char, check, events.Nothing(), fail)
def Shop5(char):
  # TODO: Oh Dear:  3 common items for sale, any player may purchase 1 or more
  # conflicts are decided by the player that drew the card
  return events.Nothing()
def Shop6(char):
  check = events.Check(char, "luck", -1)
  commonUnique = events.Nothing() # TODO: you may purchase the top item of the common and/or unique deck
  common = events.Nothing() # TODO: you may purchase the top item of the common deck
  return events.PassFail(char, check, commonUnique, common)
def Shop7(char):
  return events.Nothing() # TODO: draw a mythos card, move to the gate location shown, have an encounter there

def Newspaper1(char):
  money = events.Gain(char, {"dollars": 2})
  move = events.Nothing() # TODO: move to any location or street, if a location, have an event
  return events.Sequence([money, move], char)
def Newspaper2(char):
  return events.Gain(char, {"dollars": 5})
def Newspaper3(char):
  return events.StatusChange(char, "retainer")
def Newspaper4(char):
  # Newspaper 4 is the same as Newspaper 3
  return Newspaper3(char)
def Newspaper5(char):
  check = events.Check(char, "lore", -1)
  clues = events.Gain(char, {"clues": 3})
  return events.PassFail(char, check, clues, events.Nothing())
def Newspaper6(char):
  check = events.Check(char, "luck", -1)
  clues = events.Gain(char, {"clues": 1})
  return events.PassFail(char, check, clues, events.Nothing())
def Newspaper7(char):
  return events.Loss(char, {"sanity": 1})

def Train1(char):
  check = events.Check(char, "sneak", -1)
  unique = events.Draw(char, "unique", 1)
  arrested = events.Arrested(char)
  return events.PassFail(char, check, unique, arrested)
def Train2(char):
  check = events.Check(char, "speed", -2)
  spell = events.Draw(char, "spells", 1)
  die = events.DiceRoll(char, 1)
  sanity = events.Loss(char, {"sanity": die})
  return events.PassFail(char, check, spell, events.Sequence([die, sanity], char))
def Train3(char):
  return events.SplitGain(char, "stamina", "sanity", 2)
def Train4(char):
  return events.Nothing() # TODO: draw the top common item and purchase it for +1 if you wish
def Train5(char):
  move = events.Nothing() # TODO: Move to a street or location of your choice and have an encounter there
  choice = events.BinaryChoice(char, "Accept a ride?", "Yes", "No",
                              move, events.Nothing())
  return choice
def Train6(char):
  prereq = events.AttributePrerequisite(char, "dollars", 3, "at least")
  pay = events.Loss(char, {"dollars": 3})
  check = events.Check(char, "luck", -2)
  common = events.Draw(char, "common", 1)
  unique = events.Draw(char, "unique", 1)
  item = events.PassFail(char, check, unique, common)
  choice = events.BinaryChoice(char, "Claim item left at lost and found for $3?", "Yes", "No",
                               events.Sequence([pay, item], char), events.Nothing())
  return events.PassFail(char, prereq, choice, events.Nothing())
def Train7(char):
  check = events.Check(char, "luck", -1)
  unique = events.Draw(char, "unique", 1)
  die = events.DiceRoll(char, 1)
  stab = events.Loss(char, {"stamina": die})
  return events.PassFail(char, check, unique, events.Sequence([die, stab], char))

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
  ally = events.GainAllyOrReward(char, "Fortune Teller", events.Gain(char, {'clues': 2}))
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
  fail = events.OpenGate("Square")
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
  lost = events.LostInTimeAndSpace(char)
  return events.PassFail(char, check, events.Nothing(), lost)
def Docks7(char):
  check = events.Check(char, "luck", -1)
  draw = events.Draw(char, "common", 1)
  struggle = events.Loss(char, {"stamina": 3, "sanity": 1})
  return events.PassFail(char, check, draw, struggle)

def Unnamable1(char):
  loss = events.Loss(char, {"sanity": 2})
  ally = events.GainAllyOrReward(char, "Brave Guy", events.Gain(char, {"clues": 3}))
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
  return events.OpenGate("Unnamable")
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
  lost = events.LostInTimeAndSpace(char)
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
  reward = events.Gain(char, {"sanity": float("inf"), "stamina": float("inf")})
  ally = events.GainAllyOrReward(char, "Mortician", reward)
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

def Hospital1(char):
  prereq = events.AttributePrerequisite(char, "clues", 1, "at least")
  return events.PassFail(char, prereq, events.Loss(char, {"clues": 1}), events.Nothing())
def Hospital2(char):
  sanity = events.Loss(char, {"sanity": 1})
  prep = events.CombatChoice(char, "Choose weapons to fight the corpse")
  check = events.Check(char, "combat", -1)
  won = events.Gain(char, {"clues": 1})
  lost = events.ForceMovement(char, "Uptown")
  cond = events.Conditional(char, check, "successes", {0: lost, 1: won})
  return events.Sequence([sanity, prep, check, cond], char)
def Hospital3(char):
  die = events.DiceRoll(char, 1)
  cond = events.Conditional(
    char, die, "sum",
    {0: events.Nothing(), 1: events.Gain(char, {"stamina": die}), 4: events.Nothing()}
  )
  return events.Sequence([die, cond], char)
def Hospital4(char):
  check = events.Check(char, "luck", -1)
  gain = events.Gain(char, {"sanity": 2, "dollars": 3})
  loss = events.Loss(char, {"sanity": 2})
  move = events.ForceMovement(char, "Uptown")
  fail = events.Sequence([loss, move], char)
  return events.PassFail(char, check, gain, fail)
def Hospital5(char):
  check = events.Check(char, "sneak", -1)
  gain = events.Draw(char, "spells", 1)
  return events.PassFail(char, check, gain, events.Nothing())
def Hospital6(char):
  check = events.Check(char, "will", -1)
  item = events.Draw(char, "unique", 1)
  fail1 = events.Loss(char, {"sanity": 1})
  fail2 = events.ForceMovement(char, "Uptown")
  fail = events.Sequence([fail1, fail2], char)
  return events.PassFail(char, check, item, fail)
def Hospital7(char):
  check = events.Check(char, "lore", 0)
  clue = events.Gain(char, {"clues": 1})
  return events.PassFail(char, check, clue, events.Nothing())

def Woods1(char):
  box = events.Check(char, "luck", 0)
  foot = events.Loss(char, {"sanity": 1})
  common = events.Draw(char, "common", 1)
  unique = events.Draw(char, "unique", 1)
  jewelry = events.Gain(char, {"dollars": 10})
  cond = events.Conditional(char, box, "successes", {0: foot, 1: common, 2: unique, 3: jewelry})
  open_box = events.Sequence([box, cond], char)
  return events.BinaryChoice(char, "Open the locked box?", "Yes", "No", open_box, events.Nothing())
def Woods2(char):
  check = events.Check(char, "sneak", -1)
  make_check = events.PassFail(char, check, events.Nothing(), events.Loss(char, {"stamina": 2}))
  leave = events.ForceMovement(char, "Uptown")
  return events.Sequence([make_check, leave], char)
def Woods3(char):
  check = events.Check(char, "sneak", -2)
  shotgun = events.DrawSpecific(char, "common", "Shotgun")
  fail = events.Sequence([events.Loss(char, {'stamina': 2}), events.ForceMovement(char, "Uptown")], char)
  return events.PassFail(char, check, shotgun, fail)
def Woods4(char):
  check = events.Check(char, "luck", -1)
#  bushwhack1a = events.ItemChoice(char, "Choose first item to lose")
#  bushwhack1b = events.DiscardSpecific(char, bushwhack1a)
#  bushwhack1c = events.ItemChoice(char, "Choose second item to lose")
#  bushwhack1d = events.DiscardSpecific(char, bushwhack1c)
  n_items = min(len(char.possessions), 2)
  items = events.ItemCountChoice(char, f"Choose {n_items} to discard", n_items)
  bushwhack2 = events.Loss(char, {"stamina": 2})
  bushwhack = events.Sequence([
#    bushwhack1a,
#    bushwhack1b,
#    bushwhack1c,
#    bushwhack1d,
    items,
    events.DiscardSpecific(char, items),
    bushwhack2,
  ], char)
  return events.PassFail(char, check, events.Nothing(), bushwhack)
def Woods5(char):
  #TODO: Check whether you have food to give to the doggy
  prereq = events.ItemPrerequisite(char, "Food")
  check = events.Check(char, "speed", -2)
  dog = events.GainAllyOrReward(char, "Dog", events.Gain(char, {"dollars": 3}))
  give_food = events.DiscardNamed(char, "Food")
  catch = events.PassFail(char, check, dog, events.Nothing())
  seq = events.Sequence([give_food, dog], char)
  choose_give_food = events.BinaryChoice(char, "Give food to the dog?", "Yes", "No", seq, catch)
  return events.PassFail(char, prereq, choose_give_food, catch)
def Woods6(char):
  return events.OpenGate("Woods")
def Woods7(char):
  choice = events.MultipleChoice(
    char, "Which would you like to gain?", ["A skill", "2 spells", "4 clues"]
  )
  skill = events.Draw(char, "skills", 1)
  spells = events.Draw(char, "spells", 2) #TODO: Implement keep_count
  clues = events.Gain(char, {"clues": 4})
  gain = events.Conditional(char, choice, "choice_index", {0: skill, 1: spells, 2: clues})
  gains = events.Sequence([choice, gain], char)
  check = events.Check(char, "lore", -2)
  cond = events.PassFail(char, check, gains, events.Nothing())
  turn = events.LoseTurn(char)
  seq = events.Sequence([turn, cond], char)
  return events.BinaryChoice(char, "Share in the old wise-guy's wisdom?", "Yes", "No", seq, events.Nothing())

def Shoppe1(char):
  return events.Loss(char, {"sanity": 1})
def Shoppe2(char):
  #TODO: Implement "Turn the top card of one location deck face up, next player to have an enounter there draws that encounter"
  return events.Nothing()
  # What follows is the start of an implementation
  streets = {
    placename: place
    for placename, place in char.game_state.places.items()
    if isinstance(place, places.Street)
  }
  choice = events.MultipleChoice(
    char,
    "Choose a location deck to view the top card of",
    list(keys(streets))
  )
  return choice
def Shoppe3(char):
  prereq = events.AttributePrerequisite(char, "dollars", 5, "at least")
  luck = events.Check(char, "luck", 0)
  dice = events.DiceRoll(char, 2)
  coins = events.Sequence([dice, events.Gain(char, {"dollars": dice})], char)
  # TODO: add a keep counter
  jackpot = events.Draw(char, "unique", 2)
  cond = events.Conditional(char, luck, "successes", {0: events.Nothing(), 1: coins, 2: jackpot})
  buy = events.Sequence([events.Loss(char, {"dollars": 5}), luck, cond], char)
  box = events.BinaryChoice(char, "Buy the locked trunk?", "Yes", "No", buy, events.Nothing())
  return events.PassFail(char, prereq, box, events.Nothing())
def Shoppe4(char):
  check = events.Check(char, "lore", -1)
  curse = events.Curse(char)
  return events.PassFail(char, check, events.Nothing(), curse)
def Shoppe5(char):
  return events.Gain(char, {"clues": 1})
def Shoppe6(char):
  check = events.Check(char, "lore", -1)
  #TODO: Implement buying at a discount
  underpriced = events.Nothing()
  return events.PassFail(char, check, underpriced, events.Nothing())
def Shoppe7(char):
  move = events.ForceMovement(char, "Uptown")
  san = events.Loss(char, {"sanity": 1})
  return events.Sequence([move, san], char)


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
        EncounterCard("FrenchHill1", {"Lodge": Lodge1, "Witch": Witch1, "Sanctum": Sanctum1}),
        EncounterCard("FrenchHill2", {"Lodge": Lodge2, "Witch": Witch2, "Sanctum": Sanctum2}),
        EncounterCard("FrenchHill3", {"Lodge": Lodge3, "Witch": Witch3, "Sanctum": Sanctum3}),
        EncounterCard("FrenchHill4", {"Lodge": Lodge4, "Witch": Witch4, "Sanctum": Sanctum4}),
        EncounterCard("FrenchHill5", {"Lodge": Lodge5, "Witch": Witch5, "Sanctum": Sanctum5}),
        EncounterCard("FrenchHill6", {"Lodge": Lodge6, "Witch": Witch6, "Sanctum": Sanctum6}),
        EncounterCard("FrenchHill7", {"Lodge": Lodge7, "Witch": Witch7, "Sanctum": Sanctum7}),
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
        EncounterCard("Northside1", {"Shop": Shop1, "Newspaper": Newspaper1, "Train": Train1}),
        EncounterCard("Northside2", {"Shop": Shop2, "Newspaper": Newspaper2, "Train": Train2}),
        EncounterCard("Northside3", {"Shop": Shop3, "Newspaper": Newspaper3, "Train": Train3}),
        EncounterCard("Northside4", {"Shop": Shop4, "Newspaper": Newspaper4, "Train": Train4}),
        EncounterCard("Northside5", {"Shop": Shop5, "Newspaper": Newspaper5, "Train": Train5}),
        EncounterCard("Northside6", {"Shop": Shop6, "Newspaper": Newspaper6, "Train": Train6}),
        EncounterCard("Northside7", {"Shop": Shop7, "Newspaper": Newspaper7, "Train": Train7}),
      ],
      "Rivertown": [
        EncounterCard("Rivertown1", {"Cave": Cave1, "Store": Store1, "Graveyard": Graveyard1}),
        EncounterCard("Rivertown2", {"Cave": Cave2, "Store": Store2, "Graveyard": Graveyard2}),
        EncounterCard("Rivertown3", {"Cave": Cave3, "Store": Store3, "Graveyard": Graveyard3}),
        EncounterCard("Rivertown4", {"Cave": Cave4, "Store": Store4, "Graveyard": Graveyard4}),
        EncounterCard("Rivertown5", {"Cave": Cave5, "Store": Store5, "Graveyard": Graveyard5}),
        EncounterCard("Rivertown6", {"Cave": Cave6, "Store": Store6, "Graveyard": Graveyard6}),
        EncounterCard("Rivertown7", {"Cave": Cave7, "Store": Store7, "Graveyard": Graveyard7}),
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
      "Uptown": [
        EncounterCard("Uptown1", {"Hospital": Hospital1, "Woods": Woods1, "Shoppe": Shoppe1}),
        EncounterCard("Uptown2", {"Hospital": Hospital2, "Woods": Woods2, "Shoppe": Shoppe2}),
        EncounterCard("Uptown3", {"Hospital": Hospital3, "Woods": Woods3, "Shoppe": Shoppe3}),
        EncounterCard("Uptown4", {"Hospital": Hospital4, "Woods": Woods4, "Shoppe": Shoppe4}),
        EncounterCard("Uptown5", {"Hospital": Hospital5, "Woods": Woods5, "Shoppe": Shoppe5}),
        EncounterCard("Uptown6", {"Hospital": Hospital6, "Woods": Woods6, "Shoppe": Shoppe6}),
        EncounterCard("Uptown7", {"Hospital": Hospital7, "Woods": Woods7, "Shoppe": Shoppe7}),
      ]
  }
