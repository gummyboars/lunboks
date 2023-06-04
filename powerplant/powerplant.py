import collections
from dataclasses import asdict, dataclass, field
from enum import Enum
import heapq
import json
from random import SystemRandom
from typing import Dict, List

from game import (  # pylint: disable=unused-import
    BaseGame, ValidatePlayer, CustomEncoder, InvalidInput, UnknownMove, InvalidMove,
    InvalidPlayer, TooManyPlayers, NotYourTurn,
)
from powerplant import cities
from powerplant import materials
from powerplant import plants as plantinfo

random = SystemRandom()
COAL = materials.Resource.COAL
OIL = materials.Resource.OIL
GAS = materials.Resource.GAS
URANIUM = materials.Resource.URANIUM
GREEN = materials.Resource.GREEN
HYBRID = materials.Resource.HYBRID


@dataclass
class Count:
  play_regions: int
  plants_removed: int
  max_plants: int
  stage_2_count: int
  end_game_count: int


COUNTS = {
    2: Count(play_regions=3, plants_removed=8, max_plants=4, stage_2_count=10, end_game_count=21),
    3: Count(play_regions=3, plants_removed=8, max_plants=3, stage_2_count=7, end_game_count=17),
    4: Count(play_regions=4, plants_removed=4, max_plants=3, stage_2_count=7, end_game_count=17),
    5: Count(play_regions=5, plants_removed=0, max_plants=3, stage_2_count=7, end_game_count=15),
    6: Count(play_regions=5, plants_removed=0, max_plants=3, stage_2_count=6, end_game_count=14),
}
SUPPLY_RATES = {
    2: {COAL: [3, 4, 3], OIL: [2, 2, 4], GAS: [1, 2, 3], URANIUM: [1, 1, 1]},
    3: {COAL: [4, 5, 3], OIL: [2, 3, 4], GAS: [1, 2, 3], URANIUM: [1, 1, 1]},
    4: {COAL: [5, 6, 4], OIL: [3, 4, 5], GAS: [2, 3, 4], URANIUM: [1, 2, 2]},
    5: {COAL: [5, 7, 5], OIL: [4, 5, 6], GAS: [3, 3, 5], URANIUM: [2, 3, 2]},
    6: {COAL: [7, 9, 6], OIL: [5, 6, 7], GAS: [3, 5, 6], URANIUM: [2, 3, 3]},
}
COSTS: Dict[materials.Resource, List[int]] = {
    COAL: sum([[x] * 3 for x in range(8, 0, -1)], []),
    OIL: sum([[x] * 3 for x in range(8, 0, -1)], []),
    GAS: sum([[x] * 3 for x in range(8, 0, -1)], []),
    URANIUM: [16, 14, 12, 10, 8, 7, 6, 5, 4, 3, 2, 1],
}
PAYMENTS = [
    10, 22, 33, 44, 54, 64, 73,
    82, 90, 98, 105, 112, 118, 124,
    129, 134, 138, 142, 145, 148, 150,
]
STAGE_3_COST = 10000


@dataclass
class Player:
  name: str
  color: str
  plants: List[plantinfo.Plant] = field(default_factory=list)
  money: int = 50

  @classmethod
  def parse_json(cls, data):
    data["plants"] = [plantinfo.Plant.parse_json(p) for p in data["plants"]]
    return cls(**data)


class TurnPhase(str, Enum):
  AUCTION = "auction"
  MATERIALS = "materials"
  BUILDING = "building"
  BUREAUCRACY = "bureaucracy"


