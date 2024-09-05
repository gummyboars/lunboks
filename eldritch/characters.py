import abc
from collections import OrderedDict
import math
from typing import Iterable

from eldritch import events
from eldritch import gates
from eldritch import monsters


class BaseCharacter(metaclass=abc.ABCMeta):
  def __init__(self, name, focus, home):
    self.name = name
    self._focus = focus
    self.dollars = 0
    self.clues = 0
    self.possessions = []  # includes special abilities, skills, and allies
    self.trophies = []
    self.delayed_until = None
    self.lose_turn_until = None
    self.arrested_until = None
    self.gone = False
    self.focus_points = self.focus
    self.home = home
    self.place = None
    self.explored = False
    self.avoid_monsters = []
    self.movement_points = 0
    self.sanity = 0
    self.stamina = 0

  def get_json(self, state):
    attrs = [
      "name",
      "stamina",
      "sanity",
      "focus",
      "movement_points",
      "focus_points",
      "dollars",
      "clues",
      "possessions",  # TODO: special cards
      "delayed_until",
      "lose_turn_until",
      "arrested_until",
      "gone",
    ]
    data = {attr: getattr(self, attr) for attr in attrs}
    for numeric in ["delayed_until", "lose_turn_until", "arrested_until"]:
      if data[numeric] is not None and math.isinf(data[numeric]):
        data[numeric] = "\u221e"  # Any placeholder non-integer value.
    data["sliders"] = OrderedDict()
    for slider in self._slider_names:
      data["sliders"][slider] = {
        "pairs": getattr(self, "_" + slider),
        "selection": getattr(self, slider + "_slider"),
      }
    data["trophies"] = []
    for trophy in self.trophies:
      if isinstance(trophy, monsters.Monster):
        data["trophies"].append(trophy.json_repr(state, self))
      else:
        data["trophies"].append(trophy)
    computed = ["speed", "sneak", "fight", "will", "lore", "luck", "max_sanity", "max_stamina"]
    data.update({attr: getattr(self, attr)(state) for attr in computed})
    data["place"] = self.place.name if self.place is not None else None
    data["fixed"] = sum(self.fixed_possessions().values(), [])
    data["random"] = self.random_possessions()
    data["initial"] = self.initial_attributes()
    data["abilities"] = self.abilities()
    return data

  @abc.abstractmethod
  def base_speed(self):
    raise NotImplementedError

  def speed(self, state, check=True):
    return self.base_speed() + self.bonus("speed", state, check=check)

  @abc.abstractmethod
  def base_sneak(self):
    raise NotImplementedError

  def sneak(self, state, check=True):
    return self.base_sneak() + self.bonus("sneak", state, check=check)

  @abc.abstractmethod
  def base_fight(self):
    raise NotImplementedError

  def fight(self, state, check=True):
    return self.base_fight() + self.bonus("fight", state, check=check)

  @abc.abstractmethod
  def base_will(self):
    raise NotImplementedError

  def will(self, state, check=True):
    return self.base_will() + self.bonus("will", state, check=check)

  @abc.abstractmethod
  def base_lore(self):
    raise NotImplementedError

  def lore(self, state, check=True):
    return self.base_lore() + self.bonus("lore", state, check=check)

  @abc.abstractmethod
  def base_luck(self):
    raise NotImplementedError

  def luck(self, state, check=True):
    return self.base_luck() + self.bonus("luck", state, check=check)

  @property
  @abc.abstractmethod
  def _slider_names(self) -> Iterable:
    pass

  @abc.abstractmethod
  def max_stamina(self, state):
    pass

  @abc.abstractmethod
  def max_sanity(self, state):
    pass

  def movement_speed(self):
    speed = self.base_speed()
    for pos in self.possessions:
      speed += getattr(pos, "passive_bonuses", {}).get("speed", 0)
    return speed

  def evade(self, state):
    return self.sneak(state) + self.bonus("evade", state, check=True)

  def combat(self, state, attributes):
    combat = self.fight(state)
    for bonus_type in ["physical", "magical", "combat"]:
      combat += self.bonus(bonus_type, state, attributes, check=True)
    return combat

  def horror(self, state):
    return self.will(state) + self.bonus("horror", state, check=True)

  def spell(self, state):
    return self.lore(state) + self.bonus("spell", state, check=True)

  def bonus(self, check_name, state, attributes=None, check=True):
    modifier = 0
    if state:
      modifier += state.get_modifier(self, check_name + ("_check" if check else ""))
    for pos in self.possessions:
      bonus = pos.get_bonus(check_name, attributes, self, state)
      if check:
        bonus += pos.get_bonus(check_name + "_check", attributes, self, state)
      if attributes and check_name in {"magical", "physical"}:
        if check_name + " immunity" in attributes:
          bonus = 0
        elif check_name + " resistance" in attributes:
          bonus = (bonus + 1) // 2
      modifier += bonus
    return modifier

  def get_modifier(self, other, attribute):
    return sum(p.get_modifier(other, attribute) or 0 for p in self.possessions)

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
    successes = len([result for result in roll if self.is_success(result, check_type)])
    if check_type == "combat":  # HACK: hard-code the Shotgun's functionality here.
      shotgun_active = any(
        item.name == "Shotgun" for item in self.possessions if getattr(item, "active", False)
      )
      if shotgun_active:
        successes += roll.count(6)
    return successes

  def is_success(self, die, check_type):
    return die >= 5 - self.bless_curse

  def hands_available(self):
    return 2 - sum(pos.hands_used() for pos in self.possessions if hasattr(pos, "hands_used"))

  def sliders(self):
    return {slider: getattr(self, slider + "_slider") for slider in self._slider_names}

  @property
  def focus(self):
    return self._focus

  @property
  def bless_curse(self):
    if "Blessing" in [p.name for p in self.possessions]:
      return 1
    if "Curse" in [p.name for p in self.possessions]:
      return -1
    return 0

  @property
  def lodge_membership(self):
    return "Lodge Membership" in [p.name for p in self.possessions]

  @property
  def n_monster_trophies(self):
    return len([t for t in self.trophies if isinstance(t, monsters.Monster)])

  @property
  def n_gate_trophies(self):
    return len([t for t in self.trophies if isinstance(t, gates.Gate)])

  def abilities(self):
    return []

  def initial_attributes(self):
    return {}

  def fixed_possessions(self):
    return {}

  def random_possessions(self):
    return {}

  def get_interrupts(self, event, state):
    return [
      p.get_interrupt(event, self, state)
      for p in self.possessions
      if p.get_interrupt(event, self, state)
    ]

  def get_usable_interrupts(self, event, state):
    return {
      pos.handle: pos.get_usable_interrupt(event, self, state)
      for pos in self.possessions
      if (pos.get_usable_interrupt(event, self, state) and state.get_override(pos, "can_use"))
    }

  def get_spendables(self, event, state):
    spendables = {
      pos.handle: pos.get_spend_amount(event, self, state)
      for pos in self.possessions
      if pos.get_spend_amount(event, self, state) is not None
    }
    if isinstance(event, events.SpendMixin) and event.character == self and not event.is_done():
      spent_handles = event.spent_handles()
      for trophy in self.trophies:
        handle = trophy.handle
        if handle in spent_handles:
          spendables[handle] = False
          continue
        if isinstance(trophy, monsters.Monster):
          if "toughness" in event.spendable:
            spendables[handle] = {"toughness": trophy.toughness(state, self)}
          elif "monsters" in event.spendable:
            spendables[handle] = {"monsters": 1}
        elif isinstance(trophy, gates.Gate) and "gates" in event.spendable:
          spendables[handle] = {"gates": 1}
    return spendables

  def get_triggers(self, event, state):
    triggers = []
    if isinstance(event, events.DiscardSpecific):
      triggers.extend(
        [
          p.get_trigger(event, self, state)
          for p in event.discarded
          if p.get_trigger(event, self, state)
        ]
      )
    if isinstance(event, events.DiscardNamed) and event.discarded:
      trig = event.discarded.get_trigger(event, self, state)
      triggers.extend([trig] if trig else [])
    return triggers + [
      p.get_trigger(event, self, state)
      for p in self.possessions
      if p.get_trigger(event, self, state)
    ]

  def get_usable_triggers(self, event, state):
    return {
      pos.handle: pos.get_usable_trigger(event, self, state)
      for pos in self.possessions
      if pos.get_usable_trigger(event, self, state) and state.get_override(pos, "can_use")
    }

  def get_spend_event(self, handle):
    matching = [pos for pos in self.possessions if pos.handle == handle]
    if matching:
      if len(matching) > 1:
        print(f"ERROR: handle {handle} matched multiple possessions: {matching}")
      return matching[0].get_spend_event(self)
    matching = [trophy for trophy in self.trophies if trophy.handle == handle]
    if not matching:
      print(f"ERROR: handle {handle} matched no possessions or trophies")
      return events.Nothing()
    if len(matching) > 1:
      print(f"ERROR: handle {handle} matched multiple trophies: {matching}")
    trophy = matching[0]
    if isinstance(trophy, monsters.Monster):
      return events.ReturnMonsterToCup(self, handle)
    return events.ReturnGateToStack(self, handle)

  def focus_cost(self, pending_sliders):
    return sum(abs(orig - pending_sliders[name]) for name, orig in self.sliders().items())

  def slider_focus_available(self):
    abnormal_focus = self.bonus("abnormal_focus", None)
    if abnormal_focus:
      return abnormal_focus
    return self.focus_points

  def spend_slider_focus(self, focus_spent_to_slide):
    self.focus_points -= focus_spent_to_slide


