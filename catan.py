import asyncio
import collections
import json
import os
import random

from game import InvalidMove


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
    assert x % 2 == 0
    if x % 4 == 0:
      assert y % 2 == 0
    else:
      assert y % 2 == 1
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
      assert corner_left.x < corner_right.x
      self.corner_left = corner_left
      self.corner_right = corner_right
    elif len(args) == 4:
      leftx, lefty, rightx, righty = args
      assert leftx < rightx
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

  def __str__(self):
    return str(self.json_repr())


class Tile(object):

  TYPES = ["olivine", "clay", "metal", "sulfur", "water", "space", "desert"]

  def __init__(self, x, y, tile_type, number, rotation=0):
    self.location = TileLocation(x, y)
    self.tile_type = tile_type
    self.number = number
    self.rotation = rotation

  def json_repr(self):
    return {
        "location": self.location,
        "tile_type": self.tile_type,
        "number": self.number,
        "rotation": self.rotation,
    }

  def __str__(self):
    return str(self.json_repr())


class CatanState(object):

  TRADE_SIDES = ["want", "give"]
  TRADABLE_RESOURCES = ["sulfur", "olivine", "water", "clay", "metal"]
  WANT = TRADE_SIDES.index("want")
  GIVE = TRADE_SIDES.index("give")
  PLAYABLE_DEV_CARDS = ["yearofplenty", "monopoly", "roadbuilding", "knight"]
  VICTORY_CARDS = ["palace", "chapel", "university", "market", "library"]

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
    self.turn_idx = None
    self.turn_order = []
    self.dice_roll = None
    self.trade_offer = None
    self.game_phase = "place1"  # valid values are place1, place2, main
    self.turn_phase = "settle"  # valid values are settle, road, dice, robber, main

  def save(self, filename):
    # TODO: finish this. problem is, a lot of custom classes need a json -> class converter.
    # TODO: maybe this should just return a json blob, and the server should save it?
    path = "/".join([ROOT_DIR, filename])
    path = os.path.abspath(path)
    if os.path.dirname(path) != ROOT_DIR:
      raise RuntimeError("dirname is %s but root is %s" % (os.path.dirname(path), ROOT_DIR))
    if os.exists(filename):
      raise RuntimeError("save file %s already exists" % filename)
    with open(filename, "w") as fileobj:
      json.dump(self.__dict__, fileobj, cls=CustomEncoder)

  def json_repr(self):
    ret = dict([(name, getattr(self, name)) for name in
      ["robber", "pirate", "turn_order", "dice_roll", "player_colors", "trade_offer", "game_phase", "turn_phase"]])
    more = dict([(name, list(getattr(self, name).values())) for name in
      ["ports", "tiles", "pieces", "roads"]])
    ret.update(more)
    corners = {}
    # TODO: instead of sending a list of corners, we should send something like
    # a list of legal moves for tiles, corners, and edges.
    for tile in self.tiles.values():
      if tile.tile_type == "space":
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

  def for_player(self, player):
    data = self.json_repr()
    data["type"] = "game_state"
    data["turn"] = self.turn_order[self.turn_idx]
    data["you"] = {"name": player}
    color = self.player_colors.get(player)
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
    # - the robber needs to rob
    # - players must discard at 8+ cards if a 7 is rolled
    # - check buildings against players' total supply (e.g. 15 roads)
    # - must be able to trade with other players
    # - able to play development cards
    # - longest road and largest army
    # - victory conditions
    player = self.player_colors.get(player_name)
    if not player:
      return
    # Insert before turn check:
    # - discarding cards
    # - trade offer acceptance
    # - trade counter-offers
    if self.turn_order[self.turn_idx] != player:
      raise InvalidMove("It is not %s's turn." % player_name)
    location = data.get("location")
    if data.get("type") == "roll_dice":
      self.handle_roll_dice()
    if data.get("type") == "robber":
      self._validate_location(location)
      self.handle_robber(location)
    if data.get("type") == "road":
      self._validate_location(location, num_entries=4)
      self.handle_road(location, player)
    if data.get("type") == "buy_dev":
      self.handle_buy_dev(player)
    if data.get("type") == "play_dev":
      self.handle_play_dev(data.get("card_type"), player)
    if data.get("type") == "settle":
      self._validate_location(location)
      self.handle_settle(location, player)
    if data.get("type") == "city":
      self._validate_location(location)
      self.handle_city(location, player)
    if data.get("type") == "trade_offer":
      self.handle_trade_offer(data.get("offer"), player)
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
    raise RuntimeError("location %s should be a tuple of size %s" % (location, num_entries))

  def handle_end_turn(self):
    self.unusable.clear()
    self.played_dev = 0
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
      self.turn_phase = "robber"
      return
    self.distribute_resources(red + white)
    self.turn_phase = "main"

  def handle_robber(self, location):
    if self.turn_phase != "robber":
      raise InvalidMove("You cannot play the robber right now.")
    self.robber = TileLocation(*location)
    self.turn_phase = "main"

  def _check_resources(self, resources, player, build_type):
    errors = []
    for resource, count in resources:
      if self.cards[player][resource] < count:
        errors.append("%s %s" % (count - self.cards[player][resource], resource))
    if errors:
      raise InvalidMove("You would need an extra %s to buy a %s." % (", ".join(errors), build_type))

  def _remove_resources(self, resources, player, build_type):
    self._check_resources(resources, player, build_type)
    for resource, count in resources:
      self.cards[player][resource] -= count

  def _check_road_building(self, location, player):
    left_corner = location.corner_left
    right_corner = location.corner_right
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
    # Check resources and deduct from player.
    resources = [("olivine", 1), ("clay", 1)]
    self._remove_resources(resources, player, "road")

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
    resources = [("sulfur", 1), ("olivine", 1), ("water", 1), ("clay", 1)]
    self._remove_resources(resources, player, "settlement")

    self._build_settlement(location, player)

  def _build_settlement(self, location, player):
    """Build assuming all checks have been done."""
    self.add_piece(Piece(location[0], location[1], "settlement", player))
    port_type = self.ports.get(tuple(location))
    if port_type == "3":
      for rsrc in self.TRADABLE_RESOURCES:
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
    resources = [("water", 2), ("metal", 3)]
    self._remove_resources(resources, player, "city")

    del self.pieces[tuple(location)]
    self.add_piece(Piece(location[0], location[1], "city", player))

  def handle_buy_dev(self, player):
    # Check that this is the right part of the turn.
    self._check_main_phase("buy a development card")
    resources = [("sulfur", 1), ("water", 1), ("metal", 1)]
    if len(self.dev_cards) < 1:
      raise InvalidMove("There are no development cards left.")
    self._remove_resources(resources, player, "development card")
    self.add_dev_card(player)

  def handle_play_dev(self, card_type, player):
    if card_type not in self.PLAYABLE_DEV_CARDS:
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
    self.played_dev += 1

  def add_dev_card(self, player):
    card_type = self.dev_cards.pop()
    self.cards[player][card_type] += 1
    self.unusable[card_type] += 1

  def _validate_trade(self, offer, player):
    """Validates a well-formed trade & that the player has enough resources."""
    if not isinstance(offer, (list, tuple)) or len(offer) != len(self.TRADE_SIDES):
      raise RuntimeError("invalid offer format - must be a list of two sides")
    for idx in range(len(self.TRADE_SIDES)):
      if not isinstance(offer[idx], dict):
        raise RuntimeError("invalid offer format - each side must be a dict")
    for rsrc, count in offer[self.WANT].items():
      if rsrc not in self.TRADABLE_RESOURCES:
        raise InvalidMove("%s is not tradable." % rsrc)
      if count < 0:
        raise InvalidMove("You cannot trade a negative quantity.")
    for rsrc, count in offer[self.GIVE].items():
      if self.cards[player][rsrc] < count:
        raise InvalidMove("You do not have enough %s." % rsrc)
      if count < 0:
        raise InvalidMove("You cannot trade a negative quantity.")

  def handle_trade_offer(self, offer, player):
    self._check_main_phase("make a trade")
    self._validate_trade(offer, player)
    self.trade_offer = offer

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
        raise InvalidMove("You must trade %s with the bank at a %s:1 ratio." % (rsrc, ratio))
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

  def init_normal(self):
    tile_types = [
      "olivine", "olivine", "olivine", "olivine",
      "metal", "metal", "metal",
      "clay", "clay", "clay",
      "sulfur", "sulfur", "sulfur", "sulfur",
      "water", "water", "water", "water",
      "desert"]
    random.shuffle(tile_types)
    numbers = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]
    sequence = [
        (2, 3), (4, 2), (6, 1), (8, 2), (10, 3),  # around the top
        (10, 5), (10, 7), (8, 8), (6, 9),  # down the side to the bottom
        (4, 8), (2, 7), (2, 5),  # back up the left side
        (4, 4), (6, 3), (8, 4), (8, 6), (6, 7), (4, 6), (6, 5)  # inner loop
        ]
    if len(sequence) != len(tile_types):
      raise RuntimeError("you screwed it up")
    num_idx = 0
    robber_loc = None
    for idx, loc in enumerate(sequence):
      if tile_types[idx] == "desert":
        robber_loc = TileLocation(*sequence[idx])
        number = None
      else:
        number = numbers[num_idx]
        num_idx += 1
      self.add_tile(Tile(sequence[idx][0], sequence[idx][1], tile_types[idx], number))
    space_tiles = [
        (2, 1), (4, 0), (6, -1), (8, 0), (10, 1), (12, 2),  # around the top
        (12, 4), (12, 6), (12, 8),  # down the right side
        (10, 9), (8, 10), (6, 11), (4, 10), (2, 9), (0, 8),  # around the bottom
        (0, 6), (0, 4), (0, 2)  # up the left side
        ]
    ports = ["3port", "3port", "3port", "3port",
             "sulfurport", "clayport", "olivineport", "metalport", "waterport"]
    rotations = [-1, 0, 1, 1, 2, 3, 3, -2, -1]
    random.shuffle(ports)
    if len(ports) != len(space_tiles) / 2 or len(ports) != len(rotations):
      raise RuntimeError("you screwed it up")
    for idx, loc in enumerate(space_tiles):
      tile_name = "space"
      if idx % 2 == 0:
        tile_name = ports[idx//2]
      self.add_tile(Tile(loc[0], loc[1], tile_name, None, rotations[idx//2]))
    self.compute_ports()
    self.robber = robber_loc
    dev_cards = ["knight"] * 14 + ["monopoly"] * 2 + ["roadbuilding"] * 2 + ["yearofplenty"] * 2
    dev_cards.extend(self.VICTORY_CARDS)
    random.shuffle(dev_cards)
    self.dev_cards = dev_cards

  def compute_ports(self):
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
