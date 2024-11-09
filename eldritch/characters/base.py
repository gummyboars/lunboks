from eldritch.characters.core import Character


class Student(Character):
  def __init__(self):
    super().__init__("Student", 5, 5, 4, 4, 4, 4, 4, 4, 3, "Bank")

  def abilities(self):
    return ["Studious"]

  def initial_attributes(self):
    return {"dollars": 1, "clues": 1}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 1, "unique": 1, "spells": 1, "skills": 2}


class Drifter(Character):
  def __init__(self):
    super().__init__("Drifter", 6, 4, 3, 6, 5, 5, 3, 3, 1, "Docks")

  def abilities(self):
    return ["Scrounge"]

  def initial_attributes(self):
    return {"dollars": 1, "clues": 3}

  def fixed_possessions(self):
    return {"allies": ["Dog"]}

  def random_possessions(self):
    return {"common": 1, "unique": 1, "skills": 1}


class Salesman(Character):
  def __init__(self):
    super().__init__("Salesman", 6, 4, 5, 3, 4, 6, 3, 4, 1, "Store")

  def abilities(self):
    return ["Shrewd Dealer"]

  def initial_attributes(self):
    return {"dollars": 9}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 2, "unique": 2, "skills": 1}


class Psychologist(Character):
  def __init__(self):
    super().__init__("Psychologist", 4, 6, 3, 3, 4, 4, 5, 5, 2, "Asylum")

  def abilities(self):
    return ["Psychology"]

  def initial_attributes(self):
    return {"dollars": 7, "clues": 1}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"unique": 2, "common": 2, "skills": 1}


class Photographer(Character):
  def __init__(self):
    super().__init__("Photographer", 6, 4, 5, 3, 5, 4, 3, 4, 2, "Newspaper")

  def abilities(self):
    return ["Hometown Advantage"]

  def initial_attributes(self):
    return {"dollars": 1, "clues": 1}

  def fixed_possessions(self):
    return {"specials": ["Retainer"]}

  def random_possessions(self):
    return {"common": 1, "unique": 2, "skills": 1}


class Magician(Character):
  def __init__(self):
    super().__init__("Magician", 5, 5, 5, 4, 4, 3, 5, 3, 2, "Shoppe")

  def abilities(self):
    return ["Magical Gift"]

  def initial_attributes(self):
    return {"dollars": 5}

  def fixed_possessions(self):
    return {"spells": ["Shrivelling"]}

  def random_possessions(self):
    return {"common": 1, "unique": 1, "spells": 2, "skills": 1}


class Author(Character):
  def __init__(self):
    super().__init__("Author", 4, 6, 4, 3, 3, 5, 4, 5, 2, "Diner")

  def abilities(self):
    return ["Psychic Sensitivity"]

  def initial_attributes(self):
    return {"dollars": 7, "clues": 2}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 2, "spells": 2, "skills": 1}


class Professor(Character):
  def __init__(self):
    super().__init__("Professor", 3, 7, 3, 5, 3, 3, 6, 4, 2, "Administration")

  def abilities(self):
    return ["Strong Mind"]

  def initial_attributes(self):
    return {"dollars": 5, "clues": 1}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"unique": 2, "spells": 2, "skills": 1}


class Dilettante(Character):
  def __init__(self):
    super().__init__("Dilettante", 4, 6, 3, 4, 4, 5, 4, 5, 1, "Train")

  def abilities(self):
    return ["Trust Fund"]

  def initial_attributes(self):
    return {"dollars": 10}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 2, "unique": 1, "spells": 1, "skills": 1}


class PrivateEye(Character):
  def __init__(self):
    super().__init__("Private Eye", 6, 4, 6, 4, 5, 3, 3, 3, 3, "Police")

  def abilities(self):
    return ["Hunches"]

  def initial_attributes(self):
    return {"dollars": 8, "clues": 3}

  def fixed_possessions(self):
    return {"common": [".45 Automatic"]}

  def random_possessions(self):
    return {"common": 2, "skills": 1}


class Scientist(Character):
  def __init__(self):
    super().__init__("Scientist", 4, 6, 4, 5, 4, 3, 5, 4, 1, "Science")

  def abilities(self):
    return ["Flux Stabilizer"]

  def initial_attributes(self):
    return {"dollars": 7, "clues": 2}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 1, "unique": 1, "spells": 2, "skills": 1}


class Researcher(Character):
  def __init__(self):
    super().__init__("Researcher", 5, 5, 4, 5, 3, 5, 4, 3, 2, "Library")

  def abilities(self):
    return ["Research"]

  def initial_attributes(self):
    return {"dollars": 6, "clues": 4}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 2, "unique": 1, "skills": 1}


class Nun(Character):
  def __init__(self):
    super().__init__("Nun", 3, 7, 4, 4, 3, 4, 4, 6, 1, "Church")

  def abilities(self):
    return ["Guardian Angel"]

  def initial_attributes(self):
    return {}

  def fixed_possessions(self):
    return {"common": ["Cross"], "unique": ["Holy Water"], "specials": ["Blessing"]}

  def random_possessions(self):
    return {"spells": 2, "skills": 1}


class Doctor(Character):
  def __init__(self):
    super().__init__("Doctor", 5, 5, 3, 5, 3, 4, 5, 4, 2, "Hospital")

  def abilities(self):
    return ["Physician"]

  def initial_attributes(self):
    return {"dollars": 9, "clues": 1}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 2, "spells": 2, "skills": 1}


class Archaeologist(Character):
  def __init__(self):
    super().__init__("Archaeologist", 7, 3, 4, 3, 5, 3, 4, 5, 2, "Shop")

  def abilities(self):
    return ["Archaeology"]

  def initial_attributes(self):
    return {"dollars": 7, "clues": 1}

  def fixed_possessions(self):
    return {"common": [".38 Revolver", "Bullwhip"]}

  def random_possessions(self):
    return {"unique": 2, "skills": 1}


class Gangster(Character):
  def __init__(self):
    super().__init__("Gangster", 7, 3, 5, 4, 6, 4, 3, 3, 1, "House")

  def abilities(self):
    return ["Strong Body"]

  def initial_attributes(self):
    return {"dollars": 8}

  def fixed_possessions(self):
    return {"common": ["Dynamite", "Tommy Gun"]}

  def random_possessions(self):
    return {"unique": 1, "skills": 1}


def CreateCharacters():
  return {
    c.name: c
    for c in [
      Student(),
      Drifter(),
      Salesman(),
      Psychologist(),
      Photographer(),
      Magician(),
      Author(),
      Professor(),
      Dilettante(),
      PrivateEye(),
      Scientist(),
      Researcher(),
      Nun(),
      Doctor(),
      Archaeologist(),
      Gangster(),
    ]
  }
