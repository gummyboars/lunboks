import abc
import collections
import json
from random import SystemRandom
from typing import List, Dict, Optional, Tuple
import os

from game import (
    BaseGame, ValidatePlayer, CustomEncoder, InvalidInput, UnknownMove, InvalidMove,
    InvalidPlayer, TooManyPlayers, NotYourTurn,
)

random = SystemRandom()

# pylint: disable=consider-using-f-string

RESOURCES = ["rsrc1", "rsrc2", "rsrc3", "rsrc4", "rsrc5"]
PLAYABLE_DEV_CARDS = ["yearofplenty", "monopoly", "roadbuilding", "knight"]
VICTORY_CARDS = ["palace", "chapel", "university", "market", "library"]
TILE_NUMBERS = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]
EXTRA_NUMBERS = [
    2, 5, 4, 6, 3, 9, 8, 11, 11, 10, 6, 3, 8, 4, 8, 10, 11, 12, 10, 5, 4, 9, 5, 9, 12, 3, 12, 6]


def _validate_name(current_name, used_names, data):
  # TODO: maybe this should actually return the new name instead of having callers figure it out.
  ValidatePlayer(data)
  new_name = data["name"].strip()
  # Check this before checking used_names.
  if new_name == current_name:
    return
  if new_name in used_names:
    raise InvalidPlayer("There is already a player named %s" % new_name)
  # TODO: re-enable this easter egg
  # if len(player_name) > 50:
  #   unused_names = set(["Joey", "Ross", "Chandler", "Phoebe", "Rachel", "Monica"]) - used_names
  #   if unused_names:
  #     new_name = random.choice(list(unused_names))
  #     self.player_data[player_idx].name = new_name
  #     raise InvalidPlayer(
  #         "Oh, is that how you want to play it? Well, you know what? I'm just gonna call you " +
  #         new_name
  #     )
  if len(new_name) > 16:
    raise InvalidPlayer("Max name length is 16.")


_event = collections.namedtuple(
    "Event", ["event_type", "public_text", "secret_text", "visible_players"])


class Event(_event):

  def __new__(cls, *args):
    defaults = ["", None]
    missing = len(cls._fields) - len(args)
    if missing > 0:
      args = list(args) + defaults[-missing:]
    return super().__new__(cls, *args)


class GameOption:

  def __init__(self, name, forced=False, default=False, choices=None, value=None, hidden=False):
    self.name = name
    self.forced = forced
    if choices is None:
      assert isinstance(default, bool)
    else:
      assert default in choices
    self.default = default
    self.choices = choices
    self.hidden = hidden
    if value is None:
      self.value = default
    else:
      self.value = value

  def set(self, value):
    if self.forced:
      assert value == self.default
    if self.choices is None:
      assert isinstance(value, bool)
    else:
      assert value in self.choices
    self.value = value

  def force(self, value):
    self.default = value
    self.value = value
    self.forced = True

  def json_repr(self):
    return {attr: getattr(self, attr) for attr in self.__dict__}


class Options(collections.OrderedDict):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.reset()

  def reset(self):
    self["seafarers"] = GameOption("Seafarers", default=False, forced=True)
    self["friendly_robber"] = GameOption("Friendly Robber", default=False)
    self["victory_points"] = GameOption("Victory Points", default=10, choices=list(range(8, 22)))
    self["foreign_island_points"] = GameOption(
        "", default=0, choices=[0, 1, 2], forced=True, hidden=True,
    )
    self["norsrc_is_connected"] = GameOption("", default=True, forced=True, hidden=True)
    self["extra_build"] = GameOption("5-6 Players", default=False, forced=True)
    self["debug"] = GameOption("Debug", default=False)

  def load(self, data):
    if data.keys() - self.keys():
      raise RuntimeError("Unknown option %s" % ", ".join(data.keys() - self.keys()))
    for key in self.keys() & data.keys():
      option_data = data[key]
      for attr, val in option_data.items():
        if not hasattr(self[key], attr):
          raise RuntimeError("Unknown attribute %s" % attr)
        setattr(self[key], attr, val)

  def __getattr__(self, attr):
    return self[attr].value


class TileLocation(collections.namedtuple("TileLocation", ["x", "y"])):

  __slots__ = ()

  def __new__(cls, x, y):
    assert x % 3 == 1, "tile's x location must be 1 mod 3: %s, %s" % (x, y)
    if x % 6 == 1:
      assert y % 2 == 1, "tiles must line up correctly %s, %s" % (x, y)
    else:
      assert y % 2 == 0, "tiles must line up correctly %s, %s" % (x, y)
    return super().__new__(cls, x, y)

  def get_upper_left_tile(self):
    return TileLocation(self.x - 3, self.y - 1)

  def get_upper_tile(self):
    return TileLocation(self.x, self.y - 2)

  def get_upper_right_tile(self):
    return TileLocation(self.x + 3, self.y - 1)

  def get_lower_right_tile(self):
    return TileLocation(self.x + 3, self.y + 1)

  def get_lower_tile(self):
    return TileLocation(self.x, self.y + 2)

  def get_lower_left_tile(self):
    return TileLocation(self.x - 3, self.y + 1)

  def get_upper_left_corner(self):
    return CornerLocation(self.x-1, self.y-1)

  def get_upper_right_corner(self):
    return CornerLocation(self.x+1, self.y-1)

  def get_right_corner(self):
    return CornerLocation(self.x+2, self.y)

  def get_lower_right_corner(self):
    return CornerLocation(self.x+1, self.y+1)

  def get_lower_left_corner(self):
    return CornerLocation(self.x-1, self.y+1)

  def get_left_corner(self):
    return CornerLocation(self.x-2, self.y)

  def get_adjacent_tiles(self):
    # NOTE: order matters here. Index in this array lines up with rotation semantics.
    return [self.get_lower_tile(), self.get_lower_left_tile(),
            self.get_upper_left_tile(), self.get_upper_tile(),
            self.get_upper_right_tile(), self.get_lower_right_tile()]

  def get_corner_locations(self):
    return [self.get_upper_left_corner(), self.get_upper_right_corner(),
            self.get_lower_left_corner(), self.get_lower_right_corner(),
            self.get_left_corner(), self.get_right_corner()]

  def get_edge_locations(self):
    # Order matters here.
    corners = [
        self.get_left_corner(), self.get_upper_left_corner(), self.get_upper_right_corner(),
        self.get_right_corner(), self.get_lower_right_corner(), self.get_lower_left_corner(),
    ]
    edges = []
    for idx, corner in enumerate(corners):
      edges.append(corner.get_edge(corners[(idx+1) % 6]))
    return edges


class CornerLocation(collections.namedtuple("CornerLocation", ["x", "y"])):

  __slots__ = ()

  def __new__(cls, x, y):
    assert x % 3 != 1, f"corner location's x must not be 1 mod 3: {x}, {y}"
    assert x % 2 == y % 2, f"corners must line up with tiles: {x}, {y}"
    return super().__new__(cls, x, y)

  def get_tiles(self):
    """Returns the tile coordinates of all tiles touching this corner.

    Every corner is at the top of some hex. It touches that hex, as well as
    the hex above that one.
    Every corner is either a left corner or a right corner. If it is a left
    corner (x-coordinate is 2 mod 3), it also touches the tile right of itself.
    Otherwise (x-coordinate is 0 mod 3), it touches the tile left of itself.
    """
    if self.x % 3 == 0:
      lower_hex = TileLocation(self.x + 1, self.y + 1)
      upper_hex = TileLocation(self.x + 1, self.y - 1)
      middle_hex = TileLocation(self.x - 2, self.y)
    elif self.x % 3 == 2:
      lower_hex = TileLocation(self.x - 1, self.y + 1)
      upper_hex = TileLocation(self.x - 1, self.y - 1)
      middle_hex = TileLocation(self.x + 2, self.y)
    return [lower_hex, upper_hex, middle_hex]

  def get_adjacent_corners(self):
    """Returns locations of adjacent corners.

    If this is a right corner (x-coordinate is 0 mod 3), we look right, up-left,
    and down-left. If it is a left corner (x-coordinate is 2 mod 3), we look left,
    up-right, and down-right.
    """
    if self.x % 3 == 0:
      return [
          CornerLocation(self.x + 2, self.y),
          CornerLocation(self.x - 1, self.y - 1),
          CornerLocation(self.x - 1, self.y + 1),
      ]
    return [
        CornerLocation(self.x - 2, self.y),
        CornerLocation(self.x + 1, self.y - 1),
        CornerLocation(self.x + 1, self.y + 1),
    ]

  def get_edge(self, other_corner):
    """Returns edge coordinates linking this corner to the other corner."""
    if other_corner.x < self.x:
      return EdgeLocation(other_corner.x, other_corner.y, self.x, self.y)
    return EdgeLocation(self.x, self.y, other_corner.x, other_corner.y)

  def get_edges(self):
    """Returns edge coordinates of edges adjacent to this corner."""
    # NOTE: this code is on the hot path. A simplified but less efficient implementation is
    # return [self.get_edge(other_corner) for other_corner in self.get_adjacent_corners()]
    if self.x % 3 == 0:
      return [
          EdgeLocation(self.x, self.y, self.x + 2, self.y),
          EdgeLocation(self.x - 1, self.y - 1, self.x, self.y),
          EdgeLocation(self.x - 1, self.y + 1, self.x, self.y),
      ]
    return [
        EdgeLocation(self.x - 2, self.y, self.x, self.y),
        EdgeLocation(self.x, self.y, self.x + 1, self.y - 1),
        EdgeLocation(self.x, self.y, self.x + 1, self.y + 1),
    ]


