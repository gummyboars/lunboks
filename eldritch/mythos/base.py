import operator

from eldritch import events
from eldritch import gates
from eldritch.monsters import core as monsters
from eldritch.monsters.base import Cultist
from eldritch import places
from eldritch import values
from eldritch import items
from eldritch.mythos.core import (
  Headline,
  Environment,
  Rumor,
  CityBonus,
  GainPrevention,
  ReturnMonstersHeadline,
  ReturnAndIncreaseHeadline,
  ReleaseMonstersHeadline,
  CloseLocationsHeadline,
  HealthWager,
)


class Mythos1(Headline):
  def __init__(self):
    super().__init__("Mythos1", "Woods", "Society", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    seq = super().create_event(state)
    for char in state.characters:
      if char.gone:
        continue
      check = events.Check(char, "luck", -1)
      bless = events.Bless(char)
      seq.events.append(events.PassFail(char, check, bless, events.Nothing()))
    return seq


class Mythos2(Environment):
  def __init__(self):
    super().__init__("Mythos2", "Isle", "Science", {"square", "diamond"}, {"circle"}, "urban")

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Monster) and thing.name == "Pinata" and attribute == "toughness":
      return 2
    return 0

  def get_interrupt(self, event, state):
    if len(state.event_stack) < 3:
      return None
    trophy = state.event_stack[-3]
    if not isinstance(trophy, events.TakeTrophy) or getattr(trophy.monster, "name", "") != "Pinata":
      return None
    if isinstance(event, events.DrawItems):
      return events.ChangeCount(event, "draw_count", 1)
    if isinstance(event, events.KeepDrawn):
      return events.ChangeCount(event, "keep_count", 1)
    return None


class Mythos3(GainPrevention):
  def __init__(self):
    super().__init__(
      "Mythos3", "Square", "Unnamable", {"square", "diamond"}, {"circle"}, "mystic", "stamina"
    )


class Mythos4(ReturnAndIncreaseHeadline):
  def __init__(self):
    super().__init__(
      "Mythos4",
      "Science",
      "WitchHouse",
      {"hex"},
      {"slash", "triangle", "star"},
      monster_names={"Furry Beast", "Dream Flier"},
    )


class Mythos5(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos5", "Square", "Unnamable", {"moon"}, {"plus"}, from_places={"Sky", "Outskirts"}
    )


class Mythos6(CityBonus):
  def __init__(self):
    super().__init__(
      "Mythos6",
      "Graveyard",
      "Isle",
      {"plus"},
      {"moon"},
      "weather",
      bonus_skill="sneak",
      penalty_skill="will",
    )

  def get_interrupt(self, event, state):
    if isinstance(event, events.MoveMonster) and event.monster.has_attribute("flying", state, None):
      return events.CancelEvent(event)
    return None


class Mythos7(Headline):
  def __init__(self):
    super().__init__("Mythos7", "Unnamable", "Woods", {"hex"}, {"slash", "triangle", "star"})
    self.active_until = None

  def create_event(self, state):
    seq = super().create_event(state)
    for char in state.characters:
      if char.arrested_until is not None:
        seq.events.append(events.ClearStatus(char, "arrested"))
    seq.events.append(
      events.AddGlobalEffect(self, source_deck="mythos", active_until=state.turn_number + 1)
    )
    return seq

  def get_interrupt(self, event, state):
    if isinstance(event, events.Arrested):
      return events.CancelEvent(event)
    return None

  def get_trigger(self, event, state):
    if (
      self.active_until is not None
      and state.turn_number >= self.active_until
      and isinstance(event, events.Mythos)
    ):
      return events.RemoveGlobalEffect(self, source_deck="mythos")
    return None


class Mythos8(Environment):
  def __init__(self):
    super().__init__(
      "Mythos8", "Square", "Unnamable", {"square", "diamond"}, {"circle"}, "mystic", "Rivertown"
    )

  def get_trigger(self, event, state):
    if isinstance(event, events.Movement) and event.character.place.name == self.activity_location:
      return HealthWager(
        self,
        event.character,
        "stamina",
        "Delve into mysteries with your life force?",
        events.Gain(event.character, {"clues": 3}),
      )
    return None

  def get_interrupt(self, event, state):
    if (
      isinstance(event, events.InsaneOrUnconscious)
      and len(state.event_stack) > 1
      and isinstance(state.event_stack[-2], events.GainOrLoss)
      and state.event_stack[-2].source == self
    ):
      return events.Devoured(event.character)
    return None


