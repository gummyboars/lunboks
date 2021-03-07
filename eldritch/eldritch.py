import collections
import json
from random import SystemRandom
random = SystemRandom()

from game import (
    BaseGame, ValidatePlayer, CustomEncoder, InvalidInput, UnknownMove, InvalidMove,
    InvalidPlayer, TooManyPlayers, NotYourTurn,
)

import eldritch.abilities as abilities
import eldritch.assets as assets
import eldritch.characters as characters
import eldritch.encounters as encounters
import eldritch.events as events
import eldritch.gates as gates
import eldritch.gate_encounters as gate_encounters
import eldritch.items as items
import eldritch.monsters as monsters
import eldritch.mythos as mythos
import eldritch.places as places


class GameState(object):

  DEQUE_ATTRIBUTES = {"common", "unique", "spells", "skills", "allies", "gates"}
  HIDDEN_ATTRIBUTES = {
      "event_stack", "interrupt_stack", "trigger_stack", "usables", "mythos", "gate_cards"}
  TURN_PHASES = ["upkeep", "movement", "encounter", "otherworld", "mythos"]

  def __init__(self):
    self.places = {}
    self.characters = []
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
    self.game_stage = "slumber"  # valid values are setup, slumber, awakened, victory, defeat
    # valid values are setup, upkeep, movement, encounter, otherworld, mythos, awakened
    self.turn_phase = "upkeep"
    self.event_stack = collections.deque()
    self.interrupt_stack = collections.deque()
    self.trigger_stack = collections.deque()
    self.usables = {}
    self.done_using = {}
    self.event_log = []
    self.turn_number = 0
    self.turn_idx = 0
    self.first_player = 0
    self.rumor = None
    self.environment = None
    self.ancient_one = None
    self.other_globals = []
    self.check_result = None
    self.dice_result = []

  def initialize(self):
    self.places = places.CreatePlaces()
    infos, other_worlds = places.CreateOtherWorlds()
    self.places.update(other_worlds)
    encounter_cards = encounters.CreateEncounterCards()
    self.gate_cards.extend(gate_encounters.CreateGateCards())
    for neighborhood_name, cards in encounter_cards.items():
      self.places[neighborhood_name].encounters.extend(cards)

    gate_markers = gates.CreateGates(infos)
    random.shuffle(gate_markers)
    self.gates.extend(gate_markers)

    self.monsters = monsters.CreateMonsters()
    for monster in self.monsters:
      monster.place = self.monster_cup

    self.common.extend(items.CreateCommon())
    self.unique.extend(items.CreateUnique())
    self.skills.extend(abilities.CreateSkills())
    self.allies.extend(assets.CreateAllies())

    self.mythos.extend(mythos.CreateMythos())

    self.characters = characters.CreateCharacters()
    for char in self.characters:
      char.place = self.places[char.home]

  def get_modifier(self, thing, attribute):
    modifier = 0
    for glob in self.globals():
      if not glob:
        continue
      modifier += glob.get_modifier(thing, attribute)
    return modifier

  def globals(self):
    return [self.rumor, self.environment, self.ancient_one] + self.other_globals

  def game_status(self):
    return "eldritch game"  # TODO

  def json_repr(self):
    output = {}
    output.update({
      key: getattr(self, key) for key in
      self.__dict__.keys() - self.DEQUE_ATTRIBUTES - self.HIDDEN_ATTRIBUTES - {"characters"}
    })
    for attr in self.DEQUE_ATTRIBUTES:
      output[attr] = list(getattr(self, attr))
    output["characters"] = []
    for char in self.characters:
      output["characters"].append(char.get_json(self))
    return output

  def for_player(self, char_idx):
    output = self.json_repr()
    if self.turn_idx == char_idx and self.turn_phase == "movement":
      output["distances"] = self.get_distances(self.turn_idx)

    # We only return the counts of these items, not the actual items.
    output["monster_cup"] = len([mon for mon in self.monsters if mon.place == self.monster_cup])
    output["gates"] = len(self.gates)

    output["choice"] = None
    top_event = self.event_stack[-1] if self.event_stack else None
    if top_event and isinstance(top_event, events.ChoiceEvent) and not top_event.is_resolved():
      if top_event.character == self.characters[char_idx]:
        output["choice"] = {"prompt": top_event.prompt()}
        if isinstance(top_event, events.CardChoice):
          output["choice"]["cards"] = top_event.choices
        elif isinstance(top_event, events.MultipleChoice):
          output["choice"]["choices"] = top_event.choices
        elif isinstance(top_event, events.CombatChoice):
          output["choice"]["items"] = 0
        elif isinstance(top_event, events.ItemCountChoice):
          output["choice"]["items"] = top_event.count
        else:
          raise RuntimeError("Unknown choice type %s" % top_event.__class__.__name__)
    if self.usables.get(char_idx):
      output["usables"] = list(self.usables[char_idx].keys())
    else:
      output["usables"] = None
    return output

  @classmethod
  def parse_json(cls, json_str):
    pass  # TODO

  def handle(self, char_idx, data):
    if char_idx not in range(len(self.characters)):
      raise InvalidPlayer("no such player %s" % char_idx)
    if data.get("type") == "end_turn":
      self.handle_end_turn(char_idx)
    elif data.get("type") == "set_slider":
      self.handle_slider(char_idx, data.get("name"), data.get("value"))
    elif data.get("type") == "move":
      self.handle_move(char_idx, data.get("place"))
    elif data.get("type") == "check":  # TODO: remove
      self.handle_check(char_idx, data.get("check_type"), data.get("modifier"))
    elif data.get("type") == "monster":  # TODO: remove
      self.handle_spawn_monster(data.get("monster"), data.get("place"))
    elif data.get("type") == "mythos":
      self.handle_mythos()
    elif data.get("type") == "gate":  # TODO: remove
      self.handle_spawn_gate(data.get("place"))
    elif data.get("type") == "clue":  # TODO: remove
      self.handle_spawn_clue(data.get("place"))
    elif data.get("type") == "choice":
      self.handle_choice(char_idx, data.get("choice"))
    elif data.get("type") == "use":
      self.handle_use(char_idx, data.get("idx"))
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
      if isinstance(event, events.ChoiceEvent) and not event.is_resolved():
        yield None
        return
      self.usables = self.get_usable_interrupts(event)
      if not all([self.done_using.get(char_idx) for char_idx in self.usables]):
        yield None
        return
      if not event.is_resolved():
        event.resolve(self)
      if not event.is_resolved():
        continue
      if self.finish_event(event):
        yield None
      if self.trigger_stack[-1]:
        self.event_stack.append(self.trigger_stack[-1].pop())
        continue
      self.usables = self.get_usable_triggers(event)
      if not all([self.done_using.get(char_idx) for char_idx in self.usables]):
        yield None
        return
      self.pop_event(event)
      yield None

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
    # TODO: maybe find a better way to detect when the turn is over. Test with going insane.
    if event.is_resolved() and isinstance(event, events.EndTurn):
      self.next_turn()

  def clear_usables(self):
    self.usables.clear()
    self.done_using.clear()

  # TODO: global interrupts/triggers from ancient one, environment, other mythos/encounter cards
  def get_interrupts(self, event):
    interrupts = []
    if isinstance(event, (events.MoveOne, events.EndMovement)):
      nearby_monsters = [mon for mon in self.monsters if mon.place == event.character.place]
      if nearby_monsters:
        interrupts.append(events.EvadeOrFightAll(event.character, nearby_monsters))
    interrupts += sum([char.get_interrupts(event, self) for char in self.characters], [])
    return interrupts

  def get_usable_interrupts(self, event):
    i = {idx: char.get_usable_interrupts(event, self) for idx, char in enumerate(self.characters)}
    return {char_idx: interrupt_list for char_idx, interrupt_list in i.items() if interrupt_list}

  def get_triggers(self, event):
    triggers = []
    if isinstance(event, events.GainOrLoss):
      # TODO: both going to zero at the same time means you are devoured.
      if event.character.sanity <= 0:
        triggers.append(events.Insane(event.character, self.places["Asylum"]))
      if event.character.stamina <= 0:
        triggers.append(events.Unconscious(event.character, self.places["Hospital"]))
    triggers.extend(sum([char.get_triggers(event, self) for char in self.characters], []))
    return triggers

  def get_usable_triggers(self, event):
    t = {idx: char.get_usable_triggers(event, self) for idx, char in enumerate(self.characters)}
    return {char_idx: trigger_list for char_idx, trigger_list in t.items() if trigger_list}

  def handle_use(self, char_idx, possession_idx):
    assert char_idx in self.usables
    assert possession_idx in self.usables[char_idx]
    self.event_stack.append(self.usables[char_idx].pop(possession_idx))

  def handle_done_using(self, char_idx):
    assert char_idx in self.usables
    self.done_using[char_idx] = True

  def handle_choice(self, char_idx, choice):
    event = self.event_stack[-1]
    assert isinstance(event, events.ChoiceEvent)
    assert event.character == self.characters[char_idx]
    event.resolve(self, choice)

  def handle_check(self, char_idx, check_type, modifier):
    if char_idx != self.turn_idx:
      raise NotYourTurn("It is not your turn.")
    if check_type is None:
      raise InvalidInput("no check type")
    if check_type not in assets.CHECK_TYPES:
      raise InvalidInput("unknown check type")
    try:
      modifier = int(modifier)
    except (ValueError, TypeError):
      raise InvalidInput("invalid difficulty")
    if self.event_stack:
      raise InvalidInput("there are events on the stack")
    self.event_stack.append(events.Check(self.characters[char_idx], check_type, modifier))

  def handle_mythos(self):
    chosen = self.mythos.popleft()
    self.mythos.append(chosen)
    self.event_stack.append(chosen.create_event(self))

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
    assert getattr(self.places[place], "unstable", False) == True
    self.event_stack.append(events.OpenGate(place))

  def handle_spawn_clue(self, place):
    assert place in self.places
    assert getattr(self.places[place], "unstable", False) == True
    self.event_stack.append(events.SpawnClue(place))

  def handle_slider(self, char_idx, name, value):
    if char_idx != self.turn_idx:
      raise NotYourTurn("It is not your turn.")
    if self.turn_phase != "upkeep":
      raise InvalidMove("You may only move sliders during the upkeep phase.")
    if name is None:
      raise InvalidInput("missing slider name")
    char = self.characters[char_idx]
    if not hasattr(char, name + "_slider"):
      raise InvalidInput("invalid slider name %s" % name)
    try:
      value = int(value)
    except (ValueError, TypeError):
      raise InvalidInput("invalid value %s" % value)
    if 0 > value or value >= len(getattr(char, "_" + name)):
      raise InvalidInput("invalid slider value %s" % value)
    slots_moved = abs(getattr(char, name + "_slider") - value)
    if slots_moved > char.focus_points:
      raise InvalidMove(
          "You only have %s focus left; you would need %s." % (char.focus_points, slots_moved))
    char.focus_points -= slots_moved
    setattr(char, name + "_slider", value)

  def handle_move(self, char_idx, place):
    if char_idx != self.turn_idx:
      raise NotYourTurn("It is not your turn.")
    if self.turn_phase != "movement":
      raise InvalidMove("You may only move during the movement phase.")
    if place is None:
      raise InvalidInput("no place")
    if place not in self.places:
      raise InvalidInput("unknown place")
    routes = self.get_routes(char_idx)
    if place not in routes or len(routes[place]) > self.characters[char_idx].movement_points:
      raise InvalidMove(
          "You cannot reach that location with %s movement." %
          self.characters[char_idx].movement_points
      )
    self.event_stack.append(events.Movement(
      self.characters[char_idx], [self.places[name] for name in routes[place]]))

  def handle_end_turn(self, char_idx):
    if char_idx != self.turn_idx:
      raise NotYourTurn("It is not your turn.")
    if self.event_stack:
      raise InvalidMove("There are unresolved events.")
    if self.turn_phase == "movement":
      self.event_stack.append(events.EndMovement(self.characters[char_idx]))
    elif self.turn_phase == "upkeep":
      self.event_stack.append(events.EndUpkeep(self.characters[char_idx]))
    else:
      self.next_turn()  # TODO - this is not valid

  def next_turn(self):
    # TODO: game stages other than slumber
    # Handle the end of the mythos phase separately.
    if self.turn_phase == "mythos":
      self.turn_number += 1
      self.first_player += 1
      self.first_player %= len(self.characters)
      self.turn_idx = self.first_player
      self.turn_phase = "upkeep"
      # TODO: separate upkeep into three phases - refresh, upkeep actions, adjust skills.
      for char in self.characters:
        if char.lose_turn_until == self.turn_number:
          char.lose_turn_until = None
    else:
      self.turn_idx += 1
      self.turn_idx %= len(self.characters)

      # Handle a switch to the next turn phase.
      if self.turn_idx == self.first_player:
        # Guaranteed to not go off the end of the list because this is not the mythos phase.
        phase_idx = self.TURN_PHASES.index(self.turn_phase)
        self.turn_phase = self.TURN_PHASES[phase_idx + 1]
        # No start-of-turn effects or skipping for the mythos phase.
        if self.turn_phase == "mythos":
          return

    # Handle start-of-turn effects or turn skipping.
    char = self.characters[self.turn_idx]
    if char.lose_turn_until is not None:
      return self.next_turn()
    if self.turn_phase == "upkeep":
      char.focus_points = char.focus
    if self.turn_phase == "movement":
      if char.delayed_until == self.turn_number:
        char.delayed_until = None
      elif char.delayed_until is not None:
        return self.next_turn()
      char.movement_points = char.speed(self)
    if self.turn_phase == "encounter":
      if not isinstance(char.place, places.Location):
        return self.next_turn()
      elif char.place.neighborhood.encounters:
        self.event_stack.append(events.Encounter(char, char.place.name))
    if self.turn_phase == "otherworld":
      if not isinstance(char.place, places.OtherWorld):
        return self.next_turn()
      else:
        self.event_stack.append(events.GateEncounter(char, char.place.info))

  def get_distances(self, char_idx):
    routes = self.get_routes(char_idx)
    return {loc: len(route) for loc, route in routes.items()}

  def get_routes(self, char_idx):
    if self.characters[char_idx].movement_points == 0:
      return {}
    routes = {self.characters[char_idx].place.name: []}
    if self.characters[char_idx].place.closed:
      return routes

    monster_counts = collections.defaultdict(int)
    for monster in self.monsters:
      monster_counts[monster.place.name] += 1

    queue = collections.deque()
    for place in self.characters[char_idx].place.connections:
      if not place.closed:
        queue.append((place, []))
    while queue:
      place, route = queue.popleft()
      if place.name in routes:
        continue
      if place.closed:  # TODO: more possibilities?
        continue
      routes[place.name] = route + [place.name]
      if len(routes[place.name]) == self.characters[char_idx].movement_points:
        continue
      if monster_counts[place.name] > 0:
        continue
      for next_place in place.connections:
        queue.append((next_place, route + [place.name]))
    return routes


