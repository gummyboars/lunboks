from collections import namedtuple

from eldritch import events
from eldritch import values

FixedEncounter = namedtuple("FixedEncounter", ["name", "prereq", "spend", "encounter"])


def BlessAnyCharacter(char, state):
  eligible = [character for character in state.characters if not character.gone]
  blesses = {idx: events.Bless(character) for idx, character in enumerate(eligible)}
  names = [character.name for character in eligible]
  choice = events.MultipleChoice(char, "Choose an investigator to be blessed.", names)
  return events.Sequence([choice, events.Conditional(char, choice, "choice_index", blesses)], char)


def CreateFixedEncounters():
  purchase_unique = FixedEncounter(
      name="unique",  # Make it the name of the deck so it shows up in CardChoice
      prereq=lambda char: values.AttributePrerequisite(char, "dollars", 1, "at least"),
      spend=lambda char: None,
      encounter=lambda char, state: events.Purchase(char, "unique", 3, must_buy=True),
  )

  take_loan = FixedEncounter(
      name="Bank Loan",
      prereq=lambda char: values.OverridePrerequisite(char, "can_take_bank_loan"),
      spend=lambda char: None,
      encounter=lambda char, state: events.TakeBankLoan(char)
  )

  restore_sanity = FixedEncounter(
      name="Restore 1 Sanity",
      prereq=lambda char: values.AttributeNotMaxedPrerequisite(char, "sanity"),
      spend=lambda char: None,
      encounter=lambda char, state: events.Gain(char, {"sanity": 1}, source=state.places["Asylum"]),
  )

  restore_all_sanity = FixedEncounter(
      name="Restore All Sanity",
      prereq=lambda char: values.AttributeNotMaxedPrerequisite(char, "sanity"),
      spend=lambda char: values.ExactSpendPrerequisite({"dollars": 2}),
      encounter=lambda char, state: events.Gain(
          char, {"sanity": float("inf")}, source=state.places["Asylum"]),
  )

  deputize = FixedEncounter(
      name="Deputy",  # Make it the name of the card so it shows up in CardChoice
      prereq=lambda char: values.ContainsPrerequisite(
          "specials", "Deputy", error_fmt="Someone else is already the deputy",
      ),
      spend=lambda char: values.ToughnessOrGatesSpend(10),
      encounter=lambda char, state: events.DrawSpecific(char, "specials", "Deputy"),
  )

  purchase_common = FixedEncounter(
      name="common",  # Make it the name of the deck so it shows up in CardChoice
      prereq=lambda char: values.AttributePrerequisite(char, "dollars", 1, "at least"),
      spend=lambda char: None,
      encounter=lambda char, state: events.Purchase(char, "common", 3, must_buy=True),
  )

  ally = FixedEncounter(
      name="allies",
      prereq=lambda char: None,
      spend=lambda char: values.ToughnessOrGatesSpend(10),
      encounter=lambda char, state: events.Draw(char, "allies", float("inf")),
  )

  bless = FixedEncounter(
      name="Blessing",
      prereq=lambda char: None,
      spend=lambda char: values.ToughnessOrGatesSpend(5),
      encounter=BlessAnyCharacter,
  )

  spell = FixedEncounter(
      name="spells",  # Make it the name of the deck so it shows up in CardChoice
      prereq=lambda char: None,
      spend=lambda char: values.ExactSpendPrerequisite({"dollars": 5}),
      encounter=lambda char, state: events.Draw(char, "spells", 2, "Keep one spell"),
  )

  restore_stamina = FixedEncounter(
      name="Restore 1 Stamina",
      prereq=lambda char: values.AttributeNotMaxedPrerequisite(char, "stamina"),
      spend=lambda char: None,
      encounter=lambda char, state: events.Gain(
          char, {"stamina": 1}, source=state.places["Hospital"]),
  )

  restore_all_stamina = FixedEncounter(
      name="Restore All Stamina",
      prereq=lambda char: values.AttributeNotMaxedPrerequisite(char, "stamina"),
      spend=lambda char: values.ExactSpendPrerequisite({"dollars": 2}),
      encounter=lambda char, state: events.Gain(
          char, {"stamina": float("inf")}, source=state.places["Hospital"]),
  )

  skill = FixedEncounter(
      name="skills",  # Make it the name of the deck so it shows up in CardChoice
      prereq=lambda char: None,
      spend=lambda char: values.ExactSpendPrerequisite({"dollars": 8}),
      encounter=lambda char, state: events.Draw(char, "skills", 2, "Keep one skill"),
  )

  clues = FixedEncounter(
      name="Gain 2 clues",
      prereq=lambda char: None,
      spend=lambda char: values.ToughnessOrGatesSpend(5),
      encounter=lambda char, state: events.Gain(char, {"clues": 2}),
  )

  dollars = FixedEncounter(
      name="Gain $5",
      prereq=lambda char: None,
      spend=lambda char: values.ToughnessOrGatesSpend(5),
      encounter=lambda char, state: events.Gain(char, {"dollars": 5})
  )

  return {
      "Shop": [purchase_unique],
      "Bank": [take_loan],
      "Asylum": [restore_sanity, restore_all_sanity],
      "Police": [deputize],
      "Store": [purchase_common],
      "House": [ally],
      "Church": [bless],
      "Shoppe": [spell],
      "Hospital": [restore_stamina, restore_all_stamina],
      "Administration": [skill],
      "Science": [clues],
      "Docks": [dollars],
  }
