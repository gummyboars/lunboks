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
        "dollars", "clues", "possessions", # TODO: special cards
        "delayed_until", "lose_turn_until",
    ]
    data = {attr: getattr(self, attr) for attr in attrs}
    data["sliders"] = {}
    for slider in ["speed_sneak", "fight_will", "lore_luck"]:
      data["sliders"][slider] = {
          "pairs": getattr(self, "_" + slider),
          "selection": getattr(self, slider + "_slider"),
      }
    computed = ["speed", "sneak", "fight", "will", "lore", "luck"]
    data.update({attr: getattr(self, attr)(state) for attr in computed})
    data["place"] = self.place.name
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

  def combat(self, state):
    return self.fight(state) + self.bonus("combat", state)

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
    # TODO: revisit index
    if self.clues > 0 and isinstance(event, events.Check) and event.character == self:
      triggers[-1] = events.SpendClue(self, event)
    return triggers

  def bonus(self, check_name, state):
    modifier = state.get_modifier(self, check_name)
    return sum([p.get_bonus(check_name) for p in self.possessions]) + modifier

  def count_successes(self, roll, check_type):
    threshold = 5 - self.bless_curse
    return len([result for result in roll if result >= threshold])


def CreateCharacters():
  # TODO: there's a lot of cleanup needed here, especially around starting equipment.
  Nun = Character("Nun", 3, 7, 4, 4, 3, 4, 4, 6, 1, "Church")
  Nun.bless_curse = 1
  Doctor = Character("Doctor", 5, 5, 3, 5, 3, 4, 5, 4, 2, "Hospital")
  Doctor.dollars = 9
  Doctor.clues = 1
  Archaeologist = Character("Archaeologist", 7, 3, 4, 3, 5, 3, 4, 5, 2, "Shop")
  Archaeologist.dollars = 7
  Archaeologist.clues = 1
  Gangster = Character("Gangster", 7, 3, 5, 4, 6, 4, 3, 3, 1, "House")
  Gangster.dollars = 8

  Nun.possessions.extend([items.Cross(), items.HolyWater()])
  Doctor.possessions.extend([abilities.Medicine()])
  Archaeologist.possessions.extend([items.Revolver38(), items.Bullwhip()])
  Gangster.possessions.extend([items.Dynamite(), items.TommyGun()])

  return [Nun, Doctor, Archaeologist, Gangster]
