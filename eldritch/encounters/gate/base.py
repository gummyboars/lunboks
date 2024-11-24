import operator
from eldritch import events
from eldritch import items
from eldritch import values
from eldritch.encounters.gate.core import GateCard


def Abyss1(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  succeed = events.Return(char, char.place.info.name)
  monster = events.MonsterAppears(char)
  return events.PassFail(char, check, succeed, monster)


def GreatHall1(char) -> events.Event:
  check = events.Check(char, "sneak", -2)
  spell = events.Draw(char, "spells", float("inf"))
  stamina = events.Loss(char, {"stamina": 2})
  return events.PassFail(char, check, spell, stamina)


def Other1(char) -> events.Event:
  check = events.Check(char, "fight", -1)
  spell = events.Draw(char, "spells", 1)
  return events.PassFail(char, check, spell, events.Nothing())


def Abyss2(char) -> events.Event:
  return events.Gain(char, {"stamina": 1})  # TODO: Should we attach a source somehow?


def Pluto2(char) -> events.Event:
  check = events.Check(char, "fight", -2)
  return events.PassFail(char, check, events.Nothing(), events.LostInTimeAndSpace(char))


def Other2(char) -> events.Event:
  def return_and_close(name):
    return events.Sequence(
      [events.Return(char, char.place.info.name), events.CloseGate(char, name, True, True)], char
    )

  check = events.Check(char, "speed", -2)
  place = values.EnteredGate(char)
  gate_exists = values.Calculation(place, None, bool)
  place_as_list = values.Calculation(place, None, lambda name: [name] if name is not None else [])
  fail = events.Sequence(
    [events.CloseGate(char, place, False, False), events.LostInTimeAndSpace(char)], char
  )
  # TODO: this is a horrible hack where we use a ForEach to evaluate the place name before the
  # Return event is finished (which will erase the entered gate from the character).
  foreach = events.ForEach(char, place_as_list, return_and_close)
  results = {0: events.Return(char, char.place.info.name), 1: foreach}
  success = events.Conditional(char, gate_exists, None, results)
  return events.PassFail(char, check, success, fail)


def Abyss3(char) -> events.Event:
  check = events.Check(char, "lore", -1)
  return events.PassFail(char, check, events.Nothing(), events.Delayed(char))


def Pluto3(char) -> events.Event:
  check = events.Check(char, "sneak", -1)
  lose_count = values.Calculation(values.ItemCount(char), None, operator.floordiv, 2)
  fail = events.Sequence(
    [events.LoseItems(char, lose_count), events.Return(char, char.place.info.name)], char
  )
  return events.PassFail(char, check, events.Nothing(), fail)


def Other3(char) -> events.Event:
  return events.Loss(char, {"sanity": 1})


def Abyss4(char) -> events.Event:
  check = events.Check(char, "luck", 1)
  cave = events.ForceMovement(char, "Cave")
  dreamlands = events.ForceMovement(char, "Dreamlands1")
  # I assume that you always move to the first dreamlands, regardless of where in the Abyss you were
  temple_check = events.Check(char, "luck", -1)
  temple = events.PassFail(char, temple_check, events.Draw(char, "unique", 1), events.Nothing())
  return events.Sequence(
    [check, events.Conditional(char, check, "successes", {0: cave, 2: dreamlands, 3: temple})], char
  )


def GreatHall4(char) -> events.Event:
  check = events.Check(char, "fight", -1, difficulty=2)
  spells = events.Draw(char, "spells", 3, keep_count=2)
  loss = events.Loss(char, {"stamina": 3})
  read = events.PassFail(char, check, spells, loss)
  return events.BinaryChoice(char, "Read the book?", "Yes", "No", read, events.Nothing())


def Other4(char) -> events.Event:
  return events.MonsterAppears(char)


def Dreamlands5(char) -> events.Event:
  return events.Nothing()


def Abyss5(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  fishy_object = events.Sequence(
    [events.Gain(char, {"dollars": 3}), events.Draw(char, "unique", 1)], char
  )
  return events.PassFail(char, check, fishy_object, events.Nothing())


def Other5(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  gain = events.Gain(char, {"clues": values.Calculation(check, "successes")})
  gain_cond = events.PassFail(char, values.Calculation(check, "successes"), gain, events.Nothing())
  return events.Sequence([check, gain_cond], char)


def Dreamlands6(char) -> events.Event:
  check = events.Check(char, "speed", -1)
  loss = events.Loss(char, {"dollars": float("inf")})
  return events.PassFail(char, check, events.Nothing(), loss)


def GreatHall6(char) -> events.Event:
  check = events.Check(char, "lore", -1)
  return events.PassFail(char, check, events.Nothing(), events.Curse(char))


def Other6(char) -> events.Event:
  return events.MonsterAppears(char)


def Dreamlands7(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  clues = events.Gain(char, {"clues": 2})
  delay = events.Delayed(char)
  return events.PassFail(char, check, clues, delay)


def GreatHall7(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  gain = events.Gain(char, {"sanity": 2, "stamina": 2})  # TODO: Source?
  loss = events.LoseItems(char, 2)
  return events.PassFail(char, check, gain, loss)


def Other7(char) -> events.Event:
  check = events.Check(char, "fight", -2)
  gain = events.Gain(char, {"dollars": 8})
  loss = events.Loss(char, {"stamina": 1})
  return events.PassFail(char, check, gain, loss)


def Dreamlands8(char) -> events.Event:
  check = events.Check(char, "lore", 0)
  freeze = events.LostInTimeAndSpace(char)
  return events.PassFail(char, check, events.Return(char, char.place.info.name), freeze)


def Pluto8(char) -> events.Event:
  check = events.Check(char, "speed", -1)
  statue = events.Gain(char, {"dollars": 5, "clues": 2})
  lost = events.LostInTimeAndSpace(char)
  return events.PassFail(char, check, statue, lost)


def Other8(char) -> events.Event:
  return events.Draw(char, "common", 1)


def Dreamlands9(char) -> events.Event:
  check = events.Check(char, "sneak", 0)
  lose_item_count = values.Calculation(values.ItemCount(char), None, values.ceildiv, 2)
  lose_money_count = values.Calculation(char, "dollars", values.ceildiv, 2)
  loss = events.Sequence(
    [events.LoseItems(char, lose_item_count), events.Loss(char, {"dollars": lose_money_count})],
    char,
  )
  return events.PassFail(char, check, events.Nothing(), loss)


def Pluto9(char) -> events.Event:
  check = events.Check(char, "will", -2)
  loss = events.LoseItems(char, 1)
  return events.PassFail(char, check, events.Nothing(), loss)


def Other9(char) -> events.Event:
  return events.Loss(char, {"sanity": 1})


def Dreamlands10(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  loss = events.Loss(char, {"stamina": 1})
  delay = events.Delayed(char)
  return events.PassFail(char, check, events.Nothing(), events.Sequence([loss, delay], char))


def Abyss10(char) -> events.Event:
  check = events.Check(char, "luck", -2)
  loss = events.Loss(char, {"sanity": 1})
  delay = events.Delayed(char)
  return events.PassFail(char, check, events.Nothing(), events.Sequence([loss, delay], char))


def Other10(char) -> events.Event:
  check = events.Check(char, "lore", -1)
  delay = events.Delayed(char)
  return events.PassFail(char, check, events.Nothing(), delay)


def Pluto11(char) -> events.Event:
  return events.MonsterAppears(char)


def GreatHall11(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  dice_roll = events.DiceRoll(char, 1)
  successes = values.Calculation(dice_roll, "successes")
  monster = events.MonsterAppears(char)
  delayed = events.Delayed(char)
  prison = events.Sequence(
    [dice_roll, events.Conditional(char, successes, None, {0: monster, 1: delayed})], char
  )
  return events.PassFail(char, check, events.Nothing(), prison)


def Other11(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  look = events.LookAtItems(char, "common", 1, target_type="weapon")
  weapon = events.Sequence([look, events.KeepDrawn(char, look)], char)
  return events.PassFail(char, check, weapon, events.Nothing())


def Pluto12(char) -> events.Event:
  check = events.Check(char, "will", -2)
  san_loss = events.Loss(char, {"sanity": 2})
  spell_loss = events.LoseItems(char, 2, "Lose spells", {"spells"})
  prereq = values.ItemDeckPrerequisite(char, "spells", threshold=2)
  choice = events.BinaryChoice(
    char,
    "Lose spells or sanity?",
    "Lose 2 spells",
    "Lose 2 sanity",
    spell_loss,
    san_loss,
    prereq=prereq,
  )
  return events.PassFail(char, check, events.Nothing(), choice)


def GreatHall12(char) -> events.Event:
  return events.MonsterAppears(char)


def Other12(char) -> events.Event:
  check = events.Check(char, "sneak", -2)
  return events.PassFail(char, check, events.Nothing(), events.Delayed(char))


def City13(char) -> events.Event:
  check = events.Check(char, "sneak", -1, difficulty=2)
  escape = events.Sequence(
    [events.Draw(char, "unique", 1), events.Return(char, char.place.info.name)], char
  )
  captors = events.Loss(char, {"sanity": 3, "stamina": 1})
  return events.PassFail(char, check, escape, captors)


def Plateau13(char) -> events.Event:
  check = events.Check(char, "lore", -2)
  trade = events.Gain(char, {"dollars": 6})
  lost = events.LostInTimeAndSpace(char)
  prompt = "Trade with the dangerous hooved folk?"
  return events.BinaryChoice(
    char, prompt, "Yes", "No", events.PassFail(char, check, trade, lost), events.Nothing()
  )


def Other13(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  return events.PassFail(char, check, events.Gain(char, {"clues": 2}), events.Nothing())


def City14(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  statue = events.Sequence([events.Gain(char, {"dollars": 10}), events.Curse(char)])
  choice = events.BinaryChoice(
    char, "Take the golden statue?", "Yes", "No", statue, events.Nothing()
  )
  return events.PassFail(char, check, choice, events.Nothing())


def GreatHall14(char) -> events.Event:
  return events.Delayed(char)


def Other14(char) -> events.Event:
  check = events.Check(char, "fight", -1)
  rope = events.Return(char, char.place.info.name)
  fall = events.Sequence([events.Loss(char, {"stamina": 2}), events.Delayed(char)], char)
  return events.PassFail(char, check, rope, fall)


def City15(char) -> events.Event:
  check = events.Check(char, "lore", -2, difficulty=2)
  spells = events.Draw(char, "spells", 2)
  return events.PassFail(char, check, spells, events.Nothing())


def GreatHall15(char) -> events.Event:
  check = events.Check(char, "lore", 2)
  gain = events.Gain(char, {"clues": values.Calculation(check, "successes")})
  gain_cond = events.PassFail(char, values.Calculation(check, "successes"), gain, events.Nothing())
  return events.Sequence([check, gain_cond], char)


def Other15(char) -> events.Event:
  return events.Gain(char, {"dollars": 3})


def Plateau16(char) -> events.Event:
  return events.Nothing()


def GreatHall16(char) -> events.Event:
  check = events.Check(char, "luck", -1, difficulty=2)
  draw = events.Draw(char, "skills", 1)
  return events.PassFail(char, check, draw, events.Nothing())


def Other16(char) -> events.Event:
  check = events.Check(char, "sneak", -1)
  gain = events.Gain(char, {"dollars": 3})
  loss = events.Loss(char, {"stamina": 2})
  return events.PassFail(char, check, gain, loss)


def Plateau17(char) -> events.Event:
  check = events.Check(char, "will", 0, difficulty=2)
  skill = events.Draw(char, "skills", 1)
  return events.PassFail(char, check, skill, events.Nothing())


def GreatHall17(char) -> events.Event:
  check = events.Check(char, "luck", -2)
  tome = events.Draw(char, "unique", 1, target_type=items.Tome)
  return events.PassFail(char, check, tome, events.Nothing())


def Other17(char) -> events.Event:
  return events.Draw(char, "spells", 1)


def City18(char) -> events.Event:
  check = events.Check(char, "sneak", -1)
  draw = events.Draw(char, "unique", draw_count=2, keep_count=1)
  lost = events.LostInTimeAndSpace(char)
  prompt = "Infiltrate the structures?"
  return events.BinaryChoice(
    char, prompt, "Yes", "No", events.PassFail(char, check, draw, lost), events.Nothing()
  )


def Plateau18(char) -> events.Event:
  check = events.Check(char, "will", 0)
  gain = events.Gain(char, {"sanity": float("inf")})
  return events.PassFail(char, check, gain, events.Nothing())


def Other18(char) -> events.Event:
  return events.Gain(char, {"clues": 1})


def Dreamlands19(char) -> events.Event:
  check = events.Check(char, "will", 0)
  spell = events.Draw(char, "spells", 1)
  return events.PassFail(char, check, spell, events.Nothing())


def City19(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  item = events.Draw(char, "unique", 1)
  return events.PassFail(char, check, item, events.Nothing())


def Other19(char) -> events.Event:
  return events.Gain(char, {"sanity": 1})


def Dreamlands20(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  draw = events.Draw(char, "common", 1)
  return events.PassFail(char, check, draw, events.Nothing())


def GreatHall20(char) -> events.Event:
  check = events.Check(char, "luck", -2)
  tome = events.Draw(char, "unique", 1, target_type=items.Tome)
  return events.PassFail(char, check, tome, events.Nothing())


def Other20(char) -> events.Event:
  return events.Gain(char, {"stamina": 1})


def Dreamlands21(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  bird = events.Gain(char, {"sanity": float("inf"), "stamina": float("inf")})
  return events.PassFail(char, check, bird, events.Nothing())


def GreatHall21(char) -> events.Event:
  check = events.Check(char, "lore", -1)
  bless = events.Bless(char)
  return events.PassFail(char, check, bless, events.Nothing())


def Other21(char) -> events.Event:
  check = events.Check(char, "fight", -2)
  something = events.Draw(char, "unique", 1)
  return events.PassFail(char, check, something, events.Nothing())


def Dreamlands22(char) -> events.Event:
  check = events.Check(char, "will", -1)
  dice = events.DiceRoll(char, 2, bad=[])
  money = events.Gain(char, {"dollars": values.Calculation(dice, "sum")})
  return events.PassFail(char, check, events.Sequence([dice, money], char), events.Nothing())


def Plateau22(char) -> events.Event:
  check = events.Check(char, "luck", -2)
  common = events.Draw(char, "common", 1)
  spell = events.Draw(char, "spells", 1)
  draws = events.Sequence([common, spell], char)
  return events.PassFail(char, check, draws, events.Nothing())


def Other22(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  return events.PassFail(char, check, events.Return(char, char.place.info.name), events.Nothing())


def Dreamlands23(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  if char.place.name == "Dreamlands1":
    ride_to_next = events.ForceMovement(char, "Dreamlands2")
  else:
    ride_to_next = events.Return(char, char.place.info.name)
  return events.PassFail(char, check, ride_to_next, events.Nothing())


def Plateau23(char) -> events.Event:
  check = events.Check(char, "fight", -1)
  draw = events.Draw(char, "unique", 1)
  lost = events.LostInTimeAndSpace(char)
  return events.PassFail(char, check, draw, lost)


def Other23(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  draw = events.DrawMonstersFromCup(1, char, to_board=False)
  creature = events.Sequence(
    [draw, events.ForceTakeTrophy(char, draw), events.Gain(char, {"clues": 2})], char
  )
  return events.PassFail(char, check, creature, events.Nothing())


def Dreamlands24(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  spell = events.Draw(char, "spells", 1)
  caught = events.LoseItems(char, 1)
  return events.PassFail(char, check, spell, caught)


def City24(char) -> events.Event:
  violence = events.Check(char, "fight", -1)
  is_the_answer = events.Return(char, char.place.info.name)
  return events.PassFail(char, violence, is_the_answer, events.Nothing())


def Other24(char) -> events.Event:
  check = events.Check(char, "sneak", -1)
  steal = events.Draw(char, "spells", 1)
  pain = events.Loss(char, {"sanity": 3})
  steal = events.PassFail(char, check, steal, pain)
  return events.BinaryChoice(char, "Steal the scroll?", "Yes", "No", steal, events.Nothing())


def Abyss25(char) -> events.Event:
  return events.MonsterAppears(char)


def Dreamlands25(char) -> events.Event:
  check = events.Check(char, "speed", -2)
  loss = events.Loss(char, {"stamina": 2})
  return events.PassFail(char, check, events.Nothing(), loss)


def Other25(char) -> events.Event:
  check = events.Check(char, "luck", -2)
  chant = events.Sequence([events.Gain(char, {"clues": 2}), events.Draw(char, "spells", 1)], char)
  return events.PassFail(char, check, chant, events.MonsterAppears(char))


def Abyss26(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  die = events.DiceRoll(char, 1, bad=[])
  val = values.Calculation(die, "sum")
  gain = events.Sequence([die, events.Gain(char, {"stamina": val})], char)
  loss = events.Sequence([die, events.Loss(char, {"stamina": val})], char)
  eat = events.PassFail(char, check, gain, loss)
  return events.BinaryChoice(char, "Eat the mushrooms?", "Yes", "No", eat, events.Nothing())


def Plateau26(char) -> events.Event:
  return events.MonsterAppears(char)


def Other26(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "sneak", 0), events.Nothing(), events.Loss(char, {"stamina": 2})
  )


def Abyss27(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "sneak", -1), events.Nothing(), events.Loss(char, {"sanity": 2})
  )


def Plateau27(char) -> events.Event:
  check = events.Check(char, "fight", -1, difficulty=2)
  victory = events.Sequence([events.Gain(char, {"clues": 1}), events.Draw(char, "unique", 1)], char)
  defeat = events.Loss(char, {"sanity": 1, "stamina": 2})
  return events.PassFail(char, check, victory, defeat)


def Other27(char) -> events.Event:
  dice = events.DiceRoll(char, values.Calculation(char, "stamina"), bad=[])
  amount = values.Calculation(
    left=char, left_attr="stamina", operand=operator.sub, right=dice, right_attr="successes"
  )
  loss = events.Loss(char, {"stamina": amount})
  final = events.PassFail(
    char,
    values.Calculation(char, "stamina"),
    events.Gain(char, {"clues": values.Calculation(dice, "successes")}),
    events.Nothing(),
  )
  return events.Sequence([dice, loss, final], char)


def Plateau28(char) -> events.Event:
  check = events.Check(char, "sneak", -1)
  rites = events.Sequence(
    [events.Loss(char, {"sanity": 3, "stamina": 3}), events.Delayed(char)], char
  )
  return events.PassFail(char, check, events.Nothing(), rites)


def Dreamlands28(char) -> events.Event:
  check = events.Check(char, "sneak", -1)
  success = events.Sequence(
    [events.Gain(char, {"clues": 3}), events.Return(char, char.place.info.name)], char
  )
  return events.PassFail(char, check, success, events.Devoured(char))


def Other28(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "speed", -1), events.Draw(char, "spells", 1), events.Nothing()
  )


def Plateau29(char) -> events.Event:
  check = events.Check(char, "speed", -1)
  loss = events.Loss(char, {"stamina": 2})
  return events.PassFail(char, check, events.Nothing(), loss)


def Dreamlands29(char) -> events.Event:
  check = events.Check(char, "speed", -1)
  loss = events.Loss(char, {"stamina": 3})
  return events.PassFail(char, check, events.Nothing(), loss)


def Other29(char) -> events.Event:
  return events.Loss(char, {"stamina": 1})


def Abyss30(char) -> events.Event:
  return events.PassOrLoseDice(char, "speed", -1, "stamina")


def Dreamlands30(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "luck", -1), events.Nothing(), events.LostInTimeAndSpace(char)
  )


def Other30(char) -> events.Event:
  return events.Loss(char, {"stamina": 1})


def SunkenCity31(char) -> events.Event:
  check = events.Check(char, "luck", 0)
  pit = events.Sequence([events.Loss(char, {"sanity": 1}), events.Delayed(char)], char)
  return events.PassFail(char, check, events.Nothing(), pit)


def Plateau31(char) -> events.Event:
  return events.PassOrLoseDice(char, "sneak", 0, "stamina")


def Other31(char) -> events.Event:
  return events.Nothing()


def SunkenCity32(char) -> events.Event:
  return events.MonsterAppears(char)


def Abyss32(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "speed", -1), events.Nothing(), events.LostInTimeAndSpace(char)
  )


def Other32(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "lore", -1), events.Nothing(), events.Delayed(char)
  )


def SunkenCity33(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "speed", -1), events.Nothing(), events.Loss(char, {"stamina": 3})
  )


def Abyss33(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "luck", -1), events.Nothing(), events.Loss(char, {"sanity": 3})
  )


def Other33(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "fight", -1), events.Nothing(), events.Delayed(char)
  )


def SunkenCity34(char) -> events.Event:
  check = events.Check(char, "fight", -2)
  shadow = events.Sequence([events.Loss(char, {"stamina": 2}), events.Delayed(char)], char)
  return events.PassFail(char, check, events.Nothing(), shadow)


def Dreamlands34(char) -> events.Event:
  check = events.Check(char, "luck", -2)
  wine = events.Gain(char, {"sanity": 1, "clues": 1})
  teeth = events.LostInTimeAndSpace(char)
  return events.PassFail(char, check, wine, teeth)


def Other34(char) -> events.Event:
  return events.PassFail(
    char,
    events.Check(char, "luck", -1),
    events.Gain(char, {"sanity": 2, "stamina": 2}),
    events.Nothing(),
  )


def SunkenCity35(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "fight", -1), events.Nothing(), events.Loss(char, {"stamina": 3})
  )


def Dreamlands35(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "fight", -1), events.Nothing(), events.Loss(char, {"stamina": 2})
  )


def Other35(char) -> events.Event:
  return events.MonsterAppears(char)


def SunkenCity36(char) -> events.Event:
  return events.PassOrLoseDice(char, "luck", -1, "stamina")


def Plateau36(char) -> events.Event:
  return events.PassFail(
    char,
    events.Check(char, "lore", -2),
    events.Draw(char, "spells", 1),
    events.LostInTimeAndSpace(char),
  )


def Other36(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "luck", -1), events.Draw(char, "unique", 1), events.Nothing()
  )


def City37(char) -> events.Event:
  buzzing = events.Gain(char, {"clues": 2})
  check = events.Check(char, "luck", -1)
  origins = events.PassFail(char, check, events.Nothing(), events.Loss(char, {"sanity": 2}))
  return events.Sequence([buzzing, origins], char)


def Pluto37(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "will", -2), events.Nothing(), events.Loss(char, {"sanity": 2})
  )


def Other37(char) -> events.Event:
  return events.MonsterAppears(char)


def City38(char) -> events.Event:
  return events.Nothing()


def Dreamlands38(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "lore", -1), events.Nothing(), events.Loss(char, {"sanity": 3})
  )


def Other38(char) -> events.Event:
  return events.PassFail(
    char,
    events.Check(char, "will", -1),
    events.Nothing(),
    events.Loss(char, {"sanity": 1, "stamina": 1}),
  )


def City39(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "speed", -1), events.Nothing(), events.LostInTimeAndSpace(char)
  )


def Dreamlands39(char) -> events.Event:
  check = events.Check(char, "lore", -1, difficulty=2)
  clues = events.Gain(char, {"clues": 4})
  loss = events.Loss(char, {"sanity": float("inf")})
  return events.PassFail(char, check, clues, loss)


def Other39(char) -> events.Event:
  return events.Gain(char, {"clues": 1})


def SunkenCity40(char) -> events.Event:
  check = events.Check(char, "will", -1)
  vomit = events.Loss(char, {"sanity": 1, "stamina": 1})
  return events.PassFail(char, check, events.Nothing(), vomit)


def City40(char) -> events.Event:
  return events.GainOrLoss(char, gains={"clues": 1}, losses={"sanity": 1})


def Other40(char) -> events.Event:
  return events.PassFail(
    char,
    events.Check(char, "luck", -1),
    events.Return(char, char.place.info.name),
    events.Delayed(char),
  )


def SunkenCity41(char) -> events.Event:
  die = events.DiceRoll(char, 1, bad=[])
  return events.Sequence([die, events.Loss(char, {"sanity": values.Calculation(die, "sum")})], char)


def City41(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "will", -1), events.Nothing(), events.Loss(char, {"sanity": 2})
  )


def Other41(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "will", -2), events.Nothing(), events.Delayed(char)
  )


def City42(char) -> events.Event:
  return events.PassFail(
    char,
    events.Check(char, "fight", -1),
    events.Nothing(),
    events.Loss(char, {"sanity": 1, "stamina": 1}),
  )


def Pluto42(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "luck", -2), events.Gain(char, {"clues": 2}), events.Delayed(char)
  )


