class Room:

  def __init__(self, short_name, name, number):
    self.short_name = short_name
    self.name = name
    self.number = number
    self.connections = set()
    self.sight = set()

  def add_sight(self, other_room):
    other_room.sight.add(self)
    self.sight.add(other_room)

  def add_conn(self, other_room):
    other_room.connections.add(self)
    self.connections.add(other_room)

  def json_repr(self):
    return {"name": self.name, "number": self.number, "short": self.short_name}


def direct_connect(room_a, room_b):
  room_a.add_sight(room_b)
  room_a.add_conn(room_b)


def create_hallway(*rooms):
  for idx, room in enumerate(rooms):
    for other_room in rooms[idx+1:]:
      room.add_conn(other_room)


def create_sightline(*rooms):
  for idx, room in enumerate(rooms[1:], 1):
    prev_room = rooms[idx-1]
    if room is None or prev_room is None:
      continue
    prev_room.add_conn(room)

  for idx, room in enumerate(rooms):
    for other_room in rooms[idx+1:]:
      if room is None or other_room is None:
        continue
      room.add_sight(other_room)


def CreateRooms():
  drawing = Room("drawing", "Drawing Room", 1)
  parlor = Room("parlor", "Parlor", 2)
  billiard = Room("billiard", "Billiard Room", 3)
  dingha = Room("dingha", "Dining Hall", 4)
  sitting = Room("sitting", "Sitting Room", 5)
  trophy = Room("trophy", "Trophy Room", 6)
  green = Room("green", "Green House", 7)
  garden = Room("garden", "Winter Garden", 8)
  cellar = Room("cellar", "Wine Cellar", 9)
  kitchen = Room("kitchen", "Kitchen", 10)
  lancaster = Room("lancaster", "Lancaster Room", 11)
  master = Room("master", "Master Suite", 12)
  nursery = Room("nursery", "Nursery", 13)
  armory = Room("armory", "Armory", 14)  # who puts an armory next to a nursery?
  gallery = Room("gallery", "Gallery", 15)
  library = Room("library", "Library", 16)
  tennessee = Room("tennessee", "Tennessee Room", 17)
  lilac = Room("lilac", "Lilac Room", 18)
  servants = Room("servants", "Servants' Quarters", 19)
  white = Room("white", "White Room", 20)
  maze = Room("maze", "Hedge Maze", 21)
  carriage = Room("carriage", "Carriage House", 22)
  piazza = Room("piazza", "Piazza", 23)
  foyer = Room("foyer", "Foyer", 24)
  hall = None

  create_sightline(nursery, armory, library, hall, tennessee)
  create_sightline(master, hall, nursery, gallery, library)
  create_sightline(lancaster, hall, dingha)
  create_sightline(dingha, hall, lilac)
  create_sightline(sitting, dingha, billiard)
  create_sightline(trophy, drawing, parlor)
  create_sightline(kitchen, hall, trophy)
  create_sightline(parlor, hall, servants)
  create_sightline(green, hall, carriage)
  create_sightline(piazza, carriage, maze)
  create_sightline(garden, green, piazza)

  create_sightline(master, hall, kitchen)
  create_sightline(master, lancaster)
  create_sightline(kitchen, cellar, garden)
  create_sightline(trophy, green)
  create_sightline(sitting, hall, trophy)
  create_sightline(armory, gallery)
  create_sightline(gallery, dingha, drawing, foyer)
  gallery.connections.remove(dingha)
  dingha.connections.remove(gallery)
  create_sightline(billiard, hall, parlor)
  create_sightline(parlor, carriage)
  create_sightline(tennessee, lilac)
  create_sightline(servants, white, maze)
  create_sightline(tennessee, hall, servants)

  create_hallway(green, carriage, piazza, foyer)
  create_hallway(dingha, sitting, trophy, garden, kitchen, lancaster, master)
  create_hallway(dingha, sitting, lancaster, master, nursery)
  create_hallway(dingha, billiard, library, tennessee, lilac)
  create_hallway(dingha, billiard, parlor, maze, servants, tennessee, lilac)

  return [
      drawing, parlor, billiard, dingha, sitting, trophy, green, garden, cellar, kitchen, lancaster,
      master, nursery, armory, gallery, library, tennessee, lilac, servants, white, maze, carriage,
      piazza, foyer,
  ]