class Mythos9(CityBonus):
  def __init__(self):
    super().__init__(
      "Mythos9",
      "Cave",
      "Roadhouse",
      {"square", "diamond"},
      {"circle"},
      "mystic",
      bonus_skill="sneak",
      penalty_skill="luck",
    )

  def get_modifier(self, thing, attribute, state):
    if getattr(thing, "name", None) == "Haunter" and attribute == "combatdifficulty":
      return -3
    return super().get_modifier(thing, attribute, state)


class Mythos10(CloseLocationsHeadline):
  def __init__(self):
    super().__init__(
      "Mythos10",
      "Isle",
      "Science",
      {"hex"},
      {"slash", "triangle", "star"},
      ["Store", "Shop", "Shoppe"],
    )


class Mythos11(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos11",
      "Cave",
      "Roadhouse",
      {"hex"},
      {"slash", "triangle", "star"},
      from_places={"Southside", "House", "Church", "Society"},
    )


class Mythos12(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos12",
      "Square",
      "Unnamable",
      {"circle"},
      {"square", "diamond"},
      from_places={"University", "Library", "Administration", "Science"},
    )


class Mythos13(Rumor):
  def __init__(self):
    super().__init__("Mythos13", "Cave", {"slash", "triangle", "star"}, {"hex"}, "Rivertown")

  def should_fail(self, state):
    return state.terror >= 10

  def get_interrupt(self, event, state):
    if not self.failed and isinstance(event, events.EncounterPhase):
      return self.get_pass_interrupt(event, state)
    return None

  def get_pass_interrupt(self, event, state):
    if event.character.place != state.places["Rivertown"]:
      return None
    seq = events.Sequence(
      [events.EndRumor(self, failed=False)]
      + [events.Draw(char, "spells", 1) for char in state.characters if not char.gone]
    )
    return events.BinarySpend(
      event.character,
      "gates",
      2,
      "Spend 2 gate trophies to end the rumor?",
      "Yes",
      "No",
      seq,
      visual=self.name,
    )

  def get_trigger(self, event, state):
    if isinstance(event, events.IncreaseTerror) and self.should_fail(state):
      curses = [events.Curse(char) for char in state.characters if not char.gone]
      return events.Sequence(curses + [events.EndRumor(self, failed=True)])
    return super().get_trigger(event, state)

  def progress_event(self, state):
    first_player = state.characters[state.first_player]
    dice1 = events.DiceRoll(first_player, 1, name=self.name, bad=[1, 2])
    prog1 = events.IncreaseTerror()
    cond1 = events.Conditional(first_player, values.Die(dice1), "", {0: prog1, 3: events.Nothing()})
    return events.Sequence([dice1, cond1])

  def get_progress(self, state):
    return state.terror

  def max_progress(self, state):
    return 10


class Mythos14(Environment):
  def __init__(self):
    super().__init__(
      "Mythos14", "Unnamable", "Woods", {"square", "diamond"}, {"circle"}, "urban", "Northside"
    )

  def get_trigger(self, event, state):
    if isinstance(event, events.Movement) and event.character.place.name == "Northside":
      clues = events.Gain(event.character, {"clues": 1})
      check = events.Check(event.character, "will", -1)
      loss = events.Loss(event.character, {"sanity": 1})
      return events.Sequence(
        [clues, events.PassFail(event.character, check, events.Nothing(), loss)], event.character
      )
    return None


class Mythos15(Environment):
  def __init__(self):
    super().__init__("Mythos15", "Isle", "Science", {"plus"}, {"moon"}, "urban")

  def get_trigger(self, event, state):
    if isinstance(event, events.Movement) and isinstance(event.character.place, places.Street):
      is_deputy = values.ItemNameCount(event.character, "Deputy")
      check = events.Check(event.character, "will", 0, name=self.name)
      arrested = events.Arrested(event.character)
      make_check = events.PassFail(event.character, check, events.Nothing(), arrested)
      return events.PassFail(event.character, is_deputy, events.Nothing(), make_check)
    return None


