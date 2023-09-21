from eldritch import characters


class Secretary(characters.Character):
  def __init__(self):
    super().__init__("Secretary", 4, 6, 5, 4, 4, 4, 4, 3, 2, "Hospital")

  def abilities(self):
    return ["Synergy", "Team Player"]

  def initial_attributes(self):
    return {"dollars": 4, "clues": 2}

  def fixed_possessions(self):
    return {"unique": ["Yellow Play"]}

  def random_possessions(self):
    return {"common": 2, "unique": 1, "spells": 1, "skills": 1}


class Spy(characters.BaseCharacter):
  _slider_names = ["fight_sneak", "lore_will", "speed_luck"]

  def __init__(self):
    super().__init__("Spy", 1, "Newspaper")
    self._max_sanity = 6
    self.sanity = self._max_sanity
    self._max_stamina = 4
    self.stamina = self._max_stamina
    self._fight_sneak = [(1, 3), (2, 4), (3, 5), (4, 6)]
    self._lore_will = [(2, 1), (3, 2), (4, 3), (5, 4)]
    self._speed_luck = [(1, 0), (2, 1), (3, 2), (4, 3)]
    self.fight_sneak_slider = 0
    self.lore_will_slider = 0
    self.speed_luck_slider = 0
    self.movement_points = 1

  def base_fight(self):
    return self._fight_sneak[self.fight_sneak_slider][0]

  def base_sneak(self):
    return self._fight_sneak[self.fight_sneak_slider][1]

  def base_speed(self):
    return self._speed_luck[self.speed_luck_slider][0]

  def base_luck(self):
    return self._speed_luck[self.speed_luck_slider][1]

  def base_lore(self):
    return self._lore_will[self.lore_will_slider][0]

  def base_will(self):
    return self._lore_will[self.lore_will_slider][1]

  def max_stamina(self, state):
    return self._max_stamina + self.bonus("max_stamina", state)

  def max_sanity(self, state):
    return self._max_sanity + self.bonus("max_sanity", state)

  def abilities(self):
    return ["Abnormal Focus", "Breaking the Limits"]

  def initial_attributes(self):
    return {"dollars": 4, "clues": 2}

  def fixed_possessions(self):
    return {
        "common": [
            "Cigarette Case"
        ]
    }

  def random_possessions(self):
    return {"common": 2, "unique": 2, "skills": 1}

  def focus_cost(self, pending_sliders):
    return sum(pending_sliders[name] for name in self.sliders())