def Other42(char) -> events.Event:
  return events.Gain(char, {"dollars": 2})


def SunkenCity43(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "speed", -1), events.Nothing(), events.Loss(char, {"sanity": 1})
  )


def Pluto43(char) -> events.Event:
  return events.PassOrLoseDice(char, "luck", -1, {"stamina", "sanity"}, adjustment=-2)


def Other43(char) -> events.Event:
  return events.MonsterAppears(char)


def SunkenCity44(char) -> events.Event:
  check = events.Check(char, "will", 0)
  visage = events.Sequence([events.Loss(char, {"stamina": 1}), events.Delayed(char)], char)
  return events.PassFail(char, check, events.Nothing(), visage)


def Dreamlands44(char) -> events.Event:
  check = events.Check(char, "luck", 0)
  web = events.Sequence([events.Loss(char, {"sanity": 2}), events.Delayed(char)], char)
  return events.PassFail(char, check, events.Nothing(), web)


def Other44(char) -> events.Event:
  return events.Gain(char, {"clues": 1})


def SunkenCity45(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "speed", -1), events.Nothing(), events.LostInTimeAndSpace(char)
  )


def Dreamlands45(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "will", -2), events.Nothing(), events.Loss(char, {"sanity": 2})
  )


def Other45(char) -> events.Event:
  return events.MonsterAppears(char)


