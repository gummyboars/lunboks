from eldritch.test_events import EventTest
from eldritch import assets
from eldritch import events
from eldritch import gates
from eldritch import stories


class StoryTest(EventTest):
  def setUp(self):
    super().setUp()
    self.state.specials.extend(stories.CreateStories())
    self.state.allies.extend(assets.CreateAllies())


class NightmaresTest(StoryTest):
  def setUp(self):
    super().setUp()
    self.story = stories.PowerfulNightmares()
    self.char.possessions.append(self.story)

  def testDontPassStory(self):
    self.state.gates.appendleft(gates.Gate("Dummy", 0, 0, "star"))
    self.state.event_stack.append(events.TakeGateTrophy(self.char, "draw"))
    self.resolve_until_done()
    self.assertListEqual(self.char.possessions, [self.story])

  def testPassStory(self):
    dreamlands = next(gate for gate in self.state.gates if gate.name == "Dreamlands")
    self.state.gates.remove(dreamlands)
    self.state.gates.appendleft(dreamlands)
    self.state.event_stack.append(events.TakeGateTrophy(self.char, "draw"))
    self.resolve_until_done()
    self.assertListEqual([p.name for p in self.char.possessions], ["Sweet Dreams"])

  def testFailStory(self):
    for target_ally in ["Dog", "Arm Wrestler", "Old Professor"]:
      for ally in self.state.allies:
        if ally.name == target_ally:
          self.char.possessions.append(ally)
          self.state.allies.remove(ally)
          break

    self.assertListEqual(
        [p.name for p in self.char.possessions],
        ["Powerful Nightmares", "Dog", "Arm Wrestler", "Old Professor"])
    self.state.event_stack.append(events.AddDoom(count=5))
    self.resolve_until_done()
    self.assertListEqual([p.name for p in self.char.possessions], ["Dog", "Living Nightmare"])

    # Discarding allies should return them to the deck, right?
    self.assertIn("Old Professor", [ally.name for ally in self.state.allies])

    self.state.event_stack.append(events.DrawSpecific(self.char, "allies", "Police Inspector"))
    self.resolve_until_done()
    self.assertListEqual([p.name for p in self.char.possessions], ["Dog", "Living Nightmare"])

    self.state.event_stack.append(events.Draw(self.char, "allies", 1))
    self.resolve_until_done()
    self.assertListEqual([p.name for p in self.char.possessions], ["Dog", "Living Nightmare"])

  def testDontFail(self):
    for target_ally in ["Dog", "Arm Wrestler", "Old Professor"]:
      for ally in self.state.allies:
        if ally.name == target_ally:
          self.char.possessions.append(ally)
          self.state.allies.remove(ally)
          break

    self.assertListEqual(
        [p.name for p in self.char.possessions],
        ["Powerful Nightmares", "Dog", "Arm Wrestler", "Old Professor"])
    self.state.event_stack.append(events.AddDoom())
    self.resolve_until_done()
    self.assertListEqual(
        [p.name for p in self.char.possessions],
        ["Powerful Nightmares", "Dog", "Arm Wrestler", "Old Professor"])
    self.state.event_stack.append(events.AddDoom(count=3))
    self.resolve_until_done()
    self.assertListEqual(
        [p.name for p in self.char.possessions],
        ["Powerful Nightmares", "Dog", "Arm Wrestler", "Old Professor"])
