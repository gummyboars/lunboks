from random import SystemRandom
random = SystemRandom()

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
    self.money = 0
    self.clues = 0
    self.possessions = []  # includes skills and allies
    self.active_possessions = []  # being used by hands
    self.bless_curse = 0  # -1 for curse, +1 for blessed
    self.retainer = False
    self.lodge_membership = False
    self.delayed = False
    self.arrested = False  # TODO: necessary?
    self.movement_points = self.speed
    self.focus_points = self.focus
    self.place = home

  def json_repr(self):
    attrs = [
        "name", "max_stamina", "max_sanity", "stamina", "sanity", "focus",
        "speed", "sneak", "fight", "will", "lore", "luck", "movement_points", "focus_points",
        "money", "clues", "possessions", "active_possessions", # TODO: special cards
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

  def bonus(self, check_name):
    modifier = 0
    modifier += sum([p.get_passive_bonus(check_name) for p in self.possessions])
    modifier += sum([p.get_hand_bonus(check_name) for p in self.active_possessions])
    return modifier

  def start_using(self, item):
    assert item in self.possessions
    hands_used = sum([p.hands for p in self.active_possessions])
    assert item.hands + hands_used <= 2
    self.active_possessions.append(item)

  def stop_using(self, item):
    assert item in self.active_possessions
    assert item in self.possessions
    self.active_possessions.remove(item)

  def make_check(self, check_type, modifier):
    value = getattr(self, check_type) + modifier
    dice_result = [random.randint(1, 6) for _ in range(value)]
    successes = len([result for result in dice_result if result >= 5])
    return successes, dice_result


Nun = Character("Nun", 3, 7, 4, 4, 3, 4, 4, 6, 1, places.Church)
Doctor = Character("Doctor", 5, 5, 3, 5, 3, 4, 5, 4, 2, places.Hospital)
Archaeologist = Character("Archaeologist", 7, 3, 4, 3, 5, 3, 4, 5, 2, places.Shop)
Gangster = Character("Gangster", 7, 3, 5, 4, 6, 4, 3, 3, 1, places.House)

Nun.possessions.extend([items.Cross])
Archaeologist.possessions.extend([items.Revolver38, items.Bullwhip])
Gangster.possessions.extend([items.Dynamite, items.TommyGun])
Archaeologist.start_using(items.Revolver38)
Archaeologist.start_using(items.Bullwhip)
Gangster.start_using(items.TommyGun)
Nun.start_using(items.Cross)


CHARACTERS = [Nun, Doctor, Archaeologist, Gangster]
