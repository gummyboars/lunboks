from eldritch import abilities
from eldritch import events


class Character:

  def __init__(
      self, name, max_stamina, max_sanity, max_speed, max_sneak,
      max_fight, max_will, max_lore, max_luck, focus, home,
  ):
    self.name = name
    self._max_stamina = max_stamina
    self._max_sanity = max_sanity
    self._speed_sneak = [(max_speed - 3 + i, max_sneak - i) for i in range(4)]
    self._fight_will = [(max_fight - 3 + i, max_will - i) for i in range(4)]
    self._lore_luck = [(max_lore - 3 + i, max_luck - i) for i in range(4)]
    self.speed_sneak_slider = 3
    self.fight_will_slider = 3
    self.lore_luck_slider = 3
    self._focus = focus
    self.stamina = self.max_stamina
    self.sanity = self.max_sanity
    self.dollars = 0
    self.clues = 0
    self.possessions = []  # includes special abilities, skills, and allies
    # TODO: maybe the blessings, retainers, bank loans, and lodge memberships should be possessions.
    self.bless_curse = 0  # -1 for curse, +1 for blessed
    self.bless_curse_start = None
    self.retainer_start = None
    self.bank_loan_start = None
    self.lodge_membership = False
    self.delayed_until = None
    self.lose_turn_until = None
    self.movement_points = self._speed_sneak[self.speed_sneak_slider][0]
    self.focus_points = self.focus
    self.home = home
    self.place = None
    self.explored = False

  def get_json(self, state):
    attrs = [
        "name", "max_stamina", "max_sanity", "stamina", "sanity", "focus",
        "movement_points", "focus_points",
        "dollars", "clues", "possessions",  # TODO: special cards
        "delayed_until", "lose_turn_until",
    ]
    data = {attr: getattr(self, attr) for attr in attrs}
    data["sliders"] = {}
    for slider in self.sliders():
      data["sliders"][slider] = {
          "pairs": getattr(self, "_" + slider),
          "selection": getattr(self, slider + "_slider"),
      }
    computed = ["speed", "sneak", "fight", "will", "lore", "luck"]
    data.update({attr: getattr(self, attr)(state) for attr in computed})
    data["place"] = self.place.name if self.place is not None else None
    data["fixed"] = sum(self.fixed_possessions().values(), [])
    data["random"] = self.random_possessions()
    data["initial"] = self.initial_attributes()
    return data

  # TODO: add global effects to all properties
  @property
  def max_stamina(self):
    return self._max_stamina

  @property
  def max_sanity(self):
    return self._max_sanity

  def speed(self, state):
    return self._speed_sneak[self.speed_sneak_slider][0] + self.bonus("speed", state)

  def sneak(self, state):
    return self._speed_sneak[self.speed_sneak_slider][1] + self.bonus("sneak", state)

  def fight(self, state):
    return self._fight_will[self.fight_will_slider][0] + self.bonus("fight", state)

  def will(self, state):
    return self._fight_will[self.fight_will_slider][1] + self.bonus("will", state)

  def lore(self, state):
    return self._lore_luck[self.lore_luck_slider][0] + self.bonus("lore", state)

  def luck(self, state):
    return self._lore_luck[self.lore_luck_slider][1] + self.bonus("luck", state)

  def evade(self, state):
    return self.sneak(state) + self.bonus("evade", state)

  def combat(self, state, attributes):
    combat = self.fight(state)
    for bonus_type in {"physical", "magical", "combat"}:
      combat += self.bonus(bonus_type, state, attributes)
    return combat

  def horror(self, state):
    return self.will(state) + self.bonus("horror", state)

  def spell(self, state):
    return self.lore(state) + self.bonus("spell", state)

  @property
  def focus(self):
    return self._focus

  def get_interrupts(self, event, state):
    return [
        p.get_interrupt(event, self, state) for p in self.possessions
        if p.get_interrupt(event, self, state)
    ]

  def get_usable_interrupts(self, event, state):
    return {
        idx: p.get_usable_interrupt(event, self, state) for idx, p in enumerate(self.possessions)
        if p.get_usable_interrupt(event, self, state)
    }

  def get_triggers(self, event, state):
    return [
        p.get_trigger(event, self, state) for p in self.possessions
        if p.get_trigger(event, self, state)
    ]

  def get_usable_triggers(self, event, state):
    triggers = {
        idx: p.get_usable_trigger(event, self, state) for idx, p in enumerate(self.possessions)
        if p.get_usable_trigger(event, self, state)
    }
    if self.clues > 0 and isinstance(event, events.Check) and event.character == self:
      triggers["clues"] = events.SpendClue(self, event)
    return triggers

  def bonus(self, check_name, state, attributes=None):
    modifier = state.get_modifier(self, check_name)
    for pos in self.possessions:
      bonus = pos.get_bonus(check_name, attributes)
      if attributes and check_name in {"magical", "physical"}:
        if check_name + " immunity" in attributes:
          bonus = 0
        elif check_name + " resistance" in attributes:
          bonus = (bonus + 1) // 2
      modifier += bonus
    return modifier

  def get_modifier(self, other, attribute):
    return sum([p.get_modifier(other, attribute) or 0 for p in self.possessions])

  def get_override(self, other, attribute):
    override = None
    for pos in self.possessions:
      val = pos.get_override(other, attribute)  # pylint: disable=assignment-from-none
      if val is None:
        continue
      if override is None:
        override = val
      override = override and val
    return override

  def count_successes(self, roll, check_type):
    # pylint: disable=unused-argument
    threshold = 5 - self.bless_curse
    return len([result for result in roll if result >= threshold])

  def hands_available(self):
    return 2 - sum([pos.hands_used() for pos in self.possessions if hasattr(pos, "hands_used")])

  def sliders(self):
    sliders = {}
    for key, val in self.__dict__.items():
      if key.endswith("_slider"):
        sliders[key[:-7]] = val
    return sliders

  def focus_cost(self, pending_sliders):
    return sum([abs(orig - pending_sliders[name]) for name, orig in self.sliders().items()])

  def abilities(self):
    return []

  def initial_attributes(self):
    return {}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {}