class EdgeLocation(collections.namedtuple("EdgeLocation", "left_x left_y right_x right_y")):

  __slots__ = ()

  def __new__(cls, left_x, left_y, right_x, right_y):
    assert left_x < right_x, "first corner must be left of second corner"
    # Validate that the two corners are valid and adjacent.
    # NOTE: this code is on the hot path. A simplified but less efficient implementation would be
    # assert CornerLocation(right_x, right_y) in CornerLocation(left_x, left_y).get_adjacent_corners
    assert left_x % 3 != 1, f"corner location's x must not be 1 mod 3: {left_x}, {left_y}"
    assert left_x % 2 == left_y % 2, f"corners must line up with tiles: {left_x}, {left_y}"
    assert right_x % 3 != 1, f"corner location's x must not be 1 mod 3: {right_x}, {right_y}"
    assert right_x % 2 == right_y % 2, f"corners must line up with tiles: {right_x}, {right_y}"
    if left_x % 3 == 0:
      assert (right_x, right_y) in [(left_x+2, left_y), (left_x-1, left_y-1), (left_x-1, left_y+1)]
    else:
      assert (right_x, right_y) in [(left_x-2, left_y), (left_x+1, left_y-1), (left_x+1, left_y+1)]
    return super().__new__(cls, left_x, left_y, right_x, right_y)

  @property
  def corner_left(self):
    return CornerLocation(self.left_x, self.left_y)

  @property
  def corner_right(self):
    return CornerLocation(self.right_x, self.right_y)

  def get_adjacent_tiles(self):
    """Returns the two TileLocations that share a border at this edge."""
    return list(set(self.corner_right.get_tiles()) & set(self.corner_left.get_tiles()))

  def get_end_tiles(self):
    """Returns the two TileLocations at either end of this edge."""
    return list(set(self.corner_right.get_tiles()) ^ set(self.corner_left.get_tiles()))


def parse_location(location, location_type):
  expected_size = len(location_type._fields)
  if not isinstance(location, (tuple, list)) or len(location) != expected_size:
    raise InvalidMove("location %s should be a tuple of size %s" % (location, expected_size))
  if not all(isinstance(val, int) for val in location):
    raise InvalidMove("location %s should be a tuple of ints" % (location,))
  if location_type == EdgeLocation:
    if CornerLocation(*location[:2]) not in CornerLocation(*location[2:]).get_adjacent_corners():
      raise InvalidMove("%s is not a valid edge" % (location,))
  return location_type(*location)


class Road:

  TYPES = ["road", "ship"]

  def __init__(self, location, road_type, player, closed=False, movable=True, source=None):
    assert road_type in self.TYPES
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
      source = CornerLocation(*value["source"])
    return Road(
        value["location"], value["road_type"], value["player"], value.get("closed", False),
        value.get("movable", True), source,
    )

  def __str__(self):
    return str(self.json_repr())


class Piece:

  TYPES = ["settlement", "city"]

  def __init__(self, x, y, piece_type, player):
    assert piece_type in self.TYPES
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


class Tile:

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
    return Tile(
        value["location"][0], value["location"][1], value["tile_type"], value["is_land"],
        value["number"], value["rotation"], value.get("variant") or "",
        value.get("land_rotations") or [],
    )

  def __str__(self):
    return str(self.json_repr())


class Port:
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


class Player:

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
    player = Player(None, None)
    for attr in defaultdict_attrs:
      getattr(player, attr).update(value[attr])
    for attr in set(player.__dict__.keys()) - set(defaultdict_attrs):
      setattr(player, attr, value[attr])
    return player

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


