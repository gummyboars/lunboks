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


def Plateau17(char) -> events.Event:
  return events.Unimplemented()


def GreatHall17(char) -> events.Event:
  return events.Unimplemented()


def Other17(char) -> events.Event:
  return events.Unimplemented()


def Plateau18(char) -> events.Event:
  return events.Unimplemented()


def City18(char) -> events.Event:
  return events.Unimplemented()


def Other18(char) -> events.Event:
  return events.Unimplemented()


def City19(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands19(char) -> events.Event:
  return events.Unimplemented()


def Other19(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands20(char) -> events.Event:
  return events.Unimplemented()


def GreatHall20(char) -> events.Event:
  return events.Unimplemented()


def Other20(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands21(char) -> events.Event:
  return events.Unimplemented()


def GreatHall21(char) -> events.Event:
  return events.Unimplemented()


def Other21(char) -> events.Event:
  return events.Unimplemented()


def Plateau22(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands22(char) -> events.Event:
  return events.Unimplemented()


def Other22(char) -> events.Event:
  return events.Unimplemented()


def Plateau23(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands23(char) -> events.Event:
  return events.Unimplemented()


def Other23(char) -> events.Event:
  return events.Unimplemented()


def City24(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands24(char) -> events.Event:
  return events.Unimplemented()


def Other24(char) -> events.Event:
  return events.Unimplemented()


def Abyss25(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands25(char) -> events.Event:
  return events.Unimplemented()


def Other25(char) -> events.Event:
  return events.Unimplemented()


def Abyss26(char) -> events.Event:
  return events.Unimplemented()


def Plateau26(char) -> events.Event:
  return events.Unimplemented()


def Other26(char) -> events.Event:
  return events.Unimplemented()


def Abyss27(char) -> events.Event:
  return events.Unimplemented()


def Plateau27(char) -> events.Event:
  return events.Unimplemented()


def Other27(char) -> events.Event:
  return events.Unimplemented()


def Plateau28(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands28(char) -> events.Event:
  return events.Unimplemented()


def Other28(char) -> events.Event:
  return events.Unimplemented()


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
  return events.Unimplemented()


def Dreamlands30(char) -> events.Event:
  return events.Unimplemented()


def Other30(char) -> events.Event:
  return events.Unimplemented()


def Plateau31(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity31(char) -> events.Event:
  return events.Unimplemented()


def Other31(char) -> events.Event:
  return events.Unimplemented()


def Abyss32(char) -> events.Event:
  return events.Unimplemented()


def Other32(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity32(char) -> events.Event:
  return events.Unimplemented()


def Abyss33(char) -> events.Event:
  return events.Unimplemented()


def Other33(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity33(char) -> events.Event:
  return events.Unimplemented()


def Other34(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands34(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity34(char) -> events.Event:
  return events.Unimplemented()


def Other35(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands35(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity35(char) -> events.Event:
  return events.Unimplemented()


def Plateau36(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity36(char) -> events.Event:
  return events.Unimplemented()


def Other36(char) -> events.Event:
  return events.Unimplemented()


def City37(char) -> events.Event:
  return events.Unimplemented()


def Pluto37(char) -> events.Event:
  return events.Unimplemented()


def Other37(char) -> events.Event:
  return events.Unimplemented()


def City38(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands38(char) -> events.Event:
  return events.Unimplemented()


def Other38(char) -> events.Event:
  return events.Unimplemented()


def City39(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands39(char) -> events.Event:
  return events.Unimplemented()


def Other39(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity40(char) -> events.Event:
  return events.Unimplemented()


def City40(char) -> events.Event:
  return events.Unimplemented()


def Other40(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity41(char) -> events.Event:
  return events.Unimplemented()


def City41(char) -> events.Event:
  return events.Unimplemented()


def Other41(char) -> events.Event:
  return events.Unimplemented()


def City42(char) -> events.Event:
  return events.Unimplemented()


def Pluto42(char) -> events.Event:
  return events.Unimplemented()


def Other42(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity43(char) -> events.Event:
  return events.Unimplemented()


def Pluto43(char) -> events.Event:
  return events.Unimplemented()


def Other43(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity44(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands44(char) -> events.Event:
  return events.Unimplemented()


def Other44(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity45(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands45(char) -> events.Event:
  return events.Unimplemented()


def Other45(char) -> events.Event:
  return events.Unimplemented()


def Pluto46(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands46(char) -> events.Event:
  return events.Unimplemented()


def Other46(char) -> events.Event:
  return events.Unimplemented()


def Pluto47(char) -> events.Event:
  return events.Unimplemented()


def Dreamlands47(char) -> events.Event:
  return events.Unimplemented()


def Other47(char) -> events.Event:
  return events.Unimplemented()


def SunkenCity48(char) -> events.Event:
  return events.Unimplemented()


def Pluto48(char) -> events.Event:
  return events.Unimplemented()


def Other48(char) -> events.Event:
  return events.Unimplemented()


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
          "Gate17", {"green"}, {"Plateau": Plateau17, "Great Hall": GreatHall17, "Other": Other17}),
      GateCard(
          "Gate18", {"green"}, {"City": City18, "Plateau": Plateau18, "Other": Other18}),
      GateCard(
          "Gate19", {"green"}, {"Dreamlands": Dreamlands19, "City": City19, "Other": Other19}),
      GateCard(
          "Gate20", {"green"},
          {"Dreamlands": Dreamlands20, "Great Hall": GreatHall20, "Other": Other20}),
      GateCard(
          "Gate21", {"green"},
          {"Dreamlands": Dreamlands21, "Great Hall": GreatHall21, "Other": Other21}),
      GateCard(
          "Gate22",
          {"green"}, {"Dreamlands": Dreamlands22, "Plateau": Plateau22, "Other": Other22}),
      GateCard(
          "Gate23",
          {"green"}, {"Dreamlands": Dreamlands23, "Plateau": Plateau23, "Other": Other23}),
      GateCard(
          "Gate24", {"green"}, {"Dreamlands": Dreamlands24, "City": City24, "Other": Other24}),
      GateCard(
          "Gate25", {"red"}, {"Abyss": Abyss25, "Dreamlands": Dreamlands25, "Other": Other25}),
      GateCard(
          "Gate26", {"red"}, {"Abyss": Abyss26, "Plateau": Plateau26, "Other": Other26}),
      GateCard(
          "Gate27", {"red"}, {"Abyss": Abyss27, "Plateau": Plateau27, "Other": Other27}),
      GateCard(
          "Gate28", {"red"}, {"Plateau": Plateau28, "Dreamlands": Dreamlands28, "Other": Other28}),
      GateCard(
          "Gate29", {"red"}, {"Plateau": Plateau29, "Dreamlands": Dreamlands29, "Other": Other29}),
      GateCard(
          "Gate30", {"red"}, {"Abyss": Abyss30, "Dreamlands": Dreamlands30, "Other": Other30}),
      GateCard(
          "Gate31", {"red"}, {"Sunken City": SunkenCity31, "Plateau": Plateau31, "Other": Other31}),
      GateCard(
          "Gate32", {"red"}, {"Sunken City": SunkenCity32, "Abyss": Abyss32, "Other": Other32}),
      GateCard(
          "Gate33", {"red"}, {"Sunken City": SunkenCity33, "Abyss": Abyss33, "Other": Other33}),
      GateCard(
          "Gate34", {"red"},
          {"Sunken City": SunkenCity34, "Dreamlands": Dreamlands34, "Other": Other34}),
      GateCard(
          "Gate35", {"red"},
          {"Sunken City": SunkenCity35, "Dreamlands": Dreamlands35, "Other": Other35}),
      GateCard(
          "Gate36", {"red"}, {"Sunken City": SunkenCity36, "Plateau": Plateau36, "Other": Other36}),
      GateCard(
          "Gate37", {"yellow"}, {"City": City37, "Pluto": Pluto37, "Other": Other37}),
      GateCard(
          "Gate38", {"yellow"}, {"City": City38, "Dreamlands": Dreamlands38, "Other": Other38}),
      GateCard(
          "Gate39", {"yellow"}, {"City": City39, "Dreamlands": Dreamlands39, "Other": Other39}),
      GateCard(
          "Gate40", {"yellow"}, {"Sunken City": SunkenCity40, "City": City40, "Other": Other40}),
      GateCard(
          "Gate41", {"yellow"}, {"Sunken City": SunkenCity41, "City": City41, "Other": Other41}),
      GateCard(
          "Gate42", {"yellow"}, {"City": City42, "Pluto": Pluto42, "Other": Other42}),
      GateCard(
          "Gate43", {"yellow"}, {"Sunken City": SunkenCity43, "Pluto": Pluto43, "Other": Other43}),
      GateCard(
          "Gate44", {"yellow"},
          {"Sunken City": SunkenCity44, "Dreamlands": Dreamlands44, "Other": Other44}),
      GateCard(
          "Gate45", {"yellow"},
          {"Sunken City": SunkenCity45, "Dreamlands": Dreamlands45, "Other": Other45}),
      GateCard(
          "Gate46", {"yellow"}, {"Pluto": Pluto46, "Dreamlands": Dreamlands46, "Other": Other46}),
      GateCard(
          "Gate47", {"yellow"}, {"Pluto": Pluto47, "Dreamlands": Dreamlands47, "Other": Other47}),
      GateCard(
          "Gate48", {"yellow"}, {"Sunken City": SunkenCity48, "Pluto": Pluto48, "Other": Other48}),
      GateCard("ShuffleGate", set(), {"Other": lambda char: events.Nothing()}),
  ]