class GameState:

  PHASES = [TurnPhase.AUCTION, TurnPhase.MATERIALS, TurnPhase.BUILDING, TurnPhase.BUREAUCRACY]

  def __init__(self, players, region, plantlist):
    self.players = players
    self.cities = cities.CreateCities(region)
    self.all_cities = cities.CreateCities(region)
    self.plants = plantinfo.CreatePlants(plantlist)
    self.resources = cities.StartingResources(region)
    self.colors = set()
    self.turn_idx = 0
    self.turn_order = list(range(len(self.players)))
    self.first_round = True
    self.stage_idx = 0
    self.begin_stage_2 = False
    self.begin_stage_3 = False
    self.phase_idx = 0
    self.auction_idx = 0
    self.auction_plant_idx = None
    self.auction_bid = None
    self.auction_passed = set()
    self.auction_bought = {}
    self.auction_discard_idx = None
    self.to_choose = COUNTS[len(self.players)].play_regions
    self.max_plants = COUNTS[len(self.players)].max_plants
    self.stage_2_count = COUNTS[len(self.players)].stage_2_count
    self.end_game_count = COUNTS[len(self.players)].end_game_count
    self.market = []
    self.pending_buy = {}
    self.pending_build = []
    self.pending_spend = 0
    self.powered = {}
    self.winner = None
    self.setup_plants(plantlist)

  def setup_plants(self, plantlist):
    to_randomize = []
    top_plant = None
    for plant in self.plants:
      if plant.cost in plantinfo.FixedPlants(plantlist):
        self.market.append(plant)
      elif plant.cost == plantinfo.TopPlant(plantlist):
        top_plant = plant
      else:
        to_randomize.append(plant)
    if top_plant is None:
      raise RuntimeError("Top plant not found")
    if len(self.market) != 8:
      raise RuntimeError(f"Incorrect initial market size {self.market}")

    self.market.sort()
    random.shuffle(to_randomize)
    for _ in range(COUNTS[len(self.players)].plants_removed):
      to_randomize.pop()
    self.plants = [top_plant] + to_randomize + [plantinfo.Plant(STAGE_3_COST, GREEN, 0, 0)]

  def json_repr(self):
    data = {}
    for attr, val in self.__dict__.items():
      if isinstance(val, set):
        data[attr] = sorted(list(val))
      elif attr == "resources":
        data[attr] = {k.value: v for k, v in val.items()}
      else:
        data[attr] = val
    return data

  @classmethod
  def parse_json(cls, gamedata):
    players = [Player.parse_json(playerdata) for playerdata in gamedata["players"]]
    state = cls(players, "Germany", "old")
    state.all_cities = {
        name: cities.City.parse_json(data) for name, data in gamedata["all_cities"].items()
    }
    state.cities = {name: cities.City.parse_json(data) for name, data in gamedata["cities"].items()}
    state.plants = [plantinfo.Plant.parse_json(data) for data in gamedata["plants"]]
    state.resources = {materials.Resource(rsrc): n for rsrc, n in gamedata["resources"].items()}
    state.colors = {cities.Color(color) for color in gamedata["colors"]}
    state.auction_passed = set(gamedata["auction_passed"])
    state.market = [plantinfo.Plant.parse_json(data) for data in gamedata["market"]]
    state.pending_buy = {materials.Resource(rsrc): n for rsrc, n in gamedata["pending_buy"].items()}

    handled = {
        "players", "cities", "plants", "resources", "colors", "auction_passed", "market",
        "pending_buy",
    }
    for attr in state.__dict__.keys() - handled:
      setattr(state, attr, gamedata[attr])
    return state

  def for_player(self, player_idx):
    data = self.json_repr()
    data["players"] = [asdict(player) for player in self.players]
    for idx, playerdict in enumerate(data["players"]):
      if idx != player_idx and not self.winner:
        playerdict["money"] = None
    data["plants"] = len(self.plants)
    del data["phase_idx"]
    data["phase"] = self.PHASES[self.phase_idx]
    data["player_idx"] = player_idx
    return data

  def handle(self, player_idx, data):
    if self.winner is not None:
      raise InvalidMove("The game is over.")

    if len(self.colors) < self.to_choose:  # Still choosing regions
      if data.get("type") != "region":
        raise InvalidMove("The game will not begin until the play area has been determined")
      if player_idx != self.turn_idx:
        raise InvalidMove("It is not your turn")
      return self.handle_region(data.get("region"))

    if data.get("type") == "shuffle":
      return self.handle_shuffle(
          player_idx, data.get("resource"), data.get("source"), data.get("dest"),
      )

    if self.auction_discard_idx is not None:
      if player_idx != self.auction_discard_idx:
        raise InvalidMove("Waiting for another player to discard a power plant")
      if data.get("type") == "discard":
        return self.handle_discard(data.get("plant"))
      raise InvalidMove("You must choose a plant to discard")

    if self.PHASES[self.phase_idx] is TurnPhase.AUCTION:
      if player_idx != self.auction_idx:
        raise InvalidMove("It is not your turn")
    else:
      if player_idx != self.turn_idx:
        raise InvalidMove("It is not your turn")

    if data.get("type") == "bid":
      return self.handle_bid(data.get("bid"), data.get("plant"))
    if data.get("type") == "buy":
      return self.handle_buy(data.get("resource"), data.get("count"))
    if data.get("type") == "build":
      return self.handle_build(data.get("city"))
    if data.get("type") == "reset":
      return self.handle_reset()
    if data.get("type") == "confirm":
      return self.handle_confirm()
    if data.get("type") == "burn":
      return self.handle_burn(data.get("counts"))
    raise UnknownMove(f"Unknown move {data.get('type')}")

  def is_connected(self, color):
    if not self.colors:
      return True
    for city in self.cities.values():
      if city.color in self.colors:
        for conn in city.connections:
          if self.cities[conn].color is color:
            return True
    return False

  def handle_region(self, region):
    if len(self.colors) >= self.to_choose:
      raise InvalidMove("The play area has already been determined")

    try:
      chosen = cities.Color(region)
    except ValueError:
      raise InvalidMove(f"Unknown play region {region}")
    if chosen in self.colors:
      raise InvalidMove(f"{chosen.value} is already in the list of chosen regions")

    if not self.is_connected(chosen):
      raise InvalidMove("The play area must be contiguous")

    self.colors.add(chosen)
    if len(self.colors) >= self.to_choose:
      self.filter_regions()
      self.turn_idx = 0
    else:
      self.turn_idx += 1
      self.turn_idx %= len(self.players)

  def filter_regions(self):
    self.cities = {city.name: city for city in self.cities.values() if city.color in self.colors}
    for city in self.cities.values():
      city.connections = {name: x for name, x in city.connections.items() if name in self.cities}

  def handle_bid(self, bid, plant_idx):
    if bid is None:  # player has decided to pass
      self.handle_pass()
      return

    if not isinstance(bid, int) or bid <= 0:
      raise InvalidMove("You must bid a positive integral amount")
    if not isinstance(plant_idx, int) or plant_idx < 0 or plant_idx >= len(self.market):
      raise InvalidMove(f"Invalid plant {plant_idx}")
    if self.stage_idx < 2 and plant_idx >= 4:
      raise InvalidMove("You cannot buy plants from the future market")
    if bid > self.players[self.auction_idx].money:
      raise InvalidMove("You do not have enough money")

    if self.auction_plant_idx is None:  # Opening bid on a plant
      if bid < self.market[plant_idx].cost:
        raise InvalidMove("You must bid at least the price shown on the plant")
      self.auction_plant_idx = plant_idx
      self.auction_bid = bid
      self.next_bidder()
      return

    if self.auction_plant_idx != plant_idx:
      raise InvalidMove("You must wait until this plant is sold before bidding on another one")
    if bid < self.auction_bid + 1:
      raise InvalidMove("You must bid more than the previous bidder")
    self.auction_bid = bid
    self.next_bidder()

  def handle_pass(self):
    if self.auction_plant_idx is not None:
      # The player is choosing to pass on bidding for this plant.
      self.auction_passed.add(self.auction_idx)
      self.next_bidder()
      return

    # The player choosing the plant is passing.
    if self.first_round:
      raise InvalidMove("You must buy a plant in the first round")
    self.auction_bought[self.auction_idx] = False
    self.next_auction()

  def next_bidder(self):
    # calculate remaining eligible auction participants, preserving order
    # eligible represents players still eligible to participate in any auction
    eligible = [idx for idx in self.turn_order if idx not in self.auction_bought]
    # remaining represents players still eligible to participate in this specific auction
    remaining = [idx for idx in eligible if idx not in self.auction_passed]
    if len(remaining) == 1:  # The last player standing gets the plant.
      self.award_plant(remaining[0], self.auction_plant_idx, self.auction_bid)
      self.next_auction()
      return
    # find the next eligible bidder
    # NOTE: we find auction_idx inside eligible instead of finding them inside remaining - this
    # is because one of the cases where this function is called is where auction_idx has just
    # passed on bidding, which means they cannot be found inside of remaining.
    next_idx_idx = eligible.index(self.auction_idx)
    next_idx_idx += 1
    next_idx_idx %= len(eligible)
    while eligible[next_idx_idx] in self.auction_passed:
      next_idx_idx += 1
      next_idx_idx %= len(eligible)
    self.auction_idx = eligible[next_idx_idx]

  def next_auction(self):
    self.auction_plant_idx = None
    self.auction_bid = None
    self.auction_passed = set()
    eligible = [idx for idx in self.turn_order if idx not in self.auction_bought]
    if not eligible:
      self.next_turn()
      return
    self.auction_idx = eligible[0]

  def award_plant(self, player_idx, plant_idx, winning_bid):
    plant = self.market[plant_idx]
    self.remove_plant(plant)
    self.players[player_idx].plants.append(plant)
    self.players[player_idx].money -= winning_bid
    self.auction_bought[player_idx] = True
    if len(self.players[player_idx].plants) > self.max_plants:
      self.auction_discard_idx = player_idx

  def remove_plant(self, plant):
    built = collections.defaultdict(int)
    for city in self.cities.values():
      for idx in city.occupants:
        built[idx] += 1
    max_built = max(built.values()) if built else 0

    self.market.remove(plant)
    expected_len = 8 if self.stage_idx < 2 else 6
    while self.plants and len(self.market) < expected_len:
      next_plant = self.plants.pop(0)
      if next_plant.cost >= STAGE_3_COST:
        self.begin_stage_3 = True
        random.shuffle(self.plants)
        if self.PHASES[self.phase_idx] is TurnPhase.AUCTION:
          self.market.append(next_plant)
        else:
          self.market.pop(0)
          expected_len = 6
      elif next_plant.cost > max_built:
        self.market.append(next_plant)
        self.market.sort()

  def handle_discard(self, plant_idx):
    if self.auction_discard_idx is None:
      raise InvalidMove("You cannot discard a plant at this time")
    if not isinstance(plant_idx, int):
      raise InvalidMove(f"Invalid plant {plant_idx}")
    if plant_idx < 0 or plant_idx > self.max_plants:
      raise InvalidMove(f"Invalid plant {plant_idx}")
    if plant_idx == self.max_plants:
      raise InvalidMove("You cannot discard the plant you just bought")
    # TODO: move any resources that would otherwise be discarded onto the new plant if possible
    # or maybe that should happen in the UI?
    self.players[self.auction_discard_idx].plants.pop(plant_idx)
    self.auction_discard_idx = None

  def handle_buy(self, resource_name, count):
    if self.PHASES[self.phase_idx] is not TurnPhase.MATERIALS:
      raise InvalidMove("You cannot buy materials at this time")
    try:
      resource = materials.Resource(resource_name)
    except ValueError:
      raise InvalidMove(f"Unknown resource {resource_name}")
    if not isinstance(count, int) or count <= 0:
      raise InvalidMove(f"You must purchase a positive integer amount of {resource_name}")

    if resource not in self.resources:
      raise InvalidMove(f"You cannot buy {resource_name}")
    rsrc_available = self.resources[resource] - self.pending_buy.get(resource, 0)
    if rsrc_available < count:
      raise InvalidMove(f"There is not enough {resource_name} available")

    money_available = self.players[self.turn_idx].money - self.pending_spend
    spend = 0
    for _ in range(count):
      spend += COSTS[resource][rsrc_available-1]
      rsrc_available -= 1
    if spend > money_available:
      raise InvalidMove(f"You would need {spend} to buy that much")

    capacity = collections.defaultdict(int)
    for plant in self.players[self.turn_idx].plants:
      capacity[plant.resource] += 2*plant.intake - sum(plant.storage.values())

    overflow = {}
    for rsrc in self.pending_buy.keys() | {resource}:
      pending_amount = self.pending_buy.get(rsrc, 0)
      if rsrc is resource:
        pending_amount += count
      if capacity[rsrc] < pending_amount:
        overflow[rsrc] = pending_amount - capacity[rsrc]

    if overflow.keys() - {COAL, OIL}:
      raise InvalidMove("You do not have enough storage")
    if overflow.get(COAL, 0) + overflow.get(OIL, 0) > capacity[HYBRID]:
      raise InvalidMove("You do not have enough storage")

    self.pending_spend += spend
    self.pending_buy[resource] = self.pending_buy.get(resource, 0) + count

  def handle_build(self, city_name):
    if self.PHASES[self.phase_idx] is not TurnPhase.BUILDING:
      raise InvalidMove("You cannot build at this time")
    if city_name not in self.cities:
      raise InvalidMove(f"Unknown city {city_name}")
    city = self.cities[city_name]
    if len(city.occupants) > self.stage_idx:
      raise InvalidMove(
          f"Cities may only be occupied by {self.stage_idx+1} players in this stage of the game"
      )
    if self.turn_idx in city.occupants or city_name in self.pending_build:
      raise InvalidMove(f"You are already in {city_name}")

    distance_cost = self.distance_cost(city)
    build_cost = 10 + 5 * len(city.occupants)
    cost = distance_cost + build_cost
    if self.players[self.turn_idx].money - self.pending_spend < cost:
      raise InvalidMove(f"You would need at least {cost} to build in {city_name}")

    self.pending_spend += cost
    self.pending_build.append(city_name)

  def distance_cost(self, city):
    # The first city that you build in has no connection cost.
    if not (any(self.turn_idx in c.occupants for c in self.cities.values()) or self.pending_build):
      return 0

    heap = []
    seen = set()
    for conn, cost in city.connections.items():
      heapq.heappush(heap, (cost, conn))

    while heap:
      closest = heapq.heappop(heap)
      cost = closest[0]
      dest = closest[-1]
      if dest in seen:
        continue
      seen.add(dest)

      if self.turn_idx in self.cities[dest].occupants or dest in self.pending_build:
        return cost

      for conn, added_cost in self.cities[dest].connections.items():
        if conn in seen:
          continue
        heapq.heappush(heap, (cost + added_cost, *list(closest[1:]) + [conn]))

    raise RuntimeError(f"No route to {city.name} for {self.turn_idx} from any of {seen}")

  def handle_reset(self):
    if self.PHASES[self.phase_idx] not in (TurnPhase.BUILDING, TurnPhase.MATERIALS):
      raise InvalidMove("You cannot do that right now")
    self.pending_build.clear()
    self.pending_buy.clear()
    self.pending_spend = 0

  def finish_buy(self):
    allocate = [collections.defaultdict(int) for _ in self.players[self.turn_idx].plants]
    remaining_buy = self.pending_buy.copy()
    # Start with non-hybrid plants to make sure resources are allocated optimally.
    for idx, plant in enumerate(self.players[self.turn_idx].plants):
      if not remaining_buy.get(plant.resource):  # This skips hybrid plants and irrelevant plants.
        continue
      remaining_capacity = 2*plant.intake - sum(plant.storage.values())
      allocated = min(remaining_capacity, remaining_buy[plant.resource])
      allocate[idx][plant.resource] += allocated
      remaining_buy[plant.resource] -= allocated
    # Now allocated to hybrid plants anything that is left over.
    # Note that we allocate to each plant exactly once, so we never check the values in allocate.
    for idx, plant in enumerate(self.players[self.turn_idx].plants):
      if plant.resource is not HYBRID:
        continue
      remaining_capacity = 2*plant.intake - sum(plant.storage.values())
      if remaining_buy.get(COAL):
        coal = min(remaining_capacity, remaining_buy[COAL])
        allocate[idx][COAL] += coal
        remaining_buy[COAL] -= coal
        remaining_capacity -= coal
      if remaining_buy.get(OIL):
        oil = min(remaining_capacity, remaining_buy[OIL])
        allocate[idx][OIL] += oil
        remaining_buy[OIL] -= oil

    if sum(remaining_buy.values()):
      raise InvalidMove("You do not have enough storage ")

    for idx, plant in enumerate(self.players[self.turn_idx].plants):
      for resource, count in allocate[idx].items():
        if not count:
          continue
        plant.storage[resource] = plant.storage.get(resource, 0) + count
    for resource, count in self.pending_buy.items():
      self.resources[resource] -= count

  def finish_build(self):
    # TODO: ensure there isn't a more efficient way to build using dynamic programming?
    for city_name in self.pending_build:
      self.cities[city_name].occupants.append(self.turn_idx)
    total_built = len([c for c in self.cities.values() if self.turn_idx in c.occupants])
    if total_built >= self.stage_2_count and self.stage_idx == 0:
      self.begin_stage_2 = True
    # Remove any plants with cost lower than the number built.
    while self.market and self.market[0].cost <= total_built:
      self.remove_plant(self.market[0])

  def handle_confirm(self):
    if self.PHASES[self.phase_idx] is TurnPhase.BUILDING:
      self.finish_build()
    elif self.PHASES[self.phase_idx] is TurnPhase.MATERIALS:
      self.finish_buy()
    else:
      raise InvalidMove("You cannot do that right now")

    self.players[self.turn_idx].money -= self.pending_spend
    self.handle_reset()
    self.next_turn()

  def handle_shuffle(self, player_idx, resource_name, source, dest):
    player = self.players[player_idx]
    if not isinstance(source, int) or not isinstance(dest, int):
      raise InvalidMove("Invalid source or destination plant")
    if not 0 <= source < len(player.plants):
      raise InvalidMove(f"Invalid source plant {source}")
    if not 0 <= dest < len(player.plants):
      raise InvalidMove(f"Invalid destination plant {dest}")
    try:
      resource = materials.Resource(resource_name)
    except ValueError:
      raise InvalidMove(f"Invalid resource {resource_name}")

    if not player.plants[source].storage.get(resource):
      raise InvalidMove(f"You do not have any {resource} on that plant")
    if not player.plants[dest].can_take(resource):
      raise InvalidMove(f"You cannot store {resource} on that plant")
    if sum(player.plants[dest].storage.values()) < 2*player.plants[dest].intake:
      player.plants[source].storage[resource] -= 1
      player.plants[dest].storage[resource] = player.plants[dest].storage.get(resource, 0) + 1
      return

    # Special case: if the destination is full, we allow the player to swap with one resource on
    # the destination if both the source and destination have at least two different types of
    # resources. This allows players to shuffle coal and oil between different hybrid plants, even
    # if those plants are full.
    on_dest = {rsrc for rsrc, count in player.plants[dest].storage.items() if count}
    if len(on_dest) < 2:
      raise InvalidMove("That plant is full")
    can_swap_back = [rsrc for rsrc in on_dest - {resource} if player.plants[source].can_take(rsrc)]
    if not can_swap_back:
      raise InvalidMove("Cannot swap resources between those plants")
    to_swap = can_swap_back[0]
    player.plants[source].storage[resource] -= 1
    player.plants[dest].storage[resource] = player.plants[dest].storage.get(resource, 0) + 1
    player.plants[source].storage[to_swap] = player.plants[source].storage.get(to_swap, 0) + 1
    player.plants[dest].storage[to_swap] -= 1

  def handle_burn(self, resource_counts):
    if self.PHASES[self.phase_idx] is not TurnPhase.BUREAUCRACY:
      raise InvalidMove("You cannot fire your power plants right now")
    if not isinstance(resource_counts, list):
      raise InvalidMove("Invalid resource counts")
    if not all(isinstance(count, dict) or count is None for count in resource_counts):
      raise InvalidMove("Invalid resource counts")
    if len(resource_counts) != len(self.players[self.turn_idx].plants):
      raise InvalidMove("You must specify which resources to burn on each plant you own")

    burn_counts = []
    try:
      for counts in resource_counts:
        if counts is None:
          burn_counts.append(None)
        else:
          burn_counts.append({materials.Resource(rsrc): count for rsrc, count in counts.items()})
    except ValueError:
      raise InvalidMove("Invalid resource in resource counts")

    for idx, counts in enumerate(burn_counts):
      if counts is None:
        continue
      plant = self.players[self.turn_idx].plants[idx]
      if not all(isinstance(val, int) and val > 0 for val in counts.values()):
        raise InvalidMove("You must burn a positive integral amount of resources")
      if not all(val <= plant.storage.get(rsrc, 0) for rsrc, val in counts.items()):
        raise InvalidMove("You must burn the resources that are on your plants")
      if sum(counts.values()) != plant.intake:
        raise InvalidMove("You must burn the exact number of resources the plant requires")

    output = 0
    for idx, counts in enumerate(burn_counts):
      if counts is None:
        continue
      plant = self.players[self.turn_idx].plants[idx]
      for resource, count in counts.items():
        plant.storage[resource] -= count
      # Remove 0 entries to make unit testing easier.
      plant.storage = {rsrc: cnt for rsrc, cnt in plant.storage.items() if cnt}
      output += plant.output

    operated = len([c for c in self.cities.values() if self.turn_idx in c.occupants])
    self.powered[self.turn_idx] = min(output, operated)
    payable = min(self.powered[self.turn_idx], len(PAYMENTS)-1)
    self.players[self.turn_idx].money += PAYMENTS[payable]

    self.next_turn()

  def resupply(self):
    owned = collections.defaultdict(int)
    for player in self.players:
      for plant in player.plants:
        for resource, count in plant.storage.items():
          owned[resource] += count
    for resource in [COAL, OIL, GAS, URANIUM]:
      rate = SUPPLY_RATES[len(self.players)][resource][self.stage_idx]
      total = len(COSTS[resource])
      available = max(total - owned[resource] - self.resources[resource], 0)
      self.resources[resource] += min(available, rate)

  def next_turn(self):
    # If we're staying in the same phase, just advance to the next player's turn.
    phase = self.PHASES[self.phase_idx]
    if phase is TurnPhase.BUREAUCRACY:
      next_idx = self.turn_order.index(self.turn_idx)+1
      if next_idx < len(self.turn_order):
        self.turn_idx = self.turn_order[next_idx]
        return
    elif phase in [TurnPhase.MATERIALS, TurnPhase.BUILDING]:
      next_idx = self.turn_order.index(self.turn_idx)-1
      if next_idx >= 0:
        self.turn_idx = self.turn_order[next_idx]
        return
    elif phase is TurnPhase.AUCTION:
      if self.first_round:
        self.reorder_players()
        self.first_round = False
      if self.market and not any(self.auction_bought.values()):
        self.remove_plant(self.market[0])

    # The phase is over; move to the next phase.
    if phase is TurnPhase.BUREAUCRACY:
      # If at least one player has enough cities connected, end the game.
      built = collections.defaultdict(int)
      for city in self.cities.values():
        for idx in city.occupants:
          built[idx] += 1
      max_built = max(built.values()) if built else 0
      if max_built >= self.end_game_count:
        self.find_winner()
        return

      # Remove a power plant (depending on game stage)
      if self.plants:
        if self.stage_idx < 2:
          cycle = self.market[-1]
          self.remove_plant(cycle)
          self.plants.append(cycle)
        else:
          self.remove_plant(self.market[0])
      self.resupply()

    if self.stage_idx < 2 and self.begin_stage_3:
      self.stage_idx = 2
      if self.market and self.market[-1].cost >= STAGE_3_COST:
        self.remove_plant(self.market[0])
        if self.market:
          self.remove_plant(self.market[-1])
    if self.stage_idx == 0 and self.begin_stage_2:
      self.stage_idx = 1
      if self.market:
        self.remove_plant(self.market[0])
    if phase is not TurnPhase.BUREAUCRACY:
      self.phase_idx += 1
      if self.PHASES[self.phase_idx] is TurnPhase.BUREAUCRACY:
        self.turn_idx = self.turn_order[0]
      else:
        self.turn_idx = self.turn_order[-1]
      return

    # Bureaucracy has ended; move to the next turn.
    self.reorder_players()  # Determine player order
    self.phase_idx = 0
    self.turn_idx = self.turn_order[0]
    self.auction_idx = self.turn_idx
    self.auction_plant_idx = None
    self.auction_bid = None
    self.auction_passed = set()
    self.auction_bought = {}
    return

  def find_winner(self):
    scores = []
    for idx, player in enumerate(self.players):
      built = len([c for c in self.cities.values() if idx in c.occupants])
      money = player.money
      powered = self.powered[idx]
      scores.append((powered, money, built, idx))
    scores.sort(reverse=True)
    best = scores[0][:-1]
    self.winner = []
    for score in scores:
      if score[:-1] == best:
        self.winner.append(score[-1])
      else:
        break

  def reorder_players(self):
    counts = collections.defaultdict(int)
    for city in self.cities.values():
      for occupant in city.occupants:
        counts[occupant] += 1

    def ordering(idx):
      return (counts[idx], max(self.players[idx].plants))

    self.turn_order.sort(key=ordering, reverse=True)