class Mythos16(Environment):
  def __init__(self):
    super().__init__(
      "Mythos16",
      "WitchHouse",
      "Cave",
      {"square", "diamond"},
      {"circle"},
      "urban",
      activity_location="Uptown",
    )

  def get_trigger(self, event, state):
    if not isinstance(event, events.Movement):
      return None
    if event.character.place.name != self.activity_location:
      return None
    return events.BinaryChoice(
      event.character,
      "Shop at estate sale?",
      "Yes",
      "No",
      events.Purchase(event.character, "unique", draw_count=2, keep_count=2),
      events.Nothing(),
      visual=self.name,
    )


class Mythos17(Environment):
  def __init__(self):
    super().__init__(
      "Mythos17", "WitchHouse", "Cave", {"plus"}, {"moon"}, "urban", activity_location="University"
    )

  def get_trigger(self, event, state):
    if not isinstance(event, events.Movement):
      return None
    if event.character.place.name != self.activity_location:
      return None
    check = events.Check(event.character, "lore", -1, name=self.name)
    gain = events.Gain(event.character, {"clues": 1})
    return events.PassFail(event.character, check, gain, events.Nothing())


class Mythos18(GainPrevention):
  def __init__(self):
    super().__init__("Mythos18", "Square", "Unnamable", {"plus"}, {"moon"}, "mystic", "sanity")


class Mythos19(CloseLocationsHeadline):
  def __init__(self):
    super().__init__(
      "Mythos19", "WitchHouse", "Cave", {"moon"}, {"plus"}, ["Merchant"], evict=False
    )