class Student(Character):

  def __init__(self):
    super(Student, self).__init__("Student", 5, 5, 4, 4, 4, 4, 4, 4, 3, "Bank")

  def abilities(self):
    return []  # TODO: Studious

  def initial_attributes(self):
    return {"dollars": 1, "clues": 1}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 1, "unique": 1, "spells": 1, "skills": 2}


class Drifter(Character):

  def __init__(self):
    super(Drifter, self).__init__("Drifter", 6, 4, 3, 6, 5, 5, 3, 3, 1, "Docks")

  def abilities(self):
    return []  # TODO: Scrounge

  def initial_attributes(self):
    return {"dollars": 1, "clues": 3}

  def fixed_possessions(self):
    return {"allies": ["Dog"]}

  def random_possessions(self):
    return {"common": 1, "unique": 1, "skills": 1}


class Salesman(Character):

  def __init__(self):
    super(Salesman, self).__init__("Salesman", 6, 4, 5, 3, 4, 6, 3, 4, 1, "Store")

  def abilities(self):
    return []  # TODO: Shrewd

  def initial_attributes(self):
    return {"dollars": 9}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 2, "unique": 2, "skills": 1}


class Psychologist(Character):

  def __init__(self):
    super(Psychologist, self).__init__("Psychologist", 4, 6, 3, 3, 4, 4, 5, 5, 2, "Asylum")

  def abilities(self):
    return []  # TODO: Psychology

  def initial_attributes(self):
    return {"dollars": 7, "clues": 1}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"unique": 2, "common": 2, "skills": 1}


class Photographer(Character):

  def __init__(self):
    super(Photographer, self).__init__("Photographer", 6, 4, 5, 3, 5, 4, 3, 4, 2, "Newspaper")

  def abilities(self):
    return []  # TODO: Hometown

  def initial_attributes(self):
    return {"dollars": 1, "clues": 1, "retainer_start": 0}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 1, "unique": 2, "skills": 1}


