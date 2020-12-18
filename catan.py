import collections
from http import HTTPStatus
import json
import operator
import os
import random
from unittest import mock

from game import (
    BaseGame, ValidatePlayer, InvalidInput, UnknownMove, InvalidMove,
    InvalidPlayer, TooManyPlayers, NotYourTurn
)

RESOURCES = ["rsrc1", "rsrc2", "rsrc3", "rsrc4", "rsrc5"]
PLAYABLE_DEV_CARDS = ["yearofplenty", "monopoly", "roadbuilding", "knight"]
VICTORY_CARDS = ["palace", "chapel", "university", "market", "library"]
TILE_NUMBERS = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]
TILE_SEQUENCE = [
    (2, 3), (4, 2), (6, 1), (8, 2), (10, 3),  # around the top
    (10, 5), (10, 7), (8, 8), (6, 9),  # down the side to the bottom
    (4, 8), (2, 7), (2, 5),  # back up the left side
    (4, 4), (6, 3), (8, 4), (8, 6), (6, 7), (4, 6), (6, 5)  # inner loop
    ]
SPACE_TILE_SEQUENCE = [
    (2, 1), (4, 0), (6, -1), (8, 0), (10, 1), (12, 2),  # around the top
    (12, 4), (12, 6), (12, 8),  # down the right side
    (10, 9), (8, 10), (6, 11), (4, 10), (2, 9), (0, 8),  # around the bottom
    (0, 6), (0, 4), (0, 2)  # up the left side
    ]
SPACE_TILE_ROTATIONS = [5, 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5]


def _validate_name(current_name, used_names, data):
  # TODO: maybe this should actually return the new name instead of having callers figure it out.
  ValidatePlayer(data)
  new_name = data["name"].strip()
  # Check this before checking used_names.
  if new_name == current_name:
    return
  if new_name in used_names:
    raise InvalidPlayer("There is already a player named %s" % new_name)
  '''
  TODO: re-enable this easter egg
  if len(player_name) > 50:
    unused_names = set(["Joey", "Ross", "Chandler", "Phoebe", "Rachel", "Monica"]) - used_names
    if unused_names:
      new_name = random.choice(list(unused_names))
      self.player_data[player_idx].name = new_name
      raise InvalidPlayer("Oh, is that how you want to play it? Well, you know what? I'm just gonna call you %s." % new_name)
  '''
  if len(new_name) > 16:
    raise InvalidPlayer("Max name length is 16.")


class CustomEncoder(json.JSONEncoder):

  def default(self, o):
    if hasattr(o, "json_repr"):
      return o.json_repr()
    return json.JSONEncoder.default(self, o)


class GameOption(object):

  def __init__(self, name, forced=False, default=False, choices=None, value=None):
    self.name = name
    self.forced = forced
    if choices is None:
      assert isinstance(default, bool)
    else:
      assert default in choices
    self.default = default
    self.choices = choices
    if value is None:
      self.value = default
    else:
      self.value = value

  def json_repr(self):
    return self.__dict__


class Location(object):

  def __init__(self, x, y):
    self.x = x
    self.y = y

  def as_tuple(self):
    return (self.x, self.y)

  def json_repr(self):
    return self.as_tuple()

  def __str__(self):
    return str(self.json_repr())

  def __eq__(self, other):
    return self.__class__ == other.__class__ and self.json_repr() == other.json_repr()

  def __hash__(self):
    return hash(self.as_tuple())


class TileLocation(Location):

  def __init__(self, x, y):
    assert x % 2 == 0, "tiles x location must be even %s, %s" % (x, y)
    if x % 4 == 0:
      assert y % 2 == 0, "tiles must line up correctly %s, %s" % (x, y)
    else:
      assert y % 2 == 1, "tiles must line up correctly %s, %s" % (x, y)
    Location.__init__(self, x, y)

  def get_upper_left_tile(self):
    return TileLocation(self.x - 2, self.y - 1)

  def get_upper_tile(self):
    return TileLocation(self.x, self.y - 2)

  def get_upper_right_tile(self):
    return TileLocation(self.x + 2, self.y - 1)

  def get_lower_right_tile(self):
    return TileLocation(self.x + 2, self.y + 1)

  def get_lower_tile(self):
    return TileLocation(self.x, self.y + 2)

  def get_lower_left_tile(self):
    return TileLocation(self.x - 2, self.y + 1)

  def get_upper_left_corner(self):
    return CornerLocation(self.x, self.y)

  def get_upper_right_corner(self):
    return CornerLocation(self.x+1, self.y)

  def get_right_corner(self):
    return CornerLocation(self.x+2, self.y+1)

  def get_lower_right_corner(self):
    return CornerLocation(self.x+1, self.y+2)

  def get_lower_left_corner(self):
    return CornerLocation(self.x, self.y+2)

  def get_left_corner(self):
    return CornerLocation(self.x-1, self.y+1)

  def get_adjacent_tiles(self):
    # NOTE: order matters here. Index in this array lines up with rotation semantics.
    return [self.get_lower_tile(), self.get_lower_left_tile(),
            self.get_upper_left_tile(), self.get_upper_tile(),
            self.get_upper_right_tile(), self.get_lower_right_tile()]

  def get_corner_locations(self):
    return [self.get_upper_left_corner(), self.get_upper_right_corner(),
            self.get_lower_left_corner(), self.get_lower_right_corner(),
            self.get_left_corner(), self.get_right_corner()]

  def old_get_corner_locations(self):
    """Gets coordinates of all the corners surrounding this tile.

    Tiles and corners use the same coordinate system. A tile shares coordinates
    with the corner that is in the upper left.
    """
    locations = []
    locations.extend([(self.x, self.y), (self.x + 1, self.y)])  # upper two corners
    locations.extend([(self.x, self.y + 2), (self.x + 1, self.y + 2)])  # lower two corners
    locations.extend([(self.x - 1, self.y + 1), (self.x + 2, self.y + 1)])  # left & right corners
    return [CornerLocation(*loc) for loc in locations]


class CornerLocation(Location):

  def get_tiles(self):
    """Returns the tile coordinates of all tiles touching this piece.

    Every corner is at the top of some hex. It touches that hex, as well as
    the hex above that one.
    Every corner is either a left corner or a right corner. If it is a left
    corner (odd x-coordinate), it also touches the tile up-right of itself.
    Otherwise (even x-coordinate), it touches the tile up-left of itself.
    """
    lower_hex = TileLocation(self.x - (self.x % 2), self.y)
    upper_hex = TileLocation(lower_hex.x, lower_hex.y - 2)
    if self.x % 2 == 1:
      middle_hex = TileLocation(self.x + 1, self.y - 1)
    else:
      middle_hex = TileLocation(self.x - 2, self.y - 1)
    return [lower_hex, upper_hex, middle_hex]

  def get_adjacent_corners(self):
    """Returns locations of adjacent corners.

    If this is a right corner (even x-coordinate), we look right, up-left,
    and down-left. If it is a left corner (odd x-coordinate), we look left,
    up-right, and down-right. 

    """
    if self.x % 2 == 0:
      return [
          CornerLocation(self.x + 1, self.y),
          CornerLocation(self.x - 1, self.y - 1),
          CornerLocation(self.x - 1, self.y + 1),
      ]
    else:
      return [
          CornerLocation(self.x - 1, self.y),
          CornerLocation(self.x + 1, self.y - 1),
          CornerLocation(self.x + 1, self.y + 1),
      ]

  def get_edge(self, other_corner):
    """Returns edge coordinates linking this corner to the other corner."""
    if other_corner.x < self.x:
      return EdgeLocation(other_corner, self)
    else:
      return EdgeLocation(self, other_corner)

  def get_edges(self):
    """Returns edge coordinates of edges adjacent to this corner.

    Edge coordinates must be given left-to-right.
    """
    return [self.get_edge(corner) for corner in self.get_adjacent_corners()]


class EdgeLocation(object):

  def __init__(self, *args):
    """Can take either two corners or 4 coordinates. Must be left-to-right."""
    if len(args) == 2:
      corner_left, corner_right = args
      assert isinstance(corner_left, CornerLocation)
      assert isinstance(corner_right, CornerLocation)
      assert corner_left.x < corner_right.x, "first corner must be left of second corner"
      self.corner_left = corner_left
      self.corner_right = corner_right
    elif len(args) == 4:
      leftx, lefty, rightx, righty = args
      assert leftx < rightx, "first corner must be left of second corner"
      self.corner_left = CornerLocation(leftx, lefty)
      self.corner_right = CornerLocation(rightx, righty)
    else:
      raise ValueError(args)

  def as_tuple(self):
    return (self.corner_left.x, self.corner_left.y, self.corner_right.x, self.corner_right.y)

  def json_repr(self):
    return self.as_tuple()

  def __str__(self):
    return str(self.json_repr())

  def __eq__(self, other):
    return self.__class__ == other.__class__ and self.json_repr() == other.json_repr()

  def __hash__(self):
    return hash(self.as_tuple())

  def get_adjacent_tiles(self):
    """Returns the two TileLocations that share a border at this edge."""
    right_locations = [tile.as_tuple() for tile in self.corner_right.get_tiles()]
    return [tile for tile in self.corner_left.get_tiles() if tile.as_tuple() in right_locations]


class Road(object):

  TYPES = ["road", "ship"]

  def __init__(self, location, road_type, player, closed=False, movable=True, source=None):
    self.location = EdgeLocation(*location)
    self.road_type = road_type
    self.player = player
    self.closed = closed
    self.movable = movable
    self.source = source

  def json_repr(self):
    data = {
        "location": self.location,
        "road_type": self.road_type,
        "player": self.player,
    }
    if self.road_type == "ship":
      data.update({
        "closed": self.closed,
        "movable": self.movable,
        "source": self.source,
      })
    return data

  @staticmethod
  def parse_json(value):
    # TODO: maybe this assert should go into the constructor?
    source = None
    if value["road_type"] == "ship":
      assert value.get("source") is not None
      source = CornerLocation(value["source"][0], value["source"][1])
    return Road(value["location"], value["road_type"], value["player"], value.get("closed", False),
        value.get("movable", True), source)

  def __str__(self):
    return str(self.json_repr())


class Piece(object):

  TYPES = ["settlement", "city"]

  def __init__(self, x, y, piece_type, player):
    self.location = CornerLocation(x, y)
    self.piece_type = piece_type
    self.player = player

  def json_repr(self):
    return {
        "location": self.location,
        "piece_type": self.piece_type,
        "player": self.player,
    }

  @staticmethod
  def parse_json(value):
    return Piece(value["location"][0], value["location"][1], value["piece_type"], value["player"])

  def __str__(self):
    return str(self.json_repr())


class Tile(object):

  def __init__(self, x, y, tile_type, is_land, number, rotation=0, variant="", land_rotations=None):
    self.location = TileLocation(x, y)
    self.tile_type = tile_type
    self.is_land = is_land
    self.number = number
    self.rotation = rotation
    self.variant = variant
    self.land_rotations = land_rotations or []

  def json_repr(self):
    return {
        "location": self.location,
        "tile_type": self.tile_type,
        "is_land": self.is_land,
        "number": self.number,
        "rotation": self.rotation,
        "variant": self.variant,
        "land_rotations": self.land_rotations,
    }

  @staticmethod
  def parse_json(value):
    return Tile(value["location"][0], value["location"][1], value["tile_type"],
        value["is_land"], value["number"], value["rotation"], value.get("variant") or "",
        value.get("land_rotations") or [])

  def __str__(self):
    return str(self.json_repr())