class IslandersState:

  WANT = "want"
  GIVE = "give"
  TRADE_SIDES = [WANT, GIVE]
  LOCATION_ATTRIBUTES = {"tiles", "ports", "pieces", "roads"}
  HIDDEN_ATTRIBUTES = {
      "dev_cards", "dev_roads_placed", "played_dev", "ships_moved", "built_this_turn",
      "home_corners", "foreign_landings", "placement_islands",
  }
  COMPUTED_ATTRIBUTES = {"port_corners", "corners_to_islands"}
  INDEXED_ATTRIBUTES = {
      "discard_players", "collect_counts", "home_corners", "foreign_landings", "counter_offers",
  }
  REQUIRED_ATTRIBUTES = {
      "player_data", "tiles", "ports", "pieces", "roads", "robber", "dev_cards", "dice_roll",
      "game_phase", "turn_phase", "turn_idx", "dev_roads_placed", "played_dev", "discard_players",
      "rob_players", "trade_offer", "counter_offers", "options",
  }
  EXTRA_BUILD_ACTIONS = ["settle", "city", "buy_dev", "road", "ship", "end_extra_build"]

  def __init__(self):
    # Player data is a sequential list of Player objects; players are identified by index.
    self.player_data: List[Player] = []
    # Board/Card State
    self.tiles: Dict[TileLocation, Tile] = {}
    self.ports: Dict[TileLocation, Port] = {}
    self.port_corners: Dict[CornerLocation, str] = {}
    self.pieces: Dict[CornerLocation, Piece] = {}
    self.roads: Dict[EdgeLocation, Road] = {}  # includes ships
    self.robber: Optional[TileLocation] = None
    self.pirate: Optional[TileLocation] = None
    self.dev_cards: List[str] = []
    self.largest_army_player: Optional[int] = None
    self.longest_route_player: Optional[int] = None
    self.dice_roll: Optional[Tuple[int, int]] = None
    self.corners_to_islands: Dict[CornerLocation, CornerLocation] = {}  # corner -> canonical corner
    self.placement_islands: Optional[List[CornerLocation]] = None
    self.discoverable_tiles: List[str] = []
    self.discoverable_numbers: List[int] = []
    # Turn Information
    self.game_phase: str = "place1"  # valid values are place1, place2, main, victory
    # valid values: settle, road, dice, collect, discard, robber, rob, dev_road, main, extra_build
    self.turn_phase: str = "settle"
    self.turn_idx: int = 0
    self.collect_idx: Optional[int] = None
    self.extra_build_idx: Optional[int] = None
    # Bookkeeping
    self.dev_roads_placed: int = 0
    self.played_dev: int = 0
    self.ships_moved: int = 0
    self.built_this_turn: List[EdgeLocation] = []  # Locations where ships were placed this turn.
    self.discard_players: Dict[int, int] = {}  # Map of player to number of cards they must discard.
    self.rob_players: List[int] = []  # List of players that can be robbed by this robber.
    self.shortage_resources: List[str] = []
    self.collect_counts: Dict[int, int] = collections.defaultdict(int)
    self.home_corners: Dict[int, List[CornerLocation]] = collections.defaultdict(list)
    self.foreign_landings: Dict[int, List[CornerLocation]] = collections.defaultdict(list)
    self.next_die_roll: Optional[int] = None
    # Trade Information
    self.trade_offer = None
    self.counter_offers = {}  # Map of player to counter offer.
    # Special values for counter-offers: not present in dictionary means they have not
    # yet made a counter-offer. An null/None counter-offer indicates that they have
    # rejected the trade offer. A counter-offer equal to the original means they accept.
    self.event_log = collections.deque([], 50)
    # Game Options
    self.options = Options()

  @classmethod
  def parse_json(cls, gamedata):
    cstate = cls()

    missing = cls.REQUIRED_ATTRIBUTES - gamedata.keys()
    if missing:
      raise RuntimeError("Missing attributes %s from loaded data" % ", ".join(missing))

    # Regular attributes
    custom_attrs = cls.LOCATION_ATTRIBUTES | cls.COMPUTED_ATTRIBUTES | cls.INDEXED_ATTRIBUTES
    custom_attrs |= {"player_data", "event_log", "options"}
    for attr in cstate.__dict__.keys() & gamedata.keys() - custom_attrs:
      setattr(cstate, attr, gamedata[attr])

    # Parse the options.
    cstate.options.load(gamedata["options"])

    # Parse the players.
    for parsed_player in gamedata["player_data"]:
      cstate.player_data.append(Player.parse_json(parsed_player))

    # Parse the event log.
    cstate.event_log.clear()
    for event in gamedata["event_log"]:
      cstate.event_log.append(Event(*event))

    # Indexed attributes update the corresponding dictionaries.
    for attr in cls.INDEXED_ATTRIBUTES & gamedata.keys():
      for idx, val in enumerate(gamedata[attr]):
        if val is not None:
          getattr(cstate, attr)[idx] = val

    # Location dictionaries are updated with their respective items.
    cstate.parse_tiles(gamedata["tiles"])
    cstate.parse_ports(gamedata["ports"])
    cstate.parse_pieces(gamedata["pieces"])
    cstate.parse_roads(gamedata["roads"])

    # Location attributes need to be replaced with location objects.
    if cstate.robber is not None:
      cstate.robber = TileLocation(*cstate.robber)
    if cstate.pirate is not None:
      cstate.pirate = TileLocation(*cstate.pirate)

    # Built this turn needs to use locations instead of lists. Same thing for placement_islands.
    cstate.built_this_turn = [EdgeLocation(*loc) for loc in cstate.built_this_turn]
    if cstate.placement_islands is not None:
      cstate.placement_islands = [CornerLocation(*corner) for corner in cstate.placement_islands]

    # When loading json, these islands get turned into lists. Turn them into locations instead.
    for attr in ["home_corners", "foreign_landings"]:
      mapping = getattr(cstate, attr)
      for idx, corner_list in mapping.items():
        for corner in corner_list:
          assert cstate.pieces[CornerLocation(*corner)].player == idx
      mapping.update({
          idx: [CornerLocation(*corner) for corner in corner_list]
          for idx, corner_list in mapping.items()
      })

    cstate.recompute()
    return cstate

  def parse_tiles(self, tiledata):
    for tile_json in tiledata:
      tile = Tile.parse_json(tile_json)
      self.add_tile(tile)

  def parse_ports(self, portdata):
    for port_json in portdata:
      port = Port.parse_json(port_json)
      self.add_port(port)

  def parse_pieces(self, piecedata):
    for piece_json in piecedata:
      piece = Piece.parse_json(piece_json)
      self._add_piece(piece)

  def parse_roads(self, roaddata):
    for road_json in roaddata:
      road = Road.parse_json(road_json)
      self._add_road(road)

  def json_repr(self):
    custom = {"player_data", "event_log"}
    ret = {
        name: getattr(self, name) for name in
        self.__dict__.keys() - self.LOCATION_ATTRIBUTES - self.COMPUTED_ATTRIBUTES - custom
    }
    ret.update({name: list(getattr(self, name).values()) for name in self.LOCATION_ATTRIBUTES})
    for attr in self.INDEXED_ATTRIBUTES:
      ret.update({attr: [getattr(self, attr).get(idx) for idx in range(len(self.player_data))]})
    ret["player_data"] = [player.json_repr() for player in self.player_data]
    ret["event_log"] = list(self.event_log)
    return ret

  def for_player(self, player_idx):
    data = self.json_for_player()
    if player_idx is not None:
      data["you"] = player_idx
      data["cards"] = self.player_data[player_idx].cards
      data["trade_ratios"] = self.player_data[player_idx].trade_ratios
    events = data.pop("event_log")
    data["event_log"] = []
    for event in events:
      text = event.public_text
      if event.secret_text and event.visible_players and player_idx in event.visible_players:
        text = event.secret_text
      data["event_log"].append({"event_type": event.event_type, "text": text})
    return data

  def json_for_player(self):
    ret = self.json_repr()
    ret["type"] = "game_state"
    ret["turn"] = ret.pop("turn_idx")
    for name in self.HIDDEN_ATTRIBUTES:
      del ret[name]
    del ret["player_data"]
    ret["dev_cards"] = len(self.dev_cards)

    land_corners = set()
    all_corners = set()
    # TODO: instead of sending a list of corners, we should send something like
    # a list of legal moves for tiles, corners, and edges.
    for tile in self.tiles.values():
      # Triple-count each corner and dedup.
      for corner_loc in tile.location.get_corner_locations():
        all_corners.add(corner_loc)
        if not tile.is_land:
          continue
        land_corners.add(corner_loc)
    ret["corners"] = [{"location": loc} for loc in land_corners]
    edges = {}
    for corner in all_corners:
      # Double-count each edge and dedup.
      for edge in corner.get_edges():
        edge_type = self._get_edge_type(edge)
        if edge_type is not None:
          edges[edge] = {"location": edge, "edge_type": edge_type}
    ret["edges"] = list(edges.values())

    ret["landings"] = []
    for idx, corner_list in self.foreign_landings.items():
      ret["landings"].extend([{"location": corner, "player": idx} for corner in corner_list])

    is_over = (self.game_phase == "victory")

    ret["player_data"] = [player.json_for_player(is_over) for player in self.player_data]
    for idx in range(len(self.player_data)):
      ret["player_data"][idx]["points"] = self.player_points(idx, visible=(not is_over))
    return ret

  def player_points(self, idx, visible):
    count = 0
    for piece in self.pieces.values():
      if piece.player == idx:
        if piece.piece_type == "settlement":
          count += 1
        elif piece.piece_type == "city":
          count += 2
    if self.largest_army_player == idx:
      count += 2
    if self.longest_route_player == idx:
      count += 2
    if not visible:
      count += sum([self.player_data[idx].cards[card] for card in VICTORY_CARDS])
    count += len(self.foreign_landings[idx]) * self.options.foreign_island_points
    return count

  def game_status(self):
    # TODO: list the rulesets being used
    return "islanders game with %s" % ", ".join([p.name for p in self.player_data])

  def add_player(self, color, name):
    self.player_data.append(Player(color, name))

  def handle(self, player_idx, data):
    if not data.get("type"):
      raise InvalidInput("Missing move type")
    if data["type"] == "force_dice":
      self.handle_force_dice(int(data.get("value")))
      return
    if data["type"] == "debug_roll_dice":
      self.handle_debug_roll_dice(int(data.get("count", 1)))
      return
    self.check_turn_okay(player_idx, data["type"])
    self.inner_handle(player_idx, data["type"], data)
    # NOTE: use turn_idx here, since it is possible for a player to get to 10 points when it is
    # not their turn (e.g. because someone else's longest road was broken), but the rules say
    # you can only win on YOUR turn. So we check for victory after we have handled the end of
    # the previous turn, in case the next player wins at the start of their turn.
    if self.player_points(self.turn_idx, visible=False) >= self.options.victory_points:
      self.handle_victory()

  def check_turn_okay(self, player_idx, move_type):
    if move_type == "rename":
      return
    if self.game_phase == "victory":
      raise NotYourTurn("The game is over.")
    if self.turn_phase == "collect" and move_type == "collect":
      if not self.collect_counts.get(player_idx):
        raise NotYourTurn("You are not eligible to collect any resources.")
      if self.collect_idx is not None and self.collect_idx != player_idx:
        raise NotYourTurn("Another player must collect resources before you.")
      return
    if self.turn_phase == "extra_build":
      if self.extra_build_idx != player_idx:
        raise NotYourTurn("It is not your turn.")
      if move_type not in self.EXTRA_BUILD_ACTIONS:
        raise NotYourTurn("You can only build/buy during the special build phase.")
      return
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
    if move_type == "pirate" and self.options.seafarers:
      return self.handle_pirate(player_idx, location)
    if move_type == "rob":
      return self.handle_rob(data.get("player"), player_idx)
    if move_type == "collect":
      return self.handle_collect(player_idx, data.get("selection"))
    if move_type == "road":
      return self.handle_road(location, player_idx, move_type, [("rsrc2", 1), ("rsrc4", 1)])
    if move_type == "ship" and self.options.seafarers:
      return self.handle_road(location, player_idx, move_type, [("rsrc1", 1), ("rsrc2", 1)])
    if move_type == "move_ship" and self.options.seafarers:
      return self.handle_move_ship(data.get("from"), data.get("to"), player_idx)
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
      return self.handle_accept_counter(
          data.get("counter_offer"), data.get("counter_player"), player_idx
      )
    if move_type == "trade_bank":
      return self.handle_trade_bank(data.get("offer"), player_idx)
    if move_type == "end_extra_build":
      return self.handle_end_extra_build(player_idx)
    if move_type == "end_turn":
      return self.handle_end_turn()
    raise UnknownMove(f"Unknown move {move_type}")

  def _validate_selection(self, selection):
    """Selection should be a dict of rsrc -> count."""
    if not selection or not isinstance(selection, dict):
      raise InvalidMove("Invalid resource selection.")
    if set(selection.keys()) - set(RESOURCES):
      raise InvalidMove("Invalid resource selection - unknown or untradable resource.")
    if not all(isinstance(value, int) and value >= 0 for value in selection.values()):
      raise InvalidMove("Invalid resource selection - must be positive integers.")

  def rename_player(self, player_idx, data):
    _validate_name(self.player_data[player_idx].name, [p.name for p in self.player_data], data)
    self.player_data[player_idx].name = data["name"].strip()

  def handle_victory(self):
    self.game_phase = "victory"
    self.event_log.append(Event("victory", "{player%s} has won!" % self.turn_idx))

  def handle_end_extra_build(self, player_idx):
    if self.turn_phase != "extra_build":
      raise InvalidMove("It is not the extra build phase.")
    if player_idx != self.extra_build_idx:
      raise NotYourTurn("It is not your extra build phase.")
    self.extra_build_idx = (self.extra_build_idx + 1) % len(self.player_data)
    if self.extra_build_idx == self.turn_idx:
      self.extra_build_idx = None
      self.end_turn()

  def handle_end_turn(self):
    if self.game_phase != "main":
      raise InvalidMove("You MUST place your first settlement/roads.")
    self._check_main_phase("end_turn", "end your turn")
    if self.options.extra_build:
      next_player = (self.turn_idx + 1) % len(self.player_data)
      self.extra_build_idx = next_player
      self.turn_phase = "extra_build"
      return
    self.end_turn()

  def end_turn(self):
    self.player_data[self.turn_idx].unusable.clear()
    self.played_dev = 0
    self.ships_moved = 0
    self.built_this_turn.clear()
    self.shortage_resources.clear()
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
    if self.next_die_roll is not None:
      red = self.next_die_roll // 2
      white = (self.next_die_roll + 1) // 2
      self.next_die_roll = None
    else:
      red = random.randint(1, 6)
      white = random.randint(1, 6)
    self.dice_roll = (red, white)
    self.event_log.append(Event("dice", "{player%s} rolled a %s" % (self.turn_idx, red + white)))
    if (red + white) == 7:
      self.discard_players = self._get_players_with_too_many_resources()
      if sum(self.discard_players.values()):
        self.turn_phase = "discard"
      else:
        self.turn_phase = "robber"
      return
    to_receive = self.calculate_resource_distribution(self.dice_roll)
    self.distribute_resources(to_receive)

  def handle_force_dice(self, value):
    if not self.options.debug:
      raise InvalidMove("You may only force dice rolls when debug mode is enabled.")
    self.next_die_roll = value

  def handle_debug_roll_dice(self, count):
    if not self.options.debug:
      raise InvalidMove("You may only force dice rolls when debug mode is enabled.")
    for _ in range(count):
      red = random.randint(1, 6)
      white = random.randint(1, 6)
      dist = self.calculate_resource_distribution((red, white))
      self.distribute_resources(dist)

  def remaining_resources(self, rsrc):
    return 19 - sum([p.cards[rsrc] for p in self.player_data])

  def calculate_resource_distribution(self, dice_roll):
    # Figure out which players are due how many resources.
    to_receive = collections.defaultdict(lambda: collections.defaultdict(int))
    for tile in self.tiles.values():
      if tile.number != sum(dice_roll):
        continue
      if self.robber == tile.location:
        continue
      for corner_loc in tile.location.get_corner_locations():
        piece = self.pieces.get(corner_loc)
        if piece and piece.piece_type == "settlement":
          to_receive[tile.tile_type][piece.player] += 1
        elif piece and piece.piece_type == "city":
          to_receive[tile.tile_type][piece.player] += 2

    self.collect_counts = to_receive.pop("anyrsrc", {})
    return to_receive

  def distribute_resources(self, to_receive):
    self.shortage_resources = []
    # Changes the values of to_receive as it iterates through them.
    for rsrc, receive_players in to_receive.items():
      remaining = self.remaining_resources(rsrc)
      # If there are enough resources to go around, no problem.
      if sum(receive_players.values()) <= remaining:
        continue
      # Otherwise, there is a shortage of this resource.
      self.shortage_resources.append(rsrc)
      # If there is only one player receiving this resource, they receive all of the
      # remaining cards for this resources type.
      if len(receive_players) == 1:
        the_player = list(receive_players.keys())[0]
        self.event_log.append(Event(
            "shortage", "{player%s} was due %s {%s} but only received %s due to a shortage" % (
                the_player, receive_players[the_player], rsrc, remaining),
        ))
        receive_players[the_player] = remaining
        continue
      # If there is more than one player receiving this resource, and there is not enough
      # in the supply, then no players receive any of this resource.
      receive_players.clear()
      self.event_log.append(Event(
          "shortage", "There was a shortage of {%s} - no players received any" % rsrc))

    # Do the actual resource distribution.
    received = collections.defaultdict(lambda: collections.defaultdict(int))
    for rsrc, receive_players in to_receive.items():
      for player, count in receive_players.items():
        self.player_data[player].cards[rsrc] += count
        received[player][rsrc] += count

    # Write an event log.
    for player, rsrcs in received.items():
      text = "received " + ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in rsrcs.items()])
      self.event_log.append(Event("receive", "{player%s} " % player + text))

    self.next_collect_player()

  def next_collect_player(self):
    total_collect = sum(self.collect_counts.values())
    if not total_collect:
      self.finish_collect()
      return
    available = {}
    for rsrc in set(RESOURCES) - set(self.shortage_resources):
      available[rsrc] = self.remaining_resources(rsrc)
    if sum(available.values()) <= 0:
      self.finish_collect()
      return
    min_available = min(available.values())  # The minimum available of any collectible resource.
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

  def finish_collect(self):
    self.collect_counts.clear()
    self.collect_idx = None
    if self.game_phase == "place2":
      self.turn_phase = "road"
      return
    if self.dev_roads_placed > 0:
      self.turn_phase = "dev_road"
      if self.dev_roads_placed == 2:
        self.dev_roads_placed = 0
        self.turn_phase = "main"
      return
    if self.extra_build_idx is not None:
      self.turn_phase = "extra_build"
      return
    self.turn_phase = "main"

  def handle_collect(self, player_idx, selection):
    self._validate_selection(selection)
    if sum(selection.values()) != self.collect_counts[player_idx]:
      raise InvalidMove("You must select %s resources." % self.collect_counts[player_idx])
    if selection.keys() & set(self.shortage_resources):
      raise InvalidMove(
          "There is a shortage of {%s}; you cannot collect any." % (
              "}, {".join(self.shortage_resources))
      )
    # TODO: dedup with code from year of plenty
    overdrawn = [rsrc for rsrc in selection if selection[rsrc] > self.remaining_resources(rsrc)]
    if overdrawn:
      raise InvalidMove("There is not enough {%s} in the bank." % "}, {".join(overdrawn))
    for rsrc, value in selection.items():
      self.player_data[player_idx].cards[rsrc] += value
    event_text = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in selection.items()])
    self.event_log.append(Event("collect", "{player%s} collected " % player_idx + event_text))
    del self.collect_counts[player_idx]
    self.next_collect_player()

  def _get_players_with_too_many_resources(self):
    return {
        idx: player.resource_card_count() // 2
        for idx, player in enumerate(self.player_data) if player.resource_card_count() >= 8
    }

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
    discarded = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in selection.items()])
    self.event_log.append(Event("discard", "{player%s} discarded %s" % (player, discarded)))
    del self.discard_players[player]
    if sum(self.discard_players.values()) == 0:
      self.turn_phase = "robber"

  def validate_robber_location(self, location, robber_type, land):
    new_location = parse_location(location, TileLocation)
    if self.turn_phase != "robber":
      if self.turn_phase == "discard":
        raise InvalidMove("Waiting for players to discard.")
      raise InvalidMove("You cannot play the %s right now." % robber_type)
    chosen_tile = self.tiles.get(new_location)
    if chosen_tile is None or land != chosen_tile.is_land:
      raise InvalidMove(
          "You must play the %s on a valid %s tile." % (robber_type, "land" if land else "{space}")
      )
    if chosen_tile.tile_type == "discover":
      raise InvalidMove("You cannot place the %s there before exploring it." % robber_type)
    if getattr(self, robber_type) == new_location:
      raise InvalidMove("You must move the %s to a different tile." % robber_type)
    return new_location

  def check_friendly_robber(self, current_player, adjacent_players, robber_type):
    if not self.options.friendly_robber:
      return
    poor_players = [idx for idx in adjacent_players if self.player_points(idx, visible=True) <= 2]
    if set(poor_players) - {current_player}:
      raise InvalidMove("%ss refuse to rob such poor people." % robber_type.capitalize())

  def handle_robber(self, location, current_player):
    robber_loc = self.validate_robber_location(location, "robber", land=True)
    adjacent_players = {
        self.pieces[loc].player for loc in robber_loc.get_corner_locations() if loc in self.pieces
    }
    self.check_friendly_robber(current_player, adjacent_players, "robber")
    self.event_log.append(Event("robber", "{player%s} moved the robber" % current_player))
    self.robber = robber_loc
    self.activate_robber(current_player, adjacent_players)

  def handle_pirate(self, player_idx, location):
    pirate_loc = self.validate_robber_location(location, "pirate", land=False)
    adjacent_players = {
        self.roads[edge].player for edge in pirate_loc.get_edge_locations()
        if edge in self.roads and self.roads[edge].road_type == "ship"
    }
    self.check_friendly_robber(player_idx, adjacent_players, "pirate")
    self.event_log.append(Event("pirate", "{player%s} moved the pirate" % player_idx))
    self.pirate = pirate_loc
    self.activate_robber(player_idx, adjacent_players)

  def activate_robber(self, current_player, adjacent_players):
    robbable_players = {
        idx for idx in adjacent_players if self.player_data[idx].resource_card_count()
    }
    robbable_players -= {current_player}
    if len(robbable_players) > 1:
      self.rob_players = list(robbable_players)
      self.turn_phase = "rob"
      return
    if len(robbable_players) == 1:
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
    self.event_log.append(Event(
        "rob",
        "{player%s} stole a card from {player%s}" % (current_player, rob_player),
        "{player%s} stole a {%s} from {player%s}" % (current_player, chosen_rsrc, rob_player),
        [current_player, rob_player],
    ))

  def _check_main_phase(self, move_type, text):
    if self.turn_phase == "extra_build" and move_type in self.EXTRA_BUILD_ACTIONS:
      return
    if self.turn_phase != "main":
      if self.turn_phase == "dice":
        raise InvalidMove("You must roll the dice first.")
      if self.turn_phase == "robber":
        raise InvalidMove("You must move the robber first.")
      if self.turn_phase == "discard":
        raise InvalidMove("Waiting for players to discard.")
      if self.turn_phase == "collect":
        raise NotYourTurn("Waiting for players to collect resources.")
      raise InvalidMove("You cannot %s right now." % text)

  # TODO: move into the player class?
  def _check_resources(self, resources, player, action_string):
    errors = []
    for resource, count in resources:
      if self.player_data[player].cards[resource] < count:
        errors.append("%s {%s}" % (count - self.player_data[player].cards[resource], resource))
    if errors:
      raise InvalidMove("You would need an extra %s to %s." % (", ".join(errors), action_string))

  # TODO: use a dict instead of an iterable of tuples for resources?
  def _remove_resources(self, resources, player, build_type):
    self._check_resources(resources, player, build_type)
    for resource, count in resources:
      self.player_data[player].cards[resource] -= count

  def _check_road_building(self, location, player, road_type):
    left_corner = location.corner_left
    right_corner = location.corner_right
    # Validate that one side of the road is land.
    self._check_edge_type(location, road_type)
    # Validate that ships are not placed next to the pirate.
    if road_type == "ship":
      adjacent_tiles = location.get_adjacent_tiles()
      if self.pirate in adjacent_tiles:
        raise InvalidMove("You cannot place a ship next to the pirate.")
    # Validate that this connects to either a settlement or another road.
    for corner in [left_corner, right_corner]:
      # Check whether this corner has one of the player's settlements.
      maybe_piece = self.pieces.get(corner)
      if maybe_piece:
        if maybe_piece.player == player:  # pylint: disable=no-else-return
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
        maybe_road = self.roads.get(edge)
        if maybe_road and maybe_road.player == player and maybe_road.road_type == road_type:
          # They have a road leading here - they can build another road.
          return
    raise InvalidMove(f"{road_type.capitalize()}s must be connected to your {road_type} network.")

  def _check_edge_type(self, edge_location, road_type):
    edge_type = self._get_edge_type(edge_location)
    if edge_type is None:
      raise InvalidMove(f"Your {road_type} must be between two land tiles.")
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
    if not all(loc in self.tiles for loc in tile_locations):
      return None

    # If there is a road/ship here, just return the type of that road/ship.
    if edge_location in self.roads:
      return self.roads[edge_location].road_type

    # Calculate how many of the two tiles are land.
    are_lands = [self.tiles[loc].is_land for loc in tile_locations]

    # If we are not playing with seafarers, then only edges next to at least one land are valid.
    if not self.options.seafarers:
      if any(are_lands):
        return "road"
      return None

    # Seafarers: edges can be road, ship, or coast based on the number of lands.
    if all(are_lands):
      return "road"
    if not any(are_lands):
      return "ship"
    # For the coast, it matters whether the sea is on top or on bottom.
    tile_locations.sort(key=lambda loc: loc.y)
    if self.tiles[tile_locations[0]].is_land:
      return "coastdown"
    return "coastup"

  def _check_road_next_to_empty_settlement(self, location, player):
    left_corner = location.corner_left
    right_corner = location.corner_right
    for corner in [left_corner, right_corner]:
      # Check whether this corner has one of the player's settlements.
      piece = self.pieces.get(corner)
      if piece and piece.player == player:
        # They have a settlement/city here - make sure it's not the one that
        # they built before (by checking to see if it has no roads).
        for edge in corner.get_edges():
          road = self.roads.get(edge)
          if road and road.player == player:
            # No good - this is the settlement that already has a road.
            raise InvalidMove("You must put your road next to your second settlement.")
        break
    else:
      raise InvalidMove("You must put your road next to your settlement.")

  def handle_road(self, location, player, road_type, resources):
    loc = parse_location(location, EdgeLocation)
    # Check that this is the right part of the turn.
    if self.game_phase.startswith("place"):
      if self.turn_phase != "road":
        raise InvalidMove("You must build a settlement first.")
    elif self.turn_phase != "dev_road":
      self._check_main_phase(road_type, f"build a {road_type}")
    # Check nothing else is already there.
    if loc in self.roads:
      raise InvalidMove("There is already a %s there." % self.roads[loc].road_type)
    # Check that this attaches to their existing network.
    self._check_road_building(loc, player, road_type)
    # Check that the player has enough roads left.
    road_count = len([
        r for r in self.roads.values() if r.player == player and r.road_type == road_type
    ])
    if road_count >= 15:
      raise InvalidMove(f"You have no {road_type}s remaining.")
    # Handle special settlement phase.
    if self.game_phase.startswith("place"):
      self._check_road_next_to_empty_settlement(loc, player)
      self.add_road(Road(loc, road_type, player))
      self.event_log.append(Event(road_type, "{player%s} built a %s" % (player, road_type)))
      self.end_turn()
      return
    # Handle road building dev card.
    if self.turn_phase == "dev_road":
      self.dev_roads_placed += 1
      self.add_road(Road(loc, road_type, player))
      self.event_log.append(Event(road_type, "{player%s} built a %s" % (player, road_type)))
      # Road building ends if they placed 2 roads or ran out of roads.
      usable = ["road", "ship"] if self.options.seafarers else ["road"]
      used = len([r for r in self.roads.values() if r.player == player and r.road_type in usable])
      # TODO: replace this with a method to check to see if they have any legal road moves.
      if used >= 15 * len(usable):
        self.dev_roads_placed = 2  # Automatically end dev road if the player is out of roads/ships.
      # NOTE: it is possible to enter the "collect" phase while building roads, in which case
      # we will not override the turn_phase. next_collect_player() is responsible for returning
      # to the dev_road phase (or main phase) when the collection is done.
      if self.turn_phase == "dev_road":
        if self.dev_roads_placed == 2:
          self.dev_roads_placed = 0
          self.turn_phase = "main"
      return
    # Check resources and deduct from player.
    self._remove_resources(resources, player, f"build a {road_type}")

    self.event_log.append(Event(road_type, "{player%s} built a %s" % (player, road_type)))
    self.add_road(Road(loc, road_type, player))

  def _add_road(self, road):
    self.roads[road.location] = road

  def add_road(self, road):
    if road.road_type == "ship":
      road.source = self.get_ship_source(road.location, road.player)
    self._add_road(road)

    self.discover_tiles(road)

    # Check for increase in longest road, update longest road player if necessary. Also check
    # for decrease in longest road, which can happen if a player moves a ship.
    self.player_data[road.player].longest_route = self._calculate_longest_road(road.player)
    self._update_longest_route_player()

    if road.road_type == "ship":
      self.recalculate_ships(road.source, road.player)
      self.built_this_turn.append(road.location)

  def _update_longest_route_player(self):
    new_max = max([p.longest_route for p in self.player_data])
    holder_max = None
    if self.longest_route_player is not None:
      holder_max = self.player_data[self.longest_route_player].longest_route

    # If nobody meets the conditions for longest road, nobody takes the card. After this,
    # we may assume that the longest road has at least 5 segments.
    if new_max < 5:
      if self.longest_route_player is not None:
        self.event_log.append(Event(
            "longest_route", "{player%s} loses longest route" % self.longest_route_player))
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
      event_text = "{player%s} takes longest route" % eligible[0]
      if self.longest_route_player is not None:
        event_text += " from {player%s}" % self.longest_route_player
      # In some cases, the longest route player may have a shorter route than before, but still
      # maintain the longest route. In those cases, we do not add an event to the log.
      if eligible[0] != self.longest_route_player:
        self.event_log.append(Event("longest_route", event_text))
        self.longest_route_player = eligible[0]
    else:
      self.event_log.append(Event(
          "longest_route", "Nobody receives longest route because of a tie."))
      self.longest_route_player = None

  def _calculate_longest_road(self, player):
    # Get all corners of all roads for this player.
    all_corners = set()
    for road in self.roads.values():
      if road.player != player:
        continue
      all_corners.add(road.location.corner_left)
      all_corners.add(road.location.corner_right)

    # For each corner, do a DFS and find the depth.
    max_length = 0
    for corner in all_corners:
      seen = set()
      max_length = max(max_length, self._dfs_depth(player, corner, seen, None))

    return max_length

  def _dfs_depth(self, player, corner, seen_edges, prev_edge):
    # First, use the type of the piece at this corner to set a baseline. If it belongs to
    # another player, the route ends. If it belongs to this player, the next edge in the route
    # may be either a road or a ship. If there is no piece, then the type of the next edge
    # must match the type of the previous edge (except for the first edge in the DFS).
    this_piece = self.pieces.get(corner)
    if prev_edge is None:
      # First road can be anything. Can also be adjacent to another player's settlement.
      valid_types = Road.TYPES
    else:
      if this_piece is None:
        if prev_edge in self.roads:
          valid_types = [self.roads[prev_edge].road_type]
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
      edge_piece = self.roads.get(edge)
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

  def get_ship_source(self, location, player_idx):
    edges = []
    for corner in [location.corner_left, location.corner_right]:
      maybe_piece = self.pieces.get(corner)
      if maybe_piece and maybe_piece.player == player_idx:
        return maybe_piece.location
      edges.extend(corner.get_edges())
    for edge in edges:
      if edge == location:
        continue
      maybe_road = self.roads.get(edge)
      if maybe_road and maybe_road.player == player_idx and maybe_road.road_type == "ship":
        return maybe_road.source
    raise InvalidMove("Ships must be connected to your ship network.")

  def recalculate_ships(self, source, player_idx):
    self._ship_dfs_helper(source, player_idx, [], set(), source, None)

  def _ship_dfs_helper(self, source, player_idx, path, seen, corner, prev):
    seen.add(corner)
    edges = corner.get_edges()
    outgoing_edges = []

    # First, calculate all the outgoing edges.
    for edge in edges:
      # This is the edge we just walked down, ignore it.
      if edge == prev:
        continue
      other_corner = edge.corner_left if edge.corner_right == corner else edge.corner_right
      # If this edge does not have this player's ship on it, skip it.
      maybe_ship = self.roads.get(edge)
      if not maybe_ship or maybe_ship.road_type != "ship" or maybe_ship.player != player_idx:
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
        self.roads[edge].movable = True
        continue
      if other_corner in seen:
        # Here, we have created a loop. Every ship on this loop may be movable.
        start_idx = None
        for idx, rloc in reversed(list(enumerate(path))):
          if other_corner in [rloc[:2], rloc[2:]]:
            start_idx = idx
            break
        else:
          raise RuntimeError("What happened here? This shouldn't be physically possible.")
        for idx in range(start_idx, len(path)):
          self.roads[path[idx]].movable = True
        self.roads[edge].movable = True
        continue
      maybe_piece = self.pieces.get(other_corner)
      if maybe_piece and maybe_piece.player == player_idx:
        # Here, we know that there is a shipping route from one of the player's settlements to
        # another. Every ship on this shipping route is considered closed.
        for rloc in path + [edge]:
          self.roads[rloc].closed = True
      # Now we know this ship does not create a loop, so we continue to explore the far corner.
      path.append(edge)
      self._ship_dfs_helper(source, player_idx, path, seen, other_corner, edge)
      path.pop()
    seen.remove(corner)

  def handle_move_ship(self, from_location, to_location, player_idx):
    from_loc = parse_location(from_location, EdgeLocation)
    to_loc = parse_location(to_location, EdgeLocation)
    # Check that this is the right part of the turn.
    self._check_main_phase("move_ship", "move a ship")
    if self.ships_moved:
      raise InvalidMove("You have already moved a ship this turn.")
    maybe_ship = self.roads.get(from_loc)
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
    if from_loc in self.built_this_turn:
      raise InvalidMove("You may not move a ship that you built this turn.")
    maybe_dest = self.roads.get(to_loc)
    if maybe_dest:
      raise InvalidMove(f"There is already a {maybe_dest.road_type} at that destination.")
    adjacent_tiles = from_loc.get_adjacent_tiles()
    if self.pirate in adjacent_tiles:
      raise InvalidMove("You cannot move a ship that is next to the pirate.")

    # Check that this attaches to their existing network, without the original ship.
    # To do this, remove the old ship first, but restore it if any exception is thrown.
    old_ship = self.roads.pop(from_loc)
    old_source = old_ship.source
    try:
      self._check_road_building(to_loc, player_idx, "ship")
      self.add_road(Road(to_loc, "ship", player_idx))
    except:
      self.roads[old_ship.location] = old_ship
      raise

    self.event_log.append(Event("move_ship", "{player%s} moved a ship" % player_idx))
    # add_road will automatically recalculate from the new source, but we must still recalculate
    # ships' movable status from the old source in case the two locations are disconnected.
    self.recalculate_ships(old_source, player_idx)
    self.ships_moved = 1

  def discover_tiles(self, road):
    maybe_tiles = [self.tiles.get(loc) for loc in road.location.get_end_tiles()]
    discovered = [tile for tile in maybe_tiles if tile is not None and tile.tile_type == "discover"]
    collect_counts = collections.defaultdict(int)
    for tile in discovered:
      if self.discoverable_tiles:
        tile.tile_type = self.discoverable_tiles.pop()
        tile.is_land = tile.tile_type != "space"
        self._compute_coast()
        event_text = "{player%s} discovered {%s}" % (road.player, tile.tile_type)
        self.event_log.append(Event("discover", event_text))
        if tile.tile_type in ["space", "norsrc"]:
          continue
        if tile.number is None and self.discoverable_numbers:
          tile.number = self.discoverable_numbers.pop()
        if tile.tile_type in RESOURCES and self.remaining_resources(tile.tile_type) > 0:
          self.player_data[road.player].cards[tile.tile_type] += 1
        if tile.tile_type == "anyrsrc":
          collect_counts[road.player] += 1
    if collect_counts:
      self.collect_counts.update(collect_counts)
      self.next_collect_player()

  def handle_settle(self, location, player):
    loc = parse_location(location, CornerLocation)
    # Check that this is the right part of the turn.
    if self.game_phase.startswith("place"):
      if self.turn_phase != "settle":
        raise InvalidMove("You already placed your settlement; now you must build a road.")
    else:
      self._check_main_phase("settle", "build a settlement")
    # Check nothing else is already there.
    if loc in self.pieces:
      raise InvalidMove("You cannot settle on top of another player's settlement.")
    for adjacent in loc.get_adjacent_corners():
      if adjacent in self.pieces:
        raise InvalidMove("You cannot place a settlement next to existing settlement.")
    # Handle special settlement phase.
    if self.game_phase.startswith("place"):
      if self.placement_islands is not None:
        canonical_corner = self.corners_to_islands.get(loc)
        if canonical_corner not in self.placement_islands:
          raise InvalidMove("You cannot place your first settlements in that area.")
      self.add_piece(Piece(loc.x, loc.y, "settlement", player))
      self.event_log.append(Event("settlement", "{player%s} built a settlement" % player))
      self.turn_phase = "road"
      if self.game_phase == "place2":
        self.give_second_resources(player, loc)
      return
    # Check connected to one of the player's roads.
    for edge_loc in loc.get_edges():
      maybe_road = self.roads.get(edge_loc)
      if maybe_road and maybe_road.player == player:
        break
    else:
      raise InvalidMove("You must place your settlement next to one of your roads.")
    # Check player has enough settlements left.
    settle_count = len([
        p for p in self.pieces.values() if p.player == player and p.piece_type == "settlement"
    ])
    if settle_count >= 5:
      raise InvalidMove("You have no settlements remaining.")
    # Check resources and deduct from player.
    resources = [("rsrc1", 1), ("rsrc2", 1), ("rsrc3", 1), ("rsrc4", 1)]
    self._remove_resources(resources, player, "build a settlement")

    self.event_log.append(Event("settlement", "{player%s} built a settlement" % player))
    self.add_piece(Piece(loc.x, loc.y, "settlement", player))

  def _add_piece(self, piece):
    self.pieces[piece.location] = piece

  def add_piece(self, piece):
    self._add_piece(piece)

    self._add_player_port(piece.location, piece.player)

    # Check for breaking an existing longest road.
    # Start by calculating any players with an adjacent road/ship.
    players_to_check = set()
    for edge in piece.location.get_edges():
      if edge in self.roads:
        players_to_check.add(self.roads[edge].player)

    # Recompute longest road for each of these players.
    for player_idx in players_to_check:
      self.player_data[player_idx].longest_route = self._calculate_longest_road(player_idx)

    # Give longest road to the appropriate player.
    self._update_longest_route_player()

    # Calculate whether ships are open or closed.
    if piece.piece_type == "settlement":
      self.recalculate_ships(piece.location, piece.player)

    # Compute home islands / foreign landings for this piece.
    if self.game_phase.startswith("place"):
      self.home_corners[piece.player].append(piece.location)
    else:
      home_settled = [self.corners_to_islands[loc] for loc in self.home_corners[piece.player]]
      foreign_landed = [self.corners_to_islands[loc] for loc in self.foreign_landings[piece.player]]
      current_island = self.corners_to_islands[piece.location]
      if current_island not in home_settled + foreign_landed:
        self.event_log.append(Event("landing", "{player%s} settled on a new island" % piece.player))
        self.foreign_landings[piece.player].append(piece.location)

  def _add_player_port(self, location, player):
    """Sets the trade ratios for a player who built a settlement at this location."""
    port_type = self.port_corners.get(location)
    if port_type == "3":
      for rsrc in RESOURCES:
        new_ratio = min(self.player_data[player].trade_ratios[rsrc], 3)
        self.player_data[player].trade_ratios[rsrc] = new_ratio
    elif port_type:
      new_ratio = min(self.player_data[player].trade_ratios[port_type], 2)
      self.player_data[player].trade_ratios[port_type] = new_ratio

  def give_second_resources(self, player, corner_loc):
    tile_locs = [loc for loc in corner_loc.get_tiles() if loc in self.tiles]
    received = collections.defaultdict(int)
    for tile_loc in tile_locs:
      if self.tiles[tile_loc].number:
        received[self.tiles[tile_loc].tile_type] += 1

    if received.get("anyrsrc"):
      self.collect_counts[player] = received.pop("anyrsrc")
      self.turn_phase = "collect"

    for rsrc, count in received.items():
      self.player_data[player].cards[rsrc] += count
    text = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in received.items()])
    self.event_log.append(Event("collect", "{player%s} received %s" % (player, text)))

  def handle_city(self, location, player):
    loc = parse_location(location, CornerLocation)
    # Check that this is the right part of the turn.
    self._check_main_phase("city", "build a city")
    # Check this player already owns a settlement there.
    piece = self.pieces.get(loc)
    if not piece:
      raise InvalidMove("You need to build a settlement there first.")
    if piece.player != player:
      raise InvalidMove("You cannot upgrade another player's %s." % piece.piece_type)
    if piece.piece_type != "settlement":
      raise InvalidMove("You can only upgrade a settlement to a city.")
    # Check player has enough cities left.
    city_count = len([
        p for p in self.pieces.values() if p.player == player and p.piece_type == "city"
    ])
    if city_count >= 4:
      raise InvalidMove("You have no cities remaining.")
    # Check resources and deduct from player.
    resources = [("rsrc3", 2), ("rsrc5", 3)]
    self._remove_resources(resources, player, "build a city")

    self.pieces[loc].piece_type = "city"
    self.event_log.append(Event("city", "{player%s} upgraded a settlement to a city" % player))

  def handle_buy_dev(self, player):
    # Check that this is the right part of the turn.
    self._check_main_phase("buy_dev", "buy a development card")
    resources = [("rsrc1", 1), ("rsrc3", 1), ("rsrc5", 1)]
    if len(self.dev_cards) < 1:
      raise InvalidMove("There are no development cards left.")
    self._remove_resources(resources, player, "buy a development card")
    card_type = self.add_dev_card(player)
    self.event_log.append(Event(
        "buy_dev", "{player%s} bought a dev card" % player,
        "{player%s} bought a %s" % (player, card_type), [player],
    ))

  def add_dev_card(self, player):
    card_type = self.dev_cards.pop()
    self.player_data[player].cards[card_type] += 1
    self.player_data[player].unusable[card_type] += 1
    return card_type

  def handle_play_dev(self, card_type, resource_selection, player):
    if card_type not in PLAYABLE_DEV_CARDS:
      raise InvalidMove("%s is not a playable development card." % card_type)
    if card_type == "knight":
      if self.turn_phase not in ["dice", "main"]:
        raise InvalidMove(
            "You must play the knight before you roll the dice or during the "
            "build/trade part of your turn."
        )
    else:
      self._check_main_phase("play_dev", "play a development card")
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
    self.event_log.append(Event("knight", "{player%s} played a knight" % player_idx))
    if self.player_data[player_idx].knights_played > current_max >= 2:
      if self.largest_army_player != player_idx:
        # If largest army changed hands, add an event log.
        event_text = "{player%s} took largest army" % player_idx
        if self.largest_army_player is not None:
          event_text += " from {player%s}" % self.largest_army_player
        self.event_log.append(Event("largest_army", event_text))
      self.largest_army_player = player_idx
    self.turn_phase = "robber"

  def _handle_road_building(self, player):
    # Check that the player has enough roads/ships left.
    usable = ["road", "ship"] if self.options.seafarers else ["road"]
    used = len([r for r in self.roads.values() if r.player == player and r.road_type in usable])
    if used >= 15 * len(usable):
      raise InvalidMove("You have no roads remaining.")
    self.event_log.append(Event("roadbuilding", "{player%s} played a road building card" % player))
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

    received_text = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in selection.items()])
    self.event_log.append(Event("yearofplenty", "{player%s} took " % player + received_text))
    for rsrc, value in selection.items():
      self.player_data[player].cards[rsrc] += value

  def _handle_monopoly(self, player, resource_selection):
    self._validate_selection(resource_selection)
    if len(resource_selection) != 1 or sum(resource_selection.values()) != 1:
      raise InvalidMove("You must choose exactly one resource to monopolize.")
    card_type = list(resource_selection.keys())[0]
    self.event_log.append(Event(
        "monopoly", "{player%s} played a monopoly on {%s}" % (player, card_type)))
    counts = {}
    for opponent_idx, opponent in enumerate(self.player_data):
      if player == opponent_idx:
        continue
      opp_count = opponent.cards[card_type]
      if opp_count:
        counts[opponent_idx] = opp_count
      opponent.cards[card_type] -= opp_count
      self.player_data[player].cards[card_type] += opp_count
    event_text = ", ".join(["%s from {player%s}" % (count, opp) for opp, count in counts.items()])
    self.event_log.append(Event("monopoly", "{player%s} took " % player + event_text))

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
    self._check_main_phase("trade_offer", "make a trade")
    self._validate_trade(offer, player)
    self.trade_offer = offer
    # TODO: maybe we don't want to actually clear the counter offers?
    self.counter_offers.clear()

  def handle_counter_offer(self, offer, player):
    if self.turn_idx == player:
      raise InvalidMove("You cannot make a counter-offer on your turn.")
    self._check_main_phase("counter_offer", "make a counter-offer")
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
    self._check_main_phase("accept_counter", "make a trade")
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
      print(f"Offers do not match - {sorted(my_want.items())} vs {sorted(their_give.items())}")
      raise InvalidMove("The player changed their offer.")
    if sorted(my_give.items()) != sorted(their_want.items()):
      print(f"Offers do not match - {sorted(my_give.items())} vs {sorted(their_want.items())}")
      raise InvalidMove("The player changed their offer.")

    # Validate that both players have the resources to make the trade.
    self._validate_trade({self.WANT: my_want, self.GIVE: my_give}, player)
    self._validate_trade({self.WANT: their_want, self.GIVE: their_give}, counter_player)

    gave_text = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in my_give.items()])
    recv_text = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in my_want.items()])
    self.event_log.append(Event(
        "trade", "{player%s} traded %s for %s with {player%s}" % (
            player, gave_text, recv_text, counter_player),
    ))
    for rsrc, count in my_give.items():
      self.player_data[player].cards[rsrc] -= count
      self.player_data[counter_player].cards[rsrc] += count
    for rsrc, count in my_want.items():
      self.player_data[player].cards[rsrc] += count
      self.player_data[counter_player].cards[rsrc] -= count

    self.counter_offers.clear()
    # TODO: Do we want to reset the trade offer here?

  def handle_trade_bank(self, offer, player):
    self._check_main_phase("trade_bank", "make a trade")
    self._validate_trade(offer, player)
    # Also validate that ratios are correct.
    requested = sum(offer[self.WANT].values())
    available = 0
    for rsrc, give in offer[self.GIVE].items():
      if give == 0:
        continue
      ratio = self.player_data[player].trade_ratios[rsrc]
      if give % ratio != 0:
        raise InvalidMove("You must trade {%s} with the bank at a %s:1 ratio." % (rsrc, ratio))
      available += give // ratio
    if available != requested:
      raise InvalidMove(
          "You should receive %s resources, but you requested %s." % (available, requested),
      )
    # TODO: make sure there is enough left in the bank.

    gave_text = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in offer[self.GIVE].items()])
    recv_text = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in offer[self.WANT].items()])
    self.event_log.append(Event(
        "trade", "{player%s} traded %s with the bank for %s" % (player, gave_text, recv_text)))
    # Now, make the trade.
    for rsrc, want in offer[self.WANT].items():
      self.player_data[player].cards[rsrc] += want
    for rsrc, give in offer[self.GIVE].items():
      self.player_data[player].cards[rsrc] -= give

  def add_tile(self, tile):
    self.tiles[tile.location] = tile

  def add_port(self, port):
    self.ports[port.location] = port

  def _compute_edges(self):
    # Go back and figure out which ones are corners.
    # TODO: unit test this function.
    for location, tile_data in self.tiles.items():
      locs = location.get_adjacent_tiles()
      exists = [loc in self.tiles for loc in locs]
      tile_rotation = tile_data.rotation
      if exists.count(True) > 4:
        tile_data.variant = ""
      elif exists.count(True) == 3:
        tile_data.variant = "corner"
      else:
        # Takes advantage of the return order of get_adjacent_tiles.
        upper_left = locs[(tile_rotation+2) % 6]
        if upper_left in self.tiles:
          tile_data.variant = "edgeleft"
        else:
          tile_data.variant = "edgeright"

  def _compute_coast(self):
    for location, tile_data in self.tiles.items():
      if tile_data.is_land:
        continue
      adjacent_tiles = [self.tiles.get(loc) for loc in location.get_adjacent_tiles()]
      lands = [
          idx for idx, tile in enumerate(adjacent_tiles)
          if tile and tile.is_land and tile.tile_type != "discover"
      ]
      tile_data.land_rotations = lands

  def dev_card_counts(self):
    counts = {"knight": 14, "monopoly": 2, "roadbuilding": 2, "yearofplenty": 2}
    counts.update({card: 1 for card in VICTORY_CARDS})
    if self.options.extra_build:
      for card, count in {"knight": 6, "monopoly": 1, "roadbuilding": 1, "yearofplenty": 1}.items():
        counts[card] = counts[card] + count
    return counts

  def init_dev_cards(self):
    dev_cards = sum([[card] * count for card, count in self.dev_card_counts().items()], [])
    random.shuffle(dev_cards)
    self.dev_cards = dev_cards

  def init_robber(self):
    empty = [tile for tile in self.tiles.values() if tile.is_land and not tile.number]
    if empty:
      self.robber = empty[0].location

  def _compute_ports(self):
    self.port_corners.clear()
    for port in self.ports.values():
      rotation = (port.rotation + 6) % 6
      if rotation == 0:
        corners = [port.location.get_lower_left_corner(), port.location.get_lower_right_corner()]
      if rotation == 1:
        corners = [port.location.get_lower_left_corner(), port.location.get_left_corner()]
      if rotation == 2:
        corners = [port.location.get_upper_left_corner(), port.location.get_left_corner()]
      if rotation == 3:
        corners = [port.location.get_upper_left_corner(), port.location.get_upper_right_corner()]
      if rotation == 4:
        corners = [port.location.get_upper_right_corner(), port.location.get_right_corner()]
      if rotation == 5:
        corners = [port.location.get_lower_right_corner(), port.location.get_right_corner()]
      for corner in corners:
        self.port_corners[corner] = port.port_type

  def shuffle_land_tiles(self, tile_locs):
    tile_types = [self.tiles[tile_loc].tile_type for tile_loc in tile_locs]
    random.shuffle(tile_types)
    for idx, tile_loc in enumerate(tile_locs):
      self.tiles[tile_loc].tile_type = tile_types[idx]

  def init_numbers(self, start_location, number_sequence):
    directions = [(-3, 1), (0, 2), (3, 1), (3, -1), (0, -2), (-3, -1)]
    dir_idx = 0
    number_idx = 0
    bad_dir_count = 0
    visited = set()
    loc = (start_location[0] - directions[dir_idx][0], start_location[1] - directions[dir_idx][1])
    while number_idx < len(number_sequence):
      if bad_dir_count >= len(directions):
        raise RuntimeError("You screwed it up.")
      new_loc = (loc[0] + directions[dir_idx][0], loc[1] + directions[dir_idx][1])
      if not self.tiles.get(new_loc):
        dir_idx = (dir_idx+1) % len(directions)
        bad_dir_count += 1
        continue
      if new_loc in visited or not self.tiles[new_loc].is_land:
        dir_idx = (dir_idx+1) % len(directions)
        bad_dir_count += 1
        continue
      bad_dir_count = 0
      loc = new_loc
      visited.add(loc)
      if self.tiles[loc].tile_type == "norsrc":
        continue
      self.tiles[loc].number = number_sequence[number_idx]
      number_idx += 1

  def shuffle_ports(self):
    port_types = [port.port_type for port in self.ports.values()]
    random.shuffle(port_types)
    for idx, port in enumerate(self.ports.values()):
      port.port_type = port_types[idx]

  def _is_connecting_tile(self, tile):
    if self.options.norsrc_is_connected:
      return tile.is_land
    return tile.number

  def _compute_contiguous_islands(self):
    self.corners_to_islands.clear()
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
        islands[-1].add(corner_loc)
      loc_stack = tile.location.get_adjacent_tiles()
      while loc_stack:
        next_loc = loc_stack.pop()
        if next_loc in seen_tiles:
          continue
        if next_loc not in self.tiles:
          continue
        if not self._is_connecting_tile(self.tiles[next_loc]):
          continue
        seen_tiles.add(next_loc)
        for corner_loc in next_loc.get_corner_locations():
          islands[-1].add(corner_loc)
        loc_stack.extend(next_loc.get_adjacent_tiles())

    # Convert a group of sets into a map of corner -> canonical corner.
    for corner_set in islands:
      canonical_corner = min(corner_set)
      for corner in corner_set:
        self.corners_to_islands[corner] = canonical_corner

  def recompute(self):
    self._compute_contiguous_islands()
    self._compute_coast()
    self._compute_edges()
    self._compute_ports()


