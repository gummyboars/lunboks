import operator
from eldritch import events
from eldritch import items
from eldritch import values


class GateCard:

  def __init__(self, name, colors, encounter_creators):
    assert "Other" in encounter_creators
    self.name = name
    self.colors = colors
    self.encounters = {}
    for world, encounter_creator in encounter_creators.items():
      self.add_encounter(world, encounter_creator)

  def add_encounter(self, world, encounter_creator):
    self.encounters[world] = encounter_creator

  def encounter_event(self, character, world_name):
    if world_name not in self.encounters:
      world_name = "Other"
    return self.encounters[world_name](character)


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
  # check = events.Check(char, "speed", -2)
  # return events.Sequence(
  #     [
  #       events.PassFail(
  #           char,
  #           check,
  #           events.Return(char, char.place.info.name),
  #           events.LostInTimeAndSpace(char),
  #       ),
  #       events.CloseGate(char, "the one you entered"),
  #      ], char
  # )
  return events.Unimplemented()


def Abyss3(char) -> events.Event:
  check = events.Check(char, "lore", -1)
  return events.PassFail(char, check, events.Nothing(), events.Delayed(char))


def Pluto3(char) -> events.Event:
  check = events.Check(char, "sneak", -1)
  lose_count = values.Calculation(
      values.ItemCount(char), None,
      operator.floordiv, 2,
  )
  fail = events.Sequence([
      events.LoseItems(char, lose_count),
      events.Return(char, char.place.info.name)
  ], char)
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
  return events.Sequence([
      check,
      events.Conditional(char, check, "successes", {0: cave, 2: dreamlands, 3: temple}),
  ], char)


def GreatHall4(char) -> events.Event:
  check = events.Check(char, "fight", -1)
  spells = events.Draw(char, "spells", 3, keep_count=2)
  loss = events.Loss(char, {"stamina": 3})
  return events.PassFail(char, check, loss, spells, min_successes=2)


def Other4(char) -> events.Event:
  return events.MonsterAppears(char)


def Dreamlands5(char) -> events.Event:
  return events.Nothing()