def Pluto46(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "will", -1), events.Nothing(), events.Loss(char, {"sanity": 2})
  )


def Dreamlands46(char) -> events.Event:
  return events.Loss(char, {"sanity": 1})


def Other46(char) -> events.Event:
  return events.PassFail(
    char,
    events.Check(char, "lore", -1),
    events.Nothing(),
    events.LoseItems(char, 1, decks={"spells"}),
  )


def Pluto47(char) -> events.Event:
  check = events.Check(char, "sneak", -2)
  space_mead = events.Sequence(
    [events.Gain(char, {"clues": 2}), events.Return(char, char.place.info.name)], char
  )
  return events.PassFail(char, check, space_mead, events.LostInTimeAndSpace(char))


def Dreamlands47(char) -> events.Event:
  return events.PassFail(
    char, events.Check(char, "luck", -1), events.Nothing(), events.Delayed(char)
  )


def Other47(char) -> events.Event:
  dice = events.DiceRoll(char, values.Calculation(char, "sanity"), bad=[])
  amount = values.Calculation(
    left=char, left_attr="sanity", operand=operator.sub, right=dice, right_attr="successes"
  )
  loss = events.Loss(char, {"sanity": amount})
  final = events.PassFail(
    char,
    values.Calculation(char, "sanity"),
    events.Gain(char, {"clues": values.Calculation(dice, "successes")}),
    events.Nothing(),
  )
  return events.Sequence([dice, loss, final], char)