class Scenario(metaclass=abc.ABCMeta):

  @classmethod
  @abc.abstractmethod
  def preview(cls, state):
    raise NotImplementedError

  @classmethod
  @abc.abstractmethod
  def init(cls, state):
    raise NotImplementedError

  @classmethod
  def mutate_options(cls, options):
    pass

  @classmethod
  def load_file(cls, state, filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding="ascii") as data:
      json_data = json.load(data)
      state.parse_tiles(json_data["tiles"])
      state.parse_ports(json_data["ports"])
    state.recompute()


class StandardMap(Scenario):

  @classmethod
  def preview(cls, state):
    if len(state.player_data) < 2 or len(state.player_data) > 6:
      raise InvalidPlayer("Must have between 2 and 6 players.")
    if len(state.player_data) <= 4:
      cls.load_file(state, "standard4.json")
    else:
      cls.load_file(state, "standard6.json")
    # TODO: set all land types to "random" or something the UI can render, set numbers to "?"

  @classmethod
  def init(cls, state):
    if len(state.player_data) < 2 or len(state.player_data) > 6:
      raise InvalidPlayer("Must have between 2 and 6 players.")
    if len(state.player_data) <= 4:
      cls.load_file(state, "standard4.json")
    else:
      cls.load_file(state, "standard6.json")
    land_locs = [loc for loc, tile in state.tiles.items() if tile.is_land]
    state.shuffle_land_tiles(land_locs)
    if len(state.player_data) <= 4:
      state.init_numbers((7, 1), TILE_NUMBERS)
    else:
      corner_choice = random.choice([(7, 1), (-2, 4), (-2, 8)])
      state.init_numbers(corner_choice, EXTRA_NUMBERS)
    state.shuffle_ports()
    state.recompute()
    state.init_dev_cards()
    state.init_robber()


