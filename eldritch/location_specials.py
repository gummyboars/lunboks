from collections import namedtuple

from eldritch import events
from eldritch import values

FixedEncounter = namedtuple("FixedEncounter", ["name", "prereq", "spend", "encounter"])


def CreateFixedEncounters():
  purchase_unique = FixedEncounter(
      name="unique",  # Make it the name of the deck so it shows up in CardChoice
      prereq=lambda char: values.AttributePrerequisite(char, "dollars", 1, "at least"),
      spend=lambda char: None,
      encounter=lambda char: events.Purchase(char, "unique", 3),
  )

  restore_sanity = FixedEncounter(
      name="Restore 1 Sanity",
      prereq=lambda char: values.AttributeNotMaxedPrerequisite(char, "sanity"),
      spend=lambda char: None,
      encounter=lambda char: events.Gain(char, {"sanity": 1}),
  )

  restore_all_sanity = FixedEncounter(
      name="Restore All Sanity",
      prereq=lambda char: values.AttributeNotMaxedPrerequisite(char, "sanity"),
      spend=lambda char: values.ExactSpendPrerequisite({"dollars": 2}),
      encounter=lambda char: events.Gain(char, {"sanity": float("inf")}),
  )

  purchase_common = FixedEncounter(
      name="common",  # Make it the name of the deck so it shows up in CardChoice
      prereq=lambda char: values.AttributePrerequisite(char, "dollars", 1, "at least"),
      spend=lambda char: None,
      encounter=lambda char: events.Purchase(char, "common", 3),
  )

  bless = FixedEncounter(
      name="Blessing",
      prereq=lambda char: None,
      spend=lambda char: values.ToughnessOrGatesSpend(5),
      encounter=events.Bless,  # TODO: this should be bless ANY character
  )

  spell = FixedEncounter(
      name="spells",  # Make it the name of the deck so it shows up in CardChoice
      prereq=lambda char: None,
      spend=lambda char: values.ExactSpendPrerequisite({"dollars": 5}),
      encounter=lambda char: events.Draw(char, "spells", 2, "Keep one spell"),
  )

  restore_stamina = FixedEncounter(
      name="Restore 1 Stamina",
      prereq=lambda char: values.AttributeNotMaxedPrerequisite(char, "stamina"),
      spend=lambda char: None,
      encounter=lambda char: events.Gain(char, {"stamina": 1}),
  )

  restore_all_stamina = FixedEncounter(
      name="Restore All Stamina",
      prereq=lambda char: values.AttributeNotMaxedPrerequisite(char, "stamina"),
      spend=lambda char: values.ExactSpendPrerequisite({"dollars": 2}),
      encounter=lambda char: events.Gain(char, {"stamina": float("inf")}),
  )

  skill = FixedEncounter(
      name="skills",  # Make it the name of the deck so it shows up in CardChoice
      prereq=lambda char: None,
      spend=lambda char: values.ExactSpendPrerequisite({"dollars": 8}),
      encounter=lambda char: events.Draw(char, "skills", 2, "Keep one spell"),
  )

  clues = FixedEncounter(
      name="Gain 2 clues",
      prereq=lambda char: None,
      spend=lambda char: values.ToughnessOrGatesSpend(5),
      encounter=lambda char: events.Gain(char, {"clues": 2}),
  )

  dollars = FixedEncounter(
      name="Gain $5",
      prereq=lambda char: None,
      spend=lambda char: values.ToughnessOrGatesSpend(5),
      encounter=lambda char: events.Gain(char, {"dollars": 5})
  )

  return {
      "Shop": [purchase_unique],
      "Asylum": [restore_sanity, restore_all_sanity],
      "Store": [purchase_common],
      "Church": [bless],
      "Shoppe": [spell],
      "Hospital": [restore_stamina, restore_all_stamina],
      "Administration": [skill],
      "Science": [clues],
      "Docks": [dollars],
  }