class Port(object):
  def __init__(self, x, y, port_type, rotation=0):
    self.location = TileLocation(x, y)
    self.port_type = port_type
    self.rotation = rotation

  def json_repr(self):
    return {
        "location": self.location,
        "port_type": self.port_type,
        "rotation": self.rotation,
    }

  @staticmethod
  def parse_json(value):
    return Port(value["location"][0], value["location"][1], value["port_type"], value["rotation"])

  def __str__(self):
    return str(self.json_repr())


class CatanPlayer(object):

  def __init__(self, color, name):
    self.color = color
    self.name = name
    self.knights_played = 0
    self.longest_route = 0
    self.cards = collections.defaultdict(int)
    self.trade_ratios = collections.defaultdict(lambda: 4)
    self.unusable = collections.defaultdict(int)

  def json_repr(self):
    return {attr: getattr(self, attr) for attr in self.__dict__}

  @staticmethod
  def parse_json(value):
    defaultdict_attrs = ["cards", "trade_ratios", "unusable"]
    p = CatanPlayer(None, None)
    for attr in defaultdict_attrs:
      getattr(p, attr).update(value[attr])
    for attr in set(p.__dict__.keys()) - set(defaultdict_attrs):
      setattr(p, attr, value[attr])
    return p

  def __str__(self):
    return str(self.json_repr())

  def json_for_player(self, is_over):
    ret = {
        "color": self.color,
        "name": self.name,
        "armies": self.knights_played,
        "longest_route": self.longest_route,
        "resource_cards": self.resource_card_count(),
        "dev_cards": self.dev_card_count(),
        "points": 0,
    }
    if is_over:
      ret["dev_cards"] = {
          name: count for name, count in self.cards.items()
          if name in (PLAYABLE_DEV_CARDS + VICTORY_CARDS)}
    return ret

  def resource_card_count(self):
    return sum([self.cards[x] for x in RESOURCES])

  def dev_card_count(self):
    return sum([self.cards[x] for x in PLAYABLE_DEV_CARDS + VICTORY_CARDS])


