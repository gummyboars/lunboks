import operator

from eldritch import events
from eldritch import items
from eldritch import mythos
from eldritch import values
from eldritch.monsters import EventMonster


class EncounterCard:

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


class CardRevealer(mythos.GlobalEffect):
  def __init__(self, choice):
    self.choice = choice

  @property
  def name(self):
    if self.choice.choice is not None:
      return "Next " + self.choice.choice + " Card"
    return "Next Card"

  def get_trigger(self, event, state):
    if not isinstance(event, events.DrawEncounter):
      return None
    if event.neighborhood.name != self.choice.choice:
      return None
    return events.RemoveGlobalEffect(self)

  def json_repr(self, state):
    return {
        "name": state.places[self.choice.choice].encounters[0].name,
        "annotation": "Next Card",
    }


def Diner1(char):
  spend = values.RangeSpendPrerequisite("dollars", 1, 6)
  dollar_choice = events.SpendChoice(
      char, "Spend money to restore stamina and/or sanity?", ["Spend", "No Thanks"],
      spends=[spend, None],
  )
  gain = events.SplitGain(char, "stamina", "sanity", values.SpendCount(dollar_choice, "dollars"))
  cond = events.Conditional(char, dollar_choice, "choice_index", {0: gain, 1: events.Nothing()})
  return events.Sequence([dollar_choice, cond], char)


def Diner2(char):
  return events.DrawSpecific(char, "common", "Food")


def Diner3(char):
  gain = events.Gain(char, {"stamina": 2})
  return events.BinarySpend(char, "dollars", 1, "Pay $1 for pie?", "Pay $1", "Go Hungry", gain)


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
  gain = events.Gain(char, {"dollars": values.Die(die)})
  check = events.Check(char, "sneak", -1)
  return events.PassFail(char, check, events.Sequence([die, gain]), move)


def Roadhouse1(char):
  draw2 = events.Draw(char, "common", 2, keep_count=2)
  draw = events.GainAllyOrReward(char, "Traveling Salesman", draw2)
  return events.BinarySpend(char, "clues", 3, "Spend 3 clues for an ally?", "Yes", "No", draw)


def Roadhouse2(char):
  check = events.Check(char, "luck", -1)
  gain = events.Gain(char, {"dollars": 5})
  dollar_loss = events.Loss(char, {"dollars": 3})
  stamina_loss = events.Loss(char, {"stamina": 1})
  move = events.ForceMovement(char, "Easttown")
  prereq = values.AttributePrerequisite(char, "dollars", 3, "at least")
  loss = events.PassFail(char, prereq, dollar_loss, events.Sequence([stamina_loss, move], char))
  return events.PassFail(char, check, gain, loss)


def Roadhouse3(char):
  return events.DrawSpecific(char, "common", "Whiskey")


def Roadhouse4(char):
  return events.Nothing()  # TODO buying stuff


def Roadhouse5(char):
  return events.Nothing()  # TODO monster cup


def Roadhouse6(char):
  check = events.Check(char, "will", -1)
  clues = events.Gain(char, {"clues": 2})
  move = events.ForceMovement(char, "Easttown")
  dollars = events.Loss(char, {"dollars": float("inf")})
  prereq = values.ItemCountPrerequisite(char, 1, "at least")
  choice = events.ItemCountChoice(char, "Choose an item to lose", 1)
  discard = events.DiscardSpecific(char, choice)
  item = events.Sequence([choice, discard], char)
  loss = events.BinaryChoice(
      char, "Lose an item or all your money?", "Item", "Money", item, dollars, prereq,
  )
  # NOTE: we are explicitly using ItemCountChoice instead of ItemLossChoice here because we do not
  # believe it is okay for a player with only a derringer to choose to lose an item, and then avoid
  # losing anything by claiming that the derringer cannot be lost or stolen.
  return events.PassFail(char, check, clues, events.Sequence([move, loss], char))


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
  loss = events.LoseItems(char, float("inf"), "Discard your weapons", item_type="weapon")
  return events.BinarySpend(
      char, "dollars", 5, "Bribe Sheriff?", "Bribe ($5)", "Discard Weapons", events.Nothing(), loss,
  )


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
  check = events.Check(char, "will", -1)
  damage = events.Loss(char, {"stamina": 3})
  membership = events.MembershipChange(char, True)
  move = events.ForceMovement(char, "FrenchHill")
  resist = events.PassFail(char, check, move, events.Sequence([damage, move], char))
  return events.BinarySpend(
      char, "dollars", 3, "Pay $3 to join the Lodge?", "Yes", "No", membership, resist,
  )


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
  common1 = events.Draw(char, "common", 1)
  unique1 = events.Draw(char, "unique", 1)
  rolls = events.DiceRoll(char, 2)
  two_common = events.Draw(char, "common", 2, keep_count=2)
  two_unique = events.Draw(char, "unique", 2, keep_count=2)
  one_each = events.Sequence([common1, unique1], char)
  cond = events.Conditional(
      char, rolls, "successes", {0: two_common, 1: one_each, 2: two_unique, }
  )
  return events.PassFail(char, check, events.Sequence([rolls, cond], char), events.Nothing())