class BeginnerMap(Scenario):

  @classmethod
  def preview(cls, state):
    pass

  @classmethod
  def init(cls, state):
    if len(state.player_data) < 3 or len(state.player_data) > 4:
      raise InvalidPlayer("Must have between 3 and 4 players.")
    filename = "beginner4.json" if len(state.player_data) == 4 else "beginner3.json"
    with open(os.path.join(os.path.dirname(__file__), filename), encoding="ascii") as data:
      json_data = json.load(data)
      state.parse_tiles(json_data["tiles"])
      state.parse_ports(json_data["ports"])
      state.parse_pieces(json_data["pieces"])
      state.parse_roads(json_data["roads"])
    state.recompute()
    state.init_dev_cards()
    state.init_robber()
    state.give_second_resources(0, CornerLocation(6, 4))
    state.give_second_resources(1, CornerLocation(12, 4))
    state.give_second_resources(2, CornerLocation(6, 6))
    if len(state.player_data) == 4:
      state.give_second_resources(3, CornerLocation(9, 3))
    state.game_phase = "main"
    state.turn_phase = "dice"

  @classmethod
  def mutate_options(cls, options):
    options["friendly_robber"].default = True


class TestMap(Scenario):

  @classmethod
  def preview(cls, state):
    pass

  @classmethod
  def init(cls, state):
    cls.load_file(state, "test.json")
    state.recompute()
    state.init_dev_cards()