class Mythos20(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__("Mythos20", "Cave", "Roadhouse", {"moon"}, {"plus"}, from_places=["streets"])


class Mythos21(Headline):
  def __init__(self):
    super().__init__("Mythos21", "Graveyard", "Isle", {"moon"}, {"plus"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.IncreaseTerror())
    return seq


class Mythos22(ReturnAndIncreaseHeadline):
  def __init__(self):
    super().__init__(
      "Mythos22", "Square", "Unnamable", {"hex"}, {"slash", "triangle", "star"}, ["Tentacle Tree"]
    )


class Mythos23(ReleaseMonstersHeadline):
  def __init__(self):
    super().__init__("Mythos23", "Unnamable", "Woods", {"moon"}, {"plus"}, to_places="Merchant")


class Mythos24(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos24",
      "WitchHouse",
      "Cave",
      {"circle"},
      {"square", "diamond"},
      from_places=["Easttown", "Roadhouse", "Diner", "Police"],
    )


class Mythos25(CityBonus):
  def __init__(self):
    super().__init__(
      "Mythos25",
      "Woods",
      "Square",
      {"square", "diamond"},
      {"circle"},
      "weather",
      bonus_skill="lore",
      penalty_skill="fight",
    )

  def get_modifier(self, thing, attribute, state):
    # FAQ p10: If the phrase ___ is not within the text of the effect, then it affects investigators
    # in the Other Worlds
    if getattr(thing, "name", None) == "Flame Matrix" and attribute == "toughness":
      return 1
    return super().get_modifier(thing, attribute, state)


class Mythos26(Environment):
  def __init__(self):
    super().__init__("Mythos26", "Woods", "Society", {"square", "diamond"}, {"circle"}, "urban")

  def get_interrupt(self, event, state):
    if isinstance(event, events.IncreaseTerror):
      return events.CancelEvent(event)
    return None


class Mythos27(Rumor):
  def __init__(self):
    super().__init__("Mythos27", "Isle", {"slash", "triangle", "star"}, {"hex"}, "Easttown")
    self.progress = 6
    self._max_progress = 10

  def get_interrupt(self, event, state):
    if not isinstance(event, events.EncounterPhase):
      return None
    if event.character.place != state.places["Easttown"]:
      return None
    spend = values.RangeSpendPrerequisite("clues", 1, self.progress)
    choice = events.SpendChoice(
      event.character,
      "Spend clues to slow down or stop the rumor?",
      ["Spend", "Don't"],
      spends=[spend, None],
      visual=self.name,
    )
    spend_count = values.SpendCount(choice, "clues")
    neg_amount = values.Calculation(spend_count, None, operator.neg)
    cond = events.Conditional(
      event.character,
      spend_count,
      "",
      {0: events.Nothing(), 1: events.ProgressRumor(self, neg_amount)},
    )
    return events.Sequence([choice, cond])

  def progress_event(self, state):
    first_player = state.characters[state.first_player]
    dice = events.DiceRoll(first_player, 2, name=self.name, bad=[1, 2])
    bad_count = values.BadDice(dice)
    prog = events.ProgressRumor(self, amount=bad_count)
    cond = events.Conditional(first_player, bad_count, "", {0: events.Nothing(), 1: prog})
    return events.Sequence([dice, cond])

  def get_trigger(self, event, state):
    if isinstance(event, events.ProgressRumor) and event.rumor == self and self.should_fail(state):
      return events.Sequence([events.EndRumor(self, failed=True), events.RemoveAllSeals()])
    if isinstance(event, events.ProgressRumor) and event.rumor == self and self.progress <= 0:
      draws = [events.Draw(char, "unique", 1) for char in state.characters if not char.gone]
      return events.Sequence([events.EndRumor(self, failed=False)] + draws)
    return super().get_trigger(event, state)


class Mythos28(Headline):
  def __init__(self):
    super().__init__("Mythos28", "Graveyard", "Isle", {"hex"}, {"slash", "triangle", "star"})

  def create_event(self, state):
    first_player = state.characters[state.first_player]
    seq = super().create_event(state)
    if not first_player.gone:
      check = events.Check(first_player, "luck", -1)
      pass_fail = events.PassFail(first_player, check, events.Nothing(), events.Curse(first_player))
      seq.events.append(pass_fail)
    return seq


class Mythos29(Environment):
  def __init__(self):
    super().__init__("Mythos29", "Society", "Lodge", {"plus"}, {"moon"}, "weather")

  def get_override(self, thing, attribute):
    if isinstance(thing, monsters.Monster) and attribute == "fast":
      return False
    return None

  def get_interrupt(self, event, state):
    if isinstance(event, events.CityMovement):
      return events.ChangeMovementPoints(event.character, -1)
    return None


class Mythos30(ReleaseMonstersHeadline):
  def __init__(self):
    super().__init__("Mythos30", "Society", "Lodge", {"moon"}, {"plus"}, "University")


class Mythos31(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos31",
      "Woods",
      "Square",
      {"slash", "triangle", "star"},
      {"hex"},
      from_places=["locations"],
    )


class Mythos32(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos32",
      "Isle",
      "Science",
      {"circle"},
      {"square", "diamond"},
      from_places=["FrenchHill", "WitchHouse", "Lodge"],
    )


class Mythos33(ReleaseMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos33", "Cave", "Roadhouse", {"circle"}, {"square", "diamond"}, "FrenchHill"
    )


class Mythos34(Headline):
  def __init__(self):
    super().__init__("Mythos34", "Unnamable", "Woods", {"slash", "triangle", "star"}, {"hex"})

  def create_event(self, state):
    seq = super().create_event(state)
    for char in state.characters:
      if getattr(char.place, "name", None) == "Lost":
        place_choice = events.PlaceChoice(char, "Choose a place to return to")
        move = events.ForceMovement(char, place_choice)
        seq.events.extend([place_choice, move])
    return seq


class Mythos35(Headline):
  def __init__(self):
    super().__init__("Mythos35", "Roadhouse", "Square", {"moon"}, {"plus"})

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.RespawnTrophies("Elder Thing", "Docks"))
    return seq


class Mythos36(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos36",
      "Square",
      "Unnamable",
      {"circle"},
      {"square", "diamond"},
      from_places=["Merchant", "Unnamable", "Docks", "Isle"],
    )


class Mythos37(ReleaseMonstersHeadline):
  def __init__(self):
    super().__init__("Mythos37", "Isle", "Science", {"moon"}, {"plus"}, "Downtown")


class Mythos38(Environment):
  def __init__(self):
    super().__init__(
      "Mythos38", "WitchHouse", "Cave", {"slash", "triangle", "star"}, {"hex"}, "mystic"
    )

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, gates.Gate) and attribute == "seal_clues":
      return -2
    return 0


class Mythos39(Environment):
  def __init__(self):
    super().__init__("Mythos39", "Unnamable", "Woods", {"plus"}, {"moon"}, "mystic")

  def get_override(self, thing, attribute):
    if attribute == "can_seal":
      return False
    return None


class Mythos40(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos40",
      "Woods",
      "Society",
      {"circle"},
      {"square", "diamond"},
      from_places=["Uptown", "Hospital", "Shoppe", "Woods"],
    )