def Sanctum1(char):
  check = events.Check(char, "luck", -2)
  gain = events.Draw(char, "unique", float("inf"))
  return events.PassFail(char, check, gain, events.Nothing())


def Sanctum2(char):
  check = events.Check(char, "luck", -1)
  choose = events.MonsterOnBoardChoice(char, "Choose a monster to take as a trophy")
  take = events.ForceTakeTrophy(char, choose)
  success = events.Sequence([choose, take], char)
  nothing = events.Nothing()
  seq = events.PassFail(char, check, success, nothing)
  # TODO: Reach consensus on whether this is may or must spend 1 sanity
  # TODO: Should we prevent the character from choosing yes if there are no monster on the board?
  return events.BinarySpend(char, "sanity", 1, "Cast a banishment spell?", "Yes", "No", seq)


def Sanctum3(char):
  # NOTE: this card does not say "spend"; it specifically says lose.
  choice = events.MultipleChoice(
      char, "How many sanity do you want to trade for clues?", list(range(min(char.sanity, 3)+1))
  )
  gain = events.GainOrLoss(
      char,
      {"clues": values.Calculation(choice, "choice")},
      {"sanity": values.Calculation(choice, "choice")},
  )
  return events.Sequence([choice, gain], char)


def Sanctum4(char):
  dreams = events.Loss(char, {"sanity": 2})
  membership = events.MembershipChange(char, False)
  decline = events.Sequence([membership, dreams], char)
  return events.BinarySpend(
      char, "dollars", 3, "Pay your dues?", "Spend $3", "Decline", events.Nothing(), decline,
  )


def Sanctum5(char):
  check = events.Check(char, "luck", -2)
  curse = events.BlessCurse(char, False)
  return events.PassFail(char, check, events.Nothing(), curse)


def Sanctum6(char):
  return events.Nothing()  # TODO: A monster appears


def Sanctum7(char):
  # TODO: there has to actually be a gate open for you to do this.
  spend = values.ExactSpendPrerequisite({"clues": 2, "sanity": 1})
  check = events.Check(char, "lore", -2)
  close = events.Nothing()  # TODO: Close a gate
  ceremony = events.PassFail(char, check, close, events.Nothing())
  choice = events.SpendChoice(
      char, "Participate in a gating ceremony?", ["Yes", "No"], spends=[spend, None],
  )
  cond = events.Conditional(char, choice, "choice_index", {0: ceremony, 1: events.Nothing()})
  return events.Sequence([choice, cond], char)


def WitchHouse1(char):
  reward = events.Gain(char, {"clues": 2})
  ally = events.GainAllyOrReward(char,  "Police Detective", reward)
  check = events.Check(char, "lore", -1)
  return events.PassFail(char, check, ally, events.Nothing())


def WitchHouse2(char):
  check = events.Check(char, "luck", -1)
  draw = events.Draw(char, "unique", 1)
  return events.PassFail(char, check, draw, events.Nothing())


def WitchHouse3(char):
  check = events.Check(char, "luck", 0)
  cond = events.Conditional(
      char, check, "successes",
      {
          0: events.Loss(char, {"sanity": 3}),
          1: events.Delayed(char),
          2: events.Loss(char, {"stamina": 1}),
          3: events.Gain(char, {"stamina": 3})
      },
  )
  return events.Sequence([check, cond], char)


def WitchHouse4(char):
  return events.Loss(char, {"sanity": 1})


def WitchHouse5(char):
  return events.OpenGate("WitchHouse")


def WitchHouse6(char):
  die = events.DiceRoll(char, 1)
  gain = events.GainOrLoss(char, {"clues": values.Die(die)}, {"sanity": values.Die(die)})
  return events.Sequence([die, gain], char)


def WitchHouse7(char):
  check = events.Check(char, "will", -2)
  spell = events.Draw(char, "spells", 1)
  lose_count = values.Calculation(
      values.ItemDeckCount(char, {"common", "unique", "spells", "tradables"}), None,
      operator.floordiv, 2,
  )
  loss = events.LoseItems(char, lose_count, "Which items are you missing when you wake up?")
  return events.PassFail(char, check, spell, loss)


def Cave1(char):
  check = events.Check(char, "luck", 0)
  san_loss = events.Loss(char, {"sanity": 1})
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
  return events.PassFail(char, check, events.Nothing(), events.Loss(char, {"stamina": 1}))


def Cave4(char):
  # TODO: A monster appears
  return events.Nothing()


def Cave5(char):
  check = events.Check(char, "lore", -2)
  return events.PassFail(
      char,
      check,
      events.Nothing(),
      events.Sequence([events.Loss(char, {"stamina": 1}), events.Delayed(char)], char),
  )