class Magician(Character):

  def __init__(self):
    super(Magician, self).__init__("Magician", 5, 5, 5, 4, 4, 3, 5, 3, 2, "Shoppe")

  def abilities(self):
    return []  # TODO: Gift

  def initial_attributes(self):
    return {"dollars": 5}

  def fixed_possessions(self):
    return {"spells": ["Shrivelling"]}

  def random_possessions(self):
    return {"common": 1, "unique": 1, "spells": 2, "skills": 1}


class Author(Character):

  def __init__(self):
    super(Author, self).__init__("Author", 4, 6, 4, 3, 3, 5, 4, 5, 2, "Diner")

  def abilities(self):
    return []  # TODO: Sensitivity

  def initial_attributes(self):
    return {"dollars": 7, "clues": 2}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 2, "spells": 2, "skills": 1}


class Professor(Character):

  def __init__(self):
    super(Professor, self).__init__("Professor", 3, 7, 3, 5, 3, 3, 6, 4, 2, "Administration")

  def abilities(self):
    return []  # TODO: Mind

  def initial_attributes(self):
    return {"dollars": 5, "clues": 1}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"unique": 2, "spells": 2, "skills": 1}


class Dilettante(Character):

  def __init__(self):
    super(Dilettante, self).__init__("Dilettante", 4, 6, 3, 4, 4, 5, 4, 5, 1, "Train")

  def abilities(self):
    return []  # TODO: Trust Fund

  def initial_attributes(self):
    return {"dollars": 10}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 2, "unique": 1, "spells": 1, "skills": 1}


class PrivateEye(Character):

  def __init__(self):
    super(PrivateEye, self).__init__("Private Eye", 6, 4, 6, 4, 5, 3, 3, 3, 3, "Police")

  def abilities(self):
    return []  # TODO: Hunches

  def initial_attributes(self):
    return {"dollars": 8, "clues": 3}

  def fixed_possessions(self):
    return {"common": [".45 Automatic"]}

  def random_possessions(self):
    return {"common": 2, "skills": 1}


class Scientist(Character):

  def __init__(self):
    super(Scientist, self).__init__("Scientist", 4, 6, 4, 5, 4, 3, 5, 4, 1, "Science")

  def abilities(self):
    return []  # TODO: Flux Stabilizer

  def initial_attributes(self):
    return {"dollars": 7, "clues": 2}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 1, "unique": 1, "spells": 2, "skills": 1}


class Researcher(Character):

  def __init__(self):
    super(Researcher, self).__init__("Researcher", 5, 5, 4, 5, 3, 5, 4, 3, 2, "Libray")

  def abilities(self):
    return []  # TODO: Research

  def initial_attributes(self):
    return {"dollars": 6, "clues": 4}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {"common": 2, "unique": 1, "skill": 1}


class Nun(Character):

  def __init__(self):
    super().__init__("Nun", 3, 7, 4, 4, 3, 4, 4, 6, 1, "Church")

  def initial_attributes(self):
    return {"bless_curse": 1}

  def fixed_possessions(self):
    return {"common": ["Cross"], "unique": ["Holy Water"]}

  def random_possessions(self):
    return {"spells": 2, "skills": 1}


class Doctor(Character):

  def __init__(self):
    super().__init__("Doctor", 5, 5, 3, 5, 3, 4, 5, 4, 2, "Hospital")

  def abilities(self):
    return [abilities.Medicine()]

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
    return []  # TODO: Archaeology

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
    return []  # TODO: Body

  def initial_attributes(self):
    return {"dollars": 8}

  def fixed_possessions(self):
    return {"common": ["Dynamite", "Tommy Gun"]}

  def random_possessions(self):
    return {"unique": 1, "skills": 1}


def CreateCharacters():
  return {
      c.name: c for c in [
          Student(), Drifter(), Salesman(), Psychologist(), Photographer(), Magician(), Author(),
          Professor(), Dilettante(), PrivateEye(), Scientist(), Researcher(), Nun(), Doctor(),
          Archaeologist(), Gangster(),
      ]
  }