class Mythos41(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos41",
      "Lodge",
      "Graveyard",
      {"circle"},
      {"square", "diamond"},
      from_places=["Northside", "Shop", "Newspaper", "Train"],
    )


class Mythos42(Environment):
  def __init__(self):
    super().__init__(
      "Mythos42", "WitchHouse", "Cave", {"square", "diamond"}, {"circle"}, env_type="mystic"
    )

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, items.Spell) and attribute == "sanity_cost":
      return -float("inf")
    return 0


class Mythos43(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos43",
      "WitchHouse",
      "Cave",
      {"circle"},
      {"square", "diamond"},
      from_places=["Rivertown", "Graveyard", "Cave", "Store"],
    )


class Mythos44(CityBonus):
  def __init__(self):
    super().__init__(
      "Mythos44",
      "Roadhouse",
      "Square",
      {"plus"},
      {"moon"},
      env_type="weather",
      bonus_skill="sneak",
      penalty_skill="speed",
    )

  def create_event(self, state):
    seq = super().create_event(state)
    seq.events.append(events.ReturnToCup(names=["Flame Matrix"]))
    return seq

  def get_interrupt(self, event, state):
    if isinstance(event, events.CityMovement):
      return events.ChangeMovementPoints(event.character, -1)
    return None

  def get_override(self, thing, attribute):
    # Should we be able to face these as monsters in other worlds?
    if (
      isinstance(thing, monsters.Monster)
      and thing.name == "Flame Matrix"
      and attribute == "can_draw_to_board"
    ):
      return False
    return None


class Mythos45(Environment):
  def __init__(self):
    super().__init__(
      "Mythos45", "Woods", "Society", {"slash", "triangle", "star"}, {"hex"}, "mystic"
    )

  def get_modifier(self, thing, attribute, state):
    if isinstance(thing, monsters.Monster):
      if thing.name in ("Maniac", "Octopoid") and attribute == "toughness":
        return 1
    if isinstance(thing, gates.Gate) and thing.name == "Sunken City" and attribute == "difficulty":
      return 1
    return 0


class Mythos46(ReleaseMonstersHeadline):
  def __init__(self):
    super().__init__("Mythos46", "Woods", "Society", {"moon"}, {"plus"}, "Easttown")


class Mythos47(ReleaseMonstersHeadline):
  def __init__(self):
    super().__init__("Mythos47", "Graveyard", "Isle", {"circle"}, {"square", "diamond"}, "Uptown")


class Mythos48(ReturnAndIncreaseHeadline):
  def __init__(self):
    super().__init__(
      "Mythos48",
      "Isle",
      "Science",
      {"hex"},
      {"slash", "triangle", "star"},
      monster_names={"Dimensional Shambler", "Hound"},
    )


class Mythos49(CloseLocationsHeadline):
  def __init__(self):
    super().__init__(
      "Mythos49",
      "Woods",
      "Society",
      {"hex"},
      {"slash", "triangle", "star"},
      ["Administration", "Library", "Science"],
    )


class Mythos50(ReleaseMonstersHeadline):
  def __init__(self):
    super().__init__("Mythos50", "Woods", "Society", {"circle"}, {"square", "diamond"}, "Southside")


class Mythos51(Environment):
  def __init__(self):
    super().__init__(
      "Mythos51", "Graveyard", "Isle", {"square", "diamond"}, {"circle"}, env_type="mystic"
    )

  def get_override(self, thing, attribute):
    if isinstance(thing, items.Spell) and attribute == "can_use":
      return False
    return None


class Mythos52(CityBonus):
  def __init__(self):
    super().__init__(
      "Mythos52",
      "Cave",
      "Roadhouse",
      {"plus"},
      {"moon"},
      env_type="weather",
      bonus_skill="will",
      penalty_skill="sneak",
    )

  def create_event(self, state) -> events.Sequence:
    seq = super().create_event(state)
    seq.events.append(events.ReturnToCup(names=["Haunter"]))
    return seq

  def get_override(self, thing, attribute):
    if (
      isinstance(thing, monsters.Monster)
      and thing.name == "Haunter"
      and attribute == "can_draw_to_board"
    ):
      return False
    return None


