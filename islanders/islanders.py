import abc
import collections
import json
from random import SystemRandom
from typing import Optional
import os

from game import (
  BaseGame,
  ValidatePlayer,
  CustomEncoder,
  InvalidInput,
  UnknownMove,
  InvalidMove,
  InvalidPlayer,
  TooManyPlayers,
  NotYourTurn,
)

random = SystemRandom()

# pylint: disable=consider-using-f-string
# ruff: noqa: UP031

RESOURCES = ["rsrc1", "rsrc2", "rsrc3", "rsrc4", "rsrc5"]
TRADABLES = RESOURCES + ["gold"]
PLAYABLE_DEV_CARDS = ["yearofplenty", "monopoly", "roadbuilding", "knight"]
VICTORY_CARDS = ["palace", "chapel", "university", "market", "library"]
TREASURES = ["collect1", "collect2", "collectpi", "roadbuilding", "takedev"]
TILE_NUMBERS = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]
EXTRA_NUMBERS = [
  2, 5, 4, 6, 3, 9, 8, 11, 11, 10, 6, 3, 8, 4, 8, 10, 11, 12, 10, 5, 4, 9, 5, 9, 12, 3, 12, 6
]  # fmt: skip


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
  "Event", ["event_type", "public_text", "secret_text", "visible_players"]
)


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
    self["robber"] = GameOption("Robber", default=True, forced=True, hidden=True)
    self["pirate"] = GameOption("Pirate", default=False, forced=True, hidden=True)
    self["max_cities"] = GameOption(
      "Max Cities", default=4, forced=True, hidden=True, choices=[4, 8]
    )
    self["gold"] = GameOption("Gold Trading", default=False, forced=True, hidden=True)
    self["friendly_robber"] = GameOption("Friendly Robber", default=False)
    self["randomness"] = GameOption("Randomness", default=36, choices=list(range(37)))
    self["victory_points"] = GameOption("Victory Points", default=10, choices=list(range(8, 22)))
    self["immediate_dev"] = GameOption("", default=False, forced=True, hidden=True)
    self["shuffle_discards"] = GameOption(
      "Shuffle Discards", default=False, forced=True, hidden=True
    )
    self["foreign_island_points"] = GameOption(
      "", default=0, choices=[0, 1, 2], forced=True, hidden=True
    )
    self["bury_treasure"] = GameOption("Bury Treasure", default=False, forced=True, hidden=True)
    self["norsrc_is_connected"] = GameOption("", default=True, forced=True, hidden=True)
    schoices = [("settlement", "settlement"), ("settlement", "city"), ("settlement",) * 3]
    self["placements"] = GameOption(
      "", default=("settlement", "settlement"), forced=True, hidden=True, choices=schoices
    )
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
    return CornerLocation(self.x - 1, self.y - 1)

  def get_upper_right_corner(self):
    return CornerLocation(self.x + 1, self.y - 1)

  def get_right_corner(self):
    return CornerLocation(self.x + 2, self.y)

  def get_lower_right_corner(self):
    return CornerLocation(self.x + 1, self.y + 1)

  def get_lower_left_corner(self):
    return CornerLocation(self.x - 1, self.y + 1)

  def get_left_corner(self):
    return CornerLocation(self.x - 2, self.y)

  def get_adjacent_tiles(self):
    # NOTE: order matters here. Index in this array lines up with rotation semantics.
    return [
      self.get_lower_tile(),
      self.get_lower_left_tile(),
      self.get_upper_left_tile(),
      self.get_upper_tile(),
      self.get_upper_right_tile(),
      self.get_lower_right_tile(),
    ]

  def get_corner_locations(self):
    return [
      self.get_upper_left_corner(),
      self.get_upper_right_corner(),
      self.get_lower_left_corner(),
      self.get_lower_right_corner(),
      self.get_left_corner(),
      self.get_right_corner(),
    ]

  def get_corners_for_rotation(self, rotation):
    if rotation == 0:
      return [self.get_lower_left_corner(), self.get_lower_right_corner()]
    if rotation == 1:
      return [self.get_lower_left_corner(), self.get_left_corner()]
    if rotation == 2:
      return [self.get_upper_left_corner(), self.get_left_corner()]
    if rotation == 3:
      return [self.get_upper_left_corner(), self.get_upper_right_corner()]
    if rotation == 4:
      return [self.get_upper_right_corner(), self.get_right_corner()]
    if rotation == 5:
      return [self.get_lower_right_corner(), self.get_right_corner()]
    raise ValueError(f"Invalid rotation {rotation}")

  def get_edge_locations(self):
    # Order matters here.
    corners = [
      self.get_left_corner(),
      self.get_upper_left_corner(),
      self.get_upper_right_corner(),
      self.get_right_corner(),
      self.get_lower_right_corner(),
      self.get_lower_left_corner(),
    ]
    edges = []
    for idx, corner in enumerate(corners):
      edges.append(corner.get_edge(corners[(idx + 1) % 6]))
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
    return [lower_hex, upper_hex, middle_hex]  # pylint: disable=possibly-used-before-assignment

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
      assert (right_x, right_y) in [
        (left_x + 2, left_y),
        (left_x - 1, left_y - 1),
        (left_x - 1, left_y + 1),
      ]
    else:
      assert (right_x, right_y) in [
        (left_x - 2, left_y),
        (left_x + 1, left_y - 1),
        (left_x + 1, left_y + 1),
      ]
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
  TYPES = ("road", "ship")

  def __init__(
    self, location, road_type, player, *, closed=False, movable=True, source=None, conquered=False
  ):
    assert road_type in self.TYPES
    self.location = EdgeLocation(*location)
    self.road_type = road_type
    self.player = player
    self.closed = closed
    self.movable = movable
    self.source = source
    self.conquered = conquered

  def json_repr(self):
    data = {
      "location": self.location,
      "road_type": self.road_type,
      "player": self.player,
      "conquered": self.conquered,
    }
    if self.road_type == "ship":
      data.update({"closed": self.closed, "movable": self.movable, "source": self.source})
    return data

  @staticmethod
  def parse_json(value):
    # TODO: maybe this assert should go into the constructor?
    source = None
    if value["road_type"] == "ship":
      assert value.get("source") is not None
      source = CornerLocation(*value["source"])
    return Road(
      value["location"],
      value["road_type"],
      value["player"],
      closed=value.get("closed", False),
      movable=value.get("movable", True),
      source=source,
      conquered=value.get("conquered", False),
    )

  def __str__(self):
    return str(self.json_repr())


class Knight:
  def __init__(self, location, player, source, *, movement=0):
    self.location = EdgeLocation(*location)
    self.player = player
    self.source = EdgeLocation(*source)
    self.movement = movement

  def json_repr(self):
    return {
      "location": self.location,
      "player": self.player,
      "source": self.source,
      "movement": self.movement,
    }

  @staticmethod
  def parse_json(value):
    return Knight(value["location"], value["player"], value["source"], movement=value["movement"])

  def __str__(self):
    return str(self.json_repr())


class Piece:
  TYPES = ("settlement", "city")

  def __init__(self, x, y, piece_type, player, *, conquered=False):
    assert piece_type in self.TYPES
    self.location = CornerLocation(x, y)
    self.piece_type = piece_type
    self.player = player
    self.conquered = conquered

  def json_repr(self):
    return {
      "location": self.location,
      "piece_type": self.piece_type,
      "player": self.player,
      "conquered": self.conquered,
    }

  @staticmethod
  def parse_json(value):
    return Piece(
      value["location"][0],
      value["location"][1],
      value["piece_type"],
      value["player"],
      conquered=value.get("conquered", False),
    )

  def __str__(self):
    return str(self.json_repr())


class Tile:
  def __init__(
    self,
    x,
    y,
    tile_type,
    is_land,
    number,
    *,
    rotation=0,
    variant="",
    barbarians=0,
    conquered=False,
    land_rotations=None,
  ):
    self.location = TileLocation(x, y)
    self.tile_type = tile_type
    self.is_land = is_land
    self.number = number
    self.rotation = rotation
    self.variant = variant
    self.barbarians = barbarians
    self.conquered = conquered
    self.land_rotations = land_rotations or []

  def json_repr(self):
    return {attr: getattr(self, attr) for attr in self.__dict__}

  @staticmethod
  def parse_json(value):
    return Tile(
      value["location"][0],
      value["location"][1],
      value["tile_type"],
      value["is_land"],
      value["number"],
      rotation=value["rotation"],
      variant=value.get("variant", ""),
      barbarians=value.get("barbarians", 0),
      conquered=value.get("conquered", False),
      land_rotations=value.get("land_rotations") or [],
    )

  def __str__(self):
    return str(self.json_repr())


class Port:
  def __init__(self, x, y, port_type, rotation=0):
    self.location = TileLocation(x, y)
    self.port_type = port_type
    self.rotation = rotation

  def json_repr(self):
    return {"location": self.location, "port_type": self.port_type, "rotation": self.rotation}

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
    self.buried_treasure = 0
    self.cards = collections.defaultdict(int)
    self.trade_ratios = collections.defaultdict(lambda: 4)
    self.unusable = collections.defaultdict(int)
    self.gold_traded = 0

  def json_repr(self):
    defaultdict_attrs = ["cards", "trade_ratios", "unusable"]
    data = {attr: getattr(self, attr) for attr in self.__dict__.keys() - set(defaultdict_attrs)}
    for attr in defaultdict_attrs:
      data[attr] = dict(getattr(self, attr))
    data["trade_ratios"]["default"] = self.trade_ratios.default_factory()
    return data

  @staticmethod
  def parse_json(value):
    defaultdict_attrs = ["cards", "trade_ratios", "unusable"]
    player = Player(None, None)
    for attr in defaultdict_attrs:
      getattr(player, attr).update(value[attr])
    value.setdefault("buried_treasure", 0)  # Backwards compatibility
    for attr in set(player.__dict__.keys()) - set(defaultdict_attrs):
      if attr in value:
        setattr(player, attr, value[attr])
    ratio_default = player.trade_ratios.pop("default", None)
    if ratio_default is not None:
      player.trade_ratios.default_factory = lambda: ratio_default
    return player

  def __str__(self):
    return str(self.json_repr())

  def json_for_player(self, is_over):
    ret = {
      "color": self.color,
      "name": self.name,
      "armies": self.knights_played,
      "longest_route": self.longest_route,
      "buried_treasure": self.buried_treasure,
      "resource_cards": self.resource_card_count(),
      "gold": self.cards.get("gold", 0),
      "dev_cards": self.dev_card_count(),
      "trade_ratios": {rsrc: self.trade_ratios[rsrc] for rsrc in RESOURCES},
      "points": 0,
    }
    ret["trade_ratios"]["default"] = self.trade_ratios.default_factory()
    if is_over:
      ret["dev_cards"] = {
        name: count
        for name, count in self.cards.items()
        if name in (PLAYABLE_DEV_CARDS + VICTORY_CARDS)
      }
    return ret

  def too_many_cards(self):
    threshold = 8
    if self.buried_treasure >= 1:
      threshold += 2
    return self.resource_card_count() >= threshold

  def resource_card_count(self):
    return sum(self.cards[x] for x in RESOURCES)

  def dev_card_count(self):
    return sum(self.cards[x] for x in PLAYABLE_DEV_CARDS + VICTORY_CARDS)


