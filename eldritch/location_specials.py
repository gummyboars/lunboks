from collections import namedtuple

from eldritch import events
from eldritch import values

FixedEncounter = namedtuple("FixedEncounter", ["name", "prereq", "encounter"])


def CreateFixedEncounters():
  restore_sanity = FixedEncounter(
      name="Restore 1 Sanity",
      prereq=lambda char: values.AttributeNotMaxedPrerequisite(char, "sanity"),
      encounter=lambda char: events.Gain(char, {"sanity": 1}),
  )

  restore_all_sanity = FixedEncounter(
      name="Restore All Sanity",
      prereq=lambda char: values.ExactSpendPrerequisite({"dollars": 2}),
      encounter=lambda char: events.Gain(char, {"sanity": float("inf")}),
  )

  restore_stamina = FixedEncounter(
      name="Restore 1 Stamina",
      prereq=lambda char: values.AttributeNotMaxedPrerequisite(char, "stamina"),
      encounter=lambda char: events.Gain(char, {"stamina": 1}),
  )

  restore_all_stamina = FixedEncounter(
      name="Restore All Stamina",
      prereq=lambda char: values.ExactSpendPrerequisite({"dollars": 2}),
      encounter=lambda char: events.Gain(char, {"stamina": float("inf")}),
  )

  purchase_unique = FixedEncounter(
      name="unique",  # Make it the name of the deck so it shows up in CardChoice
      prereq=lambda char: values.AttributePrerequisite(char, "dollars", 1, "at least"),
      encounter=lambda char: events.Purchase(char, "unique", 3),
  )

  purchase_common = FixedEncounter(
      name="common",  # Make it the name of the deck so it shows up in CardChoice
      prereq=lambda char: values.AttributePrerequisite(char, "dollars", 1, "at least"),
      encounter=lambda char: events.Purchase(char, "common", 3),
  )

  return {
      "Shop": [purchase_unique],
      "Asylum": [restore_sanity, restore_all_sanity],
      "Store": [purchase_common],
      "Hospital": [restore_stamina, restore_all_stamina],
  }