def SunkenCity48(char) -> events.Event:
  return events.PassFail(
    char,
    events.Check(char, "speed", -1, difficulty=2),
    events.Gain(char, {"clues": 5}),
    events.Delayed(char),
  )


def Pluto48(char) -> events.Event:
  return events.Nothing()


def Other48(char) -> events.Event:
  knowledge = events.Sequence(
    [events.Draw(char, "spells", 1), events.Loss(char, {"sanity": 1})], char
  )
  return events.PassFail(char, events.Check(char, "lore", -2), knowledge, events.Nothing())


def CreateGateCards():
  return [
    GateCard("Gate1", {"blue"}, {"Abyss": Abyss1, "Great Hall": GreatHall1, "Other": Other1}),
    GateCard("Gate2", {"blue"}, {"Abyss": Abyss2, "Pluto": Pluto2, "Other": Other2}),
    GateCard("Gate3", {"blue"}, {"Abyss": Abyss3, "Pluto": Pluto3, "Other": Other3}),
    GateCard("Gate4", {"blue"}, {"Abyss": Abyss4, "Great Hall": GreatHall4, "Other": Other4}),
    GateCard("Gate5", {"blue"}, {"Dreamlands": Dreamlands5, "Abyss": Abyss5, "Other": Other5}),
    GateCard(
      "Gate6", {"blue"}, {"Dreamlands": Dreamlands6, "Great Hall": GreatHall6, "Other": Other6}
    ),
    GateCard(
      "Gate7", {"blue"}, {"Dreamlands": Dreamlands7, "Great Hall": GreatHall7, "Other": Other7}
    ),
    GateCard("Gate8", {"blue"}, {"Dreamlands": Dreamlands8, "Pluto": Pluto8, "Other": Other8}),
    GateCard("Gate9", {"blue"}, {"Dreamlands": Dreamlands9, "Pluto": Pluto9, "Other": Other9}),
    GateCard("Gate10", {"blue"}, {"Dreamlands": Dreamlands10, "Abyss": Abyss10, "Other": Other10}),
    GateCard("Gate11", {"blue"}, {"Pluto": Pluto11, "Great Hall": GreatHall11, "Other": Other11}),
    GateCard("Gate12", {"blue"}, {"Pluto": Pluto12, "Great Hall": GreatHall12, "Other": Other12}),
    GateCard("Gate13", {"green"}, {"City": City13, "Plateau": Plateau13, "Other": Other13}),
    GateCard("Gate14", {"green"}, {"City": City14, "Great Hall": GreatHall14, "Other": Other14}),
    GateCard("Gate15", {"green"}, {"City": City15, "Great Hall": GreatHall15, "Other": Other15}),
    GateCard(
      "Gate16", {"green"}, {"Plateau": Plateau16, "Great Hall": GreatHall16, "Other": Other16}
    ),
    GateCard(
      "Gate17", {"green"}, {"Plateau": Plateau17, "Great Hall": GreatHall17, "Other": Other17}
    ),
    GateCard("Gate18", {"green"}, {"City": City18, "Plateau": Plateau18, "Other": Other18}),
    GateCard("Gate19", {"green"}, {"Dreamlands": Dreamlands19, "City": City19, "Other": Other19}),
    GateCard(
      "Gate20", {"green"}, {"Dreamlands": Dreamlands20, "Great Hall": GreatHall20, "Other": Other20}
    ),
    GateCard(
      "Gate21", {"green"}, {"Dreamlands": Dreamlands21, "Great Hall": GreatHall21, "Other": Other21}
    ),
    GateCard(
      "Gate22", {"green"}, {"Dreamlands": Dreamlands22, "Plateau": Plateau22, "Other": Other22}
    ),
    GateCard(
      "Gate23", {"green"}, {"Dreamlands": Dreamlands23, "Plateau": Plateau23, "Other": Other23}
    ),
    GateCard("Gate24", {"green"}, {"Dreamlands": Dreamlands24, "City": City24, "Other": Other24}),
    GateCard("Gate25", {"red"}, {"Abyss": Abyss25, "Dreamlands": Dreamlands25, "Other": Other25}),
    GateCard("Gate26", {"red"}, {"Abyss": Abyss26, "Plateau": Plateau26, "Other": Other26}),
    GateCard("Gate27", {"red"}, {"Abyss": Abyss27, "Plateau": Plateau27, "Other": Other27}),
    GateCard(
      "Gate28", {"red"}, {"Plateau": Plateau28, "Dreamlands": Dreamlands28, "Other": Other28}
    ),
    GateCard(
      "Gate29", {"red"}, {"Plateau": Plateau29, "Dreamlands": Dreamlands29, "Other": Other29}
    ),
    GateCard("Gate30", {"red"}, {"Abyss": Abyss30, "Dreamlands": Dreamlands30, "Other": Other30}),
    GateCard(
      "Gate31", {"red"}, {"Sunken City": SunkenCity31, "Plateau": Plateau31, "Other": Other31}
    ),
    GateCard("Gate32", {"red"}, {"Sunken City": SunkenCity32, "Abyss": Abyss32, "Other": Other32}),
    GateCard("Gate33", {"red"}, {"Sunken City": SunkenCity33, "Abyss": Abyss33, "Other": Other33}),
    GateCard(
      "Gate34", {"red"}, {"Sunken City": SunkenCity34, "Dreamlands": Dreamlands34, "Other": Other34}
    ),
    GateCard(
      "Gate35", {"red"}, {"Sunken City": SunkenCity35, "Dreamlands": Dreamlands35, "Other": Other35}
    ),
    GateCard(
      "Gate36", {"red"}, {"Sunken City": SunkenCity36, "Plateau": Plateau36, "Other": Other36}
    ),
    GateCard("Gate37", {"yellow"}, {"City": City37, "Pluto": Pluto37, "Other": Other37}),
    GateCard("Gate38", {"yellow"}, {"City": City38, "Dreamlands": Dreamlands38, "Other": Other38}),
    GateCard("Gate39", {"yellow"}, {"City": City39, "Dreamlands": Dreamlands39, "Other": Other39}),
    GateCard("Gate40", {"yellow"}, {"Sunken City": SunkenCity40, "City": City40, "Other": Other40}),
    GateCard("Gate41", {"yellow"}, {"Sunken City": SunkenCity41, "City": City41, "Other": Other41}),
    GateCard("Gate42", {"yellow"}, {"City": City42, "Pluto": Pluto42, "Other": Other42}),
    GateCard(
      "Gate43", {"yellow"}, {"Sunken City": SunkenCity43, "Pluto": Pluto43, "Other": Other43}
    ),
    GateCard(
      "Gate44",
      {"yellow"},
      {"Sunken City": SunkenCity44, "Dreamlands": Dreamlands44, "Other": Other44},
    ),
    GateCard(
      "Gate45",
      {"yellow"},
      {"Sunken City": SunkenCity45, "Dreamlands": Dreamlands45, "Other": Other45},
    ),
    GateCard(
      "Gate46", {"yellow"}, {"Pluto": Pluto46, "Dreamlands": Dreamlands46, "Other": Other46}
    ),
    GateCard(
      "Gate47", {"yellow"}, {"Pluto": Pluto47, "Dreamlands": Dreamlands47, "Other": Other47}
    ),
    GateCard(
      "Gate48", {"yellow"}, {"Sunken City": SunkenCity48, "Pluto": Pluto48, "Other": Other48}
    ),
    GateCard("ShuffleGate", set(), {"Other": lambda char: events.Nothing()}),
  ]