def Cave6(char):
  prereq = values.ItemPrerequisite(char, "Whiskey")
  check = events.Check(char, "luck", -2)
  ally = events.GainAllyOrReward(  # TODO: this should be unaffected by the salesman
      char, "Tough Guy", events.Draw(char, "common", draw_count=1, target_type=items.Weapon),
  )
  give_whiskey = events.DiscardNamed(char, "Whiskey")
  gain = events.PassFail(char, check, ally, events.Nothing())
  seq = events.Sequence([give_whiskey, ally], char)
  return events.BinaryChoice(
      char, "Discard whiskey to pass automatically?", "Yes", "No", seq, gain, prereq)


def Cave7(char):
  check = events.Check(char, "luck", 0)
  evil = events.Loss(char, {"sanity": 1, "stamina": 1})
  diary = events.GainOrLoss(char, gains={"clues": 1}, losses={"sanity": 1})
  tome = events.Draw(char, "unique", 1)  # TODO: this is actually draw the first tome
  cond = events.Conditional(char, check, "successes", {0: evil, 1: diary, 2: tome})
  read = events.Sequence([check, cond], char)
  return events.BinaryChoice(char, "Do you read the book?", "Yes", "No", read, events.Nothing())


def Store1(char):
  return events.Gain(char, {"dollars": 1})


def Store2(char):
  return events.Nothing()


def Store3(char):
  return events.Sell(char, {"common"}, 1, discount_type="rate", discount=-1)


def Store4(char):
  return events.Loss(char, {"sanity": 1})


def Store5(char):
  check = events.Check(char, "will", -2)
  draw = events.Draw(char, "common", 3)
  return events.PassFail(char, check, draw, events.Nothing())


def Store6(char):
  check = events.Check(char, "lore", -2)
  guess = events.PassFail(char, check, events.Gain(char, {"dollars": 5}), events.Nothing())
  return events.BinarySpend(
      char, "dollars", 1, "Pay $1 to guess how many beans the jar contains?", "Yes", "No", guess,
  )


def Store7(char):
  return events.Draw(char, "common", 1)


def Graveyard1(char):
  return events.MonsterAppears(char)


def Graveyard2(char):
  check = events.Check(char, "lore", -1)
  fail = events.ForceMovement(char, "Rivertown")
  succeed = events.GainOrLoss(char, gains={"clues": 1}, losses={"sanity": 1})
  return events.PassFail(char, check, succeed, fail)


def Graveyard3(char):
  victory = events.Sequence([events.Draw(char, "unique", 1), events.Gain(char, {"clues": 1})])
  damage = events.DiceRoll(char, 1)
  defeat = events.Loss(char, {"stamina": values.Die(damage)})
  fail_event = events.Sequence([damage, defeat], char)
  return events.CombatRound(
      char,
      EventMonster("vampire", {"combat": -2}, pass_event=victory, fail_event=fail_event),
      deactivate=True
  )


def Graveyard4(char):
  reward = events.Draw(char, "spells", 1)
  ally = events.GainAllyOrReward(char, "Visiting Painter", reward)
  return events.BinarySpend(char, "toughness", 5, "Spend monster trophies?", "Yes", "No", ally)


def Graveyard5(char):
  check = events.Check(char, "luck", -2)
  choice = events.PlaceChoice(
      char, "Move anywhere in the city and have an encounter?", none_choice="No thanks",
  )
  move = events.ForceMovement(char, choice)
  encounter = events.Encounter(char, choice)
  clues = events.Gain(char, {"clues": 2})
  rubbings = events.Sequence([clues, choice, move, encounter], char)
  return events.PassFail(char, check, rubbings, events.Nothing())


def Graveyard6(char):
  return events.Gain(char, {"sanity": 2})


def Graveyard7(char):
  draw = events.DrawMonstersFromCup(1, char)
  return events.Sequence([draw, events.ForceTakeTrophy(char, draw)], char)


def Society1(char):
  move = events.ForceMovement(char, "Woods")
  encounter = events.Encounter(char, "Woods", 2)
  accept = events.Sequence([move, encounter], char)
  return events.BinaryChoice(char, "Accept Ride?", "Yes", "No", accept, events.Nothing())


def Society2(char):
  move = events.ForceMovement(char, "Southside")
  luck = events.Check(char, "luck", -1)
  move_dream = events.ForceMovement(char, "Dreamlands1")
  enc = events.GateEncounter(char)
  ret = events.ForceMovement(char, "Society")
  dreamlands = events.Sequence([move_dream, enc, ret], char)
  spell = events.Draw(char, "spells", 1)
  searchstacks = events.PassFail(char, luck, spell, dreamlands)
  return events.BinarySpend(
      char, "dollars", 3, "Pay $3 to access the private library", "Yes", "No", searchstacks, move,
  )


def Society3(char):
  check = events.Check(char, "sneak", -1)
  sanity = events.Gain(char, {"sanity": 1})
  curse = events.Curse(char)
  stamina = events.Loss(char, {"stamina": 2})
  move = events.ForceMovement(char, "Southside")
  return events.PassFail(char, check, sanity, events.Sequence([curse, stamina, move], char))