class Mythos53(ReturnAndIncreaseHeadline):
  def __init__(self):
    super().__init__(
      "Mythos53",
      "Square",
      "Unnamable",
      {"hex"},
      {"slash", "triangle", "star"},
      monster_names={"Land Squid", "Giant Worm"},
    )


class Mythos54(Headline):
  def __init__(self):
    super().__init__("Mythos54", "Square", "Unnamable", {"slash", "triangle", "star"}, {"hex"})

  def create_event(self, state):
    seq = super().create_event(state)
    evts = seq.events
    for char in state.characters:
      if isinstance(char.place, places.OtherWorld):
        evts.append(events.Return(char, char.place.info.name, get_lost=False, none_choice="Cancel"))
    return seq


class Mythos55(Environment):
  def __init__(self):
    super().__init__("Mythos55", "Isle", "Science", {"plus"}, {"moon"}, "mystic")

  def get_modifier(self, thing, attribute, state):
    if (
      isinstance(thing, monsters.Monster)
      and thing.has_attribute("undead", state, None)
      and attribute == "toughness"
    ):
      # TODO: Check interaction with Red Sign
      return 1
    return 0


class Mythos56(ReleaseMonstersHeadline):
  def __init__(self):
    super().__init__("Mythos56", "WitchHouse", "Cave", {"moon"}, {"plus"}, "Northside")


class Mythos57(CloseLocationsHeadline):
  def __init__(self):
    super().__init__(
      "Mythos57", "WitchHouse", "Cave", {"hex"}, {"slash", "triangle", "star"}, ["Roadhouse"]
    )

  def create_event(self, state) -> events.Sequence:
    seq = super().create_event(state)
    for char in state.characters:
      whiskies = [pos for pos in char.possessions if pos.name == "Whiskey"]
      if not (whiskies and isinstance(char.place, places.CityPlace)):
        continue
      check = events.Check(char, "sneak", -1)
      pass_fail = events.PassFail(
        char,
        check,
        events.Nothing(),
        events.Sequence([events.Arrested(char), events.DiscardSpecific(char, whiskies)], char),
      )
      seq.events.append(pass_fail)
    return seq


class Mythos58(Environment):
  def __init__(self):
    super().__init__(
      "Mythos58",
      "WitchHouse",
      "Cave",
      {"plus"},
      {"moon"},
      activity_location="FrenchHill",
      env_type="mystic",
    )

  def get_trigger(self, event, state):
    if isinstance(event, events.Movement) and event.character.place.name == self.activity_location:
      gain = [events.Gain(event.character, {"clues": 1}), events.Draw(event.character, "spells", 1)]
      prompt = "Deal with the Man in Black?"
      return HealthWager(
        self, event.character, "sanity", prompt, events.Sequence(gain, event.character)
      )
    return None

  def get_interrupt(self, event, state):
    if (
      isinstance(event, events.InsaneOrUnconscious)
      and len(state.event_stack) > 1
      and isinstance(state.event_stack[-2], events.GainOrLoss)
      and state.event_stack[-2].source == self
    ):
      return events.Devoured(event.character)
    return None


class Mythos59(Rumor):
  def __init__(self):
    super().__init__("Mythos59", "Graveyard", {"slash", "triangle", "star"}, {"hex"}, "FrenchHill")
    self._max_progress = 5

  def get_modifier(self, thing, attribute, state):
    if self.failed:
      return 0
    if not isinstance(thing, monsters.Monster):
      return 0
    if isinstance(thing, Cultist) or thing.name in ["High Priest", "Warlock", "Witch"]:
      return {"toughness": 2}.get(attribute, 0)
    return 0

  def get_interrupt(self, event, state):
    if self.failed and isinstance(event, events.Mythos):
      return self.get_failure_interrupt(event, state)
    if not self.failed and isinstance(event, events.EncounterPhase):
      return self.get_pass_interrupt(event, state)
    return None

  def get_failure_interrupt(self, event, state):  # pylint: disable=unused-argument
    draw = events.DrawMythosCard(state.characters[state.first_player])
    return events.Sequence([draw, events.OpenGate(draw)])

  def get_pass_interrupt(self, event, state):
    if event.character.place != state.places["FrenchHill"]:
      return None
    num_spells = 3 if len(state.characters) <= 4 else 4
    prompt = "Choose spells to discard"
    discard_choice = events.ItemCountChoice(
      event.character, prompt, num_spells, decks={"spells"}, select_type="x", visual=self.name
    )
    success = [
      discard_choice,
      events.DiscardSpecific(event.character, discard_choice),
      events.EndRumor(self, failed=False),
    ]
    success.extend([events.Gain(char, {"clues": 2}) for char in state.characters if not char.gone])
    prereq = values.ItemDeckPrerequisite(event.character, "spells", num_spells, "at least")
    return events.BinaryChoice(
      event.character,
      f"Discard {num_spells} spells to end the rumor?",
      "Yes",
      "No",
      events.Sequence(success),
      events.Nothing(),
      prereq,
      visual=self.name,
    )

  def get_trigger(self, event, state):
    if isinstance(event, events.ProgressRumor) and event.rumor == self and self.should_fail(state):
      return events.EndRumor(self, failed=True, add_global=True)
    return super().get_trigger(event, state)