class Character(BaseCharacter):
  """A character with the standard sliders."""

  _slider_names = ("speed_sneak", "fight_will", "lore_luck")

  def __init__(
    self,
    name,
    max_stamina,
    max_sanity,
    max_speed,
    max_sneak,
    max_fight,
    max_will,
    max_lore,
    max_luck,
    focus,
    home,
  ):
    super().__init__(name, focus, home)
    self._max_stamina = max_stamina
    self._max_sanity = max_sanity
    self._speed_sneak = [(max_speed - 3 + i, max_sneak - i) for i in range(4)]
    self._fight_will = [(max_fight - 3 + i, max_will - i) for i in range(4)]
    self._lore_luck = [(max_lore - 3 + i, max_luck - i) for i in range(4)]
    self.speed_sneak_slider = 3
    self.fight_will_slider = 3
    self.lore_luck_slider = 3
    self.stamina = self._max_stamina
    self.sanity = self._max_sanity
    self.movement_points = self._speed_sneak[self.speed_sneak_slider][0]

  def max_stamina(self, state):
    return self._max_stamina + self.bonus("max_stamina", state, check=False)

  def max_sanity(self, state):
    return self._max_sanity + self.bonus("max_sanity", state, check=False)

  def base_speed(self):
    return self._speed_sneak[self.speed_sneak_slider][0]

  def base_sneak(self):
    return self._speed_sneak[self.speed_sneak_slider][1]

  def base_fight(self):
    return self._fight_will[self.fight_will_slider][0]

  def base_will(self):
    return self._fight_will[self.fight_will_slider][1]

  def base_lore(self):
    return self._lore_luck[self.lore_luck_slider][0]

  def base_luck(self):
    return self._lore_luck[self.lore_luck_slider][1]


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
    return []  # TODO: Scrounge

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
  # pylint: disable=import-outside-toplevel
  from eldritch.expansions.clifftown import characters as clifftown_characters
  from eldritch.expansions.seaside import characters as seaside_characters

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
      seaside_characters.Secretary(),
      seaside_characters.Spy(),
      seaside_characters.Farmhand(),
      clifftown_characters.Urchin(),
    ]
  }
