class Gate(object):

  def __init__(self, info, difficulty):
    self.info = info
    self._difficulty = difficulty

  @property
  def name(self):
    return self.info.name

  @property
  def colors(self):
    return self.info.colors

  def difficulty(self, state):
    return self._difficulty + state.get_modifier(self, "difficulty")

  def json_repr(self):
    return {"name": self.name, "colors": sorted(list(self.colors))}


def CreateGates(infos):
  difficulties = {
      "Abyss": -2,
      "Another Dimension": 0,
      "City": 0,
      "Great Hall": -1,
      "Plateau": -1,
      "Sunken City": -3,
      "Dreamlands": 1,
      "Pluto": -2,
  }
  gates = []
  for info in infos:
    for _ in range(2):
      gates.append(Gate(info, difficulties[info.name]))
  return gates
