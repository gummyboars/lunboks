import copy
import json
from random import SystemRandom

from game import (  # pylint: disable=unused-import
  BaseGame,
  CustomEncoder,
  InvalidInput,  # noqa: F401
  UnknownMove,  # noqa: F401
  InvalidMove,
  InvalidPlayer,
  NotYourTurn,  # noqa: F401
  ValidatePlayer,  # noqa: F401
  TooManyPlayers,  # noqa: F401
)
from mansion import cards
from mansion import rooms


random = SystemRandom()


class Player:
  def __init__(self, room, color):
    self.room = room
    self.color = color
    self.cards = []

  def json_repr(self):
    return {"room": self.room.short_name, "color": self.color, "cards": self.cards}


class GameState:
  def __init__(self):
    self.started = False
    self.players = []
    self.turn_idx = 0
    self.turn_phase = "movement"  # valid values are movement, reaction, end
    self.react_idx = 0
    self.rooms = rooms.CreateRooms()
    self.deck = cards.CreateCards()
    self.doctor = next(idx for idx, room in enumerate(self.rooms) if room.name == "Gallery")

  def json_repr(self):
    return copy.copy(self.__dict__)

  def for_player(self, idx):
    data = self.json_repr()
    data["doctor"] = self.rooms[self.doctor].short_name
    if idx is not None:
      current = self.players[idx].room
      data["reachable"] = [room.short_name for room in current.connections] + [current.short_name]
      data["visible"] = [room.short_name for room in current.sight] + [current.short_name]
    else:
      data["reachable"] = []
      data["visible"] = []
    data["players"] = []
    for pidx, player in enumerate(self.players):
      pdata = player.json_repr()
      if pidx != idx:
        pdata["cards"] = len(pdata["cards"])
      data["players"].append(pdata)
    return data

  def handle(self, idx, data):
    if idx is None or idx < 0 or idx >= len(self.players):
      raise InvalidPlayer(f"Unknown player {idx}")

    if data.get("type") != "card" and self.turn_idx != idx:
      raise InvalidMove("It is not your turn")
    if data.get("type") != "card" and self.turn_phase != "movement":
      raise InvalidMove("Waiting for players to react.")

    if data.get("type") == "move":
      self.handle_move(idx, data.get("name"))
    elif data.get("type") == "draw":
      self.handle_draw(idx)
      yield None
      self.next_turn()
    elif data.get("type") == "attack":
      self.handle_attack(idx, data.get("card"))
      yield None
      self.begin_reaction()
    elif data.get("type") == "end":
      self.handle_end(idx)
      yield None
      self.next_turn()
    elif data.get("type") == "card":
      self.handle_card(idx, data.get("card"))
    else:
      raise InvalidMove(f"Unknown move {data.get('type')}")
    yield None

  def handle_move(self, idx, short_name):
    if self.turn_phase != "movement":
      raise InvalidMove("You cannot move after taking an action.")
    dests = [room for room in self.rooms if room.short_name == short_name]
    if len(dests) != 1:
      raise InvalidMove(f"Invalid destination {short_name}")
    dest = dests[0]
    if dest not in self.players[idx].room.connections:
      raise InvalidMove(f"You cannot get to {dest.name} from where you are.")
    self.players[idx].room = dest

  def handle_draw(self, idx):
    pass

  def handle_attack(self, idx, card):
    pass

  def handle_end(self, idx):
    pass

  def handle_card(self, idx, card):
    pass

  def next_turn(self):
    self.turn_idx += 1
    if self.turn_idx >= len(self.players):
      self.turn_idx = 0
    self.doctor += 1
    if self.doctor >= len(self.rooms):
      self.doctor = 0
    self.turn_phase = "movement"

  def begin_reaction(self):
    pass

  def handle_start(self, num_players):
    if self.started:
      raise InvalidMove("The game has already started.")
    if num_players < 2:
      raise InvalidMove("Must have at least two players.")
    if num_players > 8:
      raise InvalidMove("Cannot have more than eight players.")
    colors = [
      "blue",
      "red",
      "darkgreen",
      "orange",
      "blueviolet",
      "limegreen",
      "deepskyblue",
      "violet",
    ]
    self.players = [Player(self.rooms[0], colors[idx]) for idx in range(num_players)]
    random.shuffle(self.deck)
    for player in self.players:
      for _ in range(6):
        player.cards.append(self.deck.pop())
    self.started = True


class MansionGame(BaseGame):
  def __init__(self):
    self.game = GameState()
    self.connected = set()
    self.host = None
    self.sessions = {}

  def game_url(self, game_id):
    return f"/mansion/game.html?game_id={game_id}"

  def game_status(self):
    return "mansion game"  # TODO

  @classmethod
  def parse_json(cls, json_str):  # pylint: disable=arguments-renamed,unused-argument
    return None  # TODO

  def json_str(self):
    output = self.game.json_repr()
    output["sessions"] = self.sessions
    return json.dumps(output, cls=CustomEncoder)

  def for_player(self, session):
    output = self.game.for_player(self.sessions.get(session))
    # TODO: send connection information somehow
    output["player_idx"] = self.sessions.get(session)
    output["host"] = self.host == session
    return json.dumps(output, cls=CustomEncoder)

  def connect_user(self, session):
    self.connected.add(session)
    if self.host is None:
      self.host = session

  def disconnect_user(self, session):
    self.connected.remove(session)
    if self.host == session:
      if not self.connected:
        self.host = None
      else:
        self.host = next(iter(self.connected))

  def handle(self, session, data):
    if not isinstance(data, dict):
      raise InvalidMove("Data must be a dictionary.")
    if session not in self.sessions and data.get("type") not in ["start", "join"]:
      raise InvalidPlayer("Unknown player")
    if data.get("type") == "start":
      sessions = {sess: idx for idx, sess in enumerate(self.connected)}
      self.game.handle_start(len(sessions))
      self.sessions = sessions
      yield None
      return
    yield from self.game.handle(self.sessions.get(session), data)
