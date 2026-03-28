from .core import Character


class Entertainer(Character):
  def __init__(self):
    super().__init__("Entertainer", 4, 6, 4, 4, 3, 5, 4, 4, 2, "House")

  def initial_attributes(self):
    return {"dollars": 4, "clues": 2}

  def fixed_possessions(self):
    return {"unique": ["Enchanted Knife"], "spells": ["Voice"]}

  def random_possessions(self):
    return {"spells": 2, "skills": 1}

  def abilities(self):
    return ["Witch Blood", "Third Eye"]


class ExpeditionLeader(Character):
  def __init__(self):
    super().__init__("Expedition Leader", 5, 5, 4, 4, 4, 4, 4, 4, 2, "Docks")

  def initial_attributes(self):
    return {"dollars": 5, "clues": 2}

  def random_possessions(self):
    return {"allies": 1, "common": 1, "skills": 1}

  def abilities(self):
    return ["Leadership"]


class Phychic(Character):
  def __init__(self):
    super().__init__("Phychic", 3, 7, 4, 3, 4, 4, 5, 4, 2, "Shop")

  def initial_attributes(self):
    return {"dollars": 7, "clues": 2}

  def fixed_possessions(self):
    return {"unique": ["Enchanted Jewelry"]}

  def random_possessions(self):
    return {"common": 1, "spells": 2, "skills": 1}

  def abilities(self):
    return ["Precognition"]


def CreateCharacters():
  return {c.name: c for c in [Entertainer(), ExpeditionLeader(), Phychic()]}
