from unittest import mock
from typing import cast

import eldritch.eldritch
from eldritch.test_events import EventTest
from eldritch import assets
from eldritch import events
from eldritch import items


def mock_randint(return_value=None, side_effect=None) -> mock.MagicMock:
  return cast(
      mock.MagicMock, mock.patch.object(
          events.random, "randint",
          new=mock.MagicMock(return_value=return_value, side_effect=side_effect)
      ),
  )


class CurseBlessTest(EventTest):
  def setUp(self):
    super().setUp()
    self.advance_turn(0, "encounter")
    self.resolve_until_done()
    self.dummy_possession = assets.SelfDiscardingCard("Fake Special", 0)
    self.char.possessions.append(self.dummy_possession)

  def doBlessingTest(self, bless_int):
    self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, bless_int)
    self.assertEqual(
        len([p for p in self.char.possessions if isinstance(p, assets.BlessingOrCurse)]),
        bless_int
    )
    with mock_randint(return_value=4):
      roll = events.DiceRoll(self.char, 1)
      self.state.event_stack.append(roll)
      self.resolve_until_done()
      self.assertEqual(roll.successes, bless_int)

    # Ensure that any discarded Blessings/Curses will get a first-round pass when they're re-drawn
    for card in self.state.specials:
      if isinstance(card, assets.SelfDiscardingCard):
        self.assertEqual(card.tokens["must_roll"], 0)


class BlessingTest(CurseBlessTest):
  def testRollForBlessing(self):
    self.doBlessingTest(0)
    self.state.event_stack.append(events.Bless(self.char))
    self.resolve_until_done()
    blessing = next(p for p in self.char.possessions if isinstance(p, assets.BlessingOrCurse))
    self.assertFalse(blessing.tokens["must_roll"])
    self.doBlessingTest(1)

    with mock_randint(return_value=1):
      # Advance past Upkeep, and roll a 1 if we roll (which we shouldn't)
      self.advance_turn(1, "encounter")
      self.assertTrue(blessing.tokens["must_roll"])
    self.doBlessingTest(1)

    with mock_randint(side_effect=[6, 1]):
      # Dummy now has both a FakeSpecial from the CurseBlessTest parent and a blessing,
      # Keep the FakeSpecial, lose the Blessing
      self.advance_turn(2, "encounter")
      self.resolve_until_done()
    self.doBlessingTest(1)
    self.assertTrue(blessing.tokens["must_roll"])

    with mock_randint(side_effect=[1, 6]):
      self.advance_turn(3, "encounter")
      self.resolve_until_done()
    self.doBlessingTest(0)

  def testDoubleBlessed(self):
    self.state.event_stack.append(events.Bless(self.char))
    self.resolve_until_done()
    self.state.event_stack.append(events.AddToken(self.char.possessions[0], "must_roll"))
    self.resolve_until_done()

    bless = events.Bless(self.char)
    self.assertFalse(bless.is_resolved())
    self.state.event_stack.append(bless)
    self.resolve_until_done()

    self.assertTrue(bless.is_resolved())
    self.doBlessingTest(1)
    blessing = next(p for p in self.char.possessions if isinstance(p, assets.BlessingOrCurse))
    self.assertFalse(blessing.tokens["must_roll"])

    with mock_randint(return_value=1):
      self.advance_turn(1, "movement")

  def testCursedWhileBlessed(self):
    self.state.event_stack.append(events.Bless(self.char))
    self.resolve_until_done()

    curse = events.Curse(self.char)
    self.assertFalse(curse.is_resolved())

    self.state.event_stack.append(curse)
    self.resolve_until_done()

    self.assertTrue(curse.is_resolved())
    self.assertEqual(self.char.bless_curse, 0)
    self.assertListEqual(self.char.possessions, [self.dummy_possession])


