class Gate:

  def __init__(self, name, idx, difficulty, dimension):
    self.name = name
    self.idx = idx
    self._difficulty = difficulty
    self.dimension = dimension

  def difficulty(self, state):
    return self._difficulty + state.get_modifier(self, "difficulty")

  @property
  def handle(self):
    if self.idx is None:
      return "Gate " + self.name
    return "Gate " + self.name + str(self.idx)

  def json_repr(self):
    return {"name": "Gate " + self.name, "handle": self.handle, "dimension": self.dimension}


def CreateGates():
  gate_info = [
      ("Abyss", -2, "hex"),
      ("Another Dimension", 0, "square"),
      ("City", 0, "triangle"),
      ("Great Hall", -1, "star"),
      ("Plateau", -1, "diamond"),
      ("Sunken City", -3, "plus"),
      ("Dreamlands", 1, "slash"),
      ("Pluto", -2, "circle"),
  ]
  gates = []
  for info in gate_info:
    for idx in range(2):
      gates.append(Gate(info[0], idx, *info[1:]))
  return gates
