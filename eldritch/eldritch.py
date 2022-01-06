import collections
import json
from random import SystemRandom

from eldritch import places
from eldritch import mythos
from eldritch import monsters
from eldritch import location_specials
from eldritch import items
from eldritch import gate_encounters
from eldritch import gates
from eldritch import events
from eldritch import encounters
from eldritch import characters
from eldritch import assets
from eldritch import abilities
from game import (  # pylint: disable=unused-import
    BaseGame, CustomEncoder, InvalidInput, UnknownMove, InvalidMove, InvalidPlayer, NotYourTurn,
    ValidatePlayer, TooManyPlayers,
)


random = SystemRandom()


class GameState:

  DEQUE_ATTRIBUTES = {"common", "unique", "spells", "skills", "allies", "gates"}
  HIDDEN_ATTRIBUTES = {
      "event_stack", "interrupt_stack", "trigger_stack", "usables", "mythos", "gate_cards"}
  CUSTOM_ATTRIBUTES = {"characters", "all_characters"}
  TURN_PHASES = ["upkeep", "movement", "encounter", "otherworld", "mythos"]
  TURN_TYPES = {
      "upkeep": events.Upkeep,
      "movement": events.Movement,
      "encounter": events.EncounterPhase,
      "otherworld": events.OtherWorldPhase,
      "mythos": events.Mythos,
  }

  def __init__(self):
    self.name = "game"
    self.places = {}
    self.characters = []
    self.all_characters = characters.CreateCharacters()
    self.pending_chars = []
    self.common = collections.deque()
    self.unique = collections.deque()
    self.spells = collections.deque()
    self.skills = collections.deque()
    self.allies = collections.deque()
    self.mythos = collections.deque()
    self.gates = collections.deque()
    self.gate_cards = collections.deque()
    self.monsters = []
    self.monster_cup = monsters.MonsterCup()
    self.game_stage = "setup"  # valid values are setup, slumber, awakened, victory, defeat
    # valid values are setup, upkeep, movement, encounter, otherworld, mythos, awakened
    self.turn_phase = "setup"
    self.event_stack = collections.deque()
    self.interrupt_stack = collections.deque()
    self.trigger_stack = collections.deque()
    self.usables = {}
    self.done_using = {}
    self.event_log = []
    self.turn_number = -1
    self.turn_idx = 0
    self.first_player = 0
    self.rumor = None
    self.environment = None
    self.ancient_one = None
    self.other_globals = []
    self.check_result = None
    self.dice_result = []
    self.test_mode = False

  def initialize_for_tests(self):
    self.places = places.CreatePlaces()
    other_worlds = places.CreateOtherWorlds()
    self.places.update(other_worlds)

    self.gates.extend(gates.CreateGates())
    self.monsters = [monsters.Cultist(), monsters.Maniac()]
    for monster in self.monsters:
      monster.place = self.monster_cup

    self.game_stage = "slumber"
    self.turn_idx = 0
    self.turn_number = 0
    self.turn_phase = "upkeep"
    self.test_mode = True

  def initialize(self):
    self.places = places.CreatePlaces()
    other_worlds = places.CreateOtherWorlds()
    self.places.update(other_worlds)
    specials = location_specials.CreateFixedEncounters()
    encounter_cards = encounters.CreateEncounterCards()
    self.gate_cards.extend(gate_encounters.CreateGateCards())
    for neighborhood_name, cards in encounter_cards.items():
      self.places[neighborhood_name].encounters.extend(cards)
    for location_name, fixed_encounters in specials.items():
      self.places[location_name].fixed_encounters.extend(fixed_encounters)

    gate_markers = gates.CreateGates()
    random.shuffle(gate_markers)
    self.gates.extend(gate_markers)

    self.monsters = monsters.CreateMonsters()
    for idx, monster in enumerate(self.monsters):
      monster.idx = idx
      monster.place = self.monster_cup

    self.common.extend(items.CreateCommon())
    self.unique.extend(items.CreateUnique())
    self.spells.extend(items.CreateSpells())
    self.skills.extend(abilities.CreateSkills())
    self.allies.extend(assets.CreateAllies())
    handles = [
        card.handle for card in self.common + self.unique + self.spells + self.skills + self.allies
    ]
    assert len(handles) == len(set(handles))

    self.mythos.extend(mythos.CreateMythos())

    # Shuffle the decks.
    for deck in assets.Card.DECKS | {"gate_cards", "mythos"}:
      random.shuffle(getattr(self, deck))
    # Place initial clues. TODO: some characters may change location stability.
    for place in self.places.values():
      if isinstance(place, places.Location) and place.unstable:
        place.clues += 1

  def give_fixed_possessions(self, char, possessions):
    assert not possessions.keys() - assets.Card.DECKS
    for deck, names in possessions.items():
      cards = getattr(self, deck)
      keep = []
      rest = []
      while cards and names:
        card = cards.popleft()
        if card.name in names:
          names.remove(card.name)
          keep.append(card)
        else:
          rest.append(card)
      assert not names, f"could not find {str(names)} for {char.name} in {deck}"
      char.possessions.extend(keep)
      cards.extend(rest)

  def give_random_possessions(self, char, possessions):
    assert not char.random_possessions().keys() - assets.Card.DECKS
    for deck, count in possessions.items():
      for _ in range(count):
        char.possessions.append(getattr(self, deck).popleft())

  def get_modifier(self, thing, attribute):
    modifier = 0
    for glob in self.globals():
      if not glob:
        continue
      modifier += glob.get_modifier(thing, attribute)
    return modifier

  def get_override(self, thing, attribute):
    override = None
    for glob in self.globals():
      if not glob:
        continue
      val = glob.get_override(thing, attribute)
      if val is None:
        continue
      if override is None:
        override = val
      override = override and val
    return override

  def globals(self):
    return [self.rumor, self.environment, self.ancient_one] + self.other_globals

  def monster_limit(self):
    # TODO: return infinity when the terror track reaches 10
    limit = len(self.characters) + 3
    return limit + self.get_modifier(self, "monster_limit")

  def outskirts_limit(self):
    limit = 8 - len(self.characters)
    return limit + self.get_modifier(self, "outskirts_limit")

  def game_status(self):
    return "eldritch game"  # TODO

  def json_repr(self):
    ignore_attributes = self.DEQUE_ATTRIBUTES | self.HIDDEN_ATTRIBUTES | self.CUSTOM_ATTRIBUTES
    output = {key: getattr(self, key) for key in self.__dict__.keys() - ignore_attributes}
    for attr in self.DEQUE_ATTRIBUTES:
      output[attr] = list(getattr(self, attr))

    output["characters"] = []
    for char in self.characters:
      output["characters"].append(char.get_json(self))

    output["all_characters"] = {}
    for name, char in self.all_characters.items():
      output["all_characters"][name] = char.get_json(self)
    return output

  def for_player(self, char_idx):
    output = self.json_repr()

    # We only return the counts of these items, not the actual items.
    output["monster_cup"] = len([mon for mon in self.monsters if mon.place == self.monster_cup])
    output["gates"] = len(self.gates)

    char = None
    if char_idx is not None and char_idx < len(self.characters):
      char = self.characters[char_idx]

    top_event = self.event_stack[-1] if self.event_stack else None

    roll_events = (events.Check, events.DiceRoll, events.AddExtraDie, events.RerollCheck)
    is_roll = isinstance(top_event, roll_events)
    if len(self.event_stack) > 1 and isinstance(self.event_stack[-2], events.Check):
      if isinstance(top_event, events.SpendMixin):
        is_roll = True
    if top_event and is_roll:
      roller = top_event
      bonus = 0
      for event in reversed(self.event_stack):
        if not isinstance(event, roll_events + (events.SpendMixin,)):
          break
        if isinstance(event, events.BonusDiceRoll):
          bonus += event.count
        if isinstance(event, events.Check):
          roller = event
          break
      assert isinstance(roller, (events.Check, events.DiceRoll))
      output["dice"] = roller.count + bonus if roller.count is not None else None
      output["roll"] = roller.roll
      output["roller"] = self.characters.index(roller.character)

    output["choice"] = None
    if top_event and isinstance(top_event, events.ChoiceEvent) and not top_event.is_done():
      if top_event.character == char:
        output["choice"] = {"prompt": top_event.prompt()}
        output["choice"]["annotations"] = top_event.annotations(self)
        output["choice"]["invalid_choices"] = getattr(top_event, "invalid_choices", [])
        if isinstance(top_event, events.SpendMixin):
          output["choice"]["spendable"] = list(top_event.spendable)
          output["choice"]["spent"] = top_event.spend_map
          output["choice"]["remaining_spend"] = top_event.remaining_spend

        if isinstance(top_event, events.CardChoice):
          output["choice"]["cards"] = top_event.choices
        elif isinstance(top_event, (events.MapChoice, events.CityMovement)):
          if top_event.choices is not None:
            extra_choices = [top_event.none_choice] if top_event.none_choice is not None else []
            output["choice"]["places"] = top_event.choices + extra_choices
        elif isinstance(top_event, events.MultipleChoice):
          output["choice"]["choices"] = top_event.choices
          output["choice"]["invalid_choices"] = getattr(top_event, "invalid_choices", [])
        elif isinstance(top_event, events.ItemChoice):
          output["choice"]["chosen"] = [item.handle for item in top_event.chosen]
          output["choice"]["items"] = True
        elif isinstance(top_event, events.MonsterSpawnChoice):
          output["choice"]["monsters"] = top_event.to_spawn
        else:
          raise RuntimeError(f"Unknown choice type {top_event.__class__.__name__}")

    if top_event and isinstance(top_event, events.SliderInput) and not top_event.is_done():
      if top_event.character == char:
        output["sliders"] = {"prompt": top_event.prompt()}
        # TODO: distinguish between pending/current sliders, pending/current focus.
        for name, value in top_event.pending.items():
          output["characters"][char_idx]["sliders"][name]["selection"] = value
    if self.usables.get(char_idx):
      output["usables"] = list(self.usables[char_idx].keys())
    else:
      output["usables"] = None
    return output

  @classmethod
  def parse_json(cls, json_str):
    pass  # TODO

  def handle(self, char_idx, data):
    if data.get("type") == "start":
      self.handle_start()
      return self.resolve_loop()

    if char_idx not in range(len(self.characters)):
      raise InvalidPlayer(f"no such player {char_idx}")
    if data.get("type") == "set_slider":
      self.handle_slider(char_idx, data.get("name"), data.get("value"))
    elif data.get("type") == "give":
      self.handle_give(char_idx, data.get("recipient"), data.get("handle"), data.get("amount"))
    elif data.get("type") == "check":  # TODO: remove
      self.handle_check(char_idx, data.get("check_type"), data.get("modifier"))
    elif data.get("type") == "monster":  # TODO: remove
      self.handle_spawn_monster(data.get("monster"), data.get("place"))
    elif data.get("type") == "gate":  # TODO: remove
      self.handle_spawn_gate(data.get("place"))
    elif data.get("type") == "clue":  # TODO: remove
      self.handle_spawn_clue(data.get("place"))
    elif data.get("type") == "choice":
      self.handle_choice(char_idx, data.get("choice"))
    elif data.get("type") == "spend":
      self.handle_spend(char_idx, data.get("spend_type"))
    elif data.get("type") == "unspend":
      self.handle_unspend(char_idx, data.get("spend_type"))
    elif data.get("type") == "roll":
      self.handle_roll(char_idx)
    elif data.get("type") == "use":
      self.handle_use(char_idx, data.get("handle"))
    elif data.get("type") == "done_using":
      self.handle_done_using(char_idx)
    else:
      raise UnknownMove(data.get("type"))

    return self.resolve_loop()  # Returns a generator object.

  def resolve_loop(self):
    # NOTE: we may produce one message that is identical to the previous state.
    yield None
    while self.event_stack:
      event = self.event_stack[-1]
      if self.start_event(event):
        yield None
      if self.interrupt_stack[-1]:
        self.event_stack.append(self.interrupt_stack[-1].pop())
        continue
      # If the event requires the character to make a choice, stop here.
      self.usables = self.get_usable_interrupts(event)
      # TODO: maybe we can have an Input class. Or a needs_input() method.
      if isinstance(event, events.ChoiceEvent) and not event.is_done():
        event.compute_choices(self)
        if not event.is_done():
          yield None
          return
      if not self.test_mode and isinstance(event, events.DiceRoll) and not event.is_done():
        yield None
        return
      if isinstance(event, events.SliderInput) and not event.is_done():
        yield None
        return
      if not all(self.done_using.get(char_idx) for char_idx in self.usables):
        yield None
        return
      if not event.is_done():
        event.resolve(self)
        self.validate_resolve(event)
      if not event.is_done():
        continue
      if self.finish_event(event):
        yield None
      if self.trigger_stack[-1]:
        self.event_stack.append(self.trigger_stack[-1].pop())
        continue
      self.usables = self.get_usable_triggers(event)
      if not all(self.done_using.get(char_idx) for char_idx in self.usables):
        yield None
        return
      self.pop_event(event)
      yield None
      if not self.event_stack and not self.test_mode:
        self.next_turn()

  def validate_resolve(self, event):
    if event.is_done():
      return
    if self.event_stack[-1] != event:
      return
    if isinstance(event, (events.ChoiceEvent, events.SliderInput)):
      return
    raise RuntimeError(
        f"Event {event} returned from resolve() without (a) becoming resolved or "
        "(b) becoming cancelled or (c) adding a new event to the stack"
    )

  def start_event(self, event):
    # TODO: what about multiple events added to the stack at the same time? disallow?
    if len(self.interrupt_stack) >= len(self.event_stack):
      return False
    if event.start_str():
      self.event_log.append("  " * len(self.interrupt_stack) + event.start_str())
    self.interrupt_stack.append(self.get_interrupts(event))
    self.trigger_stack.append(None)
    assert len(self.interrupt_stack) == len(self.event_stack)
    self.clear_usables()
    return True

  def finish_event(self, event):
    assert len(self.trigger_stack) == len(self.event_stack)
    if self.trigger_stack[-1] is None:
      self.trigger_stack[-1] = self.get_triggers(event)
      return True
    # TODO: we should append to the event log here, then override when we pop it?
    return False

  def pop_event(self, event):
    assert event == self.event_stack[-1]
    assert len(self.event_stack) == len(self.trigger_stack)
    assert len(self.event_stack) == len(self.interrupt_stack)
    self.event_stack.pop()
    self.trigger_stack.pop()
    self.interrupt_stack.pop()
    if event.is_resolved() and event.finish_str():
      self.event_log.append("  " * len(self.event_stack) + event.finish_str())
    self.clear_usables()

  def clear_usables(self):
    self.usables.clear()
    self.done_using.clear()

  # TODO: global interrupts/triggers from ancient one, environment, other mythos/encounter cards
  def get_interrupts(self, event):
    interrupts = []
    if isinstance(event, events.MoveOne):
      nearby_monsters = [mon for mon in self.monsters if mon.place == event.character.place]
      if nearby_monsters:
        interrupts.append(events.EvadeOrFightAll(event.character, nearby_monsters))
    interrupts.extend(sum([char.get_interrupts(event, self) for char in self.characters], []))
    global_interrupts = [glob.get_interrupt(event, self) for glob in self.globals() if glob]
    interrupts.extend([interrupt for interrupt in global_interrupts if interrupt])
    return interrupts

  def get_usable_interrupts(self, event):
    i = {idx: char.get_usable_interrupts(event, self) for idx, char in enumerate(self.characters)}
    # If the character is in another world with another character, let them trade before moving.
    if isinstance(event, events.ForceMovement) and self.turn_phase == "movement":
      if len([char for char in self.characters if char.place == event.character.place]) > 1:
        i[self.characters.index(event.character)]["trade"] = events.Nothing()
    return {char_idx: interrupts for char_idx, interrupts in i.items() if interrupts}

  def get_triggers(self, event):
    triggers = []
    # Insane/Unconscious after sanity/stamina loss.
    if isinstance(event, (events.GainOrLoss, events.SpendMixin, events.CastSpell)):
      skip = False
      if isinstance(event, events.SpendMixin) and len(self.event_stack) > 1:
        if isinstance(self.event_stack[-2], events.CastSpell):
          skip = True  # In case of a spell, delay insanity calculations until it's done being cast.
      if not skip:
        # TODO: both going to zero at the same time means you are devoured.
        if event.character.sanity <= 0:
          triggers.append(events.Insane(event.character))
        if event.character.stamina <= 0:
          triggers.append(events.Unconscious(event.character))
    # Must fight monsters when you end your movement.
    if isinstance(event, (events.CityMovement, events.Return)):
      # TODO: special handling for the turn that you return from another world
      nearby_monsters = [mon for mon in self.monsters if mon.place == event.character.place]
      if nearby_monsters:
        triggers.append(events.EvadeOrFightAll(event.character, nearby_monsters))
      if isinstance(event.character.place, places.Location) and event.character.place.clues:
        triggers.append(events.CollectClues(event.character, event.character.place.name))
    # Pulled through a gate if it opens on top of you.
    if isinstance(event, events.OpenGate) and event.opened:
      loc = self.places[event.location_name]
      chars = [char for char in self.characters if char.place == loc]
      if chars:
        triggers.append(events.PullThroughGate(chars, loc.gate.name))
    # Non-spell items deactivate at the end of a combat round.
    if isinstance(event, (events.CombatRound, events.InsaneOrUnconscious)):
      triggers.append(events.DeactivateItems(event.character))
    # Spells deactivate at the end of an entire combat.
    if isinstance(event, (events.Combat, events.InsaneOrUnconscious)):
      triggers.append(events.DeactivateSpells(event.character))
    triggers.extend(sum([char.get_triggers(event, self) for char in self.characters], []))
    global_triggers = [glob.get_trigger(event, self) for glob in self.globals() if glob]
    triggers.extend([trigger for trigger in global_triggers if trigger])
    return triggers

  def get_usable_triggers(self, event):
    trgs = {idx: char.get_usable_triggers(event, self) for idx, char in enumerate(self.characters)}
    # If the character moved from another world to another character, let them trade after moving.
    if isinstance(event, (events.ForceMovement, events.Return)) and self.turn_phase == "movement":
      if len([char for char in self.characters if char.place == event.character.place]) > 1:
        trgs[self.characters.index(event.character)]["trade"] = events.Nothing()
    return {char_idx: triggers for char_idx, triggers in trgs.items() if triggers}

  def handle_start(self):
    assert self.game_stage == "setup"
    assert len(self.pending_chars) > 0
    self.game_stage = "slumber"
    self.turn_idx = 0
    self.turn_number = -1
    self.turn_phase = "mythos"
    self.initialize()
    seq = self.add_pending_players()
    if seq.events:
      seq.events.append(events.Mythos(None))
      self.event_stack.append(seq)
    else:
      self.event_stack.append(events.Mythos(None))

  def handle_join(self, player_idx, old_name, char_name):
    if player_idx is not None:
      raise InvalidMove("You are already playing.")
    if char_name not in self.all_characters:
      raise InvalidMove(f"Unknown character {char_name}")
    if char_name in {char.name for char in self.characters} or char_name in self.pending_chars:
      raise InvalidMove("That character is already taken.")

    if self.game_stage not in ["setup", "slumber"]:
      raise InvalidMove("You cannot join the game right now.")
    if old_name == char_name:
      return
    if old_name is not None and old_name in self.pending_chars:
      self.pending_chars.remove(old_name)
    self.pending_chars.append(char_name)

  def handle_use(self, char_idx, handle):
    assert char_idx in self.usables
    assert handle in self.usables[char_idx]
    assert handle != "trade"  # "trade" is just a placeholder
    self.event_stack.append(self.usables[char_idx].pop(handle))

  def handle_done_using(self, char_idx):
    assert char_idx in self.usables
    self.done_using[char_idx] = True

  def handle_choice(self, char_idx, choice):
    assert self.event_stack
    event = self.event_stack[-1]
    assert isinstance(event, events.ChoiceEvent)
    assert event.character == self.characters[char_idx]
    event.resolve(self, choice)

  def handle_spend(self, char_idx, spend_type):
    assert self.event_stack
    event = self.event_stack[-1]
    assert isinstance(event, events.SpendMixin)
    assert event.character == self.characters[char_idx]
    event.spend(spend_type)

  def handle_unspend(self, char_idx, spend_type):
    assert self.event_stack
    event = self.event_stack[-1]
    assert isinstance(event, events.SpendMixin)
    assert event.character == self.characters[char_idx]
    event.unspend(spend_type)

  def handle_roll(self, char_idx):
    assert self.event_stack
    event = self.event_stack[-1]
    assert isinstance(event, events.DiceRoll)
    assert event.character == self.characters[char_idx]
    event.resolve(self)

  def handle_check(self, char_idx, check_type, modifier):
    if check_type is None:
      raise InvalidInput("no check type")
    if check_type not in assets.CHECK_TYPES:
      raise InvalidInput("unknown check type")
    try:
      modifier = int(modifier)
    except (ValueError, TypeError):
      raise InvalidInput("invalid difficulty")  # pylint: disable=raise-missing-from
    if self.event_stack:
      raise InvalidInput("there are events on the stack")
    self.event_stack.append(events.Check(self.characters[char_idx], check_type, modifier))

  def handle_spawn_monster(self, monster_name, place):
    assert place in self.places
    assert monster_name in monsters.MONSTERS
    for monster in self.monsters:
      if monster.name == monster_name and monster.place == self.monster_cup:
        monster.place = self.places[place]
        break
    else:
      raise InvalidMove("No monsters of that type left in the cup.")

  def handle_spawn_gate(self, place):
    assert place in self.places
    assert getattr(self.places[place], "unstable", False) is True
    self.event_stack.append(events.OpenGate(place))

  def handle_spawn_clue(self, place):
    assert place in self.places
    assert getattr(self.places[place], "unstable", False) is True
    self.event_stack.append(events.SpawnClue(place))

  def handle_slider(self, char_idx, name, value):
    assert self.event_stack
    event = self.event_stack[-1]
    if not isinstance(event, events.SliderInput):
      raise InvalidMove("It is not time to move your sliders.")
    if event.character != self.characters[char_idx]:
      raise NotYourTurn("It is not your turn to set sliders.")
    event.resolve(self, name, value)

  def handle_give(self, char_idx, recipient_idx, handle, amount):
    if not isinstance(recipient_idx, int):
      raise InvalidPlayer("Invalid recipient")
    if recipient_idx < 0 or recipient_idx >= len(self.characters):
      raise InvalidPlayer("Invalid recipient")
    if recipient_idx == char_idx:
      raise InvalidMove("You cannot trade with yourself")
    recipient = self.characters[recipient_idx]
    donor = self.characters[char_idx]

    if not self.can_trade():
      raise InvalidMove("You cannot trade at this time.")
    if donor.place != recipient.place:
      raise InvalidMove("You must be in the same place to trade.")

    if handle == "dollars":
      if not isinstance(amount, int):
        raise InvalidMove("Invalid quantity")
      if amount < 0 or amount > donor.dollars:
        raise InvalidMove("Invaild quantity")
      recipient.dollars += amount
      donor.dollars -= amount
      return

    if not isinstance(handle, str):
      raise InvalidMove("Invalid possession")
    donations = [pos for pos in donor.possessions if pos.handle == handle]
    if len(donations) != 1:
      raise InvalidMove("Invalid possession")
    donation = donations[0]
    # TODO: trading the deputy's revolver and patrol wagon
    if getattr(donation, "deck", None) not in {"common", "unique", "spells"}:
      raise InvalidMove("You can only trade items")

    # TODO: turn this into an event.
    donor.possessions.remove(donation)
    recipient.possessions.append(donation)

  def can_trade(self):
    if self.turn_phase != "movement":  # TODO: trading during the final battle
      return False
    if not self.event_stack:
      return False
    event = self.event_stack[-1]
    if isinstance(event, (events.CityMovement, events.ForceMovement, events.Return)):
      return True
    if len(self.event_stack) < 2:
      return False
    if isinstance(self.event_stack[-2], events.Return) and isinstance(event, events.GateChoice):
      return True
    return False

  def next_turn(self):
    # TODO: game stages other than slumber
    # Handle the end of the mythos phase separately.
    if self.turn_phase == "mythos":
      seq = self.add_pending_players()
      self.turn_number += 1
      if self.turn_number != 0:
        self.first_player += 1
        self.first_player %= len(self.characters)
      self.turn_idx = self.first_player
      self.turn_phase = "upkeep"
      for char in self.characters:  # TODO: is this the right place to check for this?
        if char.lose_turn_until and char.lose_turn_until <= self.turn_number:
          char.lose_turn_until = None
      if seq.events:
        seq.events.append(events.Upkeep(self.characters[self.turn_idx]))
        self.event_stack.append(seq)
      else:
        self.event_stack.append(events.Upkeep(self.characters[self.turn_idx]))
      for place in self.places.values():
        if getattr(place, "closed_until", None) == self.turn_number:
          place.closed_until = None
      return

    self.turn_idx += 1
    self.turn_idx %= len(self.characters)

    # Handle a switch to the next turn phase.
    if self.turn_idx == self.first_player:
      # Guaranteed to not go off the end of the list because this is not the mythos phase.
      phase_idx = self.TURN_PHASES.index(self.turn_phase)
      self.turn_phase = self.TURN_PHASES[phase_idx + 1]

    # We are done updating turn phase, turn number, turn index, and first player.
    self.event_stack.append(self.TURN_TYPES[self.turn_phase](self.characters[self.turn_idx]))

  def add_pending_players(self):
    if not self.pending_chars:
      return events.Sequence([], None)

    assert not {char.name for char in self.characters} & set(self.pending_chars)
    assert len(set(self.pending_chars)) == len(self.pending_chars)
    new_characters = []
    for name in self.pending_chars:
      new_characters.append(self.all_characters[name])
    self.characters.extend(new_characters)
    self.pending_chars.clear()

    # Abilities and fixed possessions.
    for char in new_characters:
      char.place = self.places[char.home]
      char.possessions.extend(char.abilities())
      self.give_fixed_possessions(char, char.fixed_possessions())
    # Random possessions.
    for char in new_characters:
      self.give_random_possessions(char, char.random_possessions())
    # Initial attributes.
    for char in new_characters:
      for attr, val in char.initial_attributes().items():
        setattr(char, attr, val)

    return events.Sequence([events.SliderInput(char, free=True) for char in new_characters], None)