class BankLoanTest(EventTest):
  def testBasicLoanFlow(self):
    self.advance_turn(0, "encounter")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)
    self.state.event_stack.append(events.TakeBankLoan(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 10)
    with mock_randint(1) as roll:
      self.advance_turn(1, "upkeep")
      choice = self.resolve_to_choice(events.SliderInput)
      choice.resolve(self.state, "done", "done")
      payoff = self.resolve_to_usable(0, "Bank Loan0")
      self.state.done_using[0] = True
      self.resolve_until_done()
      self.assertEqual(roll.call_count, 0)  # Don't roll on your first turn

    with mock_randint(4) as roll:
      self.advance_turn(2, "upkeep")
      choice = self.resolve_to_choice(events.SliderInput)
      choice.resolve(self.state, "done", "done")
      payoff = self.resolve_to_usable(0, "Bank Loan0")
      self.state.done_using[0] = True
      self.resolve_until_done()
      self.assertEqual(roll.call_count, 1)

    with mock_randint(1) as roll:
      self.advance_turn(3, "upkeep")
      interest = self.resolve_to_choice(events.SpendChoice)
      self.spend("dollars", 1, interest)
      interest.resolve(self.state, "Yes")
      choice = self.resolve_to_choice(events.SliderInput)
      choice.resolve(self.state, "done", "done")
      payoff = self.resolve_to_usable(0, "Bank Loan0")
      # Probably shouldn't be usable if you're too poor
      self.state.done_using[0] = True
      self.resolve_until_done()
      self.assertEqual(roll.call_count, 1)

    self.char.dollars = 10

    with mock_randint(5) as roll:
      self.advance_turn(4, "upkeep")
      choice = self.resolve_to_choice(events.SliderInput)
      choice.resolve(self.state, "done", "done")
      payoff = self.resolve_to_usable(0, "Bank Loan0")
      self.state.event_stack.append(payoff)
      payoff_choice = self.resolve_to_choice(events.SpendChoice)
      self.spend("dollars", 10, payoff_choice)
      payoff_choice.resolve(self.state, "Yes")
      self.resolve_until_done()
      self.assertEqual(roll.call_count, 1)
    self.assertEqual(self.char.dollars, 0)
    self.assertNotIn("Bank Loan", [p.name for p in self.char.possessions])
    self.assertFalse(self.char.possessions)

  def defaultSequence(self) -> events.ItemLossChoice:
    self.advance_turn(0, "encounter")
    self.resolve_until_done()
    self.state.event_stack.append(events.TakeBankLoan(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 10)
    self.char.dollars = 0
    with mock_randint(3) as roll:
      self.advance_turn(1, "upkeep")
      choice = self.resolve_to_choice(events.SliderInput)
      choice.resolve(self.state, "done", "done")
      self.resolve_to_usable(0, "Bank Loan0")
      self.state.done_using[0] = True
      self.resolve_until_done()
      self.advance_turn(2, "upkeep")
      interest = self.resolve_to_choice(events.SpendChoice)
      interest.resolve(self.state, "No")
      self.assertEqual(roll.call_count, 1)
      return self.resolve_to_choice(events.ItemLossChoice)

  def testDefault(self):
    self.char.possessions = [items.Whiskey(0), items.Wither(0), items.MagicPowder(0)]
    loss_choice = self.defaultSequence()
    loss_choice.resolve(self.state, "Whiskey0")
    loss_choice.resolve(self.state, "Wither0")
    with self.assertRaises(eldritch.eldritch.InvalidMove):
      loss_choice.resolve(self.state, "done")
    loss_choice.resolve(self.state, "Magic Powder0")
    loss_choice.resolve(self.state, "done")
    self.resolve_to_choice(events.SliderInput)
    self.assertListEqual([p.name for p in self.char.possessions], ["Bad Credit"])

  def testDefaultWithDerringer(self):
    self.char.possessions = [items.Derringer18(0), items.Wither(0), items.MagicPowder(0)]
    loss_choice = self.defaultSequence()
    loss_choice.resolve(self.state, "Wither0")
    loss_choice.resolve(self.state, "Magic Powder0")
    loss_choice.resolve(self.state, "done")
    self.resolve_to_choice(events.SliderInput)
    self.assertListEqual([p.name for p in self.char.possessions], [".18 Derringer", "Bad Credit"])


class RetainerTest(EventTest):
  def testBasicRetainerFlow(self):
    self.advance_turn(0, "encounter")
    self.resolve_until_done()
    self.state.event_stack.append(events.DrawSpecific(self.char, "specials", "Retainer"))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

    with mock_randint(2) as roll:
      self.advance_turn(1, "upkeep")
      sliders = self.resolve_to_choice(events.SliderInput)
      sliders.resolve(self.state, "done", "done")
      self.resolve_until_done()
      self.assertEqual(self.char.dollars, 2)
      self.assertEqual(roll.call_count, 0)

    with mock_randint(2) as roll:
      self.advance_turn(2, "upkeep")
      sliders = self.resolve_to_choice(events.SliderInput)
      sliders.resolve(self.state, "done", "done")
      self.resolve_until_done()
      self.assertEqual(self.char.dollars, 4)
      self.assertEqual(roll.call_count, 1)

    with mock_randint(1) as roll:
      self.advance_turn(3, "upkeep")
      sliders = self.resolve_to_choice(events.SliderInput)
      sliders.resolve(self.state, "done", "done")
      self.resolve_until_done()
      self.assertEqual(self.char.dollars, 6)
      self.assertEqual(roll.call_count, 1)
      self.assertNotIn("Retainer", [p.name for p in self.char.possessions])