def Society4(char):
  check = events.Check(char, "luck", -1)
  skill = events.Sequence([events.Draw(char, "skills", 1), events.Delayed(char)], char)
  cond = events.Conditional(char, check, "successes", {0: events.Nothing(), 2: skill})
  return events.Sequence([check, cond], char)


def Society5(char):
  return events.Loss(char, {"sanity": 1})


def Society6(char):
  reward = events.Draw(char, "unique", 1)
  ally = events.GainAllyOrReward(char, "Old Professor", reward)
  return events.BinarySpend(char, "gates", 1, "Spend a Gate Trophy?", "Yes", "No", ally)


def Society7(char):
  move = events.ForceMovement(char, "Cave")
  encounter = events.Encounter(char, "Cave", 2)
  cave = events.Sequence([move, encounter], char)
  return events.BinaryChoice(char, "Go with Cindy?", "Yes", "No", cave, events.Nothing())


def House1(char):
  luck = events. Check(char, "luck", 0)
  move_dream = events.ForceMovement(char, "Dreamlands1")
  enc_dream = events.GateEncounter(char)
  ret = events.ForceMovement(char, "House")
  dreamlands = events.Sequence([move_dream, enc_dream, ret], char)
  move_abyss = events.ForceMovement(char, "Abyss1")
  enc_abyss = events.GateEncounter(char)
  abyss = events.Sequence([move_abyss, enc_abyss, ret], char)
  return events.PassFail(char, luck, dreamlands, abyss)


def House2(char):
  move = events.ForceMovement(char, "Lodge")
  encounter = events.Encounter(char, "Lodge", 2)
  lodge = events.Sequence([move, encounter], char)
  return events.BinaryChoice(char, "Enter the tunnel?", "Yes", "No", lodge, events.Nothing())


def House3(char):
  die = events.DiceRoll(char, 1)
  stamina = events.Gain(char, {"stamina":  values.Die(die)})
  return events.Sequence([die, stamina], char)


def House4(char):
  stay = events.Delayed(char)
  common = events.Nothing()  # TODO: coming soon from Peter! draw and purchase
  unique = events.Nothing()  # TODO: coming soon from Peter! draw and purchase
  item = events.BinaryChoice(
      char, "Purchase a common or unique item?", "Common", "Unique", common, unique,
  )
  will = events.Check(char, "will", 0)
  converse = events.PassFail(char, will, item, stay)
  return events.BinaryChoice(
      char, "Converse with travelling Salesman?", "Yes", "No", converse, events.Nothing(),
  )


def House5(char):
  return events.Draw(char, "common", 1)


def House6(char):
  luck = events.Check(char, "luck", -1)
  stamina = events.Loss(char, {"stamina": 1})
  sanity = events.Loss(char, {"sanity": 1})
  choice = events.BinaryChoice(
      char, "Lose 1 stamina or sanity?", "Stamina", "Sanity", stamina, sanity,
  )
  return events.PassFail(char, luck, events.Nothing(), choice)


def House7(char):
  gain = events.SplitGain(char, "sanity", "stamina", 4)
  return events.BinarySpend(char, "dollars", 3, "Spend $3 to spend the night?", "Yes", "No", gain)


def Church1(char):
  return events.Loss(char, {"sanity": 1})


def Church2(char):
  return events.Bless(char)


def Church3(char):
  dollars_up = values.Calculation(char, "dollars", operator.add, 1)
  half_dollar_ceil = values.Calculation(dollars_up, None, operator.floordiv, 2)  # ceil(dollars/2)
  money = events.Loss(char, {"dollars": half_dollar_ceil})
  items_up = values.Calculation(
      values.ItemDeckCount(char, {"common", "unique", "spells", "tradables"}), None,
      operator.add, 1,
  )
  half_items_ceil = values.Calculation(items_up, None, operator.floordiv, 2)
  lose = events.LoseItems(char, half_items_ceil, "Choose items to donate.")
  # TODO: if you choose to donate half your items, but you only have two derringers, do you still
  # have to donate a derringer to the poor?
  return events.BinaryChoice(
      char, "Donate half or your money or half of your items.", "Money", "Items", money, lose)


def Church4(char):
  holywater = events.DrawSpecific(char, "unique", "Holy Water")
  return events.BinaryChoice(
      char, "Search for Holy Water?", "Yes", "No", holywater, events.Nothing(),
  )


def Church5(char):
  check = events.Check(char, "luck", 0)
  lose_sanity = events.Loss(char, {"sanity": 3})
  move = events.ForceMovement(char, "Southside")
  lose_and_move = events.Sequence([lose_sanity, move], char)
  gain_sanity = events.Gain(char, {"sanity": float("inf")})
  cond = events.Conditional(char, check, "successes", {0: lose_and_move, 1: move, 2: gain_sanity})
  return events.Sequence([check, cond], char)