class Mythos60(Environment):
  def __init__(self):
    super().__init__("Mythos60", "Woods", "Society", {"plus"}, {"moon"}, "urban")

  def get_modifier(self, thing, attribute, state):
    if attribute != "toughness":
      return 0
    if isinstance(thing, Cultist) or getattr(thing, "name", None) == "Giant Insect":
      return 1
    return 0


class Mythos62(Rumor):
  def __init__(self):
    super().__init__("Mythos62", "Square", {"slash", "triangle", "star"}, {"hex"}, "Southside")

  def progress_event(self, state):
    fail = [events.EndRumor(self, failed=True)]
    prompt = "Lower your max sanity or stamina?"
    for char in state.characters:
      if char.gone:
        continue
      sanity = events.DrawSpecific(char, "specials", "Sanity Decrease")
      stamina = events.DrawSpecific(char, "specials", "Stamina Decrease")
      fail.append(
        events.BinaryChoice(char, prompt, "Sanity", "Stamina", sanity, stamina, visual=self.name)
      )
    results = {0: events.Sequence(fail), 1: events.AllyToBox()}
    return events.Conditional(None, values.Calculation(state, "allies", len), None, results)

  def get_interrupt(self, event, state):
    if isinstance(event, events.EncounterPhase) and event.character.place.name == "Southside":
      success = [events.EndRumor(self, failed=False)]
      success += [events.Gain(char, {"dollars": 5}) for char in state.characters if not char.gone]
      prompt = "Spend 5 clue tokens to end the rumor?"
      return events.BinarySpend(
        event.character, "clues", 5, prompt, "Yes", "No", events.Sequence(success), visual=self.name
      )
    return super().get_interrupt(event, state)

  def get_progress(self, state):
    return 11 - len(state.allies)

  def max_progress(self, state):  # pylint: disable=unused-argument
    return 11


class Mythos63(Rumor):
  def __init__(self):
    super().__init__("Mythos63", "Science", {"slash", "triangle", "star"}, {"hex"}, "Downtown")

  def progress_event(self, state):
    first_player = state.characters[state.first_player]
    dice = events.DiceRoll(first_player, 1, name=self.name, bad=[1, 2])
    prog = events.AddDoom()
    cond = events.Conditional(first_player, values.Die(dice), "", {0: prog, 3: events.Nothing()})
    return events.Sequence([dice, cond])

  def get_interrupt(self, event, state):
    downtown = state.places["Downtown"]
    if not isinstance(event, events.EncounterPhase) or event.character.place != downtown:
      return super().get_interrupt(event, state)

    prompt = "Choose ally to discard"
    discard_choice = events.ItemCountChoice(
      event.character, prompt, 1, decks={"allies"}, select_type="x", visual=self.name
    )
    success = [
      discard_choice,
      events.DiscardSpecific(event.character, discard_choice),
      events.EndRumor(self, failed=False),
    ]
    success.extend(
      [events.Draw(char, "common", 2, keep_count=2) for char in state.characters if not char.gone]
    )
    prereq = values.ItemDeckPrerequisite(event.character, "allies", 1, "at least")
    return events.BinaryChoice(
      event.character,
      "Discard an ally to end the rumor?",
      "Yes",
      "No",
      events.Sequence(success),
      events.Nothing(),
      prereq,
      visual=self.name,
    )

  def get_progress(self, state):
    return state.ancient_one.doom

  def max_progress(self, state):
    return state.ancient_one.max_doom