def Abyss5(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  fishy_object = events.Sequence([
      events.Gain(char, {"dollars": 3}),
      events.Draw(char, "unique", 1),
  ], char)
  return events.PassFail(char, check, fishy_object, events.Nothing())


def Other5(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  gain = events.Gain(char, {"clues": values.Calculation(check, "successes")})
  gain_cond = events.PassFail(
      char, values.Calculation(check, "successes"), gain, events.Nothing()
  )
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
  lose_item_count = values.Calculation(
      values.ItemCount(char), None,
      values.ceildiv, 2,
  )
  lose_money_count = values.Calculation(char, "dollars", values.ceildiv, 2)
  loss = events.Sequence([
      events.LoseItems(char, lose_item_count),
      events.Loss(char, {"dollars": lose_money_count})
  ], char)
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
  prison = events.PassFail(char, dice_roll, events.Delayed(char), events.MonsterAppears(char))
  return events.PassFail(char, check, events.Nothing(), prison)


def Other11(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  weapon = events.Draw(char, "common", 1, target_type=items.Weapon)
  return events.PassFail(char, check, weapon, events.Nothing())


def Pluto12(char) -> events.Event:
  check = events.Check(char, "will", -2)
  san_loss = events.Loss(char, {"sanity": 2})
  spell_loss = events.LoseItems(char, 2, "Lose spells", {"spells"})
  prereq = values.ItemDeckPrerequisite(char, "spells", threshold=2)
  choice = events.BinaryChoice(
      char, "Lose spells or sanity?",
      "Lose 2 spells", "Lose 2 sanity",
      spell_loss, san_loss,
      prereq=prereq
  )
  return events.PassFail(char, check, events.Nothing(), choice)


def GreatHall12(char) -> events.Event:
  return events.MonsterAppears(char)


def Other12(char) -> events.Event:
  check = events.Check(char, "sneak", -2)
  return events.PassFail(char, check, events.Nothing(), events.Delayed(char))


def City13(char) -> events.Event:
  check = events.Check(char, "sneak", -1)
  escape = events.Sequence([
      events.Draw(char, "unique", 1),
      events.Return(char, char.place.info.name),
  ], char)
  captors = events.Loss(char, {"sanity": 3, "stamina": 1})
  return events.PassFail(char, check, escape, captors, min_successes=2)


def Plateau13(char) -> events.Event:
  check = events.Check(char, "lore", -2)
  trade = events.Gain(char, {"dollars": 6})
  lost = events.LostInTimeAndSpace(char)
  choice = events.BinaryChoice(
      char, "Trade with the dangerous hooved folk?",
      "Yes", "No",
      events.PassFail(char, check, trade, lost), events.Nothing(),
  )
  return choice


def Other13(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  return events.PassFail(char, check, events.Gain(char, {"clues": 2}), events.Nothing())


def City14(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  statue = events.Sequence([
      events.Gain(char, {"dollars": 10}),
      events.Curse(char),
  ])
  choice = events.BinaryChoice(
      char, "Take the golden statue?", "Yes", "No", statue, events.Nothing()
  )
  return events.PassFail(char, check, choice, events.Nothing())


def GreatHall14(char) -> events.Event:
  return events.Delayed(char)


def Other14(char) -> events.Event:
  check = events.Check(char, "fight", -1)
  rope = events.Return(char, char.place.info.name)
  fall = events.Sequence([
      events.Loss(char, {"stamina": 2}),
      events.Delayed(char),
  ], char)
  return events.PassFail(char, check, rope, fall)


def City15(char) -> events.Event:
  check = events.Check(char, "lore", -2)
  spells = events.Draw(char, "spells", 2)
  return events.PassFail(char, check, spells, events.Nothing(), min_successes=2)


def GreatHall15(char) -> events.Event:
  check = events.Check(char, "lore", 2)
  gain = events.Gain(char, {"clues": values.Calculation(check, "successes")})
  gain_cond = events.PassFail(
      char, values.Calculation(check, "successes"), gain, events.Nothing()
  )
  return events.Sequence([check, gain_cond], char)


def Other15(char) -> events.Event:
  return events.Gain(char, {"dollars": 3})


def Plateau16(char) -> events.Event:
  return events.Nothing()


def GreatHall16(char) -> events.Event:
  check = events.Check(char, "luck", -1)
  draw = events.Draw(char, "skills", 1)
  cond = events.Conditional(char, check, "successes", {0: events.Nothing(), 2: draw})
  return events.Sequence([check, cond], char)


def Other16(char) -> events.Event:
  check = events.Check(char, "sneak", -1)
  gain = events.Gain(char, {"dollars": 3})
  loss = events.Loss(char, {"stamina": 2})
  return events.PassFail(char, check, gain, loss)


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


def CreateGateCards():
  return [
      GateCard(
          "Gate1", {"blue"}, {"Abyss": Abyss1, "GreatHall": GreatHall1, "Other": Other1}),
      GateCard(
          "Gate2", {"blue"}, {"Abyss": Abyss2, "Pluto": Pluto2, "Other": Other2}),
      GateCard(
          "Gate3", {"blue"}, {"Abyss": Abyss3, "Pluto": Pluto3, "Other": Other3}),
      GateCard(
          "Gate4", {"blue"}, {"Abyss": Abyss4, "GreatHall": GreatHall4, "Other": Other4}),
      GateCard(
          "Gate5", {"blue"}, {"Dreamlands": Dreamlands5, "Abyss": Abyss5, "Other": Other5}),
      GateCard(
          "Gate6", {"blue"}, {"Dreamlands": Dreamlands6, "GreatHall": GreatHall6, "Other": Other6}),
      GateCard(
          "Gate7", {"blue"}, {"Dreamlands": Dreamlands7, "GreatHall": GreatHall7, "Other": Other7}),
      GateCard(
          "Gate8", {"blue"}, {"Dreamlands": Dreamlands8, "Pluto": Pluto8, "Other": Other8}),
      GateCard(
          "Gate9", {"blue"}, {"Dreamlands": Dreamlands9, "Pluto": Pluto9, "Other": Other9}),
      GateCard(
          "Gate10", {"blue"}, {"Dreamlands": Dreamlands10, "Abyss": Abyss10, "Other": Other10}),
      GateCard(
          "Gate11", {"blue"}, {"Pluto": Pluto11, "GreatHall": GreatHall11, "Other": Other11}),
      GateCard(
          "Gate12", {"blue"}, {"Pluto": Pluto12, "GreatHall": GreatHall12, "Other": Other12}),
      GateCard(
          "Gate13", {"green"}, {"City": City13, "Plateau": Plateau13, "Other": Other13}),
      GateCard(
          "Gate14", {"green"}, {"City": City14, "GreatHall": GreatHall14, "Other": Other14}),
      GateCard(
          "Gate15", {"green"}, {"City": City15, "GreatHall": GreatHall15, "Other": Other15}),
      GateCard(
          "Gate16", {"green"}, {"Plateau": Plateau16, "Great Hall": GreatHall16, "Other": Other16}),
      GateCard(
          "Gate29", {"red"}, {"Plateau": Plateau29, "Dreamlands": Dreamlands29, "Other": Other29}),
      GateCard("ShuffleGate", set(), {"Other": lambda char: events.Nothing()}),
  ]