class SeafarerScenario(Scenario, metaclass=abc.ABCMeta):

  @classmethod
  def init(cls, state):
    if len(state.player_data) < 3:
      raise InvalidPlayer("Must be played with at least 3 players.")
    if len(state.player_data) > 4:
      raise InvalidPlayer("Cannot be played with more than 4 players.")

  @classmethod
  def mutate_options(cls, options):
    options["seafarers"].force(True)
    options["foreign_island_points"].default = 2


class SeafarerShores(SeafarerScenario):

  @classmethod
  def preview(cls, state):
    pass

  @classmethod
  def init(cls, state):
    super().init(state)
    if len(state.player_data) == 3:
      cls.load_file(state, "shores3.json")
      state.robber = TileLocation(19, 3)
      state.pirate = TileLocation(10, 12)
    elif len(state.player_data) == 4:
      cls.load_file(state, "shores4.json")
      state.robber = TileLocation(7, 5)
      state.pirate = TileLocation(10, 14)
      state.shuffle_ports()
    else:
      raise InvalidPlayer("Must have 3 or 4 players.")
    state.recompute()
    state.init_dev_cards()
    state.placement_islands = [state.corners_to_islands[(3, 1)]]

  @classmethod
  def mutate_options(cls, options):
    super().mutate_options(options)
    options["victory_points"].default = 14