class IslandersState:
  WANT = "want"
  GIVE = "give"
  TRADE_SIDES = (WANT, GIVE)
  PLACEMENTS = ("place1", "place2", "place3")
  LOCATION_ATTRIBUTES = frozenset({"tiles", "ports", "pieces", "roads", "knights", "treasures"})
  HIDDEN_ATTRIBUTES = frozenset(
    {
      "dev_cards",
      "num_dev",
      "played_dev",
      "ships_moved",
      "built_this_turn",
      "home_corners",
      "foreign_landings",
      "placement_islands",
    }
  )
  COMPUTED_ATTRIBUTES = frozenset({"port_corners", "corners_to_islands"})
  INDEXED_ATTRIBUTES = frozenset(
    {"discard_players", "collect_counts", "home_corners", "foreign_landings", "counter_offers"}
  )
  REQUIRED_ATTRIBUTES = frozenset(
    {
      "player_data",
      "tiles",
      "ports",
      "pieces",
      "roads",
      "robber",
      "dev_cards",
      "dice_roll",
      "game_phase",
      "action_stack",
      "turn_idx",
      "played_dev",
      "discard_players",
      "rob_players",
      "trade_offer",
      "counter_offers",
      "options",
    }
  )
  EXTRA_BUILD_ACTIONS = ("settle", "city", "buy_dev", "road", "ship", "end_extra_build")

  def __init__(self):
    # Player data is a sequential list of Player objects; players are identified by index.
    self.player_data: list[Player] = []
    # Board/Card State
    self.tiles: dict[TileLocation, Tile] = {}
    self.ports: dict[TileLocation, Port] = {}
    self.port_corners: dict[CornerLocation, str] = {}
    self.pieces: dict[CornerLocation, Piece] = {}
    self.roads: dict[EdgeLocation, Road] = {}  # includes ships
    self.knights: dict[EdgeLocation, Knight] = {}
    self.robber: Optional[TileLocation] = None
    self.pirate: Optional[TileLocation] = None
    self.treasures: dict[CornerLocation, str] = {}
    self.num_dev: collections.Counter[str] = collections.Counter()
    self.dev_cards: list[str] = []
    self.largest_army_player: Optional[int] = None
    self.longest_route_player: Optional[int] = None
    self.dice_roll: Optional[tuple[int, int]] = None
    self.dice_cards: Optional[list[tuple[int, int]]] = None
    self.corners_to_islands: dict[CornerLocation, CornerLocation] = {}  # corner -> canonical corner
    self.placement_islands: Optional[list[CornerLocation]] = None
    self.discoverable_tiles: list[str] = []
    self.discoverable_numbers: list[int] = []
    self.discoverable_treasures: list[str] = []
    # Turn Information
    self.game_phase: str = "place1"  # valid values are place1, place2, place3, main, victory
    # settle, road, dice, collect, discard, robber, rob, dev_road, deplete, expel, main, extra_build
    # collect1, collect2, collectpi, takedev, bury, placeport, knight, fastknight, treason, intrigue
    # move_knights
    self.action_stack: list[str] = ["road", "settle"]
    self.turn_idx: int = 0
    self.collect_idx: Optional[int] = None
    self.extra_build_idx: Optional[int] = None
    self.invasion_countdown: Optional[int] = None
    # Bookkeeping
    self.played_dev: int = 0
    self.ships_moved: int = 0
    self.built_this_turn: list[EdgeLocation] = []  # Locations where ships were placed this turn.
    self.discard_players: dict[int, int] = {}  # Map of player to number of cards they must discard.
    self.rob_players: list[int] = []  # List of players that can be robbed by this robber.
    self.shortage_resources: list[str] = []
    self.collect_counts: dict[int, int] = collections.defaultdict(int)
    self.target_tile: Optional[TileLocation] = None
    self.home_corners: dict[int, list[CornerLocation]] = collections.defaultdict(list)
    self.foreign_landings: dict[int, list[CornerLocation]] = collections.defaultdict(list)
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
    cstate.parse_knights(gamedata.get("knights", []))
    cstate.parse_treasures(gamedata.get("treasures", []))

    # Location attributes need to be replaced with location objects.
    if cstate.robber is not None:
      cstate.robber = TileLocation(*cstate.robber)
    if cstate.pirate is not None:
      cstate.pirate = TileLocation(*cstate.pirate)
    if cstate.target_tile is not None:
      cstate.target_tile = TileLocation(*cstate.target_tile)

    # The number of dev cards needs to be a counter instead of a plain dict.
    cstate.num_dev = collections.Counter(cstate.num_dev)

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
      mapping.update(
        {
          idx: [CornerLocation(*corner) for corner in corner_list]
          for idx, corner_list in mapping.items()
        }
      )

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

  def parse_knights(self, knightdata):
    for knight_json in knightdata:
      knight = Knight.parse_json(knight_json)
      self.knights[knight.location] = knight

  def parse_treasures(self, treasuredata):
    for treasure_json in treasuredata:
      loc = CornerLocation(*treasure_json["location"])
      self.treasures[loc] = treasure_json["treasure_type"]

  def json_repr(self):
    custom = {"player_data", "event_log"}
    ret = {
      name: getattr(self, name)
      for name in self.__dict__.keys()
      - self.LOCATION_ATTRIBUTES
      - self.COMPUTED_ATTRIBUTES
      - custom
    }
    ret["turn_phase"] = self.turn_phase
    ret.update({name: list(getattr(self, name).values()) for name in self.LOCATION_ATTRIBUTES})
    ret["treasures"] = [{"location": loc, "treasure_type": t} for loc, t in self.treasures.items()]
    for attr in self.INDEXED_ATTRIBUTES:
      ret.update({attr: [getattr(self, attr).get(idx) for idx in range(len(self.player_data))]})
    ret["player_data"] = [player.json_repr() for player in self.player_data]
    ret["event_log"] = list(self.event_log)
    return ret

  def for_player(self, player_idx):
    data = self.json_for_player()
    if self.turn_phase == "bury" and len(self.action_stack) > 1:
      data["treasure"] = self.action_stack[-2]
    if player_idx is not None:
      data["you"] = player_idx
      data["cards"] = self.player_data[player_idx].cards
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

    ret["treasures"] = [{"location": corner} for corner in self.treasures]

    is_over = self.game_phase == "victory"

    ret["player_data"] = [player.json_for_player(is_over) for player in self.player_data]
    for idx in range(len(self.player_data)):
      ret["player_data"][idx]["points"] = self.player_points(idx, visible=not is_over)
    return ret

  def player_points(self, idx, visible):
    count = 0
    for piece in self.pieces.values():
      if piece.player == idx and not piece.conquered:
        if piece.piece_type == "settlement":
          count += 1
        elif piece.piece_type == "city":
          count += 2
    if self.largest_army_player == idx:
      count += 2
    if self.longest_route_player == idx:
      count += 2
    count += max(self.player_data[idx].buried_treasure - 2, 0)
    if not visible:
      count += sum(self.player_data[idx].cards[card] for card in VICTORY_CARDS)
    count += len(self.foreign_landings[idx]) * self.options.foreign_island_points
    return count

  def game_status(self):
    # TODO: list the rulesets being used
    return "islanders game with %s" % ", ".join([p.name for p in self.player_data])

  def add_player(self, color, name):
    self.player_data.append(Player(color, name))

  @property
  def turn_phase(self):
    if self.game_phase.startswith("place"):
      if not self.action_stack:
        return "settle"
      return self.action_stack[-1]
    if not self.action_stack:
      return "main"
    return self.action_stack[-1]

  def next_action(self):
    if self.game_phase.startswith("place"):
      if not self.action_stack:
        self.end_turn()
    if self.turn_phase not in [
      "collect",
      "rob",
      "dev_road",
      "deplete",
      "takedev",
      "knight",
      "fastknight",
      "move_knights",
    ]:
      return
    if self.turn_phase == "move_knights":
      for knight in self.knights.values():
        if knight.player == self.turn_idx:
          knight.movement = 3
          knight.source = knight.location
      return
    if self.turn_phase in ["knight", "fastknight"]:
      if len([k for k in self.knights.values() if k.player == self.turn_idx]) >= 6:
        # Cannot have more than 6 knights.
        self.action_stack.pop()
        self.next_action()
      return
    if self.turn_phase == "takedev":
      if self.options.shuffle_discards and not self.dev_cards:
        self.reshuffle_dev_cards()
      if self.dev_cards:
        card_type = self.add_dev_card(self.turn_idx)
        self.event_log.append(
          Event(
            "takedev",
            "{player%s} received a dev card" % self.turn_idx,
            "{player%s} received a %s" % (self.turn_idx, card_type),
            [self.turn_idx],
          )
        )
      self.action_stack.pop()
      self.next_action()
      return
    if self.turn_phase == "collect":
      self.next_collect_player()
      return
    if self.turn_phase == "rob":
      if not self.rob_players:
        self.action_stack.pop()
        self.next_action()
        return
      if len(self.rob_players) == 1:
        self._rob_player(self.rob_players[0], self.turn_idx)
        return
    if self.turn_phase == "deplete":
      if not self._depletable_tiles():
        self.target_tile = None
        self.action_stack.pop()
        self.next_action()
        return
    if self.turn_phase == "dev_road":
      usable = ["road", "ship"] if self.options.seafarers else ["road"]
      used = len([r for r in self.roads.values() if r.player == self.turn_idx])
      # Automatically end dev road if the player is out of roads/ships.
      # TODO: replace this with a method to check to see if they have any legal road moves.
      if used >= 15 * len(usable):
        self.action_stack.pop()
        self.next_action()

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
    if move_type == "pirate":
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
    if move_type == "deplete":
      return self.handle_deplete(location, player_idx)
    if move_type == "bury":
      return self.handle_bury(player_idx, True)
    if move_type == "treasure":
      return self.handle_bury(player_idx, False)
    if move_type == "placeport":
      return self.handle_place_port(player_idx, location, data.get("rotation"), data.get("port"))
    if move_type == "buy_dev":
      return self.handle_buy_dev(player_idx)
    if move_type == "play_dev":
      return self.handle_play_dev(data.get("card_type"), data.get("selection"), player_idx)
    if move_type == "knight":
      return self.handle_place_knight(location, player_idx)
    if move_type == "move_knight":
      return self.handle_move_knight(data.get("from"), data.get("to"), player_idx)
    if move_type == "treason":
      return self.handle_treason(
        data.get("froma"), data.get("fromb"), data.get("toa"), data.get("tob"), player_idx
      )
    if move_type == "intrigue":
      return self.handle_intrigue(location, player_idx)
    if move_type == "expel":
      return self.handle_expel(location, player_idx)
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
    if move_type == "end_move_knights":
      return self.handle_end_move_knights(player_idx)
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

  def handle_end_move_knights(self, player_idx):
    if self.turn_phase != "move_knights":
      raise InvalidMove("It is not time to move your knights.")
    castles = [tile for tile in self.tiles.values() if tile.tile_type == "castle"]
    castle_edges = set(sum([tile.location.get_edge_locations() for tile in castles], []))
    if any(edge in self.knights for edge in castle_edges):
      raise InvalidMove("You must move all knights away from the castle.")
    spend = len([k for k in self.knights.values() if k.movement < 0 and k.player == player_idx])
    if self.player_data[player_idx].cards["rsrc3"] < spend:
      raise InvalidMove(f"You would need {spend} {{rsrc3}} to move your knights that far.")
    self.player_data[player_idx].cards["rsrc3"] -= spend
    text = "{player%s} " % player_idx
    if spend:
      text += "paid %s {rsrc3} to move their knights" % spend
    else:
      text += "moved their knights"
    self.event_log.append(Event("move_knights", text))

    for knight in self.knights.values():
      if knight.player == player_idx:
        knight.movement = 0
    self.action_stack.pop()
    # TODO: make this work with extra build phase
    self.end_turn()

  def handle_end_extra_build(self, player_idx):
    if self.turn_phase != "extra_build":
      raise InvalidMove("It is not the extra build phase.")
    if player_idx != self.extra_build_idx:
      raise NotYourTurn("It is not your extra build phase.")
    self.extra_build_idx = (self.extra_build_idx + 1) % len(self.player_data)
    if self.extra_build_idx == self.turn_idx:
      self.extra_build_idx = None
      self.action_stack.pop()
      self.next_action()
      self.end_turn()

  def handle_end_turn(self):
    if self.game_phase != "main":
      raise InvalidMove("You MUST place your first settlement/roads.")
    self._check_main_phase("end_turn", "end your turn")
    if any(knight.player == self.turn_idx for knight in self.knights.values()):
      self.action_stack.append("move_knights")
      self.next_action()
      return
    if self.options.extra_build:
      next_player = (self.turn_idx + 1) % len(self.player_data)
      self.extra_build_idx = next_player
      self.action_stack.append("extra_build")
      return
    self.end_turn()

  def end_turn(self):
    self.player_data[self.turn_idx].unusable.clear()
    self.player_data[self.turn_idx].gold_traded = 0
    self.played_dev = 0
    self.ships_moved = 0
    self.built_this_turn.clear()
    self.shortage_resources.clear()
    self.trade_offer = {}
    self.counter_offers.clear()
    if self.game_phase == "main":
      self.turn_idx += 1
      self.turn_idx = self.turn_idx % len(self.player_data)
      self.action_stack.append("dice")
      self.dice_roll = None
      return
    if not self.game_phase.startswith("place"):
      return
    direction = 1 - 2 * (self.PLACEMENTS.index(self.game_phase) % 2)  # 1 (forward) or -1 (backward)
    self.turn_idx += direction
    if 0 <= self.turn_idx < len(self.player_data):
      # Default case - continue to the next player.
      self.action_stack.extend(["road", "settle"])
      return
    if self.PLACEMENTS.index(self.game_phase) < len(self.options.placements) - 1:
      # Next game phase - keep the same player, as turns go in snake order.
      self.turn_idx -= direction
      self.game_phase = self.PLACEMENTS[self.PLACEMENTS.index(self.game_phase) + 1]
      self.action_stack.extend(["road", "settle"])
      return
    # Begin the main phase of the game.
    self.turn_idx = 0
    self.game_phase = "main"
    self.action_stack.append("dice")

  def handle_roll_dice(self):
    if self.turn_phase != "dice":
      raise InvalidMove("You cannot roll the dice right now.")
    if self.dice_cards is not None:
      verb = "drew"
      if len(self.dice_cards) <= self.options.randomness:  # Reshuffle
        self.init_dice_cards()
        verb = "reshuffled and drew"
      red, white = self.dice_cards.pop()
      text = "{player%s} %s a %s" % (self.turn_idx, verb, red + white)
    else:
      if self.next_die_roll is not None:
        red = self.next_die_roll // 2
        white = (self.next_die_roll + 1) // 2
        self.next_die_roll = None
      else:
        red = random.randint(1, 6)
        white = random.randint(1, 6)
      text = "{player%s} rolled a %s" % (self.turn_idx, red + white)
    self.dice_roll = (red, white)
    self.event_log.append(Event("dice", text))
    self.action_stack.pop()
    if (red + white) == 7:
      self.action_stack.append("rob")
      if self.options.robber or self.options.pirate:
        self.action_stack.append("robber")
      else:
        self.rob_players = [
          idx
          for idx in range(len(self.player_data))
          if self.player_data[idx].resource_card_count() and idx != self.turn_idx
        ]
      self.discard_players = self._get_players_with_too_many_resources()
      if sum(self.discard_players.values()):
        self.action_stack.append("discard")
      self.next_action()
      return
    self.distribute_resources(self.dice_roll)
    self.invade(red + white)

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
      self.distribute_resources((red, white))
      self.invade(red + white)

  def remaining_resources(self, rsrc):
    return 19 - sum(p.cards[rsrc] for p in self.player_data)

  def calculate_resource_distribution(self, dice_roll):
    # Figure out which players are due how many resources.
    to_receive = collections.defaultdict(lambda: collections.defaultdict(int))
    for tile in self.tiles.values():
      if tile.number != sum(dice_roll):
        continue
      if self.robber == tile.location:
        continue
      if tile.conquered:
        continue
      for corner_loc in tile.location.get_corner_locations():
        piece = self.pieces.get(corner_loc)
        if piece and piece.piece_type == "settlement":
          to_receive[tile.tile_type][piece.player] += 1
        elif piece and piece.piece_type == "city":
          to_receive[tile.tile_type][piece.player] += 2

    self.collect_counts = to_receive.pop("anyrsrc", {})
    return to_receive

  def distribute_resources(self, dice_roll):
    to_receive = self.calculate_resource_distribution(dice_roll)
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
        the_player = next(iter(receive_players.keys()))
        self.event_log.append(
          Event(
            "shortage",
            "{player%s} was due %s {%s} but only received %s due to a shortage"
            % (the_player, receive_players[the_player], rsrc, remaining),
          )
        )
        receive_players[the_player] = remaining
        continue
      # If there is more than one player receiving this resource, and there is not enough
      # in the supply, then no players receive any of this resource.
      receive_players.clear()
      self.event_log.append(
        Event("shortage", "There was a shortage of {%s} - no players received any" % rsrc)
      )

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

    if sum(self.collect_counts.values()):
      self.action_stack.append("collect")
      self.next_action()

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
      self.collect_idx = None
      return
    num_players = len(self.player_data)
    collect_players = [idx for idx, count in self.collect_counts.items() if count]
    collect_players.sort(key=lambda idx: (idx - self.turn_idx + num_players) % num_players)
    self.collect_idx = collect_players[0]
    if sum(available.values()) < self.collect_counts[self.collect_idx]:  # noqa: PLR1730
      # If there's not enough left in the bank, the player collects everything that remains.
      self.collect_counts[self.collect_idx] = sum(available.values())

  def finish_collect(self):
    self.collect_counts.clear()
    self.collect_idx = None
    self.action_stack.pop()
    self.next_action()

  def handle_collect(self, player_idx, selection):
    self._validate_selection(selection)
    expected_count = self.collect_counts.get(player_idx, 0)
    if self.turn_phase in ["collect1", "collectpi"]:
      expected_count = 1
    elif self.turn_phase == "collect2":
      expected_count = 2
    if sum(selection.values()) != expected_count:
      raise InvalidMove("You must select %s resources." % expected_count)
    if self.turn_phase == "collectpi":
      if sum(selection.get(rsrc, 0) for rsrc in ["rsrc1", "rsrc3", "rsrc4"]) != 1:
        raise InvalidMove("You may only select {rsrc1}, {rsrc3}, or {rsrc4}")
    if selection.keys() & set(self.shortage_resources):
      raise InvalidMove(
        "There is a shortage of {%s}; you cannot collect any."
        % ("}, {".join(self.shortage_resources))
      )
    # TODO: dedup with code from year of plenty
    overdrawn = [rsrc for rsrc in selection if selection[rsrc] > self.remaining_resources(rsrc)]
    if overdrawn:
      raise InvalidMove("There is not enough {%s} in the bank." % "}, {".join(overdrawn))
    for rsrc, value in selection.items():
      self.player_data[player_idx].cards[rsrc] += value
    event_text = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in selection.items()])
    self.event_log.append(Event("collect", "{player%s} collected " % player_idx + event_text))
    if self.turn_phase in ["collect1", "collect2", "collectpi"]:
      self.action_stack.pop()
    else:
      del self.collect_counts[player_idx]
    self.next_action()

  def _get_players_with_too_many_resources(self):
    return {
      idx: player.resource_card_count() // 2
      for idx, player in enumerate(self.player_data)
      if player.too_many_cards()
    }

  def handle_discard(self, selection, player):
    if self.turn_phase != "discard":
      raise InvalidMove("You cannot discard cards right now.")
    self._validate_selection(selection)
    if not self.discard_players.get(player):
      raise InvalidMove("You do not need to discard any cards.")
    discard_count = sum(selection.get(rsrc, 0) for rsrc in RESOURCES)
    if discard_count != self.discard_players[player]:
      raise InvalidMove(
        "You have %s resource cards and must discard %s."
        % (self.player_data[player].resource_card_count(), self.discard_players[player])
      )
    self._remove_resources(selection.items(), player, "discard those cards")
    discarded = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in selection.items()])
    self.event_log.append(Event("discard", "{player%s} discarded %s" % (player, discarded)))
    del self.discard_players[player]
    if sum(self.discard_players.values()) == 0:
      self.action_stack.pop()
      self.next_action()

  def validate_robber_location(self, location, robber_type, land):
    if self.turn_phase != "robber":
      if self.turn_phase == "discard":
        raise InvalidMove("Waiting for players to discard.")
      raise InvalidMove("You cannot play the %s right now." % robber_type)
    new_location = parse_location(location, TileLocation)
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
    if not self.options.robber:
      raise InvalidMove("The robber is not used in this scenario.")
    robber_loc = self.validate_robber_location(location, "robber", land=True)
    adjacent_players = {
      self.pieces[loc].player for loc in robber_loc.get_corner_locations() if loc in self.pieces
    }
    self.check_friendly_robber(current_player, adjacent_players, "robber")
    self.event_log.append(Event("robber", "{player%s} moved the robber" % current_player))
    self.robber = robber_loc
    self.activate_robber(current_player, adjacent_players)

  def handle_pirate(self, player_idx, location):
    if not self.options.pirate:
      raise InvalidMove("The pirate is not used in this scenario.")
    pirate_loc = self.validate_robber_location(location, "pirate", land=False)
    adjacent_players = {
      self.roads[edge].player
      for edge in pirate_loc.get_edge_locations()
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
    self.rob_players = list(robbable_players)
    self.action_stack.pop()
    self.next_action()

  def handle_rob(self, rob_player, current_player):
    if self.turn_phase != "rob":
      if self.options.robber or self.options.pirate:
        raise InvalidMove("You cannot rob without playing the robber/pirate.")
      raise InvalidMove("You cannot rob anyone right now.")
    if not isinstance(rob_player, int) or rob_player < 0 or rob_player >= len(self.player_data):
      raise InvalidMove("Unknown player %s" % rob_player)
    if rob_player == current_player:
      raise InvalidMove("You cannot rob from yourself.")
    if rob_player not in self.rob_players:
      if not self.player_data[rob_player].resource_card_count():
        raise InvalidMove("You cannot rob from a player that has no cards.")
      raise InvalidMove("You cannot rob from that player with that robber placement.")
    self._rob_player(rob_player, current_player)

  def _rob_player(self, rob_player, current_player):
    all_rsrc_cards = []
    for rsrc in RESOURCES:
      all_rsrc_cards.extend([rsrc] * self.player_data[rob_player].cards[rsrc])
    if len(all_rsrc_cards) <= 0:
      raise InvalidMove("You cannot rob from a player without any resources.")
    chosen_rsrc = random.choice(all_rsrc_cards)
    self.player_data[rob_player].cards[chosen_rsrc] -= 1
    self.player_data[current_player].cards[chosen_rsrc] += 1
    self.event_log.append(
      Event(
        "rob",
        "{player%s} stole a card from {player%s}" % (current_player, rob_player),
        "{player%s} stole a {%s} from {player%s}" % (current_player, chosen_rsrc, rob_player),
        [current_player, rob_player],
      )
    )
    self.rob_players = []  # Reset after successful rob.
    self.action_stack.pop()
    self.next_action()

  def hasten_invasion(self):
    if self.invasion_countdown is None or self.invasion_countdown <= 0:
      return
    count = 3 if len(self.player_data) <= 3 else 2
    deserts = [tile for tile in self.tiles.values() if tile.tile_type == "norsrc"]
    if not deserts:  # This should never happen.
      return
    for _ in range(count):
      deserts.sort(key=lambda tile: tile.barbarians)
      deserts[0].barbarians += 1
      self.invasion_countdown -= 1
    for tile in deserts:
      self.check_conquest(tile)

  def invade(self, num):
    if self.invasion_countdown is None or self.invasion_countdown > 0:
      return
    deserts = [tile for tile in self.tiles.values() if tile.tile_type == "norsrc"]
    supply = sum(tile.barbarians for tile in deserts)
    if supply <= 0:
      return

    matching = [tile for tile in self.tiles.values() if tile.number == num and tile.barbarians == 0]
    eligible = []
    for tile in matching:
      adjacents = tile.location.get_adjacent_tiles()
      if any(adj in self.tiles and self.tiles[adj].barbarians > 0 for adj in adjacents):
        eligible.append(tile)
    # In case there are not enough barbarians to distribute, prioritize tiles closer to the desert.
    eligible.sort(key=lambda t: -t.location.x)

    invaded = []
    cleared = []
    for tile in eligible:
      if supply <= 0:
        break
      invaded.append(tile)
      tile.barbarians += 1
      deserts.sort(key=lambda t: (-t.barbarians, t.location.y))
      deserts[0].barbarians -= 1
      supply -= 1
      if deserts[0].barbarians == 0:
        cleared.append(deserts[0])
    for tile in invaded:
      self.check_conquest(tile)
    for tile in cleared:
      self.check_recapture(tile)

  def check_conquest(self, tile):
    if tile.barbarians <= 0:
      return
    tile.conquered = True
    pieces = [self.pieces[c] for c in tile.location.get_corner_locations() if c in self.pieces]
    roads = [self.roads[edge] for edge in tile.location.get_edge_locations() if edge in self.roads]
    for piece in pieces:
      surrounding = [self.tiles[tile] for tile in piece.location.get_tiles() if tile in self.tiles]
      if all(tile.conquered for tile in surrounding):
        piece.conquered = True
    players_to_check = set()
    for road in roads:
      surrounding = [self.tiles[t] for t in road.location.get_adjacent_tiles() if t in self.tiles]
      if all(tile.conquered for tile in surrounding):
        road.conquered = True
        players_to_check.add(road.player)

    for player in players_to_check:
      self.player_data[player].longest_route = self._calculate_longest_road(player)
    self._update_longest_route_player()

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
    # Validate that the road does not go out of bounds.
    if not all(loc in self.tiles for loc in location.get_end_tiles()):
      raise InvalidMove(f"You cannot place a {road_type} out of bounds.")
    # Validate that one side of the road is land.
    self._check_edge_type(location, road_type)
    # Validate that ships are not placed next to the pirate.
    if road_type == "ship":
      adjacent_tiles = location.get_adjacent_tiles()
      if self.pirate in adjacent_tiles:
        raise InvalidMove("You cannot place a ship next to the pirate.")
    # Validate that this road is not surrounded by conquered tiles.
    # Note that both adjacent tiles are guaranteed to be in self.tiles because of _check_edge_type.
    if all(self.tiles[loc].conquered for loc in location.get_adjacent_tiles()):
      raise InvalidMove(f"You cannot place a {road_type} between two conquered tiles.")
    # Validate that this connects to either a settlement or another road.
    for corner in [left_corner, right_corner]:
      # Check whether this corner has one of the player's settlements.
      maybe_piece = self.pieces.get(corner)
      if maybe_piece:
        if maybe_piece.player == player:  # pylint: disable=no-else-return
          # They have a settlement/city here - they can build a road.
          return
        else:  # noqa: RET505
          # Owned by another player - continue to the next corner.
          continue
      # If no settlement at this corner, check for other roads to this corner.
      other_edges = corner.get_edges()
      for edge in other_edges:
        if edge == location:
          continue
        if edge not in self.roads:
          continue
        road = self.roads[edge]
        if road.player == player and road.road_type == road_type and not road.conquered:
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
      if self.turn_phase not in ["road", "dev_road"]:
        raise InvalidMove("You must build a settlement first.")
    elif self.turn_phase != "dev_road":
      self._check_main_phase(road_type, f"build a {road_type}")
    # Check nothing else is already there.
    if loc in self.roads:
      raise InvalidMove("There is already a %s there." % self.roads[loc].road_type)
    # Check that this attaches to their existing network.
    self._check_road_building(loc, player, road_type)
    # Check that the player has enough roads left.
    road_count = len(
      [r for r in self.roads.values() if r.player == player and r.road_type == road_type]
    )
    if road_count >= 15:
      raise InvalidMove(f"You have no {road_type}s remaining.")
    # Handle special settlement phase.
    if self.turn_phase == "road":
      self._check_road_next_to_empty_settlement(loc, player)
      self.action_stack.pop()
      self.event_log.append(Event(road_type, "{player%s} built a %s" % (player, road_type)))
      self.add_road(Road(loc, road_type, player))
      self.next_action()
      return
    # Handle road building dev card.
    if self.turn_phase == "dev_road":
      self.action_stack.pop()
      self.event_log.append(Event(road_type, "{player%s} built a %s" % (player, road_type)))
      self.add_road(Road(loc, road_type, player))
      self.next_action()
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

    self.discover_treasure(road)
    self.discover_tiles(road)

    # Check for increase in longest road, update longest road player if necessary. Also check
    # for decrease in longest road, which can happen if a player moves a ship.
    self.player_data[road.player].longest_route = self._calculate_longest_road(road.player)
    self._update_longest_route_player()

    if road.road_type == "ship":
      self.recalculate_ships(road.source, road.player)
      self.built_this_turn.append(road.location)

  def _update_longest_route_player(self):
    new_max = max(p.longest_route for p in self.player_data)
    holder_max = None
    if self.longest_route_player is not None:
      holder_max = self.player_data[self.longest_route_player].longest_route

    # If nobody meets the conditions for longest road, nobody takes the card. After this,
    # we may assume that the longest road has at least 5 segments.
    if new_max < 5:
      if self.longest_route_player is not None:
        self.event_log.append(
          Event("longest_route", "{player%s} loses longest route" % self.longest_route_player)
        )
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
      self.event_log.append(
        Event("longest_route", "Nobody receives longest route because of a tie.")
      )
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
    # seen before or that do not match our expected edge type or that are conquered.
    unseen_edges = [edge for edge in corner.get_edges() if edge not in seen_edges]
    valid_edges = []
    for edge in unseen_edges:
      if edge not in self.roads:
        continue
      road = self.roads[edge]
      if road.player == player and road.road_type in valid_types and not road.conquered:
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
    except Exception:  # pylint: disable=broad-except
      self.roads[old_ship.location] = old_ship
      raise

    self.event_log.append(Event("move_ship", "{player%s} moved a ship" % player_idx))
    # add_road will automatically recalculate from the new source, but we must still recalculate
    # ships' movable status from the old source in case the two locations are disconnected.
    self.recalculate_ships(old_source, player_idx)
    self.ships_moved = 1

  def discover_tiles(self, road):
    tiles = [self.tiles[loc] for loc in road.location.get_end_tiles() if loc in self.tiles]
    discovered = [tile for tile in tiles if tile.tile_type == "discover"]
    collect_counts = collections.defaultdict(int)
    for tile in discovered:
      if self.discoverable_tiles:
        tile.tile_type = self.discoverable_tiles.pop()
        tile.is_land = tile.tile_type != "space"
        self._compute_coast()
        event_text = "{player%s} discovered {%s}" % (road.player, tile.tile_type)
        self.event_log.append(Event("discover", event_text))
        if tile.tile_type in ["space", "norsrc"]:
          # TODO: should this be a game option?
          if self.discoverable_treasures:
            self.give_treasure(road.player, self.discoverable_treasures.pop())
          continue
        if tile.number is None and self.discoverable_numbers:
          tile.number = self.discoverable_numbers.pop()
        if tile.tile_type in RESOURCES and self.remaining_resources(tile.tile_type) > 0:
          self.player_data[road.player].cards[tile.tile_type] += 1
        if tile.tile_type == "anyrsrc":
          collect_counts[road.player] += 1
    if collect_counts:
      self.collect_counts.update(collect_counts)
      self.action_stack.append("collect")
      self.next_action()

    found = [tile for tile in tiles if tile.number == 0]
    if not found:
      return
    # You can never find more than one tile per road.
    if self.discoverable_numbers:
      found[0].number = self.discoverable_numbers.pop()
    else:
      self.target_tile = found[0].location
      self.action_stack.append("deplete")
      self.next_action()

  def discover_treasure(self, road):
    corners = [road.location.corner_left, road.location.corner_right]
    treasures = [self.treasures.pop(loc) for loc in corners if loc in self.treasures]
    if not treasures:
      return
    self.give_treasure(road.player, treasures[0])  # Impossible to have a treasure in both corners.

  def give_treasure(self, player, treasure):
    text = {
      "collectpi": "collect 1 (limited)",
      "collect1": "collect 1",
      "collect2": "collect 2",
      "takedev": "development card",
    }
    event_text = "{player%s} discovered a %s treasure" % (player, text.get(treasure, treasure))
    self.event_log.append(Event("treasure", event_text))
    if treasure == "roadbuilding":
      self.action_stack.extend(["dev_road", "dev_road"])
    else:
      self.action_stack.append(treasure)

    if self.options.bury_treasure and self.player_data[player].buried_treasure < 4:
      self.action_stack.append("bury")
    self.next_action()

  def handle_bury(self, player_idx, should_bury):
    if self.turn_phase != "bury":
      raise InvalidMove("You cannot choose to bury a treasure right now.")

    if not should_bury:
      self.action_stack.pop()
      self.next_action()
      return
    # Bury case - start by removing the bury action.
    self.action_stack.pop()
    self.player_data[player_idx].buried_treasure += 1

    # Handle dev_road - need to take the top two dev_roads off the action stack.
    if self.action_stack and self.action_stack[-1] == "dev_road":
      for _ in range(2):
        if self.action_stack and self.action_stack[-1] == "dev_road":
          self.action_stack.pop()
      self.next_action()
    # All other treasures - remove the top action.
    elif self.action_stack:
      self.action_stack.pop()

    # If the player has exactly two buried treasures, let them place a port.
    if self.player_data[player_idx].buried_treasure == 2:
      self.action_stack.append("placeport")
    self.next_action()

  def handle_place_port(self, player_idx, loc, rotation, port_type):
    if self.turn_phase != "placeport":
      raise InvalidMove("You cannot place a port right now.")
    location = parse_location(loc, TileLocation)
    if location not in self.tiles:
      raise InvalidMove("Unknown location.")
    if self.tiles[location].is_land:
      raise InvalidMove("You must place the port on {space}.")
    if location in self.ports:
      raise InvalidMove("There is already a port there.")
    if port_type not in RESOURCES:
      raise InvalidMove(f"Unknown port type {port_type}.")
    if port_type in [port.port_type for port in self.ports.values()]:
      raise InvalidMove("That port is already taken.")
    if rotation not in range(6):
      raise InvalidMove(f"Invalid rotation {rotation}.")

    connected_corner = None
    for corner in location.get_corners_for_rotation(rotation):
      if corner in self.port_corners:
        raise InvalidMove("Two ports may not share a corner")
      if corner in self.pieces and self.pieces[corner].player == player_idx:
        connected_corner = corner
    if connected_corner is None:
      raise InvalidMove("You must place the port next to one of your settlements/cities.")

    self.add_port(Port(location.x, location.y, port_type, rotation))
    self._compute_ports()
    self._add_player_port(connected_corner, player_idx)
    self.action_stack.pop()
    self.next_action()

  def _depletable_tiles(self):
    def depletable(tloc):
      return self.corners_to_islands.get(tloc.get_left_corner()) in self.placement_islands

    if self.placement_islands is None:
      return {loc for loc, tile in self.tiles.items() if tile.number}
    return {loc for loc, tile in self.tiles.items() if tile.number and depletable(loc)}

  def handle_deplete(self, loc, player_idx):
    if self.turn_phase != "deplete":
      raise InvalidMove("You cannot deplete the main island right now.")
    location = parse_location(loc, TileLocation)

    # Find all tiles on the home island.
    valid_tiles = self._depletable_tiles()

    if not valid_tiles or not self.target_tile:  # This should never happen.
      self.action_stack.pop()
      self.next_action()
      return

    if location not in valid_tiles:
      raise InvalidMove("You must take a number from the home island.")

    # Find all settlements/cities next to only one number. Their adjacent tiles cannot be depleted.
    isolated_corners = []
    for cloc in self.pieces:
      numbered_tiles = [tloc in self.tiles and self.tiles[tloc].number for tloc in cloc.get_tiles()]
      if len([val for val in numbered_tiles if val]) <= 1:
        isolated_corners.append(cloc)
    banned_tiles = {tile for cloc in isolated_corners for tile in cloc.get_tiles()}
    # If breaking this rule would leave you with no possibilities, ignore the rule.
    if valid_tiles - banned_tiles:
      if location in banned_tiles:
        raise InvalidMove("You must leave at least one number next to each settlement/city.")
      valid_tiles -= banned_tiles

    # Find all tiles next to this player's settlements/cities.
    player_corners = [cloc for cloc, piece in self.pieces.items() if piece.player == player_idx]
    player_tiles = {tloc for cloc in player_corners for tloc in cloc.get_tiles()}
    # If breaking this rule would leave you with no possibilities, ignore the rule.
    if valid_tiles & player_tiles:
      if location not in player_tiles:
        raise InvalidMove("You must deplete a tile next to one of your settlements/cities.")
      valid_tiles &= player_tiles

    # If the surrounding tiles include 6 or 8, eliminate all home tiles that include 6 or 8.
    surrounding = [tloc for tloc in self.target_tile.get_adjacent_tiles() if tloc in self.tiles]
    if any(self.tiles[tloc].number in (6, 8) for tloc in surrounding):
      invalid_tiles = {tile for tile in valid_tiles if self.tiles[tile].number in (6, 8)}
      # If breaking this rule would leave you with no possibilities, ignore the rule.
      if valid_tiles - invalid_tiles:
        if location in invalid_tiles:
          raise InvalidMove("The numbers 6 and 8 may not be placed next to eachother.")
        valid_tiles -= invalid_tiles

    assert location in valid_tiles  # This should never fail.
    self.tiles[self.target_tile].number = self.tiles[location].number
    self.tiles[location].number = None
    self.target_tile = None
    self.action_stack.pop()
    self.next_action()

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
    if self.turn_phase == "settle":
      piece_type = self.options.placements[self.PLACEMENTS.index(self.game_phase)]
      if self.placement_islands is not None:
        canonical_corner = self.corners_to_islands.get(loc)
        if canonical_corner not in self.placement_islands:
          raise InvalidMove("You cannot place your starting %s in that area." % piece_type)
      else:
        on_land = False
        for tile_loc in loc.get_tiles():
          if tile_loc not in self.tiles:
            raise InvalidMove("You must place your %s in bounds." % piece_type)
          if self.tiles[tile_loc].is_land:
            on_land = True
        if not on_land:
          raise InvalidMove("You must place your starting %s on land." % piece_type)
      self.add_piece(Piece(loc.x, loc.y, piece_type, player))
      self.event_log.append(Event(piece_type, "{player%s} built a %s" % (player, piece_type)))
      self.action_stack.pop()
      self.next_action()
      if self.PLACEMENTS.index(self.game_phase) == len(self.options.placements) - 1:
        self.give_second_resources(player, loc)
      return
    # Check connected to one of the player's roads.
    for edge_loc in loc.get_edges():
      maybe_road = self.roads.get(edge_loc)
      if maybe_road and maybe_road.player == player:
        break
    else:
      raise InvalidMove("You must place your settlement next to one of your roads.")
    # Check that this is not a conquered corner.
    if not any(tile in self.tiles and not self.tiles[tile].conquered for tile in loc.get_tiles()):
      raise InvalidMove("You cannot place your settlement on a conquered corner.")
    # Check player has enough settlements left.
    settle_count = len(
      [p for p in self.pieces.values() if p.player == player and p.piece_type == "settlement"]
    )
    if settle_count >= 5:
      raise InvalidMove("You have no settlements remaining.")
    # Check resources and deduct from player.
    resources = [("rsrc1", 1), ("rsrc2", 1), ("rsrc3", 1), ("rsrc4", 1)]
    self._remove_resources(resources, player, "build a settlement")

    self.event_log.append(Event("settlement", "{player%s} built a settlement" % player))
    self.add_piece(Piece(loc.x, loc.y, "settlement", player))
    self.hasten_invasion()

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
      self.player_data[player].trade_ratios.default_factory = lambda: 3
      for rsrc, ratio in self.player_data[player].trade_ratios.items():
        self.player_data[player].trade_ratios[rsrc] = min(ratio, 3)
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
      self.action_stack.append("collect")
      self.next_action()

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
    # Check that this is not a conquered corner.
    if not any(tile in self.tiles and not self.tiles[tile].conquered for tile in loc.get_tiles()):
      raise InvalidMove("You cannot upgrade a conquered settlement to a city.")
    # Check player has enough cities left.
    city_count = len(
      [p for p in self.pieces.values() if p.player == player and p.piece_type == "city"]
    )
    if city_count >= self.options.max_cities:
      raise InvalidMove("You have no cities remaining.")
    # Check resources and deduct from player.
    resources = [("rsrc3", 2), ("rsrc5", 3)]
    self._remove_resources(resources, player, "build a city")

    self.pieces[loc].piece_type = "city"
    self.event_log.append(Event("city", "{player%s} upgraded a settlement to a city" % player))
    self.hasten_invasion()

  def handle_buy_dev(self, player):
    # Check that this is the right part of the turn.
    self._check_main_phase("buy_dev", "buy a development card")
    if self.options.shuffle_discards and not self.dev_cards:
      self.reshuffle_dev_cards()
    if not self.dev_cards:
      raise InvalidMove("There are no development cards left.")
    resources = [("rsrc1", 1), ("rsrc3", 1), ("rsrc5", 1)]
    self._remove_resources(resources, player, "buy a development card")

    if self.options.immediate_dev:
      card_type = self.dev_cards.pop()
      self.event_log.append(Event("buy_dev", "{player%s} bought a %s" % (player, card_type)))
      self.action_stack.append(card_type)
      self.next_action()
      return
    card_type = self.add_dev_card(player)
    self.event_log.append(
      Event(
        "buy_dev",
        "{player%s} bought a dev card" % player,
        "{player%s} bought a %s" % (player, card_type),
        [player],
      )
    )

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
    if self.invasion_countdown is not None:
      self._handle_repelling_knight()
      return
    current_max = max(player.knights_played for player in self.player_data)
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
    self.action_stack.extend(["rob", "robber"])
    self.next_action()

  def _handle_repelling_knight(self):
    removable = [tile for tile in self.tiles.values() if tile.number and tile.barbarians]
    if not removable:
      raise InvalidMove("There are no barbarians that can be removed.")
    self.action_stack.append("expel")
    self.next_action()

  def handle_place_knight(self, loc, player_idx):
    if self.turn_phase not in ["knight", "fastknight"]:
      raise InvalidMove("You cannot place any knights right now.")
    location = parse_location(loc, EdgeLocation)
    if self.turn_phase == "knight":
      castles = [tile for tile in self.tiles.values() if tile.tile_type == "castle"]
      castle_edges = set(sum([tile.location.get_edge_locations() for tile in castles], []))
      if location not in castle_edges:
        raise InvalidMove("You must place your knight next to a castle.")
    else:
      edge_type = self._get_edge_type(location)
      if edge_type is None or (edge_type != "road" and not edge_type.startswith("coast")):
        raise InvalidMove("You must place your knight on a valid edge.")
    if location in self.knights:
      raise InvalidMove("There is already a knight there.")

    self.knights[location] = Knight(location, player_idx, location)
    self.event_log.append(Event("knight", "{player%s} built a knight" % player_idx))
    self.action_stack.pop()
    self.next_action()

  def handle_move_knight(self, from_loc, to_loc, player_idx):
    if self.turn_phase != "move_knights":
      raise InvalidMove("You cannot move your knights right now.")
    from_location = parse_location(from_loc, EdgeLocation)
    to_location = parse_location(to_loc, EdgeLocation)
    if from_location not in self.knights:
      raise InvalidMove("You do not have a knight there.")
    if self.knights[from_location].player != player_idx:
      raise InvalidMove("You can only move your own knights.")
    if to_location in self.knights:
      raise InvalidMove("You cannot place your knight on top of another knight.")
    edge_type = self._get_edge_type(to_location)
    if edge_type is None or (edge_type != "road" and not edge_type.startswith("coast")):
      raise InvalidMove("You must move your knight to a valid edge.")
    distance = self._bfs_search(self.knights[from_location].source, to_location)
    orig_movement = 3
    if distance is None or orig_movement - distance < -2:
      raise InvalidMove("Your knight does not have enough movement.")
    knight = self.knights.pop(from_location)
    knight.location = to_location
    knight.movement = orig_movement - distance
    self.knights[to_location] = knight

  def _bfs_search(self, start, target):
    if start == target:
      return 0
    max_search = 5
    to_search = [start]
    distances = {start: 0}
    while to_search:
      edge = to_search.pop(0)
      if distances[edge] > max_search:
        return None
      tiles = edge.get_adjacent_tiles()
      if not all(tile in self.tiles for tile in tiles):
        # If this edge is not between two tiles on the map, ignore it.
        continue
      if edge == target:
        return distances[edge]
      left_edges = edge.corner_left.get_edges()
      right_edges = edge.corner_right.get_edges()
      adjacents = set(left_edges + right_edges) - {edge}
      for adjacent in adjacents:
        if adjacent in distances:
          continue
        distances[adjacent] = distances[edge] + 1
        to_search.append(adjacent)
    return None

  def handle_treason(self, froma, fromb, toa, tob, player_idx):
    # TODO
    self.action_stack.pop()
    self.next_action()

  def handle_intrigue(self, loc, player_idx):
    # TODO
    self.action_stack.pop()
    self.next_action()

  def handle_expel(self, loc, player_idx):  # pylint: disable=unused-argument
    if self.turn_phase != "expel":
      raise InvalidMove("You cannot expel any barbarians right now.")
    location = parse_location(loc, TileLocation)
    tile = self.tiles.get(location)
    if tile is None or tile.barbarians <= 0:
      raise InvalidMove("You must choose a tile with barbarians on it.")
    tile.barbarians -= 1
    self.check_recapture(tile)
    self.action_stack.pop()
    self.next_action()

  def check_recapture(self, tile):
    if tile.barbarians > 0:
      return
    tile.conquered = False
    for corner in tile.location.get_corner_locations():
      if corner in self.pieces:
        self.pieces[corner].conquered = False
    players_to_check = set()
    for edge in tile.location.get_edge_locations():
      if edge in self.roads:
        self.roads[edge].conquered = False
        players_to_check.add(self.roads[edge].player)

    for player in players_to_check:
      self.player_data[player].longest_route = self._calculate_longest_road(player)
    self._update_longest_route_player()

  def _handle_road_building(self, player):
    # Check that the player has enough roads/ships left.
    usable = ["road", "ship"] if self.options.seafarers else ["road"]
    used = len([r for r in self.roads.values() if r.player == player and r.road_type in usable])
    if used >= 15 * len(usable):
      raise InvalidMove("You have no roads remaining.")
    self.event_log.append(Event("roadbuilding", "{player%s} played a road building card" % player))
    self.action_stack.extend(["dev_road", "dev_road"])
    self.next_action()

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
    card_type = next(iter(resource_selection.keys()))
    self.event_log.append(
      Event("monopoly", "{player%s} played a monopoly on {%s}" % (player, card_type))
    )
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
      raise InvalidInput("invalid offer format - must be a dict of two sides")
    for side in self.TRADE_SIDES:
      if not isinstance(offer[side], dict):
        raise InvalidInput("invalid offer format - each side must be a dict")
      for rsrc, count in offer[side].items():
        if rsrc not in TRADABLES:
          raise InvalidMove("{%s} is not tradable." % rsrc)
        if not isinstance(count, int) or count < 0:
          raise InvalidMove("You must trade a non-negative integer quantity.")
    wants = {key for key, count in offer[self.WANT].items() if count > 0}
    gives = {key for key, count in offer[self.GIVE].items() if count > 0}
    if wants & gives:
      raise InvalidMove("You cannot give and receive the same resource.")
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
    for rsrc in TRADABLES:
      for trade_dict in [my_want, my_give, their_want, their_give]:
        if trade_dict.get(rsrc) == 0:
          del trade_dict[rsrc]
    if sorted(my_want.items()) != sorted(their_give.items()):
      raise InvalidMove("The player changed their offer.")
    if sorted(my_give.items()) != sorted(their_want.items()):
      raise InvalidMove("The player changed their offer.")

    # Validate that both players have the resources to make the trade.
    self._validate_trade({self.WANT: my_want, self.GIVE: my_give}, player)
    self._validate_trade({self.WANT: their_want, self.GIVE: their_give}, counter_player)

    # You cannot trade for nothing.
    if sum(my_want.values()) == 0 or sum(my_give.values()) == 0:
      raise InvalidMove("You cannot trade for nothing.")

    gave_text = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in my_give.items() if count])
    recv_text = ", ".join(["%s {%s}" % (count, rsrc) for rsrc, count in my_want.items() if count])
    self.event_log.append(
      Event(
        "trade",
        "{player%s} traded %s for %s with {player%s}"
        % (player, gave_text, recv_text, counter_player),
      )
    )
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
    self._validate_bank_trade(
      offer, self.player_data[player].trade_ratios, self.player_data[player].gold_traded
    )

    gave_txt = ", ".join(f"{count} {{{rsrc}}}" for rsrc, count in offer[self.GIVE].items() if count)
    recv_txt = ", ".join(f"{count} {{{rsrc}}}" for rsrc, count in offer[self.WANT].items() if count)
    self.event_log.append(
      Event("trade", "{player%s} traded %s with the bank for %s" % (player, gave_txt, recv_txt))
    )
    # Now, make the trade.
    for rsrc, want in offer[self.WANT].items():
      self.player_data[player].cards[rsrc] += want
    for rsrc, give in offer[self.GIVE].items():
      self.player_data[player].cards[rsrc] -= give
    # Keep track of how much gold the player has traded for resources this turn.
    self.player_data[player].gold_traded += offer[self.GIVE].get("gold", 0)

  def _validate_bank_trade(self, offer, ratios, gold_traded):
    """Match up the player's exports with the imports, based on trade ratios.

    This is made tricky by the fact that even if the player has a 2:1 port, they cannot use that
    port to trade for gold. They may only use 3:1 ports or the standard 4:1 ratio to trade for
    gold. Start by computing how many of the player's cards will be used to trade for gold,
    then calculate how many additional resources the player is entitled to receive based on the
    remaining resources they are exporting. Relies on the fact that trading for gold always uses
    the player's worst trade ratio; it will break if this assumption is violated.
    """
    requested_rsrcs = {rsrc: val for rsrc, val in offer[self.WANT].items() if rsrc != "gold"}
    if not self.options.gold and offer[self.WANT].get("gold", 0):
      raise InvalidMove("There is no gold in this scenario.")
    # Make sure the player cannot receive more resources than the bank has.
    for rsrc, count in requested_rsrcs.items():
      if self.remaining_resources(rsrc) < count:
        raise InvalidMove(f"There is only {self.remaining_resources(rsrc)} {{{rsrc}}} remaining.")
    # You may only trade gold for resources up to twice per turn.
    if offer[self.GIVE].get("gold", 0) + gold_traded > 4:
      raise InvalidMove("You may only trade gold for resources up to twice per turn.")
    requested_cards = sum(requested_rsrcs.values())
    requested_gold = offer[self.WANT].get("gold", 0)
    gold_ratio = ratios.default_factory()
    used = {rsrc: 0 for rsrc in TRADABLES}

    # Sort the resources; worst trade ratio first. We will preferentially use resources with the
    # worst trade ratio to purchase gold. Consider the scenario where a player tries to trade
    # 9 of rsrc1, and 3 each of rsrc2 and rsrc3; the player has a 2:1 port for rsrc1 and 3:1 for
    # the other resources. The player wants 3 gold in return. We want to consume rsrc2 and rsrc3
    # first, giving us a return of 3 resources and 3 gold. If we consume rsrc1 to get the gold,
    # we would erroneously only get 2 resources and 3 gold.
    sorted_resources = sorted(RESOURCES, key=lambda rsrc: -ratios[rsrc])
    for rsrc in sorted_resources:
      give = offer[self.GIVE].get(rsrc)
      if not give:
        continue
      normal_ratio = ratios[rsrc]
      for num_gold in range(min(give // gold_ratio, requested_gold), 0, -1):
        # Only look for trades where when done, the rest of the cards may be traded at the normal
        # ratio. For example, if the player is giving 7 cards with a default ratio of 3, we will
        # use only 3 cards for the gold instead of 6, allowing them to user the remaining 4 cards
        # at a 2:1 ratio (assuming they have a 2:1 port).
        if (give - num_gold * gold_ratio) % normal_ratio == 0:
          requested_gold -= num_gold
          used[rsrc] = num_gold * gold_ratio
          break

    # Now that we are done figuring out how we're going to pay for gold, just count the number of
    # resources the remaining cards can buy for us and subtract from requested_cards.
    for rsrc in offer[self.GIVE]:
      give = offer[self.GIVE][rsrc] - used.get(rsrc, 0)
      if not give:
        continue
      ratio = ratios[rsrc] if rsrc != "gold" else 2
      if give % ratio != 0:
        raise InvalidMove("You must trade {%s} with the bank at a %s:1 ratio." % (rsrc, ratio))
      requested_cards -= give // ratio

    if requested_cards == 0 and requested_gold == 0:
      return

    orig_cards = sum(val for rsrc, val in offer[self.WANT].items() if rsrc != "gold")
    orig_gold = offer[self.WANT].get("gold", 0)
    if orig_gold != 0:
      if orig_cards - requested_cards == orig_gold and orig_gold - requested_gold == orig_cards:
        raise InvalidMove("You cannot trade for gold at a 2:1 ratio")
      raise InvalidMove(
        "You should receive %s cards and %s gold, but you requested %s cards and %s gold."
        % (orig_cards - requested_cards, orig_gold - requested_gold, orig_cards, orig_gold)
      )
    raise InvalidMove(
      "You should receive %s cards, but you requested %s."
      % (orig_cards - requested_cards, orig_cards)
    )

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
        upper_left = locs[(tile_rotation + 2) % 6]
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
        idx
        for idx, tile in enumerate(adjacent_tiles)
        if tile and tile.is_land and tile.tile_type != "discover"
      ]
      tile_data.land_rotations = lands

  def dev_card_counts(self):
    counts = {"knight": 14, "monopoly": 2, "roadbuilding": 2, "yearofplenty": 2}
    counts.update({card: 1 for card in VICTORY_CARDS})
    if self.options.extra_build:
      for card, count in {"knight": 6, "monopoly": 1, "roadbuilding": 1, "yearofplenty": 1}.items():
        counts[card] = counts[card] + count
    return collections.Counter(counts)

  def init_dev_cards(self):
    self.num_dev = self.dev_card_counts()
    self.reshuffle_dev_cards()
    self.init_dice_cards()

  def init_barbarian_dev_cards(self):
    self.num_dev = collections.Counter({"knight": 14, "fastknight": 4, "treason": 4, "intrigue": 4})
    self.reshuffle_dev_cards()
    self.init_dice_cards()

  def reshuffle_dev_cards(self):
    used_dev = collections.Counter()
    for p in self.player_data:
      used_dev += collections.Counter({card: p.cards.get(card, 0) for card in self.num_dev})
    knights_played = sum(p.knights_played for p in self.player_data)
    used_dev += collections.Counter({"knight": knights_played})
    to_shuffle = self.num_dev - used_dev
    self.dev_cards = list(to_shuffle.elements())
    random.shuffle(self.dev_cards)

  def init_dice_cards(self):
    if self.options.randomness >= 36:
      return
    self.dice_cards = [(red, white) for red in range(1, 7) for white in range(1, 7)]
    random.shuffle(self.dice_cards)

  def init_robber(self):
    empty = [tile for tile in self.tiles.values() if tile.tile_type == "norsrc"]
    if empty:
      self.robber = empty[0].location

  def _compute_ports(self):
    self.port_corners.clear()
    for port in self.ports.values():
      rotation = (port.rotation + 6) % 6
      for corner in port.location.get_corners_for_rotation(rotation):
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
        dir_idx = (dir_idx + 1) % len(directions)
        bad_dir_count += 1
        continue
      if new_loc in visited or not self.tiles[new_loc].is_land:
        dir_idx = (dir_idx + 1) % len(directions)
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

  @classmethod  # noqa: B027
  def mutate_options(cls, options):
    pass

  @classmethod
  def load_file(cls, state, filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding="ascii") as data:
      json_data = json.load(data)
      state.parse_tiles(json_data["tiles"])
      state.parse_ports(json_data["ports"])
      state.parse_treasures(json_data.get("treasures", []))
    state.recompute()

  @classmethod  # noqa: B027
  def post_load(cls, state):
    pass


class StandardMap(Scenario):
  @classmethod
  def preview(cls, state):
    if len(state.player_data) <= 4:
      cls.load_file(state, "standard4.json")
    else:
      cls.load_file(state, "standard6.json")
    for tile in state.tiles.values():
      if tile.is_land:
        tile.tile_type = "randomized"
    for port in state.ports.values():
      port.port_type = "randomized"
    state.recompute()

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
    filename = "beginner4.json" if len(state.player_data) >= 4 else "beginner3.json"
    with open(os.path.join(os.path.dirname(__file__), filename), encoding="ascii") as data:
      json_data = json.load(data)
      state.parse_tiles(json_data["tiles"])
      state.parse_ports(json_data["ports"])
      state.parse_pieces(json_data["pieces"])
      state.parse_roads(json_data["roads"])
    state.recompute()

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
    state.action_stack = ["dice"]

  @classmethod
  def mutate_options(cls, options):
    options["friendly_robber"].default = True


class TestMap(Scenario):
  @classmethod
  def preview(cls, state):
    cls.load_file(state, "test.json")
    state.recompute()

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
    options["pirate"].force(True)
    options["foreign_island_points"].default = 2


class SeafarerShores(SeafarerScenario):
  @classmethod
  def preview(cls, state):
    if len(state.player_data) <= 3:
      cls.load_file(state, "shores3.json")
      state.robber = TileLocation(19, 3)
      state.pirate = TileLocation(10, 12)
    else:
      cls.load_file(state, "shores4.json")
      state.robber = TileLocation(7, 5)
      state.pirate = TileLocation(10, 14)
      for port in state.ports.values():
        port.port_type = "randomized"
    state.recompute()

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
    if len(state.player_data) <= 3:
      cls.load_file(state, "islands3.json")
      state.robber = TileLocation(1, 3)
      state.pirate = TileLocation(10, 6)
    else:
      cls.load_file(state, "islands4.json")
      state.robber = TileLocation(16, 8)
      state.pirate = TileLocation(10, 12)
    state.recompute()

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
    if len(state.player_data) <= 3:
      cls.load_file(state, "desert3.json")
      state.robber = TileLocation(16, 4)
      state.pirate = TileLocation(10, 12)
    else:
      cls.load_file(state, "desert4.json")
      state.robber = TileLocation(16, 4)
      state.pirate = TileLocation(10, 14)
    state.recompute()

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
    if len(state.player_data) <= 3:
      cls.load_file(state, "fog3.json")
      state.robber = TileLocation(4, 6)
      state.pirate = TileLocation(13, 1)
    else:
      cls.load_file(state, "fog4.json")
      state.robber = TileLocation(16, 14)
      state.pirate = TileLocation(13, 1)
    state.recompute()

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
      "space",
      "space",
      "anyrsrc",
      "anyrsrc",
      "rsrc1",
      "rsrc2",
      "rsrc3",
      "rsrc3",
      "rsrc4",
      "rsrc4",
      "rsrc5",
      "rsrc5",
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


class TreasureIslands(SeafarerScenario):
  @classmethod
  def preview(cls, state):
    cls.load_file(state, "treasure4.json")
    for tile in state.tiles.values():
      if tile.is_land and tile.tile_type != "discover":
        tile.tile_type = "randomized"
    for port in state.ports.values():
      port.port_type = "randomized"
    state.recompute()

  @classmethod
  def init(cls, state):
    super().init(state)
    cls.load_file(state, "treasure4.json")
    land = [loc for loc, tile in state.tiles.items() if tile.tile_type not in ["space", "discover"]]
    state.shuffle_land_tiles(land)
    state.init_numbers((13, 5), TILE_NUMBERS)
    state.shuffle_ports()
    state.recompute()
    state.placement_islands = [state.corners_to_islands[(5, 7)]]
    state.init_dev_cards()
    state.init_robber()

    state.discoverable_tiles = [
      "space",
      "space",
      "space",
      "anyrsrc",
      "anyrsrc",
      "norsrc",
      "norsrc",
      "rsrc1",
      "rsrc2",
      "rsrc3",
      "rsrc3",
      "rsrc4",
      "rsrc4",
      "rsrc5",
      "rsrc5",
    ]
    state.discoverable_numbers = [2, 3, 4, 4, 5, 6, 9, 10, 10, 11]
    random.shuffle(state.discoverable_tiles)
    random.shuffle(state.discoverable_numbers)
    treasures = list(
      collections.Counter(
        {"collect1": 5, "collect2": 4, "takedev": 4, "roadbuilding": 4, "collectpi": 3}
      ).elements()
    )
    random.shuffle(treasures)
    for key in state.treasures:
      state.treasures[key] = treasures.pop()
    state.discoverable_treasures = treasures

  @classmethod
  def mutate_options(cls, options):
    super().mutate_options(options)
    options["victory_points"].default = 14
    options["foreign_island_points"].default = 1

  @classmethod
  def post_load(cls, state):
    # Hack to make the island computation stable(ish) across save/load. Sorry.
    if (1, 9) in state.tiles:
      is_land = state.tiles[(1, 9)].is_land
      state.tiles[(1, 9)].is_land = True
      state._compute_contiguous_islands()  # pylint: disable=protected-access
      state.tiles[(1, 9)].is_land = is_land


class IntoTheUnknown(SeafarerScenario):
  @classmethod
  def preview(cls, state):
    if len(state.player_data) <= 3:
      cls.load_file(state, "unknown3.json")
    else:
      cls.load_file(state, "unknown4.json")
    for tile in state.tiles.values():
      if tile.is_land and tile.tile_type in RESOURCES:
        tile.tile_type = "randomized"
    state.recompute()

  @classmethod
  def init(cls, state):
    super().init(state)
    if len(state.player_data) == 3:
      cls.load_file(state, "unknown3.json")
    elif len(state.player_data) == 4:
      cls.load_file(state, "unknown4.json")
    else:
      raise InvalidPlayer("Must have 3 or 4 players.")
    land = [loc for loc, tile in state.tiles.items() if tile.tile_type in RESOURCES]
    state.shuffle_land_tiles(land)
    state.recompute()
    state.init_dev_cards()

    if len(state.player_data) == 3:
      disc = {"rsrc1": 1, "rsrc2": 2, "rsrc3": 3, "rsrc4": 3, "rsrc5": 3, "space": 6}
      state.discoverable_numbers = [2, 4, 6, 8, 10, 12, 3, 3, 5, 5, 9, 9, 11, 11]
    else:
      disc = {"rsrc1": 3, "rsrc2": 3, "rsrc3": 4, "rsrc4": 4, "rsrc5": 4, "space": 9, "norsrc": 1}
      state.discoverable_numbers = [
        2, 12, 6, 8, 4, 4, 10, 10, 3, 3, 3, 5, 5, 5, 9, 9, 9, 11, 11, 11,
      ]  # fmt: skip
    state.discoverable_tiles = list(collections.Counter(disc).elements())
    random.shuffle(state.discoverable_tiles)
    random.shuffle(state.discoverable_numbers)
    treasures = list(
      collections.Counter(
        {"collect1": 5, "collect2": 4, "takedev": 4, "roadbuilding": 4, "collectpi": 3}
      ).elements()
    )
    random.shuffle(treasures)
    for key in state.treasures:
      state.treasures[key] = treasures.pop()

  @classmethod
  def mutate_options(cls, options):
    super().mutate_options(options)
    options["victory_points"].default = 12
    options["pirate"].force(False)
    options["bury_treasure"].force(True)
    options["placements"].force(("settlement", "settlement", "settlement"))
    options["foreign_island_points"].default = 0


class GreaterIslands(SeafarerScenario):
  @classmethod
  def preview(cls, state):
    if len(state.player_data) <= 3:
      cls.load_file(state, "greater3.json")
    else:
      cls.load_file(state, "greater4.json")
    for tile in state.tiles.values():
      if tile.is_land and tile.number != 0:
        tile.tile_type = "randomized"
      elif tile.is_land:
        tile.tile_type = "discover"
    for port in state.ports.values():
      port.port_type = "randomized"
    state.recompute()

  @classmethod
  def init(cls, state):
    super().init(state)
    if len(state.player_data) == 3:
      cls.load_file(state, "greater3.json")
    elif len(state.player_data) == 4:
      cls.load_file(state, "greater4.json")
    else:
      raise InvalidPlayer("Must have 3 or 4 players.")
    home_lands = [loc for loc, tile in state.tiles.items() if tile.is_land and tile.number != 0]
    foreign_lands = [loc for loc, tile in state.tiles.items() if tile.is_land and tile.number == 0]
    state.shuffle_land_tiles(home_lands)
    state.shuffle_land_tiles(foreign_lands)  # HACK: sea tiles are marked as land in the data
    for tile in state.tiles.values():
      if tile.tile_type == "space":
        tile.is_land = False
      if tile.tile_type in ["space", "norsrc"]:
        tile.number = None
    if len(state.player_data) == 4:
      state.init_numbers((13, 5), TILE_NUMBERS)
      state.shuffle_ports()
    state.recompute()
    state.placement_islands = [state.corners_to_islands[(6, 6)]]
    state.init_dev_cards()
    state.init_robber()
    state.pirate = TileLocation(10, 0)
    if len(state.player_data) == 4:
      state.discoverable_numbers = [3, 4, 5, 9, 10]
    else:
      state.discoverable_numbers = [3, 5, 9, 11]
    random.shuffle(state.discoverable_numbers)

  @classmethod
  def mutate_options(cls, options):
    super().mutate_options(options)
    options["max_cities"].force(8)
    options["victory_points"].default = 18
    options["foreign_island_points"].default = 0


class DesertRiders(SeafarerScenario):
  FIXED_TILES = ((19, 3), (19, 5), (19, 7), (10, 6), (10, 10), (16, 6), (16, 10))

  @classmethod
  def preview(cls, state):
    if len(state.player_data) <= 3:
      cls.load_file(state, "riders3.json")
    else:
      cls.load_file(state, "riders4.json")
    for tile in state.tiles.values():
      if tile.is_land and tile.location not in cls.FIXED_TILES:
        if tile.location.x > 7 and tile.location.y < 13:
          tile.tile_type = "randomized"
        else:
          tile.tile_type = "discover"
    state.recompute()

  @classmethod
  def init(cls, state):
    super().init(state)
    if len(state.player_data) == 3:
      cls.load_file(state, "riders3.json")
    elif len(state.player_data) == 4:
      cls.load_file(state, "riders4.json")
    else:
      raise InvalidPlayer("Must have 3 or 4 players.")
    home_lands = [
      loc
      for loc, tile in state.tiles.items()
      if tile.is_land and loc.x > 7 and loc.y < 13 and loc not in cls.FIXED_TILES
    ]
    foreign_lands = [
      loc
      for loc, tile in state.tiles.items()
      if tile.is_land and loc not in home_lands and loc not in cls.FIXED_TILES
    ]
    state.shuffle_land_tiles(home_lands)
    state.shuffle_land_tiles(foreign_lands)
    state.recompute()
    state.placement_islands = [state.corners_to_islands[(9, 1)]]
    state.init_dev_cards()
    state.invasion_countdown = 18

  @classmethod
  def mutate_options(cls, options):
    super().mutate_options(options)
    options["robber"].force(False)
    options["pirate"].force(False)
    options["victory_points"].default = 13
    options["foreign_island_points"].default = 0


class BarbariansAttack(Scenario):
  @classmethod
  def preview(cls, state):
    cls.load_file(state, "barbarians4.json")
    center = TileLocation(7, 5)
    center_tiles = [center] + center.get_adjacent_tiles()
    for tile in state.tiles.values():
      if tile.is_land and tile.number:
        tile.tile_type = "discover" if tile.location in center_tiles else "randomized"
    for port in state.ports.values():
      port.port_type = "randomized"
    state.recompute()

  @classmethod
  def init(cls, state):
    if len(state.player_data) < 3 or len(state.player_data) > 4:
      raise InvalidPlayer("Must have between 3 and 4 players.")
    cls.load_file(state, "barbarians4.json")
    center = TileLocation(7, 5)
    center_locs = [center] + center.get_adjacent_tiles()
    outer_locs = [
      loc for loc, tile in state.tiles.items() if tile.number and tile.location not in center_locs
    ]
    state.shuffle_land_tiles(center_locs)
    state.shuffle_land_tiles(outer_locs)
    state.shuffle_ports()
    state.recompute()
    state.init_barbarian_dev_cards()

  @classmethod
  def mutate_options(cls, options):
    super().mutate_options(options)
    options["robber"].force(False)
    options["victory_points"].default = 12
    options["gold"].force(True)
    options["immediate_dev"].force(True)
    options["shuffle_discards"].force(True)
    options["placements"].force(("settlement", "city"))


class MapMakerState(IslandersState):
  def handle(self, player_idx, data):
    if data["type"] not in ["robber", "pirate", "end_turn", "settle", "city"]:
      raise InvalidMove("This is the mapmaker. You can only change tiles and add treasure.")
    if data["type"] == "end_turn":
      self.turn_idx = (self.turn_idx + 1) % len(self.player_data)
      return
    if data["type"] in ["settle", "city"]:
      loc = CornerLocation(*data["location"])
      if loc in self.treasures:
        del self.treasures[loc]
      else:
        self.treasures[loc] = "takedev"
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
    new_type = tile_order[(idx + 1) % len(tile_order)]
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
    state.action_stack.clear()
    state.player_data[0].name = "tiles"
    state.player_data[1].name = "numbers/ports"
    if len(state.player_data) > 2:
      state.player_data[2].name = "rotations"


class IslandersGame(BaseGame):
  # The order of this dictionary determines the method resolution order of the created class.
  SCENARIOS = collections.OrderedDict(  # noqa: RUF012
    [
      ("Standard Map", StandardMap),
      ("Beginner's Map", BeginnerMap),
      ("Test Map", TestMap),
      ("Heading for New Shores", SeafarerShores),
      ("The Four Islands", SeafarerIslands),
      ("Through the Desert", SeafarerDesert),
      ("The Fog Islands", SeafarerFog),
      ("The Treasure Islands", TreasureIslands),
      ("Into the Unknown", IntoTheUnknown),
      ("Greater Islands", GreaterIslands),
      ("Desert Riders", DesertRiders),
      ("Barbarians Attack", BarbariansAttack),
      ("Map Maker", MapMaker),
    ]
  )
  COLORS = frozenset({"red", "blue", "limegreen", "darkviolet", "saddlebrown", "darkorange"})

  def __init__(self):
    self.game = None
    self.scenario = next(iter(self.SCENARIOS.keys()))
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
    cls.SCENARIOS[game.scenario].post_load(game_state)
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
      tmp_game = self.game_class()
      tmp_game.player_data = list(self.player_sessions.values())
      try:
        self.SCENARIOS[self.scenario].mutate_options(tmp_game.options)
        self.SCENARIOS[self.scenario].preview(tmp_game)
      except Exception:  # pylint: disable=broad-except # noqa: BLE001
        tmp_game.add_tile(Tile(1, 1, "randomized", True, None))
      data = tmp_game.for_player(None)
      data.update(
        {
          "type": "game_state",
          "host": self.host == session,
          "you": player_idx,
          "started": False,
          "colors": sorted(self.COLORS - {p.color for p in self.player_sessions.values()}),
        }
      )

      data["options"] = collections.OrderedDict([(key, self.choices[key]) for key in self.choices])
      data["scenario"] = GameOption(
        name="Scenario",
        default=next(iter(self.SCENARIOS.keys())),
        choices=list(self.SCENARIOS.keys()),
        value=self.scenario,
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
        self.host = next(iter(self.connected))

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

    unused_colors = self.COLORS - {player.color for player in self.player_sessions.values()}
    used_names = [player.name for player in self.player_sessions.values()]

    if session in self.player_sessions:
      current_player = self.player_sessions[session]
      _validate_name(current_player.name, used_names, data)
      if data.get("color") not in [current_player.color, None]:
        if data["color"] not in unused_colors:
          raise InvalidPlayer(f"Invalid color {data['color']}")
        current_player.color = data["color"]
      current_player.name = data["name"].strip()
      return

    if len(self.player_sessions) >= 6:
      raise TooManyPlayers("There are no open slots.")

    if not unused_colors:
      raise TooManyPlayers("There are too many players.")

    _validate_name(None, used_names, data)
    color = data.get("color")
    if color is not None and color not in unused_colors:
      raise InvalidPlayer(f"Invalid color {color}")
    if color is None:
      color = random.choice(list(unused_colors))

    # TODO: just use some arguments and stop creating fake players. This requires that we clean
    # up the javascript to know what to do with undefined values.
    self.player_sessions[session] = Player(color, data["name"].strip())
    self.update_player_count()

  def handle_takeover(self, session, data):
    if not self.game:
      raise InvalidPlayer("The game has not started yet; you must join instead.")
    if session in self.player_sessions:
      raise InvalidPlayer("You are already playing.")
    try:
      want_idx = int(data["player"])
    except Exception:  # pylint: disable=broad-except # noqa: BLE001
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