def CreateRoomsOld():
  drawing = Room("drawing", "Drawing Room", 1)
  parlor = Room("parlor", "Parlor", 2)
  billiard = Room("billiard", "Billiard Room", 3)
  dingha = Room("dingha", "Dining Hall", 4)
  sitting = Room("sitting", "Sitting Room", 5)
  trophy = Room("trophy", "Trophy Room", 6)
  green = Room("green", "Green House", 7)
  garden = Room("garden", "Winter Garden", 8)
  cellar = Room("cellar", "Wine Cellar", 9)
  kitchen = Room("kitchen", "Kitchen", 10)
  lancaster = Room("lancaster", "Lancaster Room", 11)
  master = Room("master", "Master Suite", 12)
  nursery = Room("nursery", "Nursery", 13)
  armory = Room("armory", "Armory", 14)  # who puts an armory next to a nursery?
  gallery = Room("gallery", "Gallery", 15)
  library = Room("library", "Library", 16)
  tennessee = Room("tennessee", "Tennessee Room", 17)
  lilac = Room("lilac", "Lilac Room", 18)
  servants = Room("servants", "Servants' Quarters", 19)
  white = Room("white", "White Room", 20)
  maze = Room("maze", "Hedge Maze", 21)
  carriage = Room("carriage", "Carriage House", 22)
  piazza = Room("piazza", "Piazza", 23)
  foyer = Room("foyer", "Foyer", 24)

  direct_connect(drawing, foyer)
  direct_connect(drawing, parlor)
  direct_connect(drawing, trophy)
  direct_connect(drawing, dingha)
  drawing.add_sight(gallery)

  direct_connect(parlor, carriage)
  parlor.add_sight(billiard)
  parlor.add_sight(trophy)
  parlor.add_sight(servants)

  direct_connect(billiard, dingha)
  billiard.add_sight(sitting)

  direct_connect(dingha, sitting)
  dingha.add_sight(gallery)
  dingha.add_sight(foyer)
  dingha.add_sight(lancaster)
  dingha.add_sight(lilac)

  sitting.add_sight(trophy)

  direct_connect(trophy, green)
  trophy.add_sight(kitchen)

  direct_connect(green, garden)
  direct_connect(green, piazza)
  green.add_sight(carriage)

  direct_connect(garden, cellar)
  garden.add_sight(piazza)
  garden.add_sight(kitchen)

  direct_connect(cellar, kitchen)

  kitchen.add_sight(master)

  direct_connect(master, lancaster)
  master.add_sight(nursery)
  master.add_sight(gallery)
  master.add_sight(library)

  direct_connect(nursery, armory)
  direct_connect(nursery, gallery)
  nursery.add_sight(library)
  nursery.add_sight(tennessee)

  direct_connect(armory, gallery)
  direct_connect(armory, library)
  armory.add_sight(tennessee)

  direct_connect(gallery, library)
  gallery.add_sight(foyer)

  library.add_sight(tennessee)

  direct_connect(tennessee, lilac)
  tennessee.add_sight(servants)

  direct_connect(servants, white)
  servants.add_sight(maze)

  direct_connect(white, maze)

  direct_connect(maze, carriage)
  maze.add_sight(piazza)

  direct_connect(carriage, piazza)

  create_hallway(green, carriage, piazza, foyer)
  create_hallway(dingha, sitting, trophy, garden, kitchen, lancaster, master)
  create_hallway(dingha, sitting, lancaster, master, nursery)
  create_hallway(dingha, billiard, library, tennessee, lilac)
  create_hallway(dingha, billiard, parlor, maze, servants, tennessee, lilac)

  return [
      drawing, parlor, billiard, dingha, sitting, trophy, green, garden, cellar, kitchen, lancaster,
      master, nursery, armory, gallery, library, tennessee, lilac, servants, white, maze, carriage,
      piazza, foyer,
  ]


def RoomMap(all_rooms):
  room_map = {}
  for room in all_rooms:
    room_map[room.name] = {}
    room_map[room.name]["connections"] = {conn.name for conn in room.connections}
    room_map[room.name]["sight"] = {conn.name for conn in room.sight}
  return room_map