def Church6(char):
  roll = events.DiceRoll(char, 1)
  doom = events.RemoveDoom(char)
  chance = events.PassFail(char, roll, doom, events.Nothing())
  return events.BinarySpend(
      char, "clues", 1, "Spend a clue token for a chance to remove a Doom Token?",
      "Yes", "No", chance,
  )


def Church7(char):
  check = events.Check(char, "speed", -1)
  loss = events.Loss(char, {"stamina": 2})
  move = events.ForceMovement(char, "Southside")
  flee = events.Sequence([loss, move], char)
  return events.PassFail(char, check, move, flee)


def Administration1(char):
  check = events.Check(char, "lore", -1)
  dollars = events.Gain(char, {"dollars": 5})
  return events.PassFail(char, check, dollars, events.Nothing())


def Administration2(char):
  return events.Gain(char, {"clues": 1})


def Administration3(char):
  check = events.Check(char, "will", -1)
  retainer = events.StatusChange(char, "retainer")
  return events.PassFail(char, check, retainer, events.Nothing())


def Administration4(char):
  check = events.Check(char, "lore", -2)
  spell = events.Draw(char, "spells", 1)
  curse = events.Curse(char)
  assist = events.PassFail(char, check, spell, curse)
  return events.BinaryChoice(
      char, "Help the professor and his students?", "Yes", "No", assist, events.Nothing())


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
  # TODO: this should be unaffected by the archaeologist
  tome = events.Draw(char, "unique", 1)  # TODO: this is actually draw the first tome
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
  gain = events.Gain(char, {"clues": values.Die(die)})
  loss = events.Loss(char, {"stamina": 2, "sanity": 2})
  return events.PassFail(char, check, events.Sequence([die, gain], char), loss)


def Library4(char):
  move = events.ForceMovement(char, "Dreamlands1")
  enc = events.GateEncounter(char)
  ret = events.ForceMovement(char, "Library")
  return events.Sequence([move, enc, ret], char)


def Library5(char):
  return events.Loss(char, {"sanity": 1})


def Library6(char):
  # TODO: is spending here optional?
  move = events.ForceMovement(char, "University")
  return events.BinarySpend(char, "dollars", 4, "Pay up!", "Pay $4", "Oops", events.Nothing(), move)


def Library7(char):
  check = events.Check(char, "luck", -2)
  money = events.Gain(char, {"dollars": 5})
  return events.PassFail(char, check, money, events.Nothing())


def Science1(char):
  return events.Bless(char)


def Science2(char):
  spell = events.Draw(char, "spells", 1)
  check = events.Check(char, "fight", -1)
  lose = events.LoseItems(char, 1, "Choose an item to lose.")
  fight = events.PassFail(char, check, events.Nothing(), lose)
  return events.Sequence([spell, fight], char)


def Science3(char):
  prereq = values.ItemDeckPrerequisite(char, "spells", 2, "at most")
  unique = events.Draw(char, "unique", 1)
  move = events.ForceMovement(char, "University")
  return events.PassFail(char, prereq, events.Sequence([unique, move], char), events.Nothing())


def Science4(char):
  stamina = events.Loss(char, {"stamina": 2})
  ally = events.GainAllyOrReward(char, "Arm Wrestler", events.Gain(char, {"dollars": 5}))
  return events.BinaryChoice(
      char, "Arm Wrestle?", "Yes", "No", events.Sequence([stamina, ally], char), events.Nothing(),
  )


def Science5(char):
  check = events.Check(char, "luck", 0)
  die = events.DiceRoll(char, 1)
  win = events.SplitGain(char, "stamina", "sanity", values.Die(die))
  coffee = events.Gain(char, {"stamina": 1})
  return events.PassFail(char, check, events.Sequence([die, win], char), coffee)


def Science6(char):
  check = events.Check(char, "luck", -1)
  success = events.Nothing()  # TODO: OH NO!!  Pick a new investigator...
  return events.PassFail(char, check, success, events.Nothing())


def Science7(char):
  check = events.Check(char, "lore", -2)
  die = events.DiceRoll(char, 1)
  stamina = events.Loss(char, {"stamina": values.Die(die)})
  close_gates = events.Nothing()  # TODO: close all of the gates!
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
  enc = events.GateEncounter(char)
  ret = events.ForceMovement(char, "Shop")
  abyss = events.Sequence([move, enc, ret], char)
  return events.PassFail(char, check, events.Nothing(), abyss)


def Shop3(char):
  common = events.Purchase(char, "common", float("inf"))
  unique = events.Purchase(char, "unique", float("inf"))
  choice = events.CardChoice(char, "Purchase a Common or Unique item?", ["common", "unique"])
  cond = events.Conditional(char, choice, "choice_index", {0: common, 1: unique})
  return events.Sequence([choice, cond], char)