class EldritchGame(BaseGame):

  def __init__(self):
    self.game = GameState()
    self.connected = set()
    self.host = None
    self.player_sessions = {}
    self.pending_sessions = {}

  def game_url(self, game_id):
    return f"/eldritch/game.html?game_id={game_id}"

  def game_status(self):
    return self.game.game_status()

  @classmethod
  def parse_json(cls, json_str):  # pylint: disable=arguments-renamed,unused-argument
    return None  # TODO

  def json_str(self):
    output = self.game.json_repr()
    output["player_sessions"] = self.player_sessions
    output["pending_sessions"] = self.pending_sessions
    return json.dumps(output, cls=CustomEncoder)

  def for_player(self, session):
    output = self.game.for_player(self.player_sessions.get(session))
    # is_connected = {idx: sess in self.connected for sess, idx in self.player_sessions.items()}
    # TODO: send connection information somehow
    # for idx in range(len(output["characters"])):
    #   output["characters"][idx]["disconnected"] = not is_connected.get(idx, False)
    output["player_idx"] = self.player_sessions.get(session)
    output["pending_name"] = self.pending_sessions.get(session)
    return json.dumps(output, cls=CustomEncoder)

  def connect_user(self, session):
    self.connected.add(session)
    if self.host is None:
      self.host = session

  def disconnect_user(self, session):
    self.connected.remove(session)
    if session in self.pending_sessions:
      name = self.pending_sessions[session]
      if name in self.game.pending_chars:
        self.game.pending_chars.remove(name)
      del self.pending_sessions[session]
    if self.host == session:
      if not self.connected:
        self.host = None
      else:
        self.host = list(self.connected)[0]

  def handle(self, session, data):
    if not isinstance(data, dict):
      raise InvalidMove("Data must be a dictionary.")
    if data.get("type") == "join":
      self.handle_join(session, data)
      yield None
      return
    if session not in self.player_sessions and data.get("type") != "start":
      raise InvalidPlayer("Unknown player")
    if data.get("type") == "start":
      assert session == self.host
    for val in self.game.handle(self.player_sessions.get(session), data):
      self.update_pending_players()
      yield val

  def handle_join(self, session, data):
    self.game.handle_join(
        self.player_sessions.get(session), self.pending_sessions.get(session), data.get("char"))
    self.pending_sessions[session] = data.get("char")

  def update_pending_players(self):
    if not self.pending_sessions:
      return
    indexes = {char.name: idx for idx, char in enumerate(self.game.characters)}
    pending = {name: session for session, name in self.pending_sessions.items()}
    updated = indexes.keys() & pending.keys()
    for name in updated:
      self.player_sessions[pending[name]] = indexes[name]
      self.pending_sessions.pop(pending[name])
