import collections
import json
from random import SystemRandom
random = SystemRandom()

from game import (
    BaseGame, ValidatePlayer, CustomEncoder, InvalidInput, UnknownMove, InvalidMove,
    InvalidPlayer, TooManyPlayers, NotYourTurn,
)

import eldritch.characters as characters
import eldritch.places as places
from eldritch.items import CHECK_TYPES


class GameState(object):

  DEQUE_ATTRIBUTES = {"common", "unique", "spells", "skills"}
  TURN_PHASES = ["upkeep", "movement", "encounter", "otherworld", "mythos"]

  def __init__(self):
    self.places = {}
    self.places.update(places.LOCATIONS)
    self.places.update(places.STREETS)
    self.characters = characters.CHARACTERS
    self.common = collections.deque()
    self.unique = collections.deque()
    self.spells = collections.deque()
    self.skills = collections.deque()
    self.allies = []
    self.mythos = []
    self.gates = []
    self.game_stage = "slumber"  # valid values are setup, slumber, awakened, victory, defeat
    # valid values are setup, upkeep, movement, encounter, otherworld, mythos, awakened
    self.turn_phase = "upkeep"
    self.action = None
    self.turn_idx = 0
    self.first_player = 0
    self.ancient_one = None
    self.check_result = None
    self.dice_result = []

  def game_status(self):
    return "eldritch game"  # TODO

  def json_repr(self):
    output = {}
    output.update({key: getattr(self, key) for key in self.__dict__.keys() - self.DEQUE_ATTRIBUTES})
    for attr in self.DEQUE_ATTRIBUTES:
      output[attr] = list(getattr(self, attr))
    output["distances"] = self.get_distances(self.turn_idx)
    return output

  @classmethod
  def parse_json(cls, json_str):
    pass  # TODO

  def handle(self, char_idx, data):
    if char_idx not in range(len(self.characters)):
      raise InvalidPlayer("no such player %s" % char_idx)
    if char_idx != self.turn_idx:
      raise NotYourTurn("It is not your turn.")
    if data.get("type") == "end_turn":
      return self.handle_end_turn()
    if data.get("type") == "set_slider":
      return self.handle_slider(char_idx, data.get("name"), data.get("value"))
    if data.get("type") == "move":
      return self.handle_move(char_idx, data.get("place"))
    if data.get("type") == "check":
      return self.handle_check(char_idx, data.get("check_type"), data.get("modifier"))
    raise UnknownMove(data.get("type"))

  def handle_check(self, char_idx, check_type, modifier):
    if check_type is None:
      raise InvalidInput("no check type")
    if check_type not in CHECK_TYPES:
      raise InvalidInput("unknown check type")
    try:
      modifier = int(modifier)
    except (ValueError, TypeError):
      raise InvalidInput("invalid difficulty")
    successes, self.dice_result = self.characters[char_idx].make_check(check_type, modifier)
    self.check_result = successes > 0

  def handle_slider(self, char_idx, name, value):
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
    if self.turn_phase != "movement":
      raise InvalidMove("You may only move during the movement phase.")
    if place is None:
      raise InvalidInput("no place")
    if place not in self.places:
      raise InvalidInput("unknown place")
    distances = self.get_distances(char_idx)
    if place not in distances or distances[place] > self.characters[char_idx].movement_points:
      raise InvalidMove(
          "You cannot reach that location with %s movement." %
          self.characters[char_idx].movement_points
      )
    self.characters[char_idx].place = self.places[place]
    self.characters[char_idx].movement_points -= distances[place]
    if self.characters[char_idx].movement_points <= 0:
      self.next_turn()

  def handle_end_turn(self):
    self.next_turn()

  def next_turn(self):
    # TODO: game stages other than slumber
    if self.turn_phase == "mythos":
      self.first_player += 1
      self.first_player %= len(self.characters)
      self.turn_idx = self.first_player
      self.turn_phase = "upkeep"
      for char in self.characters:
        char.focus_points = char.focus
      return
    self.turn_idx += 1
    self.turn_idx %= len(self.characters)
    if self.turn_idx == self.first_player:
      # Guaranteed to not go off the end of the list because we check for mythos above.
      phase_idx = self.TURN_PHASES.index(self.turn_phase)
      self.turn_phase = self.TURN_PHASES[phase_idx + 1]
      if self.turn_phase == "movement":
        for char in self.characters:
          char.movement_points = char.speed
    if self.turn_phase == "encounter":
      place = self.characters[self.turn_idx].place
      if not isinstance(place, places.Location):
        self.next_turn()
        return
    if self.turn_phase == "otherworld":
      place = self.characters[self.turn_idx].place
      if not isinstance(place, places.OtherWorld):
        self.next_turn()
        return

  def get_distances(self, char_idx):
    distances = {self.characters[char_idx].place.name: 0}
    queue = collections.deque()
    for place in self.characters[char_idx].place.connections:
      queue.append((place, 1))
    while queue:
      place, distance = queue.popleft()
      if place.name in distances:
        continue
      if place.closed:  # TODO: more possibilities. monsters?
        continue
      distances[place.name] = distance
      if distance == self.characters[char_idx].movement_points:
        continue
      for next_place in place.connections:
        queue.append((next_place, distance+1))
    return distances


class EldritchGame(BaseGame):

  def __init__(self):
    self.game = GameState()
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
    output = self.game.json_repr()
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