def Shop4(char):
  check = events.Check(char, "luck", -1)
  prereq = values.ItemCountPrerequisite(char, 1, "at least")
  loss = events.LoseItems(char, 1, "Choose an item to lose")
  new_encounter = events.Encounter(char, "Shop")
  fail = events.PassFail(char, prereq, loss, new_encounter)
  return events.PassFail(char, check, events.Nothing(), fail)


def Shop5(char):
  # TODO: Oh Dear:  3 common items for sale, any player may purchase 1 or more
  # conflicts are decided by the player that drew the card
  return events.Nothing()


def Shop6(char):
  check = events.Check(char, "luck", -1)
  common_unique = events.Nothing()  # TODO: purchase the top item of the common and/or unique deck
  common = events.Nothing()  # TODO: you may purchase the top item of the common deck
  return events.PassFail(char, check, common_unique, common)


def Shop7(char):
  check = events.Check(char, "speed", -1)
  draw_mythos = events.DrawMythosCard(char, require_gate=True)
  move = events.ForceMovement(char, draw_mythos)
  encounter = events.Encounter(char, draw_mythos)
  fail = events.Sequence([draw_mythos, move, encounter], char)
  return events.PassFail(char, check, events.Nothing(), fail)


def Newspaper1(char):
  money = events.Gain(char, {"dollars": 2})
  choice = events.PlaceChoice(
      char, "Get a ride anywhere in the city and have an encounter?", none_choice="No thanks",
  )
  move = events.ForceMovement(char, choice)
  encounter = events.Encounter(char, choice)
  return events.Sequence([money, choice, move, encounter], char)


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
  sanity = events.Loss(char, {"sanity": values.Die(die)})
  return events.PassFail(char, check, spell, events.Sequence([die, sanity], char))


def Train3(char):
  return events.SplitGain(char, "stamina", "sanity", 2)


def Train4(char):
  return events.Nothing()  # TODO: draw the top common item and purchase it for +1 if you wish


def Train5(char):
  choice = events.PlaceChoice(
      char, "Get a ride anywhere in the city and have an encounter?", none_choice="No thanks",
  )
  move = events.ForceMovement(char, choice)
  encounter = events.Encounter(char, choice)
  return events.Sequence([choice, move, encounter], char)


def Train6(char):
  check = events.Check(char, "luck", -2)
  common = events.Draw(char, "common", 1)
  unique = events.Draw(char, "unique", 1)
  item = events.PassFail(char, check, unique, common)
  return events.BinarySpend(
      char, "dollars", 3, "Claim item left at lost and found for $3?", "Yes", "No", item,
  )


def Train7(char):
  check = events.Check(char, "luck", -1)
  unique = events.Draw(char, "unique", 1)
  die = events.DiceRoll(char, 1)
  stab = events.Loss(char, {"stamina": values.Die(die)})
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
  clue_prereq = values.AttributePrerequisite(char, "clues", 4, "at least")
  clue_loss = events.Loss(char, {"clues": 4})
  spell_prereq = values.ItemDeckPrerequisite(char, "spells", 2, "at least")
  spell_loss = events.LoseItems(char, 2, "Choose 2 spells to lose", {"spells"})
  skill_prereq = values.ItemDeckPrerequisite(char, "skills", 1, "at least")
  skill_loss = events.LoseItems(char, 1, "Choose 1 skill to lose", {"skills"})
  nothing = events.Nothing()

  skill_spell_sum = values.Calculation(skill_prereq, None, operator.add, spell_prereq)
  overall_sum = values.Calculation(skill_spell_sum, None, operator.add, clue_prereq)
  none_prereq = values.Calculation(overall_sum, None, operator.not_)
  choice = events.MultipleChoice(
      char, "Choose something to lose", ["Nothing", "4 Clues", "2 Spells", "1 Skill"],
      prereqs=[none_prereq, clue_prereq, spell_prereq, skill_prereq],
  )
  losses = events.Conditional(
      char, choice, "choice_index", {0: nothing, 1: clue_loss, 2: spell_loss, 3: skill_loss},
  )
  lose = events.Sequence([choice, losses], char)
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
  choice = events.PlaceChoice(
      char, "Catch a lift to anywhere in the city and have an encounter?", none_choice="No thanks",
  )
  move = events.ForceMovement(char, choice)
  encounter = events.Encounter(char, choice)
  return events.Sequence([choice, move, encounter], char)


def Bank2(char):
  check = events.Check(char, "luck", -1)
  common = events.Draw(char, "common", 1)
  unique = events.Draw(char, "unique", 1)
  return events.BinarySpend(
      char, "dollars", 2, "Pay $2 for man's last possession?", "Pay $2",
      "Let man and his family go hungry", events.PassFail(char, check, unique, common),
  )


def Bank3(char):
  robbed = events.Loss(char, {"dollars": float("inf")})
  nothing = events.Nothing()
  return events.CombatRound(
      char,
      EventMonster("bank robbers", {"combat": -1}, nothing, robbed),
      deactivate=True
  )


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
  ally = events.GainAllyOrReward(char, "Fortune Teller", events.Gain(char, {"clues": 2}))
  return events.PassFail(char, check, ally, events.Nothing())


