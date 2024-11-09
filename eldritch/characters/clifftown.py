from eldritch import characters


class Urchin(characters.Character):
  def __init__(self):
    super().__init__("Urchin", 4, 4, 5, 6, 3, 3, 4, 5, 3, "Bank")

  def abilities(self):
    return ["Streetwise", "Blessed is the Child", "Minor"]

  def initial_attributes(self):
    return {"dollars": 3, "clues": 3}

  def fixed_possessions(self):
    return {"unique": ["Elder Sign"]}

  def random_possessions(self):
    return {"common": 1, "skills": 1}