class PowerPlantGame(BaseGame):

  COLORS = {"red", "blue", "forestgreen", "darkviolet", "saddlebrown", "deepskyblue"}
  OPTIONS = {"region": ["Germany", "USA"], "plantlist": ["old", "new"]}

  def __init__(self):
    self.game = None
    self.connected = set()
    self.host = None
    self.options = {"region": "Germany", "plantlist": "old"}
    self.player_sessions = {}
    self.pending_players = {}

  def game_url(self, game_id):
    return f"/powerplant/game.html?game_id={game_id}"

  def game_status(self):
    if self.game is None:
      return f"unstarted power plant game ({len(self.pending_players)} players)"
    return "power plant game"  # TODO

  @classmethod
  def parse_json(cls, data):
    gamedata = json.loads(data)
    if not gamedata:
      return cls()
    game = cls()
    game.player_sessions = gamedata.pop("player_sessions")

    game_state = GameState.parse_json(gamedata)
    game.game = game_state
    return game

  def json_str(self):
    if self.game is None:
      return "{}"
    output = self.game.json_repr()
    output["player_sessions"] = dict(self.player_sessions)
    return json.dumps(output, cls=CustomEncoder)

  def for_player(self, session):
    if self.game is None:
      idx = None
      if session in self.pending_players:
        idx = sorted(self.pending_players).index(session)
      data = {
          "type": "game_state",
          "host": self.host == session,
          "player_idx": idx,
          "started": False,
          "options": self.options,
          "players": [],
          "colors": sorted(self.COLORS - {p.get("color") for p in self.pending_players.values()})
      }
      for sess in sorted(self.pending_players):
        data["players"].append(self.pending_players[sess])
      return json.dumps(data, cls=CustomEncoder)

    output = self.game.for_player(self.player_sessions.get(session))
    output["started"] = True
    for sess, idx in self.player_sessions.items():
      output["players"][idx]["disconnected"] = sess not in self.connected
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
    if session in self.pending_players:
      del self.pending_players[session]
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
    if session in self.pending_players:
      old = self.pending_players.pop(session)
      try:
        self.join_player(session, data)
      except:
        self.pending_players[session] = old
        raise
      return

    if len(self.pending_players) >= 6:
      raise TooManyPlayers("There are no open slots.")

    self.join_player(session, data)

  def join_player(self, session, data):
    ValidatePlayer(data)
    player_name = data["name"].strip()
    player_color = data.get("color")
    if player_name in {player["name"] for player in self.pending_players.values()}:
      raise InvalidPlayer(f"There is already a player named {player_name}")
    if player_color is not None:
      if player_color in {player["color"] for player in self.pending_players.values()}:
        raise InvalidPlayer(f"There is already a player using {player_color}")
      if player_color not in self.COLORS:
        raise InvalidPlayer(f"Invalid color {player_color}")

    self.pending_players[session] = {"name": player_name, "color": player_color}

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
    if len(self.pending_players) < 2:
      raise InvalidMove("The game must have at least two players to start.")

    for player_data in self.pending_players.values():
      if not player_data["color"]:
        available_colors = self.COLORS - {data["color"] for data in self.pending_players.values()}
        player_data["color"] = list(available_colors)[0]
    sessions = list(self.pending_players.keys())
    random.shuffle(sessions)

    players = [Player(**self.pending_players[session]) for session in sessions]
    game = GameState(players=players, **self.options)
    # NOTE: only update internal state after computing all new states so that internal state
    # remains consistent if something above throws an exception.
    self.player_sessions = {session: idx for idx, session in enumerate(sessions)}
    self.pending_players = {}
    self.game = game
    self.host = None

  def handle_select_option(self, session, data):
    if self.game is not None:
      raise InvalidMove("The game has already started.")
    if session != self.host:
      raise InvalidMove("You are not the host. Only the host can select game options.")

    unknown_options = data["options"].keys() - self.OPTIONS.keys()
    if unknown_options:
      raise InvalidMove(f"Unknown option(s) {', '.join(unknown_options)}")
    for option, value in data["options"].items():
      if value not in self.OPTIONS[option]:
        raise InvalidMove(f"Invalid choice {value} for option {option}")

    for option, value in data["options"].items():
      self.options[option] = value
