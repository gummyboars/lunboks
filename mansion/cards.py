class Card:
  def __init__(self, attack=None, bonus=None, movement=None, failures=None, room=None, variant=""):
    assert any(x is not None for x in [attack, movement, failures])
    assert failures or room
    if attack or movement:
      assert room is not None
    else:
      assert room is None
    if attack is not None:
      assert bonus is not None
    self.attack = attack
    self.bonus = bonus
    self.movement = movement
    self.failures = failures
    self.room = room
    self.variant = variant

  def json_repr(self):
    return {
      "name": self.name,
      "attack": self.attack,
      "bonus": self.bonus,
      "movement": self.movement,
      "failures": self.failures,
      "room": self.room,
      "variant": self.variant,
    }

  @property
  def name(self):
    if self.attack is not None:
      return f"{self.room} weapon"
    if self.movement is not None:
      return f"{self.room} movement"
    return f"failure{self.failures}"

  def attack_value(self, room):
    if self.attack is None:
      return None
    if room == self.room:
      return self.attack + self.bonus
    return self.attack


def CreateCards():
  moves = [
    Card(room="trophy", movement=1, failures=2),
    Card(room="lancaster", movement=1),
    Card(room="white", movement=1, failures=2),
    Card(room="garden", movement=1),
    Card(room="lilac", movement=1),
    Card(room="master", movement=2, failures=2),
    Card(room="drawing", movement=2, failures=1),
    Card(room="maze", movement=1),
    Card(room="foyer", movement=1, failures=2),
    Card(room="dingha", movement=2, failures=1),
    Card(room="armory", movement=1),
    Card(room="parlor", movement=1),
    Card(room="tennessee", movement=2, failures=2),
    Card(room="cellar", movement=1, failures=2),
    Card(room="gallery", movement=1, failures=2),
    Card(room="kitchen", movement=1, failures=1),
    Card(room="green", movement=2, failures=1),
    Card(room="piazza", movement=2),
    Card(room="library", movement=1, failures=1),
    Card(room="billiard", movement=1, failures=2),
    Card(room="servants", movement=1, failures=1),
    Card(room="carriage", movement=2, failures=1),
    Card(room="nursery", movement=1, failures=1),
    Card(room="sitting", movement=1),
  ]
  weapons = [
    Card(room="trophy", attack=2, bonus=3, failures=1),
    Card(room="piazza", attack=2, bonus=2, failures=2),
    Card(room="library", attack=2, bonus=2, failures=2),
    Card(room="billiard", attack=3, bonus=2, failures=1),
    Card(room="gallery", attack=2, bonus=4),
    Card(room="drawing", attack=3, bonus=3),
    Card(room="foyer", attack=2, bonus=4),
    Card(room="dingha", attack=2, bonus=3),
    Card(room="cellar", attack=2, bonus=3, failures=1),
    Card(room="white", attack=2, bonus=4, failures=1),
    Card(room="kitchen", attack=2, bonus=4, failures=2),
    Card(room="servants", attack=2, bonus=2, failures=2),
    Card(room="lilac", attack=2, bonus=2),
    Card(room="lancaster", attack=2, bonus=2, failures=2),
    Card(room="master", attack=2, bonus=3, failures=1),
    Card(room="armory", attack=3, bonus=3),
    Card(room="parlor", attack=2, bonus=2, failures=2),
    Card(room="nursery", attack=2, bonus=3, failures=1),
    Card(room="green", attack=3, bonus=2),
    Card(room="tennessee", attack=2, bonus=4, failures=1),
    Card(room="carriage", attack=2, bonus=3, failures=1),
    Card(room="garden", attack=2, bonus=2, failures=2),
    Card(room="maze", attack=3, bonus=3),
    Card(room="sitting", attack=2, bonus=2, failures=2),
  ]
  fail_counts = {1: 10, 2: 6, 3: 4, 4: 4}
  failures = []
  for num, count in fail_counts.items():
    for idx in range(count):
      failures.append(Card(failures=num, variant=str(idx)))
  return moves + weapons + failures
