import collections
import json
from random import SystemRandom
random = SystemRandom()

from game import (
    BaseGame, ValidatePlayer, CustomEncoder, InvalidInput, UnknownMove, InvalidMove,
    InvalidPlayer, TooManyPlayers, NotYourTurn,
)

from eldritch.characters import CHARACTERS
from eldritch.places import LOCATIONS, STREETS
from eldritch.items import CHECK_TYPES


class GameState(object):

  DEQUE_ATTRIBUTES = {"common", "unique", "spells", "skills"}

  def __init__(self):
    self.places = {}
    self.places.update(LOCATIONS)
    self.places.update(STREETS)
    self.characters = CHARACTERS
    self.common = collections.deque()
    self.unique = collections.deque()
    self.spells = collections.deque()
    self.skills = collections.deque()
    self.allies = []
    self.mythos = []
    self.gates = []
    self.game_stage = "setup"  # valid values are setup, slumber, awakened, victory, defeat
    # valid values are setup, upkeep, movement, encounter, otherworld, mythos, awakened
    self.turn_phase = "setup"
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
    output["distances"] = self.get_distances(0)
    return output

  @classmethod
  def parse_json(cls, json_str):
    pass  # TODO

  def handle(self, char_idx, data):
    if char_idx not in range(len(self.characters)):
      raise InvalidPlayer("no such player %s" % char_idx)
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

  def handle_move(self, char_idx, place):
    if place is None:
      raise InvalidInput("no place")
    if place not in self.places:
      raise InvalidInput("unknown place")
    self.characters[char_idx].place = self.places[place]

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
