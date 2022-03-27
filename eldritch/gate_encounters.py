import operator

from eldritch import events
from eldritch import values

class GateCard(object):

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

def Abyss2(char):
  return events.Gain(char, {"stamina": 1})
def Pluto2(char):
  check = events.Check(char, "fight", -2)
  return events.PassFail(char, check, events.Nothing(), events.LostInTimeAndSpace(char))
def Other2(char):
  check = events.Check(char, "speed", -2)
  return events.PassFail(char, check, events.Return(char, char.place.info.name), events.LostInTimeAndSpace(char))
  #TODO for Ozan: implement "in either event, you automatically close the gate you entered through

def Dreamlands5(char):
  return events.Nothing()
def Abyss5(char):
  check = events.Check(char, "luck", -1)
  gain1 = events.Draw(char, "unique", 1)
  gain2 = events.Gain(char, {"dollars": 3})
  return events.PassFail(char, check, events.Sequence([gain1, gain2], char), events.Nothing())
def Other5(char):
  check = events.Check(char, "luck", -1)
  gain = events.Gain(char, {"clues": values.Calculation(check, "successes", operator.mul, 1)})
  return events.PassFail(char, check, gain, events.Nothing())

def Dreamlands10(char):
  check = events.Check(char, "luck", -1)
  loss = events.Loss(char, {"stamina": 1})
  delay = events.Delayed(char)
  return events.PassFail(char, check, events.Nothing(), events.Sequence([loss, delay], char))
def Abyss10(char):
  check = events.Check(char, "luck", -2)
  loss = events.Loss(char, {"sanity": 1})
  delay = events.Delayed(char)
  return events.PassFail(char, check, events.Nothing(), events.Sequence([loss, delay], char))
def Other10(char):
  check = events.Check(char, "lore", -1)
  delay = events.Delayed(char)
  return events.PassFail(char, check, events.Nothing(), delay)

def Plateau16(char):
  return events.Nothing()
def GreatHall16(char):
  check = events.Check(char, "luck", -1)
  draw = events.Draw(char, "skills", 1)
  cond = events.Conditional(char, check, "successes", {0: events.Nothing(), 2: draw})
  return events.Sequence([check, cond], char)
def Other16(char):
  check = events.Check(char, "sneak", -1)
  gain = events.Gain(char, {"dollars": 3})
  loss = events.Loss(char, {"stamina": 2})
  return events.PassFail(char, check, gain, loss)

def Plateau29(char):
  check = events.Check(char, "speed", -1)
  loss = events.Loss(char, {"stamina": 2})
  return events.PassFail(char, check, events.Nothing(), loss)
def Dreamlands29(char):
  check = events.Check(char, "speed", -1)
  loss = events.Loss(char, {"stamina": 3})
  return events.PassFail(char, check, events.Nothing(), loss)
def Other29(char):
  return events.Loss(char, {"stamina": 1})


def CreateGateCards():
  return [
      GateCard(
        "Gate2", {"blue"}, {"Abyss": Abyss2, "Pluto": Pluto2, "Other": Other2}),
      GateCard(
        "Gate5", {"blue"}, {"Dreamlands": Dreamlands5, "Abyss": Abyss5, "Other": Other5}),
      GateCard(
        "Gate10", {"blue"}, {"Dreamlands": Dreamlands10, "Abyss": Abyss10, "Other": Other10}),
      GateCard(
        "Gate16", {"green"}, {"Plateau": Plateau16, "Great Hall": GreatHall16, "Other": Other16}),
      GateCard(
        "Gate29", {"red"}, {"Plateau": Plateau29, "Dreamlands": Dreamlands29, "Other": Other29}),
      GateCard("Shuffle", set(), {"Other": lambda char: events.Nothing()}),
  ]