def Square3(char):
  check = events.Check(char, "will", -1)
  loss = events.Loss(char, {"sanity": 1, "stamina": 1})
  return events.PassFail(char, check, events.Nothing(), loss)


def Square4(char):
  check = events.Check(char, "luck", -2)
  loss = events.LoseItems(char, 1, "Choose an item to lose")
  return events.PassFail(char, check, events.Nothing(), loss)


def Square5(char):
  check = events.Check(char, "fight", -1)
  move = events.ForceMovement(char, "Downtown")
  return events.PassFail(char, check, events.Nothing(), move)


def Square6(char):
  check = events.Check(char, "luck", -1)
  stamina = events.Loss(char, {"stamina": 1})
  lose = events.Sequence([stamina, events.Curse(char)], char)
  buy = events.Nothing()  # TODO: Buying stuff
  interact = events.PassFail(char, check, buy, lose)
  return events.BinaryChoice(
      char, "Interact with the gypsies?", "Yes", "No", interact, events.Nothing(),
  )


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
  draws = events.Draw(char, "common", 2, keep_count=2)
  check = events.Check(char, "luck", -1)
  success = events.Nothing()
  fail = events.Arrested(char)
  passfail = events.PassFail(char, check, success, fail)
  return events.Sequence([draws, passfail], char)


def Docks3(char):
  check = events.Check(char, "fight", 0)
  dollars = events.Gain(char, {"dollars": values.Calculation(check, "successes", operator.mul, 3)})
  move = events.ForceMovement(char, "Merchant")
  stamina = events.Loss(char, {"stamina": 1})
  cond = events.Conditional(
      char, check, "successes", {0: events.Sequence([stamina, move], char), 1: dollars},
  )
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
  ally = events.GainAllyOrReward(char, "Police Inspector", reward)
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
  return events.Loss(char, {"clues": 1})


def Hospital2(char):
  sanity = events.Loss(char, {"sanity": 1})
  won = events.Gain(char, {"clues": 1})
  lost = events.ForceMovement(char, "Uptown")
  combat = events.CombatRound(
      char,
      EventMonster("corpse", {"combat": -1}, won, lost),
      deactivate=True)
  return events.Sequence([sanity, combat], char)