class CatanState(object):

  WANT = "want"
  GIVE = "give"
  TRADE_SIDES = [WANT, GIVE]
  LOCATION_ATTRIBUTES = {"tiles", "ports", "pieces", "roads"}
  HIDDEN_ATTRIBUTES = {"dev_cards", "dev_roads_placed", "played_dev"}
  COMPUTED_ATTRIBUTES = {"port_corners"}
  INDEXED_ATTRIBUTES = {"counter_offers", "discard_players"}

  def __init__(self):
    # Player data is a sequential list of CatanPlayer objects; players are identified by index.
    self.player_data = []
    self.tiles = {}
    self.ports = {}
    self.port_corners = {}
    self.pieces = {}
    self.roads = {}  # includes ships
    self.robber = None
    self.pirate = None
    self.dev_cards = []
    self.dev_roads_placed = 0
    self.played_dev = 0
    self.discard_players = {}  # Map of player to number of cards they must discard.
    self.rob_players = []  # List of players that can be robbed by this robber.
    self.turn_idx = 0
    self.largest_army_player = None
    self.longest_route_player = None
    self.dice_roll = None
    self.trade_offer = None
    self.counter_offers = {}  # Map of player to counter offer.
    # Special values for counter-offers: not present in dictionary means they have not
    # yet made a counter-offer. An null/None counter-offer indicates that they have
    # rejected the trade offer. A counter-offer equal to the original means they accept.
    self.game_phase = "place1"  # valid values are place1, place2, main, victory
    # valid values are settle, road, dice, collect, discard, robber, rob, dev_road, main
    self.turn_phase = "settle"
    # Flag for the don't allow players to rob at 2 points option
    self.rob_at_two = True
    self.victory_points = 10

  @classmethod
  def location_attrs(cls):
    return cls.LOCATION_ATTRIBUTES

  @classmethod
  def hidden_attrs(cls):
    return cls.HIDDEN_ATTRIBUTES

  @classmethod
  def indexed_attrs(cls):
    return cls.INDEXED_ATTRIBUTES

  @classmethod
  def computed_attrs(cls):
    return cls.COMPUTED_ATTRIBUTES

  @classmethod
  def parse_json(cls, gamedata):
    cstate = cls()

    # Regular attributes
    for attr in cstate.__dict__:
      if attr not in (cls.location_attrs() | cls.computed_attrs() | cls.indexed_attrs() | {"player_data"}):
        setattr(cstate, attr, gamedata[attr])

    # Parse the players.
    for parsed_player in gamedata["player_data"]:
      cstate.player_data.append(CatanPlayer.parse_json(parsed_player))

    # Indexed attributes update the corresponding dictionaries.
    for attr in cls.indexed_attrs():
      for idx, val in enumerate(gamedata[attr]):
        if val is not None:
          getattr(cstate, attr)[idx] = val

    # Location dictionaries are updated with their respective items.
    cstate.parse_tiles(gamedata["tiles"])
    cstate.parse_ports(gamedata["ports"])
    for piece_json in gamedata["pieces"]:
      piece = Piece.parse_json(piece_json)
      cstate._add_piece(piece)
    for road_json in gamedata["roads"]:
      road = Road.parse_json(road_json)
      cstate._add_road(road)

    # Location attributes need to be replaced with location objects.
    if cstate.robber is not None:
      cstate.robber = TileLocation(*cstate.robber)
    if cstate.pirate is not None:
      cstate.pirate = TileLocation(*cstate.pirate)

    cstate._compute_coast()  # Sets land_rotations for all space tiles.
    cstate._compute_ports()  # Sets port_corners.
    return cstate

  def parse_tiles(self, tiledata):
    for tile_json in tiledata:
      tile = Tile.parse_json(tile_json)
      self.add_tile(tile)

  def parse_ports(self, portdata):
    for port_json in portdata:
      port = Port.parse_json(port_json)
      self.add_port(port)

  def json_repr(self):
    ret = {
        name: getattr(self, name) for name in
        self.__dict__.keys() - self.location_attrs() - self.computed_attrs() - {"player_data"}
    }
    ret.update({name: list(getattr(self, name).values()) for name in self.location_attrs()})
    for attr in self.indexed_attrs():
      ret.update({attr: [getattr(self, attr).get(idx) for idx in range(len(self.player_data))]})
    ret["player_data"] = [player.json_repr() for player in self.player_data]
    return ret

  def for_player(self, player_idx):
    data = self.json_for_player()
    if player_idx is not None:
      data["you"] = player_idx
      data["cards"] = self.player_data[player_idx].cards
      data["trade_ratios"] = self.player_data[player_idx].trade_ratios
    return data

  def json_for_player(self):
    ret = self.json_repr()
    ret["type"] = "game_state"
    ret["turn"] = ret.pop("turn_idx")
    for name in self.hidden_attrs():
      del ret[name]
    del ret["player_data"]
    ret["dev_cards"] = len(self.dev_cards)

    land_corners = {}
    all_corners = {}
    # TODO: instead of sending a list of corners, we should send something like
    # a list of legal moves for tiles, corners, and edges.
    for tile in self.tiles.values():
      # Triple-count each corner and dedup.
      for corner_loc in tile.location.get_corner_locations():
        all_corners[corner_loc.as_tuple()] = corner_loc
        if not tile.is_land:
          continue
        land_corners[corner_loc.as_tuple()] = {"location": corner_loc}
    ret["corners"] = list(land_corners.values())
    edges = {}
    for corner in all_corners.values():
      # Double-count each edge and dedup.
      for edge in corner.get_edges():
        edge_type = self._get_edge_type(edge)
        if edge_type is not None:
          edges[edge.as_tuple()] = {"location": edge, "edge_type": edge_type}
    ret["edges"] = list(edges.values())

    is_over = (self.game_phase == "victory")

    ret["player_data"] = [player.json_for_player(is_over) for player in self.player_data]
    for idx in range(len(self.player_data)):
      ret["player_data"][idx]["points"] = self.player_points(idx, visible=(not is_over))
    return ret

  def player_points(self, player_idx, visible):
    count = 0
    for piece in self.pieces.values():
      if piece.player == player_idx:
        if piece.piece_type == "settlement":
          count += 1
        elif piece.piece_type == "city":
          count += 2
    if self.largest_army_player == player_idx:
      count += 2
    if self.longest_route_player == player_idx:
      count += 2
    if not visible:
      count += sum([self.player_data[player_idx].cards[card] for card in VICTORY_CARDS])
    return count

  def game_status(self):
    # TODO: list the rulesets being used
    return "catan game with %s" % ", ".join([p.name for p in self.player_data])

  def add_player(self, color, name):
    self.player_data.append(CatanPlayer(color, name))

  def handle(self, player_idx, data):
    if not data.get("type"):
      raise InvalidInput("Missing move type")
    self.check_turn_okay(player_idx, data["type"], data)
    self.inner_handle(player_idx, data["type"], data)
    self.post_handle(player_idx, data["type"], data)

  def check_turn_okay(self, player_idx, move_type, data):
    if move_type == "rename":
      return
    if self.game_phase == "victory":
      raise NotYourTurn("The game is over.")
    if self.turn_idx != player_idx:
      if move_type in ["discard", "counter_offer"]:
        return
      raise NotYourTurn("It is not your turn.")

  def inner_handle(self, player_idx, move_type, data):
    if move_type == "rename":
      return self.rename_player(player_idx, data)
    if move_type == "discard":
      return self.handle_discard(data.get("selection"), player_idx)
    if move_type == "counter_offer":
      return self.handle_counter_offer(data.get("offer"), player_idx)
    location = data.get("location")
    if move_type == "roll_dice":
      return self.handle_roll_dice()
    if move_type == "robber":
      return self.handle_robber(location, player_idx)
    if move_type == "rob":
      return self.handle_rob(data.get("player"), player_idx)
    if move_type == "road":
      return self.handle_road(location, player_idx, "road", [("rsrc2", 1), ("rsrc4", 1)])
    if move_type == "buy_dev":
      return self.handle_buy_dev(player_idx)
    if move_type == "play_dev":
      return self.handle_play_dev(data.get("card_type"), data.get("selection"), player_idx)
    if move_type == "settle":
      return self.handle_settle(location, player_idx)
    if move_type == "city":
      return self.handle_city(location, player_idx)
    if move_type == "trade_offer":
      return self.handle_trade_offer(data.get("offer"), player_idx)
    if move_type == "accept_counter":
      return self.handle_accept_counter(data.get("counter_offer"), data.get("counter_player"), player_idx)
    if move_type == "trade_bank":
      return self.handle_trade_bank(data.get("offer"), player_idx)
    if move_type == "end_turn":
      return self.handle_end_turn()
    raise UnknownMove(f"Unknown move {move_type}")

  def post_handle(self, player_idx, move_type, data):
    # NOTE: use turn_idx here, since it is possible for a player to get to 10 points when it is
    # not their turn (e.g. because someone else's longest road was broken), but the rules say
    # you can only win on YOUR turn. So we check for victory after we have handled the end of
    # the previous turn, in case the next player wins at the start of their turn.
    # TODO: victory points should be configurable.
    if self.player_points(self.turn_idx, visible=False) >= self.victory_points:
      self.handle_victory()

  def _validate_location(self, location, num_entries=2):
    if isinstance(location, (tuple, list)) and len(location) == num_entries:
      return
    raise InvalidMove("location %s should be a tuple of size %s" % (location, num_entries))

  def rename_player(self, player_idx, data):
    _validate_name(self.player_data[player_idx].name, [p.name for p in self.player_data], data)
    self.player_data[player_idx].name = data["name"].strip()

  def handle_victory(self):
    self.game_phase = "victory"

  def handle_end_turn(self):
    if self.game_phase != "main":
      raise InvalidMove("You MUST place your first settlement/roads.")
    self._check_main_phase("end your turn")
    self.end_turn()

  def end_turn(self):
    self.player_data[self.turn_idx].unusable.clear()
    self.played_dev = 0
    self.trade_offer = {}
    self.counter_offers.clear()
    if self.game_phase == "main":
      self.turn_idx += 1
      self.turn_idx = self.turn_idx % len(self.player_data)
      self.turn_phase = "dice"
      self.dice_roll = None
      return
    if self.game_phase == "place1":
      self.turn_phase = "settle"
      if self.turn_idx == len(self.player_data) - 1:
        self.game_phase = "place2"
        return
      self.turn_idx += 1
      return
    if self.game_phase == "place2":
      if self.turn_idx == 0:
        self.game_phase = "main"
        self.turn_phase = "dice"
        return
      self.turn_phase = "settle"
      self.turn_idx -= 1
      return

  def handle_roll_dice(self):
    if self.turn_phase != "dice":
      raise InvalidMove("You cannot roll the dice right now.")
    red = random.randint(1, 6)
    white = random.randint(1, 6)
    self.dice_roll = (red, white)
    if (red + white) == 7:
      self.discard_players = self._get_players_with_too_many_resources()
      if sum(self.discard_players.values()):
        self.turn_phase = "discard"
      else:
        self.turn_phase = "robber"
      return
    to_receive = self.calculate_resource_distribution(self.dice_roll)
    self.distribute_resources(to_receive)

  def handle_robber(self, location, current_player):
    self._validate_location(location)
    if self.turn_phase != "robber":
      if self.turn_phase == "discard":
        raise InvalidMove("Waiting for players to discard.")
      raise InvalidMove("You cannot play the robber right now.")
    if self.tiles.get(tuple(location)) is None:
      raise InvalidMove("Robber would be lost in time and space.")
    if self.robber == TileLocation(*location):
      raise InvalidMove("You must move the robber.")
    if not self.tiles[tuple(location)].is_land:
      raise InvalidMove("Robbers would drown at sea.")
    maybe_robber_location = TileLocation(*location)
    corners = maybe_robber_location.get_corner_locations()
    if not self.rob_at_two:
      for corner in corners:
        maybe_piece = self.pieces.get(corner.as_tuple())
        if maybe_piece:
          if maybe_piece.player != current_player:
            score = self.player_points(maybe_piece.player,visible=True)
            if score <= 2:
              raise InvalidMove("Robbers refuse to rob such poor people.")
    self.robber = TileLocation(*location)
    corners = self.robber.get_corner_locations()
    robbable_players = set([])
    for corner in corners:
      maybe_piece = self.pieces.get(corner.as_tuple())
      if maybe_piece:
        count = self.player_data[maybe_piece.player].resource_card_count()
        if count > 0:
          robbable_players.add(maybe_piece.player)
    robbable_players -= {current_player}
    if len(robbable_players) > 1:
      self.rob_players = list(robbable_players)
      self.turn_phase = "rob"
      return
    elif len(robbable_players) == 1:
      self._rob_player(list(robbable_players)[0], current_player)
    if self.dice_roll is None:
      self.turn_phase = "dice"
    else:
      self.turn_phase = "main"

  def handle_rob(self, rob_player, current_player):
    if self.turn_phase != "rob":
      raise InvalidMove("You cannot rob without playing the robber.")
    if rob_player not in self.rob_players:
      raise InvalidMove("You cannot rob from that player with that robber placement.")
    self._rob_player(rob_player, current_player)
    self.rob_players = []  # Reset after successful rob.
    if self.dice_roll is None:
      self.turn_phase = "dice"
    else:
      self.turn_phase = "main"

  def _rob_player(self, rob_player, current_player):
    all_rsrc_cards = []
    for rsrc in RESOURCES:
      all_rsrc_cards.extend([rsrc] * self.player_data[rob_player].cards[rsrc])
    if len(all_rsrc_cards) <= 0:
      raise InvalidMove("You cannot rob from a player without any resources.")
    chosen_rsrc = random.choice(all_rsrc_cards)
    self.player_data[rob_player].cards[chosen_rsrc] -= 1
    self.player_data[current_player].cards[chosen_rsrc] += 1

  def remaining_resources(self, rsrc):
    return 19 - sum([p.cards[rsrc] for p in self.player_data])

  def _get_players_with_too_many_resources(self):
    return {
        idx: player.resource_card_count() // 2
        for idx, player in enumerate(self.player_data) if player.resource_card_count() >= 8
    }

  # TODO: move into the player class?
  def _check_resources(self, resources, player, action_string):
    errors = []
    for resource, count in resources:
      if self.player_data[player].cards[resource] < count:
        errors.append("%s {%s}" % (count - self.player_data[player].cards[resource], resource))
    if errors:
      raise InvalidMove("You would need an extra %s to %s." % (", ".join(errors), action_string))

  def _remove_resources(self, resources, player, build_type):
    self._check_resources(resources, player, build_type)
    for resource, count in resources:
      self.player_data[player].cards[resource] -= count

  def _check_road_building(self, location, player, road_type):
    left_corner = location.corner_left
    right_corner = location.corner_right
    # Validate that this is an actual edge.
    if location.as_tuple() not in [edge.as_tuple() for edge in left_corner.get_edges()]:
      raise InvalidMove("%s is not a valid edge" % location)
    # Validate that one side of the road is land.
    self._check_edge_type(location, road_type)
    # Validate that this connects to either a settlement or another road.
    for corner in [left_corner, right_corner]:
      # Check whether this corner has one of the player's settlements.
      maybe_piece = self.pieces.get(corner.as_tuple())
      if maybe_piece:
        if maybe_piece.player == player:
          # They have a settlement/city here - they can build a road.
          return
        else:
          # Owned by another player - continue to the next corner.
          continue
      # If no settlement at this corner, check for other roads to this corner.
      other_edges = corner.get_edges()
      for edge in other_edges:
        if edge == location:
          continue
        maybe_road = self.roads.get(edge.as_tuple())
        if maybe_road and maybe_road.player == player and maybe_road.road_type == road_type:
          # They have a road leading here - they can build another road.
          return
    raise InvalidMove(f"{road_type.capitalize()}s must be connected to your {road_type} network.")

  def _check_road_next_to_empty_settlement(self, location, player):
    left_corner = location.corner_left
    right_corner = location.corner_right
    for corner in [left_corner, right_corner]:
      # Check whether this corner has one of the player's settlements.
      piece = self.pieces.get(corner.as_tuple())
      if piece and piece.player == player:
        # They have a settlement/city here - make sure it's not the one that
        # they built before (by checking to see if it has no roads).
        edges = corner.get_edges()
        for edge in edges:
          road = self.roads.get(edge.as_tuple())
          if road and road.player == player:
            # No good - this is the settlement that already has a road.
            raise InvalidMove("You must put your road next to your second settlement.")
        break
    else:
      raise InvalidMove("You must put your road next to your settlement.")

  def _check_main_phase(self, text):
    if self.turn_phase != "main":
      if self.turn_phase == "dice":
        raise InvalidMove("You must roll the dice first.")
      elif self.turn_phase == "robber":
        raise InvalidMove("You must move the robber first.")
      elif self.turn_phase == "discard":
        raise InvalidMove("Waiting for players to discard.")
      else:
        raise InvalidMove("You cannot %s right now." % text)

  def handle_road(self, location, player, road_type, resources):
    self._validate_location(location, num_entries=4)
    # Check that this is the right part of the turn.
    if self.game_phase.startswith("place"):
      if self.turn_phase != "road":
        raise InvalidMove("You must build a settlement first.")
    elif self.turn_phase != "dev_road":
      self._check_main_phase(f"build a {road_type}")
    # Check nothing else is already there.
    if tuple(location) in self.roads:
      raise InvalidMove("There is already a %s there." % self.roads[tuple(location)].road_type)
    # Check that this attaches to their existing network.
    self._check_road_building(EdgeLocation(*location), player, road_type)
    # Check that the player has enough roads left.
    road_count = len([r for r in self.roads.values() if r.player == player and r.road_type == road_type])
    if road_count >= 15:
      raise InvalidMove(f"You have no {road_type}s remaining.")
    # Handle special settlement phase.
    if self.game_phase.startswith("place"):
      self._check_road_next_to_empty_settlement(EdgeLocation(*location), player)
      self.add_road(Road(location, road_type, player))
      self.end_turn()
      return
    if self.turn_phase == "dev_road":
      self.add_road(Road(location, road_type, player))
      self.dev_roads_placed += 1
      # Road building ends if they placed 2 roads or ran out of roads.
      # TODO: replace this with a method to check to see if they have any legal road moves.
      if self.dev_roads_placed == 2 or road_count + 1 >= 15:
        self.dev_roads_placed = 0
        self.turn_phase = "main"
      return
    # Check resources and deduct from player.
    self._remove_resources(resources, player, f"build a {road_type}")

    self.add_road(Road(location, road_type, player))

  def handle_settle(self, location, player):
    self._validate_location(location)
    # Check that this is the right part of the turn.
    if self.game_phase.startswith("place"):
      if self.turn_phase != "settle":
        raise InvalidMove("You already placed your settlement; now you must build a road.")
    else:
      self._check_main_phase("build a settlement")
    # Check nothing else is already there.
    if tuple(location) in self.pieces:
      raise InvalidMove("You cannot settle on top of another player's settlement.")
    for adjacent in CornerLocation(*location).get_adjacent_corners():
      if adjacent.as_tuple() in self.pieces:
        raise InvalidMove("You cannot place a settlement next to existing settlement.")
    # Handle special settlement phase.
    if self.game_phase.startswith("place"):
      self.add_piece(Piece(location[0], location[1], "settlement", player))
      if self.game_phase == "place2":
        self.give_second_resources(player, CornerLocation(*location))
      self.turn_phase = "road"
      return
    # Check connected to one of the player's roads.
    for edge_loc in CornerLocation(*location).get_edges():
      maybe_road = self.roads.get(edge_loc.as_tuple())
      if maybe_road and maybe_road.player == player:
        break
    else:
      raise InvalidMove("You must place your settlement next to one of your roads.")
    # Check player has enough settlements left.
    settle_count = len([p for p in self.pieces.values() if p.player == player and p.piece_type == "settlement"])
    if settle_count >= 5:
      raise InvalidMove("You have no settlements remaining.")
    # Check resources and deduct from player.
    resources = [("rsrc1", 1), ("rsrc2", 1), ("rsrc3", 1), ("rsrc4", 1)]
    self._remove_resources(resources, player, "build a settlement")

    self.add_piece(Piece(location[0], location[1], "settlement", player))

  def _add_player_port(self, location, player):
    """Sets the trade ratios for a player who built a settlement at this location."""
    port_type = self.port_corners.get(location.as_tuple())
    if port_type == "3":
      for rsrc in RESOURCES:
        self.player_data[player].trade_ratios[rsrc] = min(self.player_data[player].trade_ratios[rsrc], 3)
    elif port_type:
      self.player_data[player].trade_ratios[port_type] = min(self.player_data[player].trade_ratios[port_type], 2)

  def handle_city(self, location, player):
    self._validate_location(location)
    # Check that this is the right part of the turn.
    self._check_main_phase("build a city")
    # Check this player already owns a settlement there.
    piece = self.pieces.get(tuple(location))
    if not piece:
      raise InvalidMove("You need to build a settlement there first.")
    if piece.player != player:
      raise InvalidMove("You cannot upgrade another player's %s." % piece.piece_type)
    if piece.piece_type != "settlement":
      raise InvalidMove("You can only upgrade a settlement to a city.")
    # Check player has enough cities left.
    city_count = len([p for p in self.pieces.values() if p.player == player and p.piece_type == "city"])
    if city_count >= 4:
      raise InvalidMove("You have no cities remaining.")
    # Check resources and deduct from player.
    resources = [("rsrc3", 2), ("rsrc5", 3)]
    self._remove_resources(resources, player, "build a city")

    self.pieces[tuple(location)].piece_type = "city"

  def handle_buy_dev(self, player):
    # Check that this is the right part of the turn.
    self._check_main_phase("buy a development card")
    resources = [("rsrc1", 1), ("rsrc3", 1), ("rsrc5", 1)]
    if len(self.dev_cards) < 1:
      raise InvalidMove("There are no development cards left.")
    self._remove_resources(resources, player, "buy a development card")
    self.add_dev_card(player)

  def handle_discard(self, selection, player):
    if self.turn_phase != "discard":
      raise InvalidMove("You cannot discard cards right now.")
    self._validate_selection(selection)
    if not self.discard_players.get(player):
      raise InvalidMove("You do not need to discard any cards.")
    discard_count = sum([selection.get(rsrc, 0) for rsrc in RESOURCES])
    if discard_count != self.discard_players[player]:
      raise InvalidMove("You have %s resource cards and must discard %s." %
                        (self.player_data[player].resource_card_count(),
                         self.discard_players[player]))
    self._remove_resources(selection.items(), player, "discard those cards")
    del self.discard_players[player]
    if sum(self.discard_players.values()) == 0:
      self.turn_phase = "robber"

  def _validate_selection(self, selection):
    """Selection should be a dict of rsrc -> count."""
    if not selection or not isinstance(selection, dict):
      raise InvalidMove("Invalid resource selection.")
    if set(selection.keys()) - set(RESOURCES):
      raise InvalidMove("Invalid resource selection - unknown or untradable resource.")
    if not all([isinstance(value, int) and value >= 0 for value in selection.values()]):
      raise InvalidMove("Invalid resource selection - must be positive integers.")

  def handle_play_dev(self, card_type, resource_selection, player):
    if card_type not in PLAYABLE_DEV_CARDS:
      raise InvalidMove("%s is not a playable development card." % card_type)
    if card_type == "knight":
      if self.turn_phase not in ["dice", "main"]:
        raise InvalidMove("You must play the knight before you roll the dice or during the build/trade part of your turn.")
    else:
      self._check_main_phase("play a development card")
    if self.player_data[player].cards[card_type] < 1:
      raise InvalidMove("You do not have any %s cards." % card_type)
    if self.player_data[player].cards[card_type] - self.player_data[player].unusable[card_type] < 1:
      raise InvalidMove("You cannot play development cards on the turn you buy them.")
    if self.played_dev:
      raise InvalidMove("You cannot play more than one development card per turn.")
    if card_type == "knight":
      self._handle_knight(player)
    elif card_type == "yearofplenty":
      self._handle_year_of_plenty(player, resource_selection)
    elif card_type == "monopoly":
      self._handle_monopoly(player, resource_selection)
    elif card_type == "roadbuilding":
      self._handle_road_building(player)
    else:
      # How would this even happen?
      raise InvalidMove("%s is not a playable development card." % card_type)
    self.player_data[player].cards[card_type] -= 1
    self.played_dev += 1

  def _handle_knight(self, player_idx):
    current_max = max([player.knights_played for player in self.player_data])
    self.player_data[player_idx].knights_played += 1
    if self.player_data[player_idx].knights_played > current_max and current_max >= 2:
      self.largest_army_player = player_idx
    self.turn_phase = "robber"

  def _handle_road_building(self, player):
    # Check that the player has enough roads left.
    road_count = len([r for r in self.roads.values() if r.player == player and r.road_type == "road"])
    if road_count >= 15:
      raise InvalidMove("You have no roads remaining.")
    self.turn_phase = "dev_road"

  def _handle_year_of_plenty(self, player, selection):
    self._validate_selection(selection)
    remaining = {rsrc: self.remaining_resources(rsrc) for rsrc in RESOURCES}
    # TODO: if there is one resource left, do we allow the player to collect just one?
    if sum(remaining.values()) < 2:
      raise InvalidMove("There are no resources left in the bank.")
    if sum(selection.values()) != 2:
      raise InvalidMove("You must request exactly two resources.")
    overdrawn = [rsrc for rsrc in selection if selection[rsrc] > remaining[rsrc]]
    if overdrawn:
      raise InvalidMove("There is not enough {%s} in the bank." % "}, {".join(overdrawn))
    for rsrc, value in selection.items():
      self.player_data[player].cards[rsrc] += value

  def _handle_monopoly(self, player, resource_selection):
    self._validate_selection(resource_selection)
    if len(resource_selection) != 1 or sum(resource_selection.values()) != 1:
      raise InvalidMove("You must choose exactly one resource to monopolize.")
    card_type = list(resource_selection.keys())[0]
    for opponent_idx in range(len(self.player_data)):
      if player == opponent_idx:
        continue
      opp_count = self.player_data[opponent_idx].cards[card_type]
      self.player_data[opponent_idx].cards[card_type] -= opp_count
      self.player_data[player].cards[card_type] += opp_count

  def add_dev_card(self, player):
    card_type = self.dev_cards.pop()
    self.player_data[player].cards[card_type] += 1
    self.player_data[player].unusable[card_type] += 1

  def _validate_trade(self, offer, player):
    """Validates a well-formed trade & that the player has enough resources."""
    if not isinstance(offer, dict) or set(offer.keys()) != set(self.TRADE_SIDES):
      raise RuntimeError("invalid offer format - must be a dict of two sides")
    for side in self.TRADE_SIDES:
      if not isinstance(offer[side], dict):
        raise RuntimeError("invalid offer format - each side must be a dict")
      for rsrc, count in offer[side].items():
        if rsrc not in RESOURCES:
          raise InvalidMove("{%s} is not tradable." % rsrc)
        if not isinstance(count, int) or count < 0:
          raise InvalidMove("You must trade an non-negative integer quantity.")
    for rsrc, count in offer[self.GIVE].items():
      if self.player_data[player].cards[rsrc] < count:
        raise InvalidMove("You do not have enough {%s}." % rsrc)

  def handle_trade_offer(self, offer, player):
    self._check_main_phase("make a trade")
    self._validate_trade(offer, player)
    self.trade_offer = offer
    # TODO: maybe we don't want to actually clear the counter offers?
    self.counter_offers.clear()

  def handle_counter_offer(self, offer, player):
    if self.turn_idx == player:
      raise InvalidMove("You cannot make a counter-offer on your turn.")
    self._check_main_phase("make a counter-offer")
    if offer == 0:  # offer rejection
      self.counter_offers[player] = offer
      return
    self._validate_trade(offer, player)
    self.counter_offers[player] = offer

  def handle_accept_counter(self, counter_offer, counter_player, player):
    if counter_player < 0 or counter_player >= len(self.player_data):
      raise InvalidMove("Invalid player.")
    if counter_player == player:
      raise InvalidMove("You cannot trade with yourself.")
    if not self.counter_offers.get(counter_player):
      raise InvalidMove("That player has not made an offer for you to accept.")
    self._check_main_phase("make a trade")
    my_want = counter_offer[self.GIVE]
    my_give = counter_offer[self.WANT]
    their_want = self.counter_offers[counter_player][self.WANT]
    their_give = self.counter_offers[counter_player][self.GIVE]
    # my_want and my_give are pulled from the message the player sent,
    # their_want and their_give are pulled from saved counter-offers.
    # We validate that they are the same to avoid any scenarios where the player
    # might accept a different offer than the counter-party is giving.
    for rsrc in RESOURCES:
      for trade_dict in [my_want, my_give, their_want, their_give]:
        if trade_dict.get(rsrc) == 0:
          del trade_dict[rsrc]
    if sorted(my_want.items()) != sorted(their_give.items()):
      print("Offers do not match - %s vs %s" % (sorted(my_want.items()), sorted(their_give.items())))
      raise InvalidMove("The player changed their offer.")
    if sorted(my_give.items()) != sorted(their_want.items()):
      print("Offers do not match - %s vs %s" % (sorted(my_give.items()), sorted(their_want.items())))
      raise InvalidMove("The player changed their offer.")

    # Validate that both players have the resources to make the trade.
    self._validate_trade({self.WANT: my_want, self.GIVE: my_give}, player)
    self._validate_trade({self.WANT: their_want, self.GIVE: their_give}, counter_player)

    for rsrc, count in my_give.items():
      self.player_data[player].cards[rsrc] -= count
      self.player_data[counter_player].cards[rsrc] += count
    for rsrc, count in my_want.items():
      self.player_data[player].cards[rsrc] += count
      self.player_data[counter_player].cards[rsrc] -= count

    self.counter_offers.clear()
    # TODO: Do we want to reset the trade offer here?

  def handle_trade_bank(self, offer, player):
    self._check_main_phase("make a trade")
    self._validate_trade(offer, player)
    # Also validate that ratios are correct.
    requested = sum([count for count in offer[self.WANT].values()])
    available = 0
    for rsrc, give in offer[self.GIVE].items():
      if give == 0:
        continue
      ratio = self.player_data[player].trade_ratios[rsrc]
      if give % ratio != 0:
        raise InvalidMove("You must trade {%s} with the bank at a %s:1 ratio." % (rsrc, ratio))
      available += give / ratio
    if available != requested:
      raise InvalidMove("You should receive %s resources, but you requested %s." % (available, requested))
    # Now, make the trade.
    for rsrc, want in offer[self.WANT].items():
      self.player_data[player].cards[rsrc] += want
    for rsrc, give in offer[self.GIVE].items():
      self.player_data[player].cards[rsrc] -= give

  def calculate_resource_distribution(self, dice_roll):
    # Figure out which players are due how many resources.
    to_receive = collections.defaultdict(lambda: collections.defaultdict(int))
    for tile in self.tiles.values():
      if tile.number != sum(dice_roll):
        continue
      if self.robber == tile.location:
        continue
      corner_locations = set([a.as_tuple() for a in tile.location.get_corner_locations()])
      for corner_loc in corner_locations:
        piece = self.pieces.get(corner_loc)
        if piece and piece.piece_type == "settlement":
          to_receive[tile.tile_type][piece.player] += 1
        elif piece and piece.piece_type == "city":
          to_receive[tile.tile_type][piece.player] += 2

    return to_receive

  def distribute_resources(self, to_receive):
    shortage = []
    # Changes the values of to_receive as it iterates through them.
    for rsrc, receive_players in to_receive.items():
      remaining = self.remaining_resources(rsrc)
      # If there are enough resources to go around, no problem.
      if sum(receive_players.values()) <= remaining:
        continue
      # Otherwise, there is a shortage of this resource.
      shortage.append(rsrc)
      # If there is only one player receiving this resource, they receive all of the
      # remaining cards for this resources type.
      if len(receive_players) == 1:
        the_player = list(receive_players.keys())[0]
        receive_players[the_player] = remaining
        continue
      # If there is more than one player receiving this resource, and there is not enough
      # in the supply, then no players receive any of this resource.
      receive_players.clear()

    # Do the actual resource distribution.
    for rsrc, receive_players in to_receive.items():
      for player, count in receive_players.items():
        self.player_data[player].cards[rsrc] += count

    self.turn_phase = "main"
    return shortage

  def give_second_resources(self, player, corner_loc):
    # TODO: handle collecting resources from the second settlement if on a bonus tile.
    tile_locs = set([loc.as_tuple() for loc in corner_loc.get_tiles()])
    for tile_loc in tile_locs:
      tile = self.tiles.get(tile_loc)
      if tile and tile.number:
        self.player_data[player].cards[tile.tile_type] += 1

  def add_tile(self, tile):
    self.tiles[tile.location.as_tuple()] = tile

  def add_port(self, port):
    self.ports[port.location.as_tuple()] = port

  def _add_piece(self, piece):
    self.pieces[piece.location.as_tuple()] = piece

  def add_piece(self, piece):
    self._add_piece(piece)

    self._add_player_port(piece.location, piece.player)

    # Check for breaking an existing longest road.
    # Start by calculating any players with an adjacent road/ship.
    players_to_check = set()
    edges = piece.location.get_edges()
    for edge in edges:
      maybe_road = self.roads.get(edge.as_tuple())
      if maybe_road:
        players_to_check.add(maybe_road.player)

    # Recompute longest road for each of these players.
    for player_idx in players_to_check:
      self.player_data[player_idx].longest_route = self._calculate_longest_road(player_idx)

    # Give longest road to the appropriate player.
    self._update_longest_route_player()

  def _update_longest_route_player(self):
    new_max = max([p.longest_route for p in self.player_data])
    holder_max = None
    if self.longest_route_player is not None:
      holder_max = self.player_data[self.longest_route_player].longest_route

    # If nobody meets the conditions for longest road, nobody takes the card. After this,
    # we may assume that the longest road has at least 5 segments.
    if new_max < 5:
      self.longest_route_player = None
      return

    # If the player with the longest road still has the longest road, they keep the longest
    # road card, even if they are now tied with another player.
    if holder_max == new_max:
      return

    # The previous card holder must now give up the longest road card. We calculate any players
    # that meet the conditions for taking the longest road card.
    eligible = [idx for idx, data in enumerate(self.player_data) if data.longest_route == new_max]
    if len(eligible) == 1:
      self.longest_route_player = eligible[0]
    else:
      self.longest_route_player = None

  def _add_road(self, road):
    self.roads[road.location.as_tuple()] = road

  def add_road(self, road):
    self._add_road(road)

    # Check for increase in longest road, update longest road player if necessary. Also check
    # for decrease in longest road, which can happen if a player moves a ship.
    self.player_data[road.player].longest_route = self._calculate_longest_road(road.player)
    self._update_longest_route_player()

  def _calculate_longest_road(self, player):
    # Get all corners of all roads for this player.
    all_corners = set([])
    for road in self.roads.values():
      if road.player != player:
        continue
      all_corners.add(road.location.corner_left)
      all_corners.add(road.location.corner_right)

    # For each corner, do a DFS and find the depth.
    max_length = 0
    for corner in all_corners:
      seen = set([])
      max_length = max(max_length, self._dfs_depth(player, corner, seen, None))

    return max_length

  def _dfs_depth(self, player, corner, seen_edges, prev_edge):
    # First, use the type of the piece at this corner to set a baseline. If it belongs to
    # another player, the route ends. If it belongs to this player, the next edge in the route
    # may be either a road or a ship. If there is no piece, then the type of the next edge
    # must match the type of the previous edge (except for the first edge in the DFS).
    this_piece = self.pieces.get(corner.as_tuple())
    if prev_edge is None:
      # First road can be anything. Can also be adjacent to another player's settlement.
      valid_types = Road.TYPES
    else:
      if this_piece is None:
        if self.roads.get(prev_edge.as_tuple()) is not None:
          valid_types = [self.roads[prev_edge.as_tuple()].road_type]
        else:
          raise RuntimeError("you screwed it up")
      elif this_piece.player != player:
        return 0
      else:
        valid_types = Road.TYPES

    # Next, get the three corners next to this corner. We can determine an edge from each one,
    # and we will throw away any edges that either do not belong to the player or that we have
    # seen before or that do not match our expected edge type.
    unseen_edges = [edge for edge in corner.get_edges() if edge not in seen_edges]
    valid_edges = []
    for edge in unseen_edges:
      edge_piece = self.roads.get(edge.as_tuple())
      if edge_piece and edge_piece.player == player and edge_piece.road_type in valid_types:
        valid_edges.append(edge)

    max_depth = 0
    for edge in valid_edges:
      other_corner = edge.corner_left if edge.corner_right == corner else edge.corner_right
      seen_edges.add(edge)
      sub_depth = self._dfs_depth(player, other_corner, seen_edges, edge)
      max_depth = max(max_depth, 1 + sub_depth)
      seen_edges.remove(edge)
    return max_depth

  def _init_tiles(self, tile_types, sequence, tile_numbers):
    if len(sequence) != len(tile_types):
      raise RuntimeError("you screwed it up")
    num_idx = 0
    robber_loc = None
    for idx, loc in enumerate(sequence):
      if tile_types[idx] == "norsrc":
        robber_loc = TileLocation(*sequence[idx])
        number = None
      else:
        number = tile_numbers[num_idx]
        num_idx += 1
      self.add_tile(Tile(sequence[idx][0], sequence[idx][1], tile_types[idx], True, number))
    self.robber = robber_loc

  def _init_space(self, space_tiles, rotations):
    if len(space_tiles) != len(rotations):
      raise RuntimeError("you screwed it up")
    for idx, loc in enumerate(space_tiles):
      self.add_tile(Tile(loc[0], loc[1], "space", False, None, rotations[idx]))

  def _compute_edges(self):
    # Go back and figure out which ones are corners.
    # TODO: unit test this function.
    for location in self.tiles:
      locs = TileLocation(location[0], location[1]).get_adjacent_tiles()
      exists = [loc.as_tuple() in self.tiles for loc in locs]
      tile_rotation = self.tiles[location].rotation
      if exists.count(True) > 4:
        self.tiles[location].variant = ""
      elif exists.count(True) == 3:
        self.tiles[location].variant = "corner"
      else:
        # Takes advantage of the return order of get_adjacent_tiles.
        upper_left = locs[(tile_rotation+2)%6].as_tuple()
        if upper_left in self.tiles:
          self.tiles[location].variant = "edgeleft"
        else:
          self.tiles[location].variant = "edgeright"

  def _create_port_every_other_tile(self, space_tiles, rotations, ports):
    for idx, loc in enumerate(space_tiles):
      if idx % 2 == 1:
        port_type = ports[idx//2]
        self.add_port(Port(loc[0], loc[1], port_type, rotations[idx]))

  def _compute_coast(self):
    for location, tile_data in self.tiles.items():
      if tile_data.is_land:
        continue
      locs = TileLocation(location[0], location[1]).get_adjacent_tiles()
      exists = [loc.as_tuple() in self.tiles for loc in locs]
      lands = [idx for idx, loc in enumerate(locs) if exists[idx] and self.tiles[loc.as_tuple()].is_land]
      self.tiles[location].land_rotations = lands

  def _init_dev_cards(self):
    dev_cards = ["knight"] * 14 + ["monopoly"] * 2 + ["roadbuilding"] * 2 + ["yearofplenty"] * 2
    dev_cards.extend(VICTORY_CARDS)
    random.shuffle(dev_cards)
    self.dev_cards = dev_cards

  def _compute_ports(self):
    for port in self.ports.values():
      rotation = (port.rotation + 6) % 6
      if rotation == 0:
        port_corners = [port.location.get_lower_left_corner(), port.location.get_lower_right_corner()]
      if rotation == 1:
        port_corners = [port.location.get_lower_left_corner(), port.location.get_left_corner()]
      if rotation == 2:
        port_corners = [port.location.get_upper_left_corner(), port.location.get_left_corner()]
      if rotation == 3:
        port_corners = [port.location.get_upper_left_corner(), port.location.get_upper_right_corner()]
      if rotation == 4:
        port_corners = [port.location.get_upper_right_corner(), port.location.get_right_corner()]
      if rotation == 5:
        port_corners = [port.location.get_lower_right_corner(), port.location.get_right_corner()]
      for corner in port_corners:
        self.port_corners[corner.as_tuple()] = port.port_type

  def _check_edge_type(self, edge_location, road_type):
    edge_type = self._get_edge_type(edge_location)
    if edge_type != road_type:
      raise InvalidMove("Your road must be between two tiles, one of which must be land.")

  def _get_edge_type(self, edge_location):
    # TODO: code duplication?
    tile_locations = edge_location.get_adjacent_tiles()
    if len(tile_locations) != 2:
      return None
    if not all([loc.as_tuple() in self.tiles for loc in tile_locations]):
      return None
    if not any([self.tiles[loc.as_tuple()].is_land for loc in tile_locations]):
      return None
    return "road"

  def _shuffle_ports(self):
    port_types = [port.port_type for port in self.ports.values()]
    random.shuffle(port_types)
    for idx, port in enumerate(self.ports.values()):
      port.port_type = port_types[idx]

  @classmethod
  def get_options(cls):
    friendly_robber = GameOption(name="Friendly Robber", default=False)
    victory = GameOption(name="Victory Points", default=10, choices=[8, 9, 10, 11, 12, 13, 14, 15])
    return collections.OrderedDict([
      ("Friendly Robber", friendly_robber), ("Victory Points", victory)])

  def init(self, options):
    self.rob_at_two = not options.get("Friendly Robber")
    self.victory_points = int(options.get("Victory Points", 10))


class RandomMap(CatanState):

  def init(self, options):
    super(RandomMap, self).init(options)
    tile_types = [
      "rsrc1", "rsrc1", "rsrc1", "rsrc1",
      "rsrc2", "rsrc2", "rsrc2", "rsrc2",
      "rsrc3", "rsrc3", "rsrc3", "rsrc3",
      "rsrc4", "rsrc4", "rsrc4",
      "rsrc5", "rsrc5", "rsrc5",
      "norsrc"]
    random.shuffle(tile_types)
    self._init_tiles(tile_types, TILE_SEQUENCE, TILE_NUMBERS)
    ports = ["3", "3", "3", "3", "rsrc1", "rsrc2", "rsrc3", "rsrc4", "rsrc5"]
    self._init_space(SPACE_TILE_SEQUENCE, SPACE_TILE_ROTATIONS)
    self._create_port_every_other_tile(SPACE_TILE_SEQUENCE, SPACE_TILE_ROTATIONS, ports)
    self._shuffle_ports()
    self._compute_coast()
    self._compute_edges()
    self._compute_ports()
    self._init_dev_cards()


class BeginnerMap(CatanState):

  def init(self, options):
    super(BeginnerMap, self).init(options)
    tile_types = [
        "rsrc5", "rsrc3", "rsrc2", "rsrc5", "rsrc3", "rsrc1", "rsrc3", "rsrc1", "rsrc2", "rsrc4",
        "norsrc", "rsrc4", "rsrc1", "rsrc1", "rsrc2", "rsrc4", "rsrc5", "rsrc2", "rsrc3"]
    self._init_tiles(tile_types, TILE_SEQUENCE, TILE_NUMBERS)
    ports = ["rsrc2", "rsrc4", "3", "3", "rsrc1", "3", "rsrc5", "rsrc3", "3"]
    self._init_space(SPACE_TILE_SEQUENCE, SPACE_TILE_ROTATIONS)
    self._create_port_every_other_tile(SPACE_TILE_SEQUENCE, SPACE_TILE_ROTATIONS, ports)
    self._compute_coast()
    self._compute_edges()
    self._compute_ports()
    self._init_dev_cards()

  @classmethod
  def get_options(cls):
    options = super(BeginnerMap, cls).get_options()
    options["Friendly Robber"].default = True
    return options


class TestMap(CatanState):

  def init(self, options):
    super(TestMap, self).init(options)
    tile_types = ["rsrc5", "rsrc3", "rsrc1", "rsrc4"]
    self._init_tiles(tile_types, [(2, 3), (4, 2), (2, 5), (4, 4)], [6, 9, 9, 5])
    space_seq = [(2, 1), (4, 0), (6, 1), (6, 3), (6, 5), (4, 6), (2, 7), (0, 6), (0, 4), (0, 2)]
    rotations = [0, 0, 1, 1, 3, 3, -2, -2, -1, -1]
    ports = ["3", "rsrc1", "3", "rsrc3", "rsrc2"]
    self._init_space(space_seq, rotations)
    self._create_port_every_other_tile(space_seq, rotations, ports)
    self._compute_coast()
    self._compute_edges()
    self._compute_ports()
    self._init_dev_cards()


class DebugRules(object):

  def __init__(self, *args, **kwargs):
    super(DebugRules, self).__init__(*args, **kwargs)
    self.debug = True
    self.next_die_roll = None

  @classmethod
  def computed_attrs(cls):
    return super(DebugRules, cls).computed_attrs() | {"debug", "next_die_roll"}

  def debug_roll_dice(self, count):
    for i in range(count):
      red = random.randint(1, 6)
      white = random.randint(1, 6)
      dist = self.calculate_resource_distribution((red, white))
      self.distribute_resources(dist)

  def debug_force_dice(self, value):
    self.next_die_roll = value

  def handle_roll_dice(self):
    if self.next_die_roll is not None:
      with mock.patch("random.randint") as randint:
        randint.side_effect=[self.next_die_roll // 2, (self.next_die_roll+1) // 2]
        super(DebugRules, self).handle_roll_dice()
      self.next_die_roll = None
      return
    super(DebugRules, self).handle_roll_dice()


class Seafarers(CatanState):

  def __init__(self, *args, **kwargs):
    super(Seafarers, self).__init__(*args, **kwargs)
    self.built_this_turn = []
    self.ships_moved = 0
    self.corners_to_islands = {}  # Map of corner to island (canonical corner location).
    self.home_corners = collections.defaultdict(list)
    self.foreign_landings = collections.defaultdict(list)
    self.foreign_island_points = 2
    self.shortage_resources = []
    self.collect_idx = None
    self.collect_counts = collections.defaultdict(int)
    self.placement_islands = None

  @classmethod
  def parse_json(cls, gamedata):
    game = super(Seafarers, cls).parse_json(gamedata)
    game.built_this_turn = [tuple(loc) for loc in gamedata["built_this_turn"]]
    game._compute_contiguous_islands()
    # When loading json, these islands get turned into lists. Turn them into tuples instead.
    for attr in ["home_corners", "foreign_landings"]:
      mapping = getattr(game, attr)
      for idx, corner_list in mapping.items():
        for corner in corner_list:
          assert game.pieces[tuple(corner)].player == idx
      mapping.update({
        idx: [tuple(corner) for corner in corner_list] for idx, corner_list in mapping.items()
      })
    # Same idea for placement_islands, except it's a list.
    if game.placement_islands is not None:
      game.placement_islands = [tuple(corner) for corner in game.placement_islands]
    return game

  def json_for_player(self):
    data = super(Seafarers, self).json_for_player()
    data["landings"] = []
    for idx, corner_list in self.foreign_landings.items():
      data["landings"].extend([{"location": corner, "player": idx} for corner in corner_list])
    return data

  @classmethod
  def hidden_attrs(cls):
    hidden = {
        "built_this_turn", "ships_moved", "home_corners", "foreign_landings", "placement_islands"}
    return super(Seafarers, cls).hidden_attrs() | hidden

  @classmethod
  def indexed_attrs(cls):
    indexed = {"home_corners", "foreign_landings", "collect_counts"}
    return super(Seafarers, cls).indexed_attrs() | indexed

  @classmethod
  def computed_attrs(cls):
    computed = {"corners_to_islands", "foreign_island_points"}
    return super(Seafarers, cls).computed_attrs() | computed

  @classmethod
  def get_options(cls):
    options = super(Seafarers, cls).get_options()
    options["Seafarers"] = GameOption(name="Seafarers", forced=True, default=True)
    return options

  def calculate_resource_distribution(self, dice_roll):
    to_receive = super(Seafarers, self).calculate_resource_distribution(dice_roll)
    if "anyrsrc" in to_receive:
      self.collect_counts = to_receive.pop("anyrsrc")
    return to_receive

  def distribute_resources(self, to_receive):
    self.shortage_resources = super(Seafarers, self).distribute_resources(to_receive)
    self.next_collect_player()
    return self.shortage_resources

  def next_collect_player(self):
    # By default, no player is collecting resources.
    self.collect_idx = None
    self.turn_phase = "main"
    total_collect = sum(self.collect_counts.values())
    if not total_collect:
      return
    available = {}
    for rsrc in set(RESOURCES) - set(self.shortage_resources):
      available[rsrc] = self.remaining_resources(rsrc)
    if sum(available.values()) <= 0:
      self.collect_counts.clear()
      return
    min_available = min(available.values()) # The minimum available of any collectible resource.
    if min_available >= total_collect:
      # Special case: if there are enough resources available such that no player can deplete
      # the bank, all players may collect resources at the same time.
      self.turn_phase = "collect"
      self.collect_idx = None
      return
    num_players = len(self.player_data)
    collect_players = [idx for idx, count in self.collect_counts.items() if count]
    collect_players.sort(key=lambda idx: (idx - self.turn_idx + num_players) % num_players)
    self.collect_idx = collect_players[0]
    self.turn_phase = "collect"
    if sum(available.values()) < self.collect_counts[self.collect_idx]:
      # If there's not enough left in the bank, the player collects everything that remains.
      self.collect_counts[self.collect_idx] = sum(available.values())

  def end_turn(self):
    super(Seafarers, self).end_turn()
    self.built_this_turn.clear()
    self.ships_moved = 0
    self.shortage_resources.clear()

  def check_turn_okay(self, player_idx, move_type, data):
    if self.turn_phase == "collect" and move_type == "collect":
      if not self.collect_counts.get(player_idx):
        raise NotYourTurn("You are not eligible to collect any resources.")
      if self.collect_idx is not None and self.collect_idx != player_idx:
        raise NotYourTurn("Another player must collect resources before you.")
      return
    super(Seafarers, self).check_turn_okay(player_idx, move_type, data)

  def _check_main_phase(self, text):
    if self.turn_phase == "collect":
      if not self.collect_counts.get(player_idx):
        raise NotYourTurn("Waiting for players to collect resources.")
      else:
        raise InvalidMove("You must collect your resources first.")
    super(Seafarers, self)._check_main_phase(text)

  def inner_handle(self, player_idx, move_type, data):
    if move_type == "ship":
      self.handle_road(data.get("location"), player_idx, "ship", [("rsrc1", 1), ("rsrc2", 1)])
      self.built_this_turn.append(tuple(data.get("location")))
      return
    if move_type == "move_ship":
      return self.handle_move_ship(data.get("from"), data.get("to"), player_idx)
    if move_type == "collect":
      return self.handle_collect(player_idx, data.get("selection"))
    return super(Seafarers, self).inner_handle(player_idx, move_type, data)

  def handle_collect(self, player_idx, selection):
    self._validate_selection(selection)
    if sum(selection.values()) != self.collect_counts[player_idx]:
      raise InvalidMove("You must select %s resources." % self.collect_counts[player_idx])
    if selection.keys() & set(self.shortage_resources):
      raise InvalidMove("There is a shortage of {%s}; you cannot collect any." %
          ("}, {".join(self.shortage_resources)))
    # TODO: dedup with code from year of plenty
    overdrawn = [rsrc for rsrc in selection if selection[rsrc] > self.remaining_resources(rsrc)]
    if overdrawn:
      raise InvalidMove("There is not enough {%s} in the bank." % "}, {".join(overdrawn))
    for rsrc, value in selection.items():
      self.player_data[player_idx].cards[rsrc] += value
    del self.collect_counts[player_idx]
    self.next_collect_player()

  def handle_move_ship(self, from_location, to_location, player_idx):
    self._validate_location(from_location, num_entries=4)
    self._validate_location(to_location, num_entries=4)
    # Check that this is the right part of the turn.
    self._check_main_phase("move a ship")
    if self.ships_moved:
      raise InvalidMove("You have already moved a ship this turn.")
    maybe_ship = self.roads.get(tuple(from_location))
    if not maybe_ship:
      raise InvalidMove("You do not have a ship there.")
    if maybe_ship.road_type != "ship":
      raise InvalidMove("You may only move ships.")
    if maybe_ship.player != player_idx:
      raise InvalidMove("You may only move your ships.")
    if maybe_ship.closed:
      raise InvalidMove("You may not move a ship that connects two of your settlements.")
    if not maybe_ship.movable:
      raise InvalidMove("You must move a ship at the end of one of your shipping routes.")
    if tuple(from_location) in self.built_this_turn:
      raise InvalidMove("You may not move a ship that you built this turn.")
    maybe_dest = self.roads.get(tuple(to_location))
    if maybe_dest:
      raise InvalidMove(f"There is already a {maybe_dest.road_type} at that destination.")

    # Check that this attaches to their existing network, without the original ship.
    # To do this, remove the old ship first, but restore it if any exception is thrown.
    old_ship = self.roads.pop(tuple(from_location))
    old_source = old_ship.source
    try:
      self._check_road_building(EdgeLocation(*to_location), player_idx, "ship")
      self.add_road(Road(to_location, "ship", player_idx))
    except:
      self.roads[old_ship.location.as_tuple()] = old_ship
      raise

    # add_road will automatically recalculate from the new source, but we must still recalculate
    # ships' movable status from the old source in case the two locations are disconnected.
    self.recalculate_ships(old_source, player_idx)
    self.ships_moved = 1

  def add_road(self, road):
    if road.road_type == "ship":
      road.source = self.get_ship_source(road.location, road.player)
    super(Seafarers, self).add_road(road)
    if road.road_type == "ship":
      self.recalculate_ships(road.source, road.player)

  def add_piece(self, piece):
    if self.game_phase.startswith("place") and self.placement_islands is not None:
      canonical_corner = self.corners_to_islands.get(piece.location.as_tuple())
      if canonical_corner not in self.placement_islands:
        raise InvalidMove("You cannot place your first settlements in that area.")
    super(Seafarers, self).add_piece(piece)
    if piece.piece_type == "settlement":
      self.recalculate_ships(piece.location, piece.player)
    if self.game_phase.startswith("place"):
      self.home_corners[piece.player].append(piece.location.as_tuple())
    else:
      home_settled = [self.corners_to_islands[loc] for loc in self.home_corners[piece.player]]
      foreign_landed = [self.corners_to_islands[loc] for loc in self.foreign_landings[piece.player]]
      current_island = self.corners_to_islands[piece.location.as_tuple()]
      if current_island not in home_settled + foreign_landed:
        self.foreign_landings[piece.player].append(piece.location.as_tuple())

  def get_ship_source(self, location, player_idx):
    edges = []
    for corner in [location.corner_left, location.corner_right]:
      maybe_piece = self.pieces.get(corner.as_tuple())
      if maybe_piece and maybe_piece.player == player_idx:
        return maybe_piece.location
      edges.extend(corner.get_edges())
    for edge in edges:
      if edge == location:
        continue
      maybe_road = self.roads.get(edge.as_tuple())
      if maybe_road and maybe_road.player == player_idx and maybe_road.road_type == "ship":
        return maybe_road.source
    raise InvalidMove("Ships must be connected to your ship network.")

  def recalculate_ships(self, source, player_idx):
    self._ship_dfs_helper(source, player_idx, [], set(), source, None)

  def _ship_dfs_helper(self, source, player_idx, path, seen, corner, prev):
    seen.add(corner.as_tuple())
    edges = corner.get_edges()
    outgoing_edges = []

    # First, calculate all the outgoing edges.
    for edge in edges:
      # This is the edge we just walked down, ignore it.
      if edge.as_tuple() == prev:
        continue
      other_corner = edge.corner_left if edge.corner_right == corner else edge.corner_right
      # If this edge does not have a ship on it, skip it.
      maybe_ship = self.roads.get(edge.as_tuple())
      if not maybe_ship or maybe_ship.road_type != "ship":
        continue
      # Now we know there is a ship from corner to other_corner.
      outgoing_edges.append((edge, other_corner))

    # Then, mark this ship as either movable or unmovable based on number of outgoing edges.
    if path:  # Skipped for the very first corner, since there is no previous edge.
      if len(outgoing_edges) == 0:
        self.roads[path[-1]].movable = True
      else:
        self.roads[path[-1]].movable = False

    # Lastly, continue the DFS. Order matters: this may mark some ships as movable that were
    # previous considered unmovable, overriding that decision (because of cycles).
    for edge, other_corner in outgoing_edges:
      if other_corner == source:
        # Here, we have circled back around to the start. We must mark the two edges at the
        # beginning and end of the path as movable. We do not touch the rest.
        self.roads[path[0]].movable = True
        self.roads[edge.as_tuple()].movable = True
        continue
      if other_corner.as_tuple() in seen:
        # Here, we have created a loop. Every ship on this loop may be movable.
        start_idx = None
        for idx, rloc in reversed(list(enumerate(path))):
          if other_corner.as_tuple() in [rloc[:2], rloc[2:]]:
            start_idx = idx
            break
        else:
          raise RuntimeError("What happened here? This shouldn't be physically possible.")
        for idx in range(start_idx, len(path)):
          self.roads[path[idx]].movable = True
        self.roads[edge.as_tuple()].movable = True
        continue
      maybe_piece = self.pieces.get(other_corner.as_tuple())
      if maybe_piece and maybe_piece.player == player_idx:
        # Here, we know that there is a shipping route from one of the player's settlements to
        # another. Every ship on this shipping route is considered closed.
        for rloc in path + [edge.as_tuple()]:
          self.roads[rloc].closed = True
      # Now we know this ship does not create a loop, so we continue to explore the far corner.
      path.append(edge.as_tuple())
      self._ship_dfs_helper(source, player_idx, path, seen, other_corner, edge.as_tuple())
      path.pop()
    seen.remove(corner.as_tuple())

  def _check_edge_type(self, edge_location, road_type):
    edge_type = self._get_edge_type(edge_location)
    if edge_type is None:
      raise InvalidMove(f"Your {road_type} must be between two tiles.")
    if edge_type == road_type or edge_type.startswith("coast"):
      return
    if road_type == "road":
      raise InvalidMove("Your road must be between two tiles, one of which must be land.")
    if road_type == "ship":
      raise InvalidMove("Your ship must be between two tiles, one of which must be water.")
    raise InvalidInput(f"Unknown road type {road_type}")

  def _get_edge_type(self, edge_location):
    # First verify that there are tiles on both sides of this edge.
    tile_locations = edge_location.get_adjacent_tiles()
    if len(tile_locations) != 2:
      return None
    if not all([loc.as_tuple() in self.tiles for loc in tile_locations]):
      return None

    # If there is a road/ship here, just return the type of that road/ship.
    if self.roads.get(edge_location.as_tuple()) is not None:
      return self.roads[edge_location.as_tuple()].road_type

    # Then, return based on how many of the two tiles are land.
    are_lands = [self.tiles[loc.as_tuple()].is_land for loc in tile_locations]
    if all(are_lands):
      return "road"
    if not any(are_lands):
      return "ship"
    # For the coast, it matters whether the sea is on top or on bottom.
    tile_locations.sort(key=lambda loc: loc.y)
    if self.tiles[tile_locations[0].as_tuple()].is_land:
      return "coastdown"
    return "coastup"

  def init(self, options):
    if len(self.player_data) < 3:
      raise InvalidPlayer("Must be played with at least 3 players.")
    if len(self.player_data) > 4:
      raise InvalidPlayer("Cannot be played with more than 4 players.")
    super(Seafarers, self).init(options)

  def _is_connecting_tile(self, tile):
    return tile.is_land

  def _compute_contiguous_islands(self):
    # Group the corners together into sets that each represent an island.
    seen_tiles = set()
    islands = []
    for location, tile in self.tiles.items():
      if location in seen_tiles:
        continue
      if not self._is_connecting_tile(tile):
        continue
      seen_tiles.add(location)
      islands.append(set())
      for corner_loc in tile.location.get_corner_locations():
        islands[-1].add(corner_loc.as_tuple())
      loc_stack = []
      loc_stack.extend([loc.as_tuple() for loc in tile.location.get_adjacent_tiles()])
      while(loc_stack):
        next_loc = loc_stack.pop()
        if next_loc in seen_tiles:
          continue
        if next_loc not in self.tiles:
          continue
        if not self._is_connecting_tile(self.tiles[next_loc]):
          continue
        seen_tiles.add(next_loc)
        loc = TileLocation(*next_loc)
        for corner_loc in loc.get_corner_locations():
          islands[-1].add(corner_loc.as_tuple())
        loc_stack.extend([x.as_tuple() for x in loc.get_adjacent_tiles()])

    # Convert a group of sets into a map of corner -> canonical corner.
    for corner_set in islands:
      canonical_corner = min(corner_set)
      for corner in corner_set:
        self.corners_to_islands[corner] = canonical_corner

  def player_points(self, idx, visible):
    points = super(Seafarers, self).player_points(idx, visible)
    return points + len(self.foreign_landings[idx]) * self.foreign_island_points

  def load_file(self, filename):
    with open(filename) as data:
      json_data = json.load(data)
      self.parse_tiles(json_data["tiles"])
      self.parse_ports(json_data["ports"])
    self._compute_coast()
    self._compute_ports()


class SeafarerShores(Seafarers):

  def init(self, options):
    super(SeafarerShores, self).init(options)
    if len(self.player_data) == 3:
      self.load_file("shores3.json")
      self.robber = TileLocation(12 ,2)
      self.pirate = TileLocation(6, 11)
    elif len(self.player_data) == 4:
      self.load_file("shores4.json")
      self.robber = TileLocation(4, 4)
      self.pirate = TileLocation(6, 13)
      self._shuffle_ports()
    else:
      raise InvalidPlayer("Must have 3 or 4 players.")
    self._compute_contiguous_islands()
    self._compute_edges()
    self._init_dev_cards()
    self.placement_islands = [self.corners_to_islands[(2, 1)]]

  @classmethod
  def get_options(cls):
    options = super(SeafarerShores, cls).get_options()
    options["Victory Points"].default = 14
    return options


class SeafarerIslands(Seafarers):

  def init(self, options):
    super(SeafarerIslands, self).init(options)
    if len(self.player_data) == 3:
      self.load_file("islands3.json")
      self.robber = TileLocation(0 ,2)
      self.pirate = TileLocation(6, 5)
    elif len(self.player_data) == 4:
      self.load_file("islands4.json")
      self.robber = TileLocation(10, 7)
      self.pirate = TileLocation(6, 11)
    else:
      raise InvalidPlayer("Must have 3 or 4 players.")
    self._compute_contiguous_islands()
    self._compute_edges()
    self._init_dev_cards()

  @classmethod
  def get_options(cls):
    options = super(SeafarerIslands, cls).get_options()
    options["Victory Points"].default = 13
    return options


class SeafarerDesert(Seafarers):

  def init(self, options):
    super(SeafarerDesert, self).init(options)
    if len(self.player_data) == 3:
      self.load_file("desert3.json")
      self.robber = TileLocation(10 ,3)
      self.pirate = TileLocation(6, 11)
    elif len(self.player_data) == 4:
      self.load_file("desert4.json")
      self.robber = TileLocation(10, 3)
      self.pirate = TileLocation(6, 13)
    else:
      raise InvalidPlayer("Must have 3 or 4 players.")
    self._compute_contiguous_islands()
    self._compute_edges()
    self._init_dev_cards()
    self.placement_islands = [self.corners_to_islands[(2, 1)]]

  def _is_connecting_tile(self, tile):
    return tile.number

  @classmethod
  def get_options(cls):
    options = super(SeafarerDesert, cls).get_options()
    options["Victory Points"].default = 14
    return options


class SeafarerFog(Seafarers):
  pass


class MapMaker(CatanState):

  def init(self, options):
    self.add_tile(Tile(2, 1, "space", False, None))
    self.game_phase = "main"
    self.turn_phase = "main"
    self.player_data[0].name = "tiles"
    self.player_data[1].name = "numbers/ports"
    if len(self.player_data) > 2:
      self.player_data[2].name = "rotations"

  def handle(self, player_idx, data):
    if data["type"] not in ["robber", "end_turn"]:
      raise InvalidMove("This is the mapmaker. You can only change tiles.")
    if data["type"] == "end_turn":
      self.turn_idx = (self.turn_idx + 1) % len(self.player_data)
      return
    loc = TileLocation(*data["location"])
    if self.turn_idx == 1 and self.tiles[loc.as_tuple()].is_land:
      # Numbers
      num = self.tiles[loc.as_tuple()].number
      if num is None:
        num = 2
      elif num == 12:
        num = None
      else:
        num += 1
      self.tiles[loc.as_tuple()].number = num
      return
    elif self.turn_idx == 1:
      # Ports
      port_order = RESOURCES + ["3"]
      maybe_port = self.ports.get(loc.as_tuple())
      if not maybe_port:
        self.add_port(Port(loc.x, loc.y, "rsrc1", 0))
        return
      port_idx = port_order.index(maybe_port.port_type)
      if port_idx + 1 == len(port_order):
        del self.ports[loc.as_tuple()]
        return
      self.ports[loc.as_tuple()].port_type = port_order[port_idx + 1]
      return
    if self.turn_idx == 2:
      # Rotation
      self.tiles[loc.as_tuple()].rotation += 1
      self.tiles[loc.as_tuple()].rotation %= 6
      if loc.as_tuple() in self.ports:
        self.ports[loc.as_tuple()].rotation += 1
        self.ports[loc.as_tuple()].rotation %= 6
      return
    # Change tile types or add tiles.
    tile_order = ["space"] + RESOURCES + ["anyrsrc", "norsrc"]
    idx = tile_order.index(self.tiles[loc.as_tuple()].tile_type)
    new_type = tile_order[(idx+1) % len(tile_order)]
    self.tiles[loc.as_tuple()].tile_type = new_type
    if new_type == "norsrc":
      self.tiles[loc.as_tuple()].is_land = True
      self.tiles[loc.as_tuple()].number = None
    elif new_type != "space":
      self.tiles[loc.as_tuple()].is_land = True
      if self.tiles[loc.as_tuple()].number is None:
        self.tiles[loc.as_tuple()].number = 2
    else:
      self.tiles[loc.as_tuple()].is_land = False
      self.tiles[loc.as_tuple()].number = None
    for location in loc.get_adjacent_tiles():
      if location.as_tuple() not in self.tiles:
        self.add_tile(Tile(location.x, location.y, "space", False, None))


class CatanGame(BaseGame):

  # The order of this dictionary determines the method resolution order of the created class.
  SCENARIOS = collections.OrderedDict([
      ("Random Map", RandomMap),
      ("Beginner's Map", BeginnerMap),
      ("Test Map", TestMap),
      ("Heading for New Shores", SeafarerShores),
      ("The Four Islands", SeafarerIslands),
      ("Through the Desert", SeafarerDesert),
      ("The Fog Islands", SeafarerFog),
      ("Map Maker", MapMaker),
  ])
  RULES = collections.OrderedDict([
      ("Debug", DebugRules),
  ])

  def __init__(self):
    self.game = None
    self.scenario = list(self.SCENARIOS.keys())[0]
    self.rules = set()
    self.game_class = self.get_game_class({"Scenario": self.scenario})
    self.choices = {}
    self.connected = set()
    self.host = None
    # player_sessions starts as a map of session to CatanPlayer. once the game
    # starts, it becomes a map of session to player_index. TODO: cleanup.
    self.player_sessions = collections.OrderedDict()

  def game_url(self, game_id):
    return f"/catan.html?game_id={game_id}"

  def game_status(self):
    if self.game is None:
      return "unstarted catan game (%s players)" % len(self.player_sessions)
    return self.game.game_status()

  def post_urls(self):
    # TODO: do we want to continue to delegate to individual rulesets?
    if self.game is not None and getattr(self.game, "debug", False):
      return ["/roll_dice", "/force_dice"]
    return []

  def handle_post(self, http_handler, path, args, data):
    if self.game is None:
      http_handler.send_error(HTTPStatus.BAD_REQUEST.value, "Game has not started")
      return
    if getattr(self.game, "debug", False):
      if path == "/roll_dice":
        try:
          count = int(args["count"][0])
        except:
          count = 1
        self.game.debug_roll_dice(count)
      elif path == "/force_dice":
        try:
          value = abs(int(args["value"][0]))
        except:
          http_handler.send_error(HTTPStatus.BAD_REQUEST.value, "Missing or invalid value")
          return
        self.game.debug_force_dice(value)
      http_handler.send_response(HTTPStatus.NO_CONTENT.value)
      http_handler.end_headers()
      return
    super(CatanGame, self).handle_post(http_handler, path, args, data)

  @classmethod
  def parse_json(cls, json_str):
    gamedata = json.loads(json_str)
    if not gamedata:
      return cls()
    game = cls()
    game.scenario = gamedata.pop("scenario")
    if game.scenario not in cls.SCENARIOS:
      raise InvalidMove("Unknown scenario %s" % game.scenario)
    game.rules = set(gamedata.pop("rules"))
    if game.rules - cls.RULES.keys():
      raise InvalidMove("Unknown rules: %s" % ", ".join(game.rules - cls.RULES.keys()))
    chosen = {"Scenario": game.scenario}
    chosen.update({rule: True for rule in game.rules})
    game.game_class = cls.get_game_class(chosen)
    player_sessions = gamedata.pop("player_sessions")

    game_state = game.game_class.parse_json(gamedata)
    game.game = game_state
    game.player_sessions.update(player_sessions)
    return game

  def json_str(self):
    if self.game is None:
      return "{}"
    output = self.game.json_repr()
    output["player_sessions"] = dict(self.player_sessions)
    output["scenario"] = self.scenario
    output["rules"] = list(self.rules)
    return json.dumps(output, cls=CustomEncoder)

  def for_player(self, session):
    if self.game is None:
      player_idx = None
      if session in self.player_sessions:
        player_idx = list(self.player_sessions.keys()).index(session)
      # TODO: update the javascript to handle undefined values for all of the attributes of
      # the state object that we don't have before the game starts.
      data = self.game_class().for_player(None)
      data.update({
        "type": "game_state",
        "host": self.host == session,
        "you": player_idx,
        "started": False,
        "player_data": [player.json_for_player(False) for player in self.player_sessions.values()],
      })

      options = self.game_class.get_options()
      for rule in self.RULES:
        options[rule] = GameOption(name=rule, default=False, value=rule in self.rules)
      options["Scenario"] = GameOption(
          name="Scenario", default=list(self.SCENARIOS.keys())[0],
          choices=list(self.SCENARIOS.keys()), value=self.scenario,
      )
      for name, option in options.items():
        if name in self.choices:
          option.value = self.choices[name]
      data["options"] = list(options.values())

      return json.dumps(data, cls=CustomEncoder)

    output = self.game.for_player(self.player_sessions.get(session))
    output["started"] = True
    is_connected = {idx: sess in self.connected for sess, idx in self.player_sessions.items()}
    for idx in range(len(output["player_data"])):
      output["player_data"][idx]["disconnected"] = not is_connected.get(idx, False)
    return json.dumps(output, cls=CustomEncoder)

  def connect_user(self, session):
    self.connected.add(session)
    if self.game is not None:
      return
    if self.host is None:
      self.host = session

  def disconnect_user(self, session):
    self.connected.remove(session)
    if self.game is not None:
      return
    # Only delete from player sessions if the game hasn't started yet.
    if session in self.player_sessions:
      del self.player_sessions[session]
    if self.host == session:
      if not self.connected:
        self.host = None
      else:
        self.host = list(self.connected)[0]

  def handle(self, session, data):
    if not isinstance(data, dict):
      raise InvalidMove("Data must be a dictionary.")
    if data.get("type") == "join":
      return self.handle_join(session, data)
    if data.get("type") == "start":
      return self.handle_start(session, data)
    if data.get("type") == "takeover":
      return self.handle_takeover(session, data)
    if data.get("type") == "options":
      return self.handle_select_option(session, data)
    if self.game is None:
      raise InvalidMove("The game has not been started.")
    if self.player_sessions.get(session) is None:
      raise InvalidPlayer("Unknown player")
    return self.game.handle(self.player_sessions[session], data)

  def handle_join(self, session, data):
    if self.game is not None:
      raise InvalidPlayer("The game has already started.")
    if session in self.player_sessions:
      raise InvalidPlayer("You have already joined the game.")
    _validate_name(None, [player.name for player in self.player_sessions.values()], data)

    if len(self.player_sessions) >= 4:
      raise TooManyPlayers("There are no open slots.")

    colors = set(["red", "blue", "forestgreen", "darkviolet", "saddlebrown", "deepskyblue"])
    unused_colors = colors - set([player.color for player in self.player_sessions.values()])
    if not unused_colors:
      raise TooManyPlayers("There are too many players.")

    # TODO: just use some arguments and stop creating fake players. This requires that we clean
    # up the javascript to know what to do with undefined values.
    self.player_sessions[session] = CatanPlayer(list(unused_colors)[0], data["name"].strip())

  def handle_takeover(self, session, data):
    if not self.game:
      raise InvalidPlayer("The game has not started yet; you must join instead.")
    if session in self.player_sessions:
      raise InvalidPlayer("You are already playing.")
    try:
      want_idx = int(data["player"])
    except:
      raise InvalidPlayer("Invalid player.")
    old_sessions = [session for session, idx in self.player_sessions.items() if idx == want_idx]
    if len(old_sessions) < 1:
      raise InvalidPlayer("Invalid player.")
    if len(old_sessions) > 1:
      raise RuntimeError("Game is in an incosistent state.")
    old_session = old_sessions[0]
    if old_session in self.connected:
      raise InvalidPlayer("That player is still connected.")
    del self.player_sessions[old_session]
    self.player_sessions[session] = want_idx

  def handle_start(self, session, data):
    if self.game is not None:
      raise InvalidMove("The game has already started.")
    if session != self.host:
      raise InvalidMove("You are not the host. Only the host can start the game.")

    player_data = [(session, info) for session, info in self.player_sessions.items()]
    if len(player_data) < 2:
      raise InvalidMove("The game must have at least two players to start.")

    self.update_rulesets_and_choices(data["options"])

    game = self.game_class()
    new_sessions = {}
    random.shuffle(player_data)
    for idx, (session, player_info) in enumerate(player_data):
      game.add_player(player_info.color, player_info.name)
      new_sessions[session] = idx
    # NOTE: init after initializing players - the number of players matters to init.
    game.init(self.choices)
    # NOTE: only update internal state after computing all new states so that internal state 
    # remains consistent if something above throws an exception.
    self.game = game
    self.player_sessions.clear()
    self.player_sessions.update(new_sessions)
    self.host = None

  def handle_select_option(self, session, data):
    if self.game is not None:
      raise InvalidMove("The game has already started.")
    if session != self.host:
      raise InvalidMove("You are not the host. Only the host can select game options.")

    self.update_rulesets_and_choices(data["options"])

  def update_rulesets_and_choices(self, user_choices):
    self.validate_scenario(user_choices)
    rule_choices, choices = self.split_choices(user_choices)
    new_game_class = self.get_game_class(rule_choices)
    new_options = new_game_class.get_options()
    old_options = self.game_class.get_options()
    self.choices.clear()

    # Set any valid options specified by the user, except options that are forced by the ruleset.
    for option_name in new_options.keys() & choices.keys():
      if new_options[option_name].forced:
        self.choices[option_name] = new_options[option_name].default
      else:
        self.choices[option_name] = choices[option_name]
    # For options that changed default values, reset them to the new default.
    for option_name in new_options.keys() & old_options.keys():
      if new_options[option_name].default != old_options[option_name].default:
        self.choices[option_name] = new_options[option_name].default
    # Set any remaining options to their default values.
    for option_name in new_options.keys() - self.choices.keys():
      self.choices[option_name] = new_options[option_name].default

    self.game_class = new_game_class
    self.scenario = rule_choices.pop("Scenario")
    self.rules = set([rule for rule, chosen in rule_choices.items() if chosen])

  def validate_scenario(self, user_choices):
    if "Scenario" not in user_choices:
      raise InvalidMove("You must select a scenario.")
    if user_choices["Scenario"] not in self.SCENARIOS:
      raise InvalidMove("Unknown scenario %s" % user_choices["Scenario"])

  @classmethod
  def split_choices(cls, user_choices):
    rulesets = {"Scenario": user_choices["Scenario"]}
    rulesets.update({key: val for key, val in user_choices.items() if key in cls.RULES})
    choices = {key: val for key, val in user_choices.items() if key not in rulesets}
    return rulesets, choices

  @classmethod
  def get_game_class(cls, rule_choices):
    rule_classes = [cls.SCENARIOS[rule_choices["Scenario"]]]
    rule_classes.extend([cls.RULES[rule] for rule in cls.RULES if rule_choices.get(rule)])

    class GameState(*reversed(rule_classes)):
      pass

    return GameState