class Mythos64(Environment):
  def __init__(self):
    super().__init__("Mythos64", "Lodge", "Graveyard", {"square", "diamond"}, {"circle"}, "mystic")

  def get_modifier(self, thing, attribute, state):
    if (
      isinstance(thing, monsters.Monster)
      and thing.name in ("Ghoul", "Formless Spawn", "Giant Amoeba", "Subterranean Flier")
      and attribute == "toughness"
    ):
      return 1
    return 0


class Mythos65(Rumor):
  def __init__(self):
    super().__init__("Mythos65", "Isle", {"slash", "triangle", "star"}, {"hex"}, "University")

  def progress_event(self, state):
    draw = events.DrawMonstersFromCup(1, to_board=False)
    return events.Sequence([draw, events.PlaceMonstersOnRumor(draw, self)])

  def get_interrupt(self, event, state):
    university = state.places["University"]
    if not isinstance(event, events.EncounterPhase) or event.character.place != university:
      return super().get_interrupt(event, state)
    monsters_on_rumor = [m for m in state.monsters if m.place == self]
    return events.EvadeOrFightAll(event.character, monsters_on_rumor, auto_evade=True)

  def get_trigger(self, event, state):
    if isinstance(event, events.StartRumor) and event.rumor == self:
      draw = events.DrawMonstersFromCup(5, to_board=False)
      return events.Sequence([draw, events.PlaceMonstersOnRumor(draw, self)])
    monsters_on_rumor = [m for m in state.monsters if m.place == self]
    if isinstance(event, events.EvadeOrCombat):
      if not monsters_on_rumor:
        success = [events.EndRumor(self, failed=False)]
        success += [events.Draw(char, "skills", 1) for char in state.characters if not char.gone]
        return events.Sequence(success)
    if isinstance(event, events.PlaceMonstersOnRumor) and len(monsters_on_rumor) >= 8:
      terror = events.IncreaseTerror(10 - state.terror)
      spawn = events.MonsterSpawnChoice([m.idx for m in monsters_on_rumor], None, ["University"])
      fail = events.EndRumor(self, failed=True)
      return events.Sequence([fail, terror, spawn])
    return super().get_trigger(event, state)

  def get_progress(self, state):
    return len([m for m in state.monsters if m.place == self])

  def max_progress(self, state):  # pylint: disable=unused-argument
    return 8


class Mythos66(ReleaseMonstersHeadline):
  def __init__(self):
    super().__init__("Mythos66", "Isle", "Science", {"moon"}, {"plus"}, "Rivertown")


class Mythos67(ReturnMonstersHeadline):
  def __init__(self):
    super().__init__(
      "Mythos67",
      "Unnamable",
      "Woods",
      {"circle"},
      {"square", "diamond"},
      from_places=["Downtown", "Bank", "Asylum", "Square"],
    )


def CreateMythos():
  return [
    Mythos1(),
    Mythos2(),
    Mythos3(),
    Mythos4(),
    Mythos5(),
    Mythos6(),
    Mythos7(),
    Mythos8(),
    Mythos9(),
    Mythos10(),
    Mythos11(),
    Mythos12(),
    Mythos13(),
    Mythos14(),
    Mythos15(),
    Mythos16(),
    Mythos17(),
    Mythos18(),
    Mythos19(),
    Mythos20(),
    Mythos21(),
    Mythos22(),
    Mythos23(),
    Mythos24(),
    Mythos25(),
    Mythos26(),
    Mythos27(),
    Mythos28(),
    Mythos29(),
    Mythos30(),
    Mythos31(),
    Mythos32(),
    Mythos33(),
    Mythos34(),
    Mythos35(),
    Mythos36(),
    Mythos37(),
    Mythos38(),
    Mythos39(),
    Mythos40(),
    Mythos41(),
    Mythos42(),
    Mythos43(),
    Mythos44(),
    Mythos45(),
    Mythos46(),
    Mythos47(),
    Mythos48(),
    Mythos49(),
    Mythos50(),
    Mythos51(),
    Mythos52(),
    Mythos53(),
    Mythos54(),
    Mythos55(),
    Mythos56(),
    Mythos57(),
    Mythos58(),
    Mythos59(),
    Mythos60(),
    Mythos62(),
    Mythos63(),
    Mythos64(),
    Mythos65(),
    Mythos66(),
    Mythos67(),
  ]
