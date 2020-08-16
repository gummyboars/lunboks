import collections
import json
import os
import random

from game import InvalidMove

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
SPACE_TILE_ROTATIONS = [0, 0, 1, 2, 2, 3, -2, -2, -1]


class CustomEncoder(json.JSONEncoder):

  def default(self, o):
    if hasattr(o, "json_repr"):
      return o.json_repr()
    return json.JSONEncoder.default(self, o)


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


class TileLocation(Location):

  def __init__(self, x, y):
    assert x % 2 == 0, "tiles x location must be even"
    if x % 4 == 0:
      assert y % 2 == 0, "tiles must line up correctly"
    else:
      assert y % 2 == 1, "tiles must line up correctly"
    Location.__init__(self, x, y)

  def get_upper_left_tile(self):
    return (self.x - 2, self.y - 1)

  def get_upper_tile(self):
    return self.x, self.y - 2

  def get_upper_right_tile(self):
    return (self.x + 2, self.y - 1)

  def get_lower_right_tile(self):
    return (self.x + 2, self.y + 1)

  def get_lower_tile(self):
    return self.x, self.y + 2

  def get_lower_left_tile(self):
    return (self.x - 2, self.y + 1)

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

  def get_edges(self):
    """Returns edge coordinates of edges adjacent to this corner.

    Edge coordinates must be given left-to-right.
    """
    edges = []
    for corner in self.get_adjacent_corners():
      if corner.x < self.x:
        edges.append(EdgeLocation(corner, self))
      else:
        edges.append(EdgeLocation(self, corner))
    return edges


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

  def get_adjacent_tiles(self):
    """Returns the two TileLocations that share a border at this edge."""
    right_locations = [tile.as_tuple() for tile in self.corner_right.get_tiles()]
    return [tile for tile in self.corner_left.get_tiles() if tile.as_tuple() in right_locations]


class Road(object):

  TYPES = ["road", "ship"]

  def __init__(self, location, road_type, player):
    self.location = EdgeLocation(*location)
    self.road_type = road_type
    self.player = player

  def json_repr(self):
    return {
        "location": self.location,
        "road_type": self.road_type,
        "player": self.player,
    }

  @staticmethod
  def parse_json(value):
    return Road(value["location"], value["road_type"], value["player"])

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

  def __init__(self, x, y, tile_type, is_land, number, rotation=0):
    self.location = TileLocation(x, y)
    self.tile_type = tile_type
    self.is_land = is_land
    self.number = number
    self.rotation = rotation

  def json_repr(self):
    return {
        "location": self.location,
        "tile_type": self.tile_type,
        "is_land": self.is_land,
        "number": self.number,
        "rotation": self.rotation,
    }

  @staticmethod
  def parse_json(value):
    return Tile(value["location"][0], value["location"][1], value["tile_type"],
        value["is_land"], value["number"], value["rotation"])

  def __str__(self):
    return str(self.json_repr())