class SeafarerIslands(SeafarerScenario):

  @classmethod
  def preview(cls, state):
    pass

  @classmethod
  def init(cls, state):
    super().init(state)
    if len(state.player_data) == 3:
      cls.load_file(state, "islands3.json")
      state.robber = TileLocation(1, 3)
      state.pirate = TileLocation(10, 6)
    elif len(state.player_data) == 4:
      cls.load_file(state, "islands4.json")
      state.robber = TileLocation(16, 8)
      state.pirate = TileLocation(10, 12)
    else:
      raise InvalidPlayer("Must have 3 or 4 players.")
    state.recompute()
    state.init_dev_cards()

  @classmethod
  def mutate_options(cls, options):
    super().mutate_options(options)
    options["victory_points"].default = 13


class SeafarerDesert(SeafarerScenario):

  @classmethod
  def preview(cls, state):
    pass

  @classmethod
  def init(cls, state):
    super().init(state)
    if len(state.player_data) == 3:
      cls.load_file(state, "desert3.json")
      state.robber = TileLocation(16, 4)
      state.pirate = TileLocation(10, 12)
    elif len(state.player_data) == 4:
      cls.load_file(state, "desert4.json")
      state.robber = TileLocation(16, 4)
      state.pirate = TileLocation(10, 14)
    else:
      raise InvalidPlayer("Must have 3 or 4 players.")
    state.recompute()
    state.init_dev_cards()
    state.placement_islands = [state.corners_to_islands[(3, 1)]]

  @classmethod
  def mutate_options(cls, options):
    super().mutate_options(options)
    options["victory_points"].default = 14
    options["norsrc_is_connected"].force(False)


