import collections

CHECK_TYPES = {
    "speed", "sneak", "fight", "will", "lore", "luck", "evade", "combat", "horror", "spell"}


class Possession(object):

  POSSESSION_TYPES = {"common", "unique", "spell", "skill", "ally"}

  # TODO: do we need use bonuses? or just add a hook that says the item is discarded after use?
  def __init__(self, name, possession_type, use_bonuses, hand_bonuses, passive_bonuses, bonus_type, hands, price):
    assert possession_type in self.POSSESSION_TYPES
    self.possession_type = possession_type
    self.name = name
    assert not ((use_bonuses.keys() | hand_bonuses.keys() | passive_bonuses.keys()) - CHECK_TYPES)
    self.use_bonuses = collections.defaultdict(int)
    self.use_bonuses.update(use_bonuses)
    self.hand_bonuses = collections.defaultdict(int)
    self.hand_bonuses.update(hand_bonuses)
    self.passive_bonuses = collections.defaultdict(int)
    self.passive_bonuses.update(passive_bonuses)
    assert bonus_type in {"physical", "magical", None}
    self.bonus_type = bonus_type
    self.hands = hands
    self.price = price
    self.exhausted = False

  def json_repr(self):
    output = {}
    output.update(self.__dict__)
    return output

  @classmethod
  def parse_json(cls, data):
    pass  # TODO

  def get_use_bonus(self, check_type):
    return self.use_bonuses[check_type]

  def get_hand_bonus(self, check_type):
    return self.hand_bonuses[check_type]

  def get_passive_bonus(self, check_type):
    return self.passive_bonuses[check_type]


# TODO: update all of these items
Revolver38 = Possession("Revolver38", "common", {}, {"combat": 3}, {}, "physical", 1, 4)
Bullwhip = Possession("Bullwhip", "common", {}, {"combat": 1}, {}, "physical", 1, 2)  # TODO: special ability
Cross = Possession("Cross", "unique", {}, {"horror": 1}, {}, "magical", 1, 3)
Dynamite = Possession("Dynamite", "common", {}, {"combat": 8}, {}, "physical", 2, 4)
TommyGun = Possession("TommyGun", "common", {}, {"combat": 6}, {}, "physical", 2, 7)
Food = Possession("Food", "common", {}, {}, {}, None, None, 1)