def Hospital3(char):
  die = events.DiceRoll(char, 1)
  cond = events.Conditional(
      char, die, "sum",
      {0: events.Nothing(), 1: events.Gain(char, {"stamina": values.Die(die)}), 4: events.Nothing()}
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
  fail = events.Sequence(
      [events.Loss(char, {"stamina": 2}), events.ForceMovement(char, "Uptown")], char,
  )
  return events.PassFail(char, check, shotgun, fail)


def Woods4(char):
  check = events.Check(char, "luck", -1)
  loss = events.LoseItems(char, 2, "Choose two items to lose")
  stamina = events.Loss(char, {"stamina": 2})
  bushwhack = events.Sequence([loss, stamina], char)
  return events.PassFail(char, check, events.Nothing(), bushwhack)


def Woods5(char):
  prereq = values.ItemPrerequisite(char, "Food")
  check = events.Check(char, "speed", -2)
  dog = events.GainAllyOrReward(char, "Dog", events.Gain(char, {"dollars": 3}))
  give_food = events.DiscardNamed(char, "Food")
  catch = events.PassFail(char, check, dog, events.Nothing())
  seq = events.Sequence([give_food, dog], char)
  return events.BinaryChoice(char, "Give food to the dog?", "Yes", "No", seq, catch, prereq)


def Woods6(char):
  return events.OpenGate("Woods")


def Woods7(char):
  choice = events.MultipleChoice(
      char, "Which would you like to gain?", ["A skill", "2 spells", "4 clues"],
  )
  skill = events.Draw(char, "skills", 1)
  spells = events.Draw(char, "spells", 2, keep_count=2)
  clues = events.Gain(char, {"clues": 4})
  gain = events.Conditional(char, choice, "choice_index", {0: skill, 1: spells, 2: clues})
  gains = events.Sequence([choice, gain], char)
  check = events.Check(char, "lore", -2)
  cond = events.PassFail(char, check, gains, events.Nothing())
  turn = events.LoseTurn(char)
  seq = events.Sequence([turn, cond], char)
  return events.BinaryChoice(
      char, "Share in the old wise-guy's wisdom?", "Yes", "No", seq, events.Nothing(),
  )


def Shoppe1(char):
  return events.Loss(char, {"sanity": 1})


def Shoppe2(char):
  prompt = "Choose a neighborhood to view the top card of"
  filters = {"streets", "open", "closed"}
  choice = events.PlaceChoice(char, prompt, choice_filters=filters, annotation="Reveal")
  was_cancelled = values.Calculation(choice, None, operator.methodcaller("is_cancelled"))
  add_global = events.AddGlobalEffect(CardRevealer(choice))
  cond = events.Conditional(char, was_cancelled, None, {0: add_global, 1: events.Nothing()})
  return events.Sequence([choice, cond], char)


def Shoppe3(char):
  luck = events.Check(char, "luck", 0)
  dice = events.DiceRoll(char, 2)
  coins = events.Sequence([dice, events.Gain(char, {"dollars": values.Die(dice)})], char)
  jackpot = events.Draw(char, "unique", 2, keep_count=2)
  cond = events.Conditional(char, luck, "successes", {0: events.Nothing(), 1: coins, 2: jackpot})
  buy = events.Sequence([luck, cond], char)
  return events.BinarySpend(char, "dollars", 5, "Buy the locked trunk?", "Yes", "No", buy)


def Shoppe4(char):
  check = events.Check(char, "lore", -1)
  curse = events.Curse(char)
  return events.PassFail(char, check, events.Nothing(), curse)


def Shoppe5(char):
  return events.Gain(char, {"clues": 1})


def Shoppe6(char):
  check = events.Check(char, "lore", -1)
  # TODO: Implement buying at a discount
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
          EncounterCard("Downtown6", {"Asylum": Asylum6, "Bank": Bank6, "Square": Square6}),
          EncounterCard("Downtown7", {"Asylum": Asylum7, "Bank": Bank7, "Square": Square7}),
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
          EncounterCard(
              "FrenchHill1", {"Lodge": Lodge1, "WitchHouse": WitchHouse1, "Sanctum": Sanctum1},
          ),
          EncounterCard(
              "FrenchHill2", {"Lodge": Lodge2, "WitchHouse": WitchHouse2, "Sanctum": Sanctum2},
          ),
          EncounterCard(
              "FrenchHill3", {"Lodge": Lodge3, "WitchHouse": WitchHouse3, "Sanctum": Sanctum3},
          ),
          EncounterCard(
              "FrenchHill4", {"Lodge": Lodge4, "WitchHouse": WitchHouse4, "Sanctum": Sanctum4},
          ),
          EncounterCard(
              "FrenchHill5", {"Lodge": Lodge5, "WitchHouse": WitchHouse5, "Sanctum": Sanctum5},
          ),
          EncounterCard(
              "FrenchHill6", {"Lodge": Lodge6, "WitchHouse": WitchHouse6, "Sanctum": Sanctum6},
          ),
          EncounterCard(
              "FrenchHill7", {"Lodge": Lodge7, "WitchHouse": WitchHouse7, "Sanctum": Sanctum7},
          ),
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
          EncounterCard("Southside1", {"Society": Society1, "House": House1, "Church": Church1}),
          EncounterCard("Southside2", {"Society": Society2, "House": House2, "Church": Church2}),
          EncounterCard("Southside3", {"Society": Society3, "House": House3, "Church": Church3}),
          EncounterCard("Southside4", {"Society": Society4, "House": House4, "Church": Church4}),
          EncounterCard("Southside5", {"Society": Society5, "House": House5, "Church": Church5}),
          EncounterCard("Southside6", {"Society": Society6, "House": House6, "Church": Church6}),
          EncounterCard("Southside7", {"Society": Society7, "House": House7, "Church": Church7}),
      ],
      "University": [
          EncounterCard(
              "University1",
              {"Administration": Administration1, "Library": Library1, "Science": Science1},
          ),
          EncounterCard(
              "University2",
              {"Administration": Administration2, "Library": Library2, "Science": Science2},
          ),
          EncounterCard(
              "University3",
              {"Administration": Administration3, "Library": Library3, "Science": Science3},
          ),
          EncounterCard(
              "University4",
              {"Administration": Administration4, "Library": Library4, "Science": Science4},
          ),
          EncounterCard(
              "University5",
              {"Administration": Administration5, "Library": Library5, "Science": Science5},
          ),
          EncounterCard(
              "University6",
              {"Administration": Administration6, "Library": Library6, "Science": Science6},
          ),
          EncounterCard(
              "University7",
              {"Administration": Administration7, "Library": Library7, "Science": Science7},
          ),
      ],
      "Uptown": [
          EncounterCard("Uptown1", {"Hospital": Hospital1, "Woods": Woods1, "Shoppe": Shoppe1}),
          EncounterCard("Uptown2", {"Hospital": Hospital2, "Woods": Woods2, "Shoppe": Shoppe2}),
          EncounterCard("Uptown3", {"Hospital": Hospital3, "Woods": Woods3, "Shoppe": Shoppe3}),
          EncounterCard("Uptown4", {"Hospital": Hospital4, "Woods": Woods4, "Shoppe": Shoppe4}),
          EncounterCard("Uptown5", {"Hospital": Hospital5, "Woods": Woods5, "Shoppe": Shoppe5}),
          EncounterCard("Uptown6", {"Hospital": Hospital6, "Woods": Woods6, "Shoppe": Shoppe6}),
          EncounterCard("Uptown7", {"Hospital": Hospital7, "Woods": Woods7, "Shoppe": Shoppe7}),
      ],
  }
