import eldritch.abilities as abilities
import eldritch.events as events
import eldritch.items as items
import eldritch.places as places


class Character(object):
  
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
    self.bless_curse = 0  # -1 for curse, +1 for blessed
    self.retainer = False
    self.lodge_membership = False
    self.delayed = False
    self.arrested = False  # TODO: necessary?
    self.lost_turn = False
    self.movement_points = self.speed
    self.focus_points = self.focus
    self.place = home

  def json_repr(self):
    attrs = [
        "name", "max_stamina", "max_sanity", "stamina", "sanity", "focus",
        "speed", "sneak", "fight", "will", "lore", "luck", "movement_points", "focus_points",
        "dollars", "clues", "possessions", # TODO: special cards
        "delayed", "arrested",
    ]
    data = {attr: getattr(self, attr) for attr in attrs}
    data["sliders"] = {}
    for slider in ["speed_sneak", "fight_will", "lore_luck"]:
      data["sliders"][slider] = {
          "pairs": getattr(self, "_" + slider),
          "selection": getattr(self, slider + "_slider"),
      }
    data["place"] = self.place.name
    return data

  # TODO: add global effects to all properties
  @property
  def max_stamina(self):
    return self._max_stamina

  @property
  def max_sanity(self):
    return self._max_sanity

  @property
  def speed(self):
    return self._speed_sneak[self.speed_sneak_slider][0] + self.bonus("speed")

  @property
  def sneak(self):
    return self._speed_sneak[self.speed_sneak_slider][1] + self.bonus("sneak")

  @property
  def fight(self):
    return self._fight_will[self.fight_will_slider][0] + self.bonus("fight")

  @property
  def will(self):
    return self._fight_will[self.fight_will_slider][1] + self.bonus("will")

  @property
  def lore(self):
    return self._lore_luck[self.lore_luck_slider][0] + self.bonus("lore")

  @property
  def luck(self):
    return self._lore_luck[self.lore_luck_slider][1] + self.bonus("luck")

  @property
  def evade(self):
    return self.sneak + self.bonus("evade")

  @property
  def combat(self):
    return self.fight + self.bonus("combat")

  @property
  def horror(self):
    return self.will + self.bonus("horror")

  @property
  def spell(self):
    return self.lore + self.bonus("spell")

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
    # TODO: revisit index
    if self.clues > 0 and isinstance(event, events.Check) and event.character == self:
      triggers[-1] = events.SpendClue(self, event)
    return triggers

  def bonus(self, check_name):
    return sum([p.get_bonus(check_name) for p in self.possessions])

  def count_successes(self, roll, check_type):
    threshold = 5 - self.bless_curse
    return len([result for result in roll if result >= threshold])


Nun = Character("Nun", 3, 7, 4, 4, 3, 4, 4, 6, 1, places.Church)
Nun.bless_curse = 1
Doctor = Character("Doctor", 5, 5, 3, 5, 3, 4, 5, 4, 2, places.Hospital)
Doctor.dollars = 9
Doctor.clues = 1
Archaeologist = Character("Archaeologist", 7, 3, 4, 3, 5, 3, 4, 5, 2, places.Shop)
Archaeologist.dollars = 7
Archaeologist.clues = 1
Gangster = Character("Gangster", 7, 3, 5, 4, 6, 4, 3, 3, 1, places.House)
Gangster.dollars = 8


Nun.possessions.extend([items.Cross(), items.HolyWater()])
Doctor.possessions.extend([abilities.Medicine()])
Archaeologist.possessions.extend([items.Revolver38(), items.Bullwhip()])
Gangster.possessions.extend([items.Dynamite(), items.TommyGun()])


CHARACTERS = [Nun, Doctor, Archaeologist, Gangster]
