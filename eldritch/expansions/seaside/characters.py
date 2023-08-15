from eldritch import characters
from eldritch import events


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
    self.abnormal_focus = 5
    self.movement_points = 1

  def fight(self, state):
    return self._fight_sneak[self.fight_sneak_slider][0] + self.bonus("fight", state)

  def sneak(self, state):
    return self._fight_sneak[self.fight_sneak_slider][1] + self.bonus("fight", state)

  def speed(self, state):
    return self._speed_luck[self.speed_luck_slider][0] + self.bonus("speed", state)

  def luck(self, state):
    return self._speed_luck[self.speed_luck_slider][1] + self.bonus("luck", state)

  def lore(self, state):
    return self._lore_will[self.lore_will_slider][0] + self.bonus("lore", state)

  def will(self, state):
    return self._lore_will[self.lore_will_slider][1] + self.bonus("lore", state)

  def movement_speed(self):
    speed = self._speed_luck[self.speed_luck_slider][0]
    for pos in self.possessions:
      speed + getattr(pos, "passive_bonuses", {}).get("speed", 0)
    return speed

  def get_interrupts(self, event, state):
    if isinstance(event, events.Upkeep) and event.character == self:
      self.fight_sneak_slider = 0
      self.lore_will_slider = 0
      self.speed_luck_slider = 0

  def max_stamina(self, state):
    return self._max_stamina + self.bonus("max_stamina", state)

  def max_sanity(self, state):
    return self._max_sanity + self.bonus("max_sanity", state)

  def abilities(self):
    return ["Abnormal Focus", "Breaking the Limits"]

  def initial_attributes(self):
    return {"dollars": 4, "clues": 2}

  def fixed_possessions(self):
    return {"common": ["Cigarette Case"]}

  def random_possessions(self):
    return {"common": 2, "unique": 2, "skills": 1}

  def focus_cost(self, pending_sliders):
    return sum(pending_sliders[name] for name in self.sliders())

  def slider_focus_available(self):
    abnormal_focus =  5
    for pos in self.possessions:
      abnormal_focus += pos.get_bonus("abnormal_focus", [])