class EldritchGame(BaseGame):

  def __init__(self):
    self.game = GameState()
    self.game.initialize()
    self.connected = set()
    self.host = None
    self.player_sessions = collections.OrderedDict()

  def game_url(self, game_id):
    return f"/eldritch/game.html?game_id={game_id}"

  def game_status(self):
    if self.game is None:
      return "unstarted eldritch game (%s players)" % len(self.player_sessions)
    return self.game.game_status()

  @classmethod
  def parse_json(cls, json_str):
    return None  # TODO

  def json_str(self):
    if self.game is None:
      return "{}"
    output = self.game.json_repr()
    output["player_sessions"] = dict(self.player_sessions)
    return json.dumps(output, cls=CustomEncoder)

  def for_player(self, session):
    if self.game is None:
      data = {
          "game_stage": "not_started",
          "players": [],  # TODO
      }
      return json.dumps(data, cls=CustomEncoder)
    output = self.game.for_player(self.player_sessions.get(session))
    is_connected = {idx: sess in self.connected for sess, idx in self.player_sessions.items()}
    '''
    TODO: send connection information somehow
    for idx in range(len(output["characters"])):
      output["characters"][idx]["disconnected"] = not is_connected.get(idx, False)
      '''
    output["player_idx"] = self.player_sessions.get(session)
    return json.dumps(output, cls=CustomEncoder)

  def connect_user(self, session):
    self.connected.add(session)
    if self.game is not None:
      # TODO: properly handle letting players join the game.
      if session not in self.player_sessions:
        missing = set(range(len(self.game.characters))) - set(self.player_sessions.values())
        if missing:
          self.player_sessions[session] = min(missing)
      return
    if self.host is None:
      self.host = session

  def disconnect_user(self, session):
    self.connected.remove(session)
    if self.game is not None:
      return
    if session in self.player_sessions:
      del self.player_sessions[session]
    if self.host == session:
      if not self.connected:
        self.host = None
      else:
        self.host = list(self.connected)[0]

  def handle(self, session, data):
    if self.player_sessions.get(session) is None:
      raise InvalidPlayer("Unknown player")
    return self.game.handle(self.player_sessions[session], data)