class SeafarerFog(SeafarerScenario):

  @classmethod
  def preview(cls, state):
    pass

  @classmethod
  def init(cls, state):
    super().init(state)
    if len(state.player_data) == 3:
      cls.load_file(state, "fog3.json")
      state.robber = TileLocation(4, 6)
      state.pirate = TileLocation(13, 1)
      state.placement_islands = [state.corners_to_islands[loc] for loc in [(3, 5), (21, 9)]]
      state.discoverable_numbers = [3, 3, 4, 5, 6, 8, 9, 10, 11, 12]
    elif len(state.player_data) == 4:
      cls.load_file(state, "fog4.json")
      state.robber = TileLocation(16, 14)
      state.pirate = TileLocation(13, 1)
      state.placement_islands = [state.corners_to_islands[loc] for loc in [(3, 3), (9, 13)]]
      state.discoverable_numbers = [3, 4, 5, 6, 8, 9, 10, 11, 11, 12]
    else:
      raise InvalidPlayer("Must have 3 or 4 players.")
    state.discoverable_tiles = [
        "space", "space", "anyrsrc", "anyrsrc", "rsrc1", "rsrc2", "rsrc3", "rsrc3", "rsrc4",
        "rsrc4", "rsrc5", "rsrc5",
    ]
    state.recompute()
    state.init_dev_cards()
    random.shuffle(state.discoverable_tiles)
    random.shuffle(state.discoverable_numbers)

  @classmethod
  def mutate_options(cls, options):
    super().mutate_options(options)
    options["victory_points"].default = 12
    options["foreign_island_points"].default = 0


class MapMakerState(IslandersState):

  def handle(self, player_idx, data):
    if data["type"] not in ["robber", "pirate", "end_turn"]:
      raise InvalidMove("This is the mapmaker. You can only change tiles.")
    if data["type"] == "end_turn":
      self.turn_idx = (self.turn_idx + 1) % len(self.player_data)
      return
    loc = TileLocation(*data["location"])
    if self.turn_idx == 1 and self.tiles[loc].is_land:
      # Numbers
      num = self.tiles[loc].number
      if num is None:
        num = 2
      elif num == 12:
        num = None
      else:
        num += 1
      self.tiles[loc].number = num
      return
    if self.turn_idx == 1:
      # Ports
      port_order = RESOURCES + ["3"]
      port_rot = 0
      if self.tiles.get(loc):
        port_rot = self.tiles[loc].rotation
      maybe_port = self.ports.get(loc)
      if not maybe_port:
        self.add_port(Port(loc.x, loc.y, "rsrc1", port_rot))
        return
      port_idx = port_order.index(maybe_port.port_type)
      if port_idx + 1 == len(port_order):
        del self.ports[loc]
        return
      self.ports[loc].port_type = port_order[port_idx + 1]
      return
    if self.turn_idx == 2:
      # Rotation
      self.tiles[loc].rotation += 1
      self.tiles[loc].rotation %= 6
      if loc in self.ports:
        self.ports[loc].rotation += 1
        self.ports[loc].rotation %= 6
      return
    # Change tile types or add tiles.
    tile_order = ["space"] + RESOURCES + ["anyrsrc", "norsrc", "discover"]
    idx = tile_order.index(self.tiles[loc].tile_type)
    new_type = tile_order[(idx+1) % len(tile_order)]
    self.tiles[loc].tile_type = new_type
    if new_type == "norsrc":
      self.tiles[loc].is_land = True
      self.tiles[loc].number = None
    elif new_type == "discover":
      self.tiles[loc].is_land = True
    elif new_type != "space":
      self.tiles[loc].is_land = True
      if self.tiles[loc].number is None:
        self.tiles[loc].number = 2
    else:
      self.tiles[loc].is_land = False
      self.tiles[loc].number = None
    for location in loc.get_adjacent_tiles():
      if location not in self.tiles:
        self.add_tile(Tile(location.x, location.y, "space", False, None))


class MapMaker(Scenario):

  @classmethod
  def preview(cls, state):
    pass

  @classmethod
  def init(cls, state):
    state.add_tile(Tile(4, 2, "space", False, None))
    state.game_phase = "main"
    state.turn_phase = "main"
    state.player_data[0].name = "tiles"
    state.player_data[1].name = "numbers/ports"
    if len(state.player_data) > 2:
      state.player_data[2].name = "rotations"


class IslandersGame(BaseGame):

  # The order of this dictionary determines the method resolution order of the created class.
  SCENARIOS = collections.OrderedDict([
      ("Standard Map", StandardMap),
      ("Beginner's Map", BeginnerMap),
      ("Test Map", TestMap),
      ("Heading for New Shores", SeafarerShores),
      ("The Four Islands", SeafarerIslands),
      ("Through the Desert", SeafarerDesert),
      ("The Fog Islands", SeafarerFog),
      ("Map Maker", MapMaker),
  ])

  def __init__(self):
    self.game = None
    self.scenario = list(self.SCENARIOS.keys())[0]
    self.game_class = self.get_game_class(self.scenario)
    self.choices = Options()
    self.connected = set()
    self.host = None
    # player_sessions starts as a map of session to Player. once the game
    # starts, it becomes a map of session to player_index. TODO: cleanup.
    self.player_sessions = collections.OrderedDict()

  def game_url(self, game_id):
    return f"/islanders/islanders.html?game_id={game_id}"

  def game_status(self):
    if self.game is None:
      return "unstarted islanders game (%s players)" % len(self.player_sessions)
    return self.game.game_status()

  @classmethod
  def parse_json(cls, data):
    gamedata = json.loads(data)
    if not gamedata:
      return cls()
    game = cls()
    game.scenario = gamedata.pop("scenario")
    if game.scenario not in cls.SCENARIOS:
      raise InvalidMove("Unknown scenario %s" % game.scenario)
    game.game_class = cls.get_game_class(game.scenario)
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
    return json.dumps(output, cls=CustomEncoder)

  def for_player(self, session):
    if self.game is None:
      player_idx = None
      if session in self.player_sessions:
        player_idx = list(self.player_sessions.keys()).index(session)
      # TODO: update the javascript to handle undefined values for all of the attributes of
      # the state object that we don't have before the game starts.
      over = False
      data = self.game_class().for_player(None)
      data.update({
          "type": "game_state",
          "host": self.host == session,
          "you": player_idx,
          "started": False,
          "player_data": [player.json_for_player(over) for player in self.player_sessions.values()],
      })

      data["options"] = collections.OrderedDict([(key, self.choices[key]) for key in self.choices])
      data["scenario"] = GameOption(
          name="Scenario", default=list(self.SCENARIOS.keys())[0],
          choices=list(self.SCENARIOS.keys()), value=self.scenario,
      )

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
      self.update_player_count()
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
    if data.get("type") == "scenario":
      return self.handle_change_scenario(session, data)
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

    if len(self.player_sessions) >= 6:
      raise TooManyPlayers("There are no open slots.")

    colors = set(["red", "blue", "forestgreen", "darkviolet", "saddlebrown", "deepskyblue"])
    unused_colors = colors - {player.color for player in self.player_sessions.values()}
    if not unused_colors:
      raise TooManyPlayers("There are too many players.")

    # TODO: just use some arguments and stop creating fake players. This requires that we clean
    # up the javascript to know what to do with undefined values.
    self.player_sessions[session] = Player(list(unused_colors)[0], data["name"].strip())
    self.update_player_count()

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

    player_data = list(self.player_sessions.items())
    if len(player_data) < 2:
      raise InvalidMove("The game must have at least two players to start.")

    self.update_rulesets_and_choices(data["options"])

    game = self.game_class()
    new_sessions = {}
    random.shuffle(player_data)
    for idx, (player_session, player_info) in enumerate(player_data):
      game.add_player(player_info.color, player_info.name)
      new_sessions[player_session] = idx
    # NOTE: init after initializing players - the number of players matters to init.
    game.options = self.choices
    self.SCENARIOS[self.scenario].init(game)
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

  def update_rulesets_and_choices(self, choices):
    if choices.keys() - self.choices.keys():
      raise InvalidMove("Unknown option(s) %s" % ", ".join(choices.keys() - self.choices.keys()))
    # Set any valid options specified by the user, except options that are forced by the ruleset.
    # Set any options not specified by the user to their default values.
    for option_name in self.choices:
      if self.choices[option_name].forced or option_name not in choices:
        self.choices[option_name].set(self.choices[option_name].default)
      else:
        self.choices[option_name].set(choices[option_name])

  def handle_change_scenario(self, session, data):
    if self.game is not None:
      raise InvalidMove("The game has already started.")
    if session != self.host:
      raise InvalidMove("You are not the host. Only the host can select the scenario.")
    scenario = data["scenario"]
    if scenario not in self.SCENARIOS:
      raise InvalidMove("Unknown scenario %s" % scenario)

    self.scenario = scenario
    self.game_class = self.get_game_class(self.scenario)

    options = Options()
    self.SCENARIOS[self.scenario].mutate_options(options)
    # Preserve user choices where the user selected something and the default has not changed.
    for key, option in options.items():
      old = self.choices[key]
      option_unchanged = old.default == option.default and old.forced == option.forced
      user_selected = old.default != old.value
      if option_unchanged and user_selected:
        option.set(self.choices[key].value)
      else:
        option.set(option.default)
    self.choices = options
    self.update_player_count()

  def update_player_count(self):
    self.choices["extra_build"].force(len(self.player_sessions) > 4)

  @classmethod
  def get_game_class(cls, scenario):
    if scenario == "Map Maker":
      return MapMakerState
    return IslandersState
