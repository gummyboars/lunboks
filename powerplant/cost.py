import heapq


def total_cost(cities, player_idx, city_names):
  if not city_names:  # No cities to connect == no cost
    return 0

  city_names = set(city_names)  # Create our own mutable copy
  heap = []
  costs = {}
  for name, city in cities.items():
    if player_idx in city.occupants:
      costs[name] = 0
      for conn, cost in city.connections.items():
        heapq.heappush(heap, (cost, conn))

  if not heap:  # Player has no cities so far - pick an arbitrary one as their starting point.
    first = city_names.pop()
    costs[first] = 0
    for conn, cost in cities[first].connections.items():
      heapq.heappush(heap, (cost, conn))

  total = 0
  while city_names and heap:
    cost, name = heapq.heappop(heap)
    if cost >= costs.get(name, float("inf")):
      continue

    if name in city_names:
      # If we have reached one of the cities that we want to build in, add the cost so far to the
      # running total, and then reset - we calculate again, assuming building to this city costs 0
      city_names.remove(name)
      total += cost
      costs[name] = 0
      for conn, added_cost in cities[name].connections.items():
        heapq.heappush(heap, (added_cost, conn))
      continue

    costs[name] = cost
    for conn, added_cost in cities[name].connections.items():
      heapq.heappush(heap, (cost + added_cost, conn))

  if city_names:
    raise RuntimeError(f"No route to {city_names} for {player_idx} from {costs}")

  return total