class CatanState(object):

  WANT = "want"
  GIVE = "give"
  TRADE_SIDES = [WANT, GIVE]
  LOCATION_ATTRIBUTES = ["tiles", "pieces", "roads"]
  HIDDEN_ATTRIBUTES = [
      "dev_cards", "cards", "trade_ratios", "unusable", "dev_roads_placed",
      "played_dev", "turn_idx"]

  def __init__(self):
    self.player_colors = {}
    self.tiles = {}
    self.ports = {}
    self.pieces = {}
    self.roads = {}  # includes ships
    self.robber = None
    self.pirate = None
    self.dev_cards = []
    self.cards = collections.defaultdict(lambda: collections.defaultdict(int))
    self.trade_ratios = collections.defaultdict(lambda: collections.defaultdict(lambda: 4))
    self.unusable = collections.defaultdict(int)
    self.dev_roads_placed = 0
    self.played_dev = 0
    self.discard_players = {}  # Map of player to number of cards they have.
    self.rob_players = []  # List of players that can be robbed by this robber.
    self.turn_idx = None
    self.turn_order = []
    self.dice_roll = None
    self.trade_offer = None
    self.counter_offers = {}  # Map of player to counter offer.
    # Special values for counter-offers: not present in dictionary means they have not
    # yet made a counter-offer. An null/None counter-offer indicates that they have
    # rejected the trade offer. A counter-offer equal to the original means they accept.
    self.game_phase = "place1"  # valid values are place1, place2, main
    self.turn_phase = "settle"  # valid values are settle, road, dice, discard, robber, dev_road, main

  @staticmethod
  def parse_json(json_str):
    gamedata = json.loads(json_str)
    cstate = CatanState()
    defaultdict_attrs = ["cards", "trade_ratios", "unusable"]

    # Regular attributes
    for attr in cstate.__dict__:
      if attr not in (CatanState.LOCATION_ATTRIBUTES + defaultdict_attrs + ["ports"]):
        setattr(cstate, attr, gamedata[attr])

    # Defaultdicts should start empty and be updated with values from json.
    for attr in defaultdict_attrs:
      dictval = gamedata[attr]
      for key, val in dictval.items():
        if isinstance(val, dict):
          # Preserve the type of the defaultdict entries.
          getattr(cstate, attr)[key].update(val)
        else:
          getattr(cstate, attr)[key] = val

    # Location dictionaries are updated with their respective items.
    for tile_json in gamedata["tiles"]:
      tile = Tile.parse_json(tile_json)
      cstate.add_tile(tile)
    for piece_json in gamedata["pieces"]:
      piece = Piece.parse_json(piece_json)
      cstate.add_piece(piece)
    for road_json in gamedata["roads"]:
      road = Road.parse_json(road_json)
      cstate.add_road(road)

    cstate._compute_ports()
    return cstate

  def json_str(self):
    return json.dumps(self.json_repr(), cls=CustomEncoder)

  def json_repr(self):
    ret = dict([(name, getattr(self, name)) for name in
      ["game_phase", "turn_phase", "player_colors", "turn_order", "dice_roll", "rob_players",
       "robber", "pirate", "trade_offer", "counter_offers", "discard_players"]])
    more = dict([(name, list(getattr(self, name).values())) for name in self.LOCATION_ATTRIBUTES])
    ret.update(more)
    hidden = dict([(name, getattr(self, name)) for name in self.HIDDEN_ATTRIBUTES])
    ret.update(hidden)
    return ret

  def json_for_player(self):
    ret = self.json_repr()
    for name in self.HIDDEN_ATTRIBUTES:
      del ret[name]
    corners = {}
    # TODO: instead of sending a list of corners, we should send something like
    # a list of legal moves for tiles, corners, and edges.
    for tile in self.tiles.values():
      if not tile.is_land:
        continue
      # Triple-count each corner and dedup.
      for corner_loc in tile.location.get_corner_locations():
        corners[corner_loc.as_tuple()] = {"location": corner_loc}
    ret["corners"] = list(corners.values())
    edges = {}
    for corner in corners.values():
      # Double-count each edge and dedup.
      for edge in corner["location"].get_edges():
        edges[edge.as_tuple()] = {"location": edge}
    ret["edges"] = list(edges.values())
    return ret

  def for_player(self, current_player):
    data = self.json_for_player()
    data["type"] = "game_state"
    data["turn"] = self.turn_order[self.turn_idx]
    data["you"] = {"name": current_player}
    data["card_counts"] = {}
    data["points"] = {}
    data["armies"] = {}
    data["longest_roads"] = {}
    color = self.player_colors.get(current_player)
    for player in self.turn_order:
      # TODO: fill these three in
      data["points"][player] = 0
      data["armies"][player] = 0
      data["longest_roads"][player] = 0
      count = sum(self.cards[player].get(rsrc, 0) for rsrc in RESOURCES)
      dev_count = sum(self.cards[player].get(crd, 0) for crd in PLAYABLE_DEV_CARDS + VICTORY_CARDS)
      data["card_counts"][player] = {"resource": count, "dev": dev_count}
    if color:
      data["cards"] = self.cards.get(color)
      data["trade_ratios"] = self.trade_ratios.get(color)
      data["you"].update({"color": color})
    return json.dumps(data, cls=CustomEncoder)

  def rename_player(self, old_player, new_player):
    self.player_colors[new_player] = self.player_colors[old_player]
    del self.player_colors[old_player]

  def remove_player(self, player):
    del self.player_colors[player]

  def add_player(self, player):
    colors = ["red", "blue", "limegreen", "darkviolet", "saddlebrown", "cyan"]
    for color in colors:
      if color not in self.player_colors.values():
        self.player_colors[player] = color
        if color not in self.turn_order:
          self.turn_order.append(color)
        if self.turn_idx is None:
          self.turn_idx = self.turn_order.index(color)
        return
    raise RuntimeError("There are too many players.")

  def handle(self, data, player_name):
    # TODO list:
    # - pre-game "not started" state
    # - fix the number of players at the start of the game
    # - save/restore functionality
    # - check buildings against players' total supply (e.g. 15 roads)
    # - check resources against total card supply
    # - longest road and largest army
    # - victory conditions
    player = self.player_colors.get(player_name)
    if not player:
      return
    if data.get("type") == "discard":
      self.handle_discard(data.get("selection"), player)
      return
    if data.get("type") == "counter_offer":
      self.handle_counter_offer(data.get("offer"), player)
      return
    if self.turn_order[self.turn_idx] != player:
      raise InvalidMove("It is not %s's turn." % player_name)
    location = data.get("location")
    if data.get("type") == "roll_dice":
      self.handle_roll_dice()
    if data.get("type") == "robber":
      self._validate_location(location)
      self.handle_robber(location, player)
    if data.get("type") == "rob":
      self.handle_rob(data.get("player"), player)
    if data.get("type") == "road":
      self._validate_location(location, num_entries=4)
      self.handle_road(location, player)
    if data.get("type") == "buy_dev":
      self.handle_buy_dev(player)
    if data.get("type") == "play_dev":
      self.handle_play_dev(data.get("card_type"), data.get("selection"), player)
    if data.get("type") == "settle":
      self._validate_location(location)
      self.handle_settle(location, player)
    if data.get("type") == "city":
      self._validate_location(location)
      self.handle_city(location, player)
    if data.get("type") == "trade_offer":
      self.handle_trade_offer(data.get("offer"), player)
    if data.get("type") == "accept_counter":
      self.handle_accept_counter(data.get("counter_offer"), data.get("counter_player"), player)
    if data.get("type") == "trade_bank":
      self.handle_trade_bank(data.get("offer"), player)
    if data.get("type") == "end_turn":
      # TODO: move this error checking into handle_end_turn
      if self.game_phase != "main":
        raise InvalidMove("You MUST place your first settlement/roads.")
      self._check_main_phase("end your turn")
      self.handle_end_turn()

  def _validate_location(self, location, num_entries=2):
    if isinstance(location, (tuple, list)) and len(location) == num_entries:
      return
    raise InvalidMove("location %s should be a tuple of size %s" % (location, num_entries))

  def handle_end_turn(self):
    self.unusable.clear()
    self.played_dev = 0
    self.trade_offer = {}
    self.counter_offers = {}
    if self.game_phase == "main":
      self.turn_idx += 1
      self.turn_idx = self.turn_idx % len(self.turn_order)
      self.turn_phase = "dice"
      self.dice_roll = None
      return
    if self.game_phase == "place1":
      self.turn_phase = "settle"
      if self.turn_idx == len(self.turn_order) - 1:
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

  def handle_force_dice(self, count):
    for i in range(count):
      red = random.randint(1, 6)
      white = random.randint(1, 6)
      self.distribute_resources(red + white)

  def handle_roll_dice(self):
    if self.turn_phase != "dice":
      raise InvalidMove("You cannot roll the dice right now.")
    red = random.randint(1, 6)
    white = random.randint(1, 6)
    self.dice_roll = (red, white)
    if (red + white) == 7:
      discard_players = self._get_players_with_too_many_resources()
      if discard_players:
        self.discard_players = discard_players
        self.turn_phase = "discard"
      else:
        self.turn_phase = "robber"
      return
    self.distribute_resources(red + white)
    self.turn_phase = "main"

  def handle_robber(self, location, current_player):
    if self.turn_phase != "robber":
      if self.turn_phase == "discard":
        raise InvalidMove("Waiting for players to discard.")
      raise InvalidMove("You cannot play the robber right now.")
    self.robber = TileLocation(*location)
    corners = self.robber.get_corner_locations()
    robbable_players = set([])
    for corner in corners:
      maybe_piece = self.pieces.get(corner.as_tuple())
      if maybe_piece:
        count = sum(self.cards[maybe_piece.player].get(rsrc, 0) for rsrc in RESOURCES)
        if count > 0:
          robbable_players.add(maybe_piece.player)
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
      all_rsrc_cards.extend([rsrc] * self.cards[rob_player].get(rsrc, 0))
    if len(all_rsrc_cards) <= 0:
      raise InvalidMove("You cannot rob from a player without any resources.")
    chosen_rsrc = random.choice(all_rsrc_cards)
    self.cards[rob_player][chosen_rsrc] -= 1
    self.cards[current_player][chosen_rsrc] += 1

  def _get_players_with_too_many_resources(self):
    the_players = {}
    for player in self.cards:
      count = sum(self.cards[player].get(rsrc, 0) for rsrc in RESOURCES)
      if count >= 8:
        the_players[player] = count
    return the_players

  def _check_resources(self, resources, player, action_string):
    errors = []
    for resource, count in resources:
      if self.cards[player][resource] < count:
        errors.append("%s {%s}" % (count - self.cards[player][resource], resource))
    if errors:
      raise InvalidMove("You would need an extra %s to %s." % (", ".join(errors), action_string))

  def _remove_resources(self, resources, player, build_type):
    self._check_resources(resources, player, build_type)
    for resource, count in resources:
      self.cards[player][resource] -= count

  def _check_road_building(self, location, player):
    left_corner = location.corner_left
    right_corner = location.corner_right
    # Validate that this is an actual edge.
    if location.as_tuple() not in [edge.as_tuple() for edge in left_corner.get_edges()]:
      raise InvalidMove("%s is not a valid edge" % location)
    # Validate that one side of the road is land.
    for tile_loc in location.get_adjacent_tiles():
      tile = self.tiles.get(tile_loc.as_tuple())
      if tile and tile.is_land:
        break
    else:
      raise InvalidMove("One side of your road must be land.")
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
        if maybe_road and maybe_road.player == player:
          # They have a road leading here - they can build another road.
          return
    raise InvalidMove("Roads must be connected to your road network.")

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

  def handle_road(self, location, player):
    # Check that this is the right part of the turn.
    if self.game_phase.startswith("place"):
      if self.turn_phase != "road":
        raise InvalidMove("You must build a settlement first.")
    elif self.turn_phase != "dev_road":
      self._check_main_phase("build a road")
    # Check nothing else is already there.
    if tuple(location) in self.roads:
      raise InvalidMove("There is already a road there.")
    # Check that this attaches to their existing network.
    self._check_road_building(EdgeLocation(*location), player)
    # Handle special settlement phase.
    if self.game_phase.startswith("place"):
      self._check_road_next_to_empty_settlement(EdgeLocation(*location), player)
      self.add_road(Road(location, "road", player)) 
      self.handle_end_turn()
      return
    if self.turn_phase == "dev_road":
      self.add_road(Road(location, "road", player))
      self.dev_roads_placed += 1
      if self.dev_roads_placed == 2:
        self.dev_roads_placed = 0
        self.turn_phase = "main"
      return
    # Check resources and deduct from player.
    resources = [("rsrc2", 1), ("rsrc4", 1)]
    self._remove_resources(resources, player, "build a road")

    self.add_road(Road(location, "road", player))

  def handle_settle(self, location, player):
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
      self._build_settlement(location, player)
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
    # Check resources and deduct from player.
    resources = [("rsrc1", 1), ("rsrc2", 1), ("rsrc3", 1), ("rsrc4", 1)]
    self._remove_resources(resources, player, "build a settlement")

    self._build_settlement(location, player)

  def _build_settlement(self, location, player):
    """Build assuming all checks have been done."""
    self.add_piece(Piece(location[0], location[1], "settlement", player))
    self._add_player_port(location, player)

  def _add_player_port(self, location, player):
    """Sets the trade ratios for a player who built a settlement at this location."""
    port_type = self.ports.get(tuple(location))
    if port_type == "3":
      for rsrc in RESOURCES:
        self.trade_ratios[player][rsrc] = min(self.trade_ratios[player][rsrc], 3)
    elif port_type:
      self.trade_ratios[player][port_type] = min(self.trade_ratios[player][port_type], 2)

  def handle_city(self, location, player):
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
    # Check resources and deduct from player.
    resources = [("rsrc3", 2), ("rsrc5", 3)]
    self._remove_resources(resources, player, "build a city")

    del self.pieces[tuple(location)]
    self.add_piece(Piece(location[0], location[1], "city", player))

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
    if player not in self.discard_players:
      raise InvalidMove("You do not need to discard any cards.")
    discard_count = sum([selection.get(rsrc, 0) for rsrc in RESOURCES])
    if discard_count != self.discard_players[player] // 2:
      raise InvalidMove("You have %s resource cards and must discard %s." %
                        (self.discard_players[player], self.discard_players[player] // 2))
    self._remove_resources(selection.items(), player, "discard those cards")
    del self.discard_players[player]
    if not self.discard_players:
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
    if self.cards[player][card_type] < 1:
      raise InvalidMove("You do not have any %s cards." % card_type)
    if self.cards[player][card_type] - self.unusable[card_type] < 1:
      raise InvalidMove("You cannot play development cards on the turn you buy them.")
    if self.played_dev:
      raise InvalidMove("You cannot play more than one development card per turn.")
    if card_type == "knight":
      self._handle_knight()
    elif card_type == "yearofplenty":
      self._handle_year_of_plenty(player, resource_selection)
    elif card_type == "monopoly":
      self._handle_monopoly(player, resource_selection)
    elif card_type == "roadbuilding":
      self._handle_road_building()
    else:
      # How would this even happen?
      raise InvalidMove("%s is not a playable development card." % card_type)
    self.cards[player][card_type] -= 1
    self.played_dev += 1

  def _handle_knight(self):
    self.turn_phase = "robber"

  def _handle_road_building(self):
    self.turn_phase = "dev_road"

  def _handle_year_of_plenty(self, player, resource_selection):
    self._validate_selection(resource_selection)
    if sum([resource_selection.get(key, 0) for key in RESOURCES]) != 2:
      raise InvalidMove("You must request exactly two resources.")
    for card_type, value in resource_selection.items():
      self.cards[player][card_type] += value

  def _handle_monopoly(self, player, resource_selection):
    self._validate_selection(resource_selection)
    if not all([value in (0, 1) for value in resource_selection.values()]):
      raise InvalidMove("You must choose exactly one resource to monopolize.")
    if sum([resource_selection.get(key, 0) for key in RESOURCES]) != 1:
      raise InvalidMove("You must choose exactly one resource to monopolize.")
    card_type = None
    for key, value in resource_selection.items():
      if value == 1:
        card_type = key
        break
    if not card_type:
      # This should never happen, but you never know.
      raise InvalidMove("You must choose exactly one resource to monopolize.")
    for opponent in self.cards:
      if opponent == player:
        continue
      opp_count = self.cards[opponent][card_type]
      self.cards[opponent][card_type] -= opp_count
      self.cards[player][card_type] += opp_count

  def add_dev_card(self, player):
    card_type = self.dev_cards.pop()
    self.cards[player][card_type] += 1
    self.unusable[card_type] += 1

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
      if self.cards[player][rsrc] < count:
        raise InvalidMove("You do not have enough {%s}." % rsrc)

  def handle_trade_offer(self, offer, player):
    self._check_main_phase("make a trade")
    self._validate_trade(offer, player)
    self.trade_offer = offer
    counter_players = list(self.counter_offers.keys())
    for p in counter_players:
      del self.counter_offers[p]

  def handle_counter_offer(self, offer, player):
    if self.turn_order[self.turn_idx] == player:
      raise InvalidMove("You cannot make a counter-offer on your turn.")
    self._check_main_phase("make a counter-offer")
    if offer is None:  # offer rejection
      self.counter_offers[player] = offer
      return
    self._validate_trade(offer, player)
    self.counter_offers[player] = offer

  def handle_accept_counter(self, counter_offer, counter_player, player):
    if counter_player not in self.player_colors.values():
      raise InvalidMove("The player %s is unknown." % counter_player)
    if counter_player == player:
      raise InvalidMove("You cannot trade with yourself.")
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
      self.cards[player][rsrc] -= count
      self.cards[counter_player][rsrc] += count
    for rsrc, count in my_want.items():
      self.cards[player][rsrc] += count
      self.cards[counter_player][rsrc] -= count

    self.counter_offers = {}
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
      ratio = self.trade_ratios[player][rsrc]
      if give % ratio != 0:
        raise InvalidMove("You must trade {%s} with the bank at a %s:1 ratio." % (rsrc, ratio))
      available += give / ratio
    if available != requested:
      raise InvalidMove("You should receive %s resources, but you requested %s." % (available, requested))
    # Now, make the trade.
    for rsrc, want in offer[self.WANT].items():
      self.cards[player][rsrc] += want
    for rsrc, give in offer[self.GIVE].items():
      self.cards[player][rsrc] -= give

  def distribute_resources(self, number):
    for tile in self.tiles.values():
      if tile.number != number:
        continue
      if self.robber == tile.location:
        continue
      corner_locations = set([a.as_tuple() for a in tile.location.get_corner_locations()])
      for corner_loc in corner_locations:
        # TODO: handle cases where there's not enough in the supply.
        piece = self.pieces.get(corner_loc)
        if piece and piece.piece_type == "settlement":
          self.cards[piece.player][tile.tile_type] += 1
        elif piece and piece.piece_type == "city":
          self.cards[piece.player][tile.tile_type] += 2

  def give_second_resources(self, player, corner_loc):
    tile_locs = set([loc.as_tuple() for loc in corner_loc.get_tiles()])
    for tile_loc in tile_locs:
      tile = self.tiles.get(tile_loc)
      if tile and tile.number:
        self.cards[player][tile.tile_type] += 1

  def add_tile(self, tile):
    self.tiles[tile.location.as_tuple()] = tile

  def add_piece(self, piece):
    self.pieces[piece.location.as_tuple()] = piece

  def add_road(self, road):
    self.roads[road.location.as_tuple()] = road

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

  def _init_space(self, space_tiles, rotations, ports):
    if len(ports) != len(space_tiles) / 2 or len(ports) != len(rotations):
      raise RuntimeError("you screwed it up")
    for idx, loc in enumerate(space_tiles):
      tile_name = "space"
      if idx % 2 == 1:
        tile_name = ports[idx//2]
      self.add_tile(Tile(loc[0], loc[1], tile_name, False, None, rotations[idx//2]))

  def _init_dev_cards(self):
    dev_cards = ["knight"] * 14 + ["monopoly"] * 2 + ["roadbuilding"] * 2 + ["yearofplenty"] * 2
    dev_cards.extend(VICTORY_CARDS)
    random.shuffle(dev_cards)
    self.dev_cards = dev_cards

  def _compute_ports(self):
    for tile in self.tiles.values():
      if not tile.tile_type.endswith("port"):
        continue
      port_type = tile.tile_type[:-4]
      rotation = (tile.rotation + 6) % 6
      if rotation == 0:
        port_corners = [tile.location.get_lower_left_corner(), tile.location.get_lower_right_corner()]
      if rotation == 1:
        port_corners = [tile.location.get_lower_left_corner(), tile.location.get_left_corner()]
      if rotation == 2:
        port_corners = [tile.location.get_upper_left_corner(), tile.location.get_left_corner()]
      if rotation == 3:
        port_corners = [tile.location.get_upper_left_corner(), tile.location.get_upper_right_corner()]
      if rotation == 4:
        port_corners = [tile.location.get_upper_right_corner(), tile.location.get_right_corner()]
      if rotation == 5:
        port_corners = [tile.location.get_lower_right_corner(), tile.location.get_right_corner()]
      for corner in port_corners:
        self.ports[corner.as_tuple()] = port_type

  def init_beginner(self):
    tile_types = [
        "rsrc5", "rsrc3", "rsrc2", "rsrc5", "rsrc3", "rsrc1", "rsrc3", "rsrc1", "rsrc2", "rsrc4",
        "norsrc", "rsrc4", "rsrc1", "rsrc1", "rsrc2", "rsrc4", "rsrc5", "rsrc2", "rsrc3"]
    self._init_tiles(tile_types, TILE_SEQUENCE, TILE_NUMBERS)
    ports = [
        "rsrc2port", "rsrc4port", "3port", "3port", "rsrc1port", "3port",
        "rsrc5port", "rsrc3port", "3port"]
    self._init_space(SPACE_TILE_SEQUENCE, SPACE_TILE_ROTATIONS, ports)
    self._compute_ports()
    self._init_dev_cards()

  def init_normal(self):
    tile_types = [
      "rsrc1", "rsrc1", "rsrc1", "rsrc1",
      "rsrc2", "rsrc2", "rsrc2", "rsrc2",
      "rsrc3", "rsrc3", "rsrc3", "rsrc3",
      "rsrc4", "rsrc4", "rsrc4",
      "rsrc5", "rsrc5", "rsrc5",
      "norsrc"]
    random.shuffle(tile_types)
    self._init_tiles(tile_types, TILE_SEQUENCE, TILE_NUMBERS)
    ports = ["3port", "3port", "3port", "3port",
             "rsrc1port", "rsrc2port", "rsrc3port", "rsrc4port", "rsrc5port"]
    random.shuffle(ports)
    self._init_space(SPACE_TILE_SEQUENCE, SPACE_TILE_ROTATIONS, ports)
    self._compute_ports()
    self._init_dev_cards()

  def init_test(self):
    tile_types = ["rsrc5", "rsrc3", "rsrc1", "rsrc4"]
    self._init_tiles(tile_types, [(2, 3), (4, 2), (2, 5), (4, 4)], [6, 9, 9, 5])
    ports = ["3port", "rsrc1port", "3port", "rsrc3port", "rsrc2port"]
    self._init_space(
        [(2, 1), (4, 0), (6, 1), (6, 3), (6, 5), (4, 6), (2, 7), (0, 6), (0, 4), (0, 2)],
        [0, 1, 3, -2, -1], ports)
    self._compute_ports()
    self._init_dev_cards()
