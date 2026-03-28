from unittest import mock

from eldritch.test_events import EventTest
from eldritch.abilities import barnville
from eldritch import events
from eldritch.encounters.location import base as encounters
from eldritch import items


class EntertainerTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.extend(
      [
        barnville.WitchBlood(),
        barnville.ThirdEye(),
        # Tank: So what do you need, besides a miracle?
        # Neo: Guns. Lots of guns.
        items.TommyGun(0),
        items.Revolver38(0),
        items.Wither(0),
        items.DreadCurse(0),
        items.BindMonster(0),
      ]
    )

  def testWitchBlood(self):
    pass

  def test2W1S(self):
    pass

  def test1W2S(self):
    pass

  def test2W2S(self):
    pass


class ExpeditionLeaderTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.append(barnville.Leadership())

  def testSanityOnly(self):
    pass

  def testStaminaOnly(self):
    pass

  def testBothOptions(self):
    pass


class PhychicTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.extend([barnville.Precognition()])

  def testNoCluesNoChoice(self):
    pass

  def testHasCluesChooseNo(self):
    pass

  def testHasCluesChooseYes(self):
    pass

  def testShop7(self):
    def testShop7(self):
      self.state.turn_phase = "encounter"
      self.char.place = self.state.places["Shop"]
      self.state.event_stack.append(encounters.Shop7(self.char))
      with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
        self.resolve_until_done()
      # Should not trigger the ability
      self.assertEqual(self.char.place.name, "Woods")
      # In theory, there would be a woods event, but I think the state isn't set up for it.
