import collections
import json
import operator
from random import SystemRandom

from eldritch import values
from eldritch import specials
from eldritch import skills
from eldritch import places
from eldritch import mythos
import eldritch.mythos.core
from eldritch import monsters
from eldritch import location_specials
from eldritch import items
from eldritch.encounters import gate as gate_encounters
from eldritch import gates
from eldritch import events
from eldritch.encounters import location as encounters
from eldritch import characters
from eldritch import cards as assets
from eldritch import allies
from eldritch import abilities
from eldritch import ancient_ones
from game import (  # pylint: disable=unused-import
  BaseGame,
  CustomEncoder,
  InvalidInput,  # noqa: F401
  UnknownMove,
  InvalidMove,
  InvalidPlayer,
  NotYourTurn,
  ValidatePlayer,  # noqa: F401
  TooManyPlayers,  # noqa: F401
)


random = SystemRandom()


class GameState:
  DEQUE_ATTRIBUTES = frozenset(
    {"common", "unique", "spells", "skills", "allies", "specials", "boxed_allies", "gates"}
  )
  HIDDEN_ATTRIBUTES = frozenset(
    {"event_stack", "interrupt_stack", "trigger_stack", "log_stack", "mythos", "gate_cards"}
  )
  CUSTOM_ATTRIBUTES = frozenset(
    {
      "options",
      "characters",
      "all_characters",
      "environment",
      "mythos",
      "other_globals",
      "ancient_one",
      "all_ancients",
      "monsters",
      "usables",
      "spendables",
    }
  )
  TURN_PHASES = ("upkeep", "movement", "encounter", "otherworld", "mythos")
  AWAKENED_PHASES = ("upkeep", "attack", "ancient")
  TURN_TYPES = {  # noqa: RUF012
    "upkeep": events.Upkeep,
    "movement": events.Movement,
    "encounter": events.EncounterPhase,
    "otherworld": events.OtherWorldPhase,
    "mythos": events.Mythos,
  }
  AWAKENED_TURNS = {  # noqa: RUF012
    "upkeep": events.Upkeep,
    "attack": events.InvestigatorAttack,
    "ancient": events.AncientAttack,
  }
  EXPANSIONS = frozenset({"hilltown", "clifftown", "seaside", "pharaoh", "king", "goat", "lurker"})
  EXPANSION_OPTIONS = frozenset(
    {"characters", "ancient_ones", "monsters", "mythos", "encounters", "items", "allies", "rules"}
  )
  HILLTOWN_OPTIONS = EXPANSION_OPTIONS | {"injuries"}
  CLIFFTOWN_OPTIONS = EXPANSION_OPTIONS | {"epic"}
  SEASIDE_OPTIONS = (EXPANSION_OPTIONS | {"stories"}) - {"items", "allies"}
  PHARAOH_OPTIONS = frozenset({"mythos", "encounters", "items", "allies", "rules"})
  KING_OPTIONS = frozenset({"mythos", "encounters", "items", "rules"})
  GOAT_OPTIONS = frozenset({"monsters", "mythos", "encounters", "items"})
  LURKER_OPTIONS = frozenset({"gates", "mythos", "encounters", "items", "rules"})
  MONSTER_EVENTS = (
    events.Combat,
    events.CombatRound,
    events.PassCombatRound,
    events.TakeTrophy,
    events.EvadeRound,
    events.MonsterCheck,
  )

  def __init__(self):
    self.name = "game"
    self.options = {
      exp: {"characters", "ancient_ones"} for exp in ("hilltown", "clifftown", "seaside")
    }
    self.options.update({exp: set() for exp in ("pharaoh", "king", "goat", "lurker")})
    self.options["seaside"].add("stories")
    self.places: dict[str, places.Place] = {}
    self.characters = []
    self.all_characters = characters.CreateCharacters(self.expansions("characters"))
    self.all_ancients = ancient_ones.AncientOnes(self.expansions("ancient_ones"))
    self.pending_chars = {}
    self.common = collections.deque()
    self.unique = collections.deque()
    self.spells = collections.deque()
    self.skills = collections.deque()
    self.allies = collections.deque()
    self.boxed_allies = collections.deque()  # Church expansion
    self.tradables = []
    self.specials = collections.deque()
    self.mythos = collections.deque()
    self.gates = collections.deque()
    self.gate_cards = collections.deque()
    self.monsters = []
    self.monster_cup = monsters.core.MonsterCup()
    self.game_stage = "setup"  # valid values are setup, slumber, awakened, victory, defeat
    # valid values are setup, upkeep, movement, encounter, otherworld, mythos, attack, ancient
    self.turn_phase = "setup"
    self.event_stack = collections.deque()
    self.interrupt_stack = collections.deque()
    self.trigger_stack = collections.deque()
    self.log_stack = collections.deque()
    self.spendables = {}
    self.usables = {}
    self.done_using = {}
    self.event_log = []
    self.turn_number = -1
    self.turn_idx = 0
    self.first_player = 0
    self.rumor = None
    self.environment = None
    self.ancient_one = None
    self.other_globals = []
    self.test_mode = False
    self.terror = 0

  def initialize_for_tests(self):
    self.places = places.CreatePlaces()
    other_worlds = places.CreateOtherWorlds()
    self.places.update(other_worlds)

    self.gates.extend(gates.CreateGates())
    self.monsters = [monsters.base.Cultist(), monsters.base.Maniac()]
    for idx, monster in enumerate(self.monsters):
      monster.idx = idx
      monster.place = self.monster_cup

    self.game_stage = "slumber"
    self.turn_idx = 0
    self.turn_number = 0
    self.turn_phase = "upkeep"
    self.ancient_one = ancient_ones.core.DummyAncient()
    self.specials.extend(specials.CreateSpecials())
    self.test_mode = True

  def initialize(self):
    self.places = places.CreatePlaces()
    other_worlds = places.CreateOtherWorlds()
    self.places.update(other_worlds)
    facilities = location_specials.CreateFixedEncounters()
    encounter_cards = encounters.CreateEncounterCards(self.expansions("encounters"))
    self.gate_cards.extend(gate_encounters.CreateGateCards(self.expansions("encounters")))
    for neighborhood_name, cards in encounter_cards.items():
      random.shuffle(cards)
      self.places[neighborhood_name].encounters.extend(cards)
    for location_name, fixed_encounters in facilities.items():
      self.places[location_name].fixed_encounters.extend(fixed_encounters)

    gate_markers = gates.CreateGates()
    random.shuffle(gate_markers)
    self.gates.extend(gate_markers)

    self.monsters = monsters.CreateMonsters(self.expansions("monsters"))
    if self.ancient_one.name != "The Thousand Masks":
      self.monsters = [mon for mon in self.monsters if not mon.has_attribute("mask", self, None)]
    for idx, monster in enumerate(self.monsters):
      monster.idx = idx
      monster.place = self.monster_cup

    self.common.extend(items.CreateCommon(self.expansions("items")))
    self.unique.extend(items.CreateUnique(self.expansions("items")))
    self.spells.extend(items.CreateSpells(self.expansions("items")))
    self.skills.extend(skills.CreateSkills(self.expansions("items")))
    self.allies.extend(allies.CreateAllies(self.expansions("allies")))
    self.tradables.extend(specials.CreateTradables())
    self.specials.extend(specials.CreateSpecials())
    all_cards = self.common + self.unique + self.spells + self.skills + self.allies + self.specials
    all_cards += self.tradables
    handles = [card.handle for card in all_cards]
    assert len(handles) == len(set(handles)), f"Card handles {handles} are not unique"

    self.mythos.extend(mythos.CreateMythos(self.expansions("mythos")))

    # Shuffle the decks.
    for deck in assets.Card.DECKS | {"gate_cards", "mythos"} - {"tradables", "specials"}:
      random.shuffle(getattr(self, deck))
    # Place initial clues.
    for place in self.places.values():
      if isinstance(place, places.Location) and place.is_unstable(self):
        place.clues += 1

  def give_fixed_possessions(self, char, possessions):
    assert not possessions.keys() - assets.Card.DECKS, "bad deck(s) {', '.join(possessions.keys())}"
    for deck, names in possessions.items():
      cards = getattr(self, deck)
      keep = []
      rest = []
      while cards and names:
        card = cards.popleft()
        if card.name in names:
          names.remove(card.name)
          keep.append(card)
        else:
          rest.append(card)
      assert not names, f"could not find {names!s} for {char.name} in {deck}"
      char.possessions.extend(keep)
      cards.extend(rest)

  def give_random_possessions(self, char, possessions):
    err_str = ", ".join(char.random_possessions().keys())
    assert not char.random_possessions().keys() - assets.Card.DECKS, err_str
    for deck, count in possessions.items():
      for _ in range(count):
        char.possessions.append(getattr(self, deck).popleft())

  def expansions(self, option):
    assert option in self.EXPANSION_OPTIONS
    return {expansion for expansion, options in self.options.items() if option in options}

  def get_modifier(self, thing, attribute):
    modifier = 0
    for glob in self.globals():
      if not glob:
        continue
      modifier += glob.get_modifier(thing, attribute, self)
    return modifier

  def get_override(self, thing, attribute):
    override = True if attribute.startswith(("can_", "cannot_")) else None
    # Anything not forbidden is permitted
    for glob in self.globals():
      if not glob:
        continue
      val = glob.get_override(thing, attribute)
      if val is None:
        continue
      if override is None:
        override = val
      override = override and val
    return override

  def globals(self) -> list[eldritch.mythos.core.GlobalEffect]:
    return [self.rumor, self.environment, self.ancient_one] + self.other_globals

  def gate_limit(self):
    limit = 9 - (len(self.characters) + 1) // 2
    return limit + self.get_modifier(self, "gate_limit")

  def monster_limit(self, original=False):
    if not original:
      if self.terror >= 10:
        return float("inf")
    limit = len(self.characters) + 3
    return limit + self.get_modifier(self, "monster_limit")

  def outskirts_limit(self):
    limit = 8 - len(self.characters)
    return limit + self.get_modifier(self, "outskirts_limit")

  def game_status(self):
    return "eldritch game"  # TODO

  def json_repr(self):
    ignore_attributes = self.DEQUE_ATTRIBUTES | self.HIDDEN_ATTRIBUTES | self.CUSTOM_ATTRIBUTES
    output = {key: getattr(self, key) for key in self.__dict__.keys() - ignore_attributes}
    for attr in self.DEQUE_ATTRIBUTES:
      output[attr] = list(getattr(self, attr))

    output["characters"] = []
    for char in self.characters:
      output["characters"].append(char.get_json(self))

    output["all_characters"] = {}
    for name, char in self.all_characters.items():
      output["all_characters"][name] = char.get_json(self)

    output["monsters"] = []
    for monster in self.monsters:
      output["monsters"].append(monster.json_repr(self, None))

    output["options"] = {}
    for expansion, options in self.options.items():
      output["options"][expansion] = sorted(options)

    for attr in ["environment", "rumor", "ancient_one"]:
      output[attr] = getattr(self, attr).json_repr(self) if getattr(self, attr) else None
    output["other_globals"] = [glob.json_repr(self) for glob in self.other_globals]
    output["all_ancients"] = {
      name: ancient.json_repr(self) for name, ancient in self.all_ancients.items()
    }

    return output

  def for_player(self, char_idx):
    output = self.json_repr()

    # We only return the counts of these items, not the actual items.
    output["monster_cup"] = len([mon for mon in self.monsters if mon.place == self.monster_cup])
    output["gates"] = len(self.gates)

    output["gate_limit"] = self.gate_limit()
    output["log"] = "" if not self.log_stack else self.log_stack[-1].text

    # If the Drifter is playing, these cards are visible.
    if any(char.name == "Drifter" for char in self.characters):
      output["bottom"] = {}
      if self.common:
        output["bottom"]["common"] = self.common[-1].name
      if self.unique:
        output["bottom"]["unique"] = self.unique[-1].name
      if self.spells:
        output["bottom"]["spells"] = self.spells[-1].name

    # Also give a map from location to activity markers. Environment is always 2, rumor is always 3.
    # Everything else is activity marker 1.
    output["activity"] = collections.defaultdict(list)
    for glob in self.other_globals:
      if getattr(glob, "activity_location", None):
        output["activity"][glob.activity_location].append((glob.name, "1"))
    if self.environment and self.environment.activity_location:
      output["activity"][self.environment.activity_location].append((self.environment.name, "2"))
    if self.rumor and self.rumor.activity_location:
      output["activity"][self.rumor.activity_location].append((self.rumor.name, "3"))

    top_event = self.event_stack[-1] if self.event_stack else None

    # Figure out the current encounter/mythos card being resolved.
    current = None
    for event in reversed(self.event_stack):
      if current is None:
        # If it's an encounter, get the name of the drawn card (or chosen card if more than 1).
        if isinstance(event, events.Encounter) and event.draw and event.draw.cards:
          if len(event.draw.cards) == 1:
            current = event.draw.cards[0].name
          else:
            seq = getattr(event.encounter, "events", [])
            if seq and seq[0].is_resolved():
              current = event.draw.cards[seq[0].choice_index].name
        # Same thing for otherworld encounters (cards attribute is in a different place).
        if isinstance(event, events.GateEncounter) and event.cards and event.encounter:
          if len(event.cards) == 1:
            current = event.cards[0].name
          else:
            seq = getattr(event.encounter, "events", [])
            if seq and seq[0].is_resolved():
              current = event.cards[seq[0].choice_index].name
        # For mythos cards, there is a single drawn card.
        if isinstance(event, events.Mythos) and event.draw and event.draw.card:
          current = event.draw.card.name
    output["current"] = current

    # Figure out any monter currently being fought or evaded. This is used for events like stamina
    # loss that happen while fighting the monster, but don't necessarily have an associated visual.
    output["monster"] = None
    for event in reversed(self.event_stack):
      if isinstance(event, events.EvadeOrCombat):
        output["monster"] = event.monster.json_repr(self, event.character)
        break

    # Figure out the current dice roll/check and how many bonus dice it has.
    roller = None
    bonus = 0
    to_remove = []
    for event in reversed(self.event_stack):
      if isinstance(event, events.BonusDiceRoll):
        bonus += event.count
      if isinstance(event, events.DiceRoll):
        roller = event
      if isinstance(event, events.RerollSpecific) and isinstance(event.reroll_indexes, list):
        to_remove = event.reroll_indexes[:]
      if isinstance(event, events.RerollCheck) and event.dice is not None:
        roller = event.dice
        break
      if isinstance(event, events.Check):
        roller = event
        break
    # Display the current dice roll/check.
    if roller is not None:
      output["dice"] = {
        "roll": roller.roll,
        "count": None,
        "prompt": None,
        "success": None,
        "bad": None,
        "check_type": getattr(roller, "check_type", None),
        "name": roller.name,
        "roller": self.characters.index(roller.character),
      }
      if roller.count is not None:
        dice_count = values.Calculation(roller.count, None, operator.add, bonus).value(self)
        output["dice"]["count"] = dice_count
      if getattr(roller, "bad", None) is not None:
        output["dice"]["bad"] = roller.bad
      elif roller.roll:
        # TODO: count extra succesess like the shotgun?
        output["dice"]["success"] = [
          roller.character.is_success(val, getattr(roller, "check_type", None))
          for val in roller.roll
        ]
      if to_remove and roller.roll:
        output["dice"]["roll"] = [
          None if i in to_remove else roll for i, roll in enumerate(roller.roll)
        ]
      if roller.name is None and current is not None:
        output["dice"]["name"] = current
      if not isinstance(self.event_stack[-1], events.ChoiceEvent):
        if isinstance(roller, events.Check):
          output["dice"]["prompt"] = f"[{roller.character.name}] makes a {roller.check_str()}"
        elif roller.name is not None:
          output["dice"]["prompt"] = f"[{roller.character.name}] rolls for [{roller.name}]"

    # Figure out the current choice, and the spell it belongs to (if any).
    choice = None
    spell = None
    for event in reversed(self.event_stack):
      if isinstance(event, events.CastSpell) and event.choice == choice:
        spell = event.spell
        break
      if choice is not None:
        break
      if isinstance(event, events.ChoiceEvent):
        # Always show the combat choice even when it's done to avoid flickering of the chosen
        # items between completion of the combat choice and activation.
        if isinstance(event, events.CombatChoice) or not event.is_done():
          choice = event
        continue
      if not isinstance(event, (events.ActivateChosenItems, events.ActivateItem, events.CastSpell)):
        break
    output["choice"] = None
    output["chooser"] = None
    if choice:
      output["chooser"] = self.characters.index(choice.character)
      output["choice"] = {"prompt": choice.prompt()}
      output["choice"]["visual"] = getattr(choice, "visual", spell.handle if spell else None)
      output["choice"]["annotations"] = choice.annotations(self)
      output["choice"]["invalid_choices"] = list(getattr(choice, "invalid_choices", {}).keys())
      if getattr(getattr(choice, "monster", None), "visual_name", None) is not None:
        output["choice"]["monster"] = choice.monster.json_repr(self, choice.character)
      if isinstance(choice, events.SpendMixin):
        output["choice"]["spendable"] = list(choice.spendable)
        output["choice"]["spent"] = choice.spend_map
        output["choice"]["remaining_spend"] = choice.remaining_spend
        output["choice"]["remaining_max"] = choice.remaining_max

      if isinstance(choice, events.CardChoice):
        output["choice"]["cards"] = choice.choices
        output["choice"]["sort_uniq"] = choice.sort_uniq
      elif isinstance(choice, (events.MapChoice, events.CityMovement)):
        extra_choices = [choice.none_choice] if choice.none_choice is not None else []
        output["choice"]["places"] = (choice.choices or []) + extra_choices
      elif isinstance(choice, events.MonsterChoice):
        output["choice"]["monsters"] = [
          monster.json_repr(self, choice.character) for monster in choice.monsters
        ]
        if choice.none_choice is not None:
          output["choice"]["monsters"] += [choice.none_choice]
      elif isinstance(choice, events.FightOrEvadeChoice):  # noqa: SIM114
        output["choice"]["choices"] = choice.choices
      elif isinstance(choice, events.MultipleChoice):
        output["choice"]["choices"] = choice.choices
      elif isinstance(choice, events.ItemChoice):
        output["choice"]["chosen"] = [item.handle for item in choice.chosen]
        output["choice"]["items"] = choice.choices or []
        output["choice"]["select_type"] = choice.select_type
      elif isinstance(choice, events.MonsterSpawnChoice):
        output["choice"] = {
          "to_spawn": choice.to_spawn,
          "min_count": choice.min_count,
          "max_count": choice.max_count,
          "location": choice.location_name,
          "open_gates": choice.open_gates,
          "board": choice.spawn_count,
          "outskirts": choice.outskirts_count,
          "steps": choice.steps_remaining,
          "pending": choice.pending,
        }
      elif isinstance(choice, events.MonsterOnBoardChoice):
        output["choice"]["board_monster"] = True
      else:
        raise RuntimeError(f"Unknown choice type {choice.__class__.__name__}")

    if top_event and isinstance(top_event, events.DrawMythosCard):
      if top_event.is_resolved():
        output["visual"] = top_event.card.name
      else:
        output["visual"] = "Mythos Card"
    if top_event and isinstance(top_event, events.GateEncounter) and not top_event.is_resolved():
      output["visual"] = "Gate Card"
    if top_event and isinstance(top_event, events.DrawEncounter) and not top_event.is_resolved():
      output["visual"] = top_event.neighborhood.name + " Card"
    if top_event and isinstance(top_event, events.LookAtItems) and top_event.drawn:
      output["visual"] = top_event.drawn[0].handle

    if top_event and isinstance(top_event, events.MoveMonsters) and top_event.is_done():
      output["visual"] = current

    if top_event and isinstance(top_event, events.SpawnGate) and top_event.opened is False:
      output["missed_gate"] = top_event.location_name

    if top_event and isinstance(top_event, events.AllyToBox) and top_event.ally:
      output["lost_ally"] = top_event.ally.name

    if top_event and isinstance(top_event, events.SliderInput) and not top_event.is_done():
      output["sliders"] = {"prompt": top_event.prompt()}
      output["chooser"] = self.characters.index(top_event.character)
      for name, value in top_event.pending.items():
        output["sliders"][name] = {"selection": value}

    if top_event and isinstance(top_event, events.InitialSliders) and not top_event.is_done():
      slider_char = self.characters[char_idx]
      if slider_char not in top_event.characters:
        slider_char = next(c for c in top_event.characters if c.name not in top_event.done_chars)
      output["sliders"] = {"prompt": top_event.prompt()}
      output["chooser"] = self.characters.index(slider_char)
      for name, value in top_event.pending[slider_char.name].items():
        output["sliders"][name] = {"selection": value}

    output["spendables"] = None
    output["usables"] = None
    if self.spendables.get(char_idx):
      output["spendables"] = list(self.spendables[char_idx].keys())
    if self.usables.get(char_idx):
      output["usables"] = list(self.usables[char_idx].keys())
    output["autochoose"] = not bool(self.usables)
    if len(self.event_stack) >= 3 and isinstance(self.event_stack[-3], events.Encounter):
      if isinstance(top_event, events.CardChoice) and not self.usables:
        output["autochoose"] = self.event_stack[-3].loc_name
    return output

  @classmethod
  def parse_json(cls, json_str):
    pass  # TODO

  def handle(self, char_idx, data):
    if self.game_stage in ["victory", "defeat"]:
      raise InvalidMove("The game is over")
    if data.get("type") == "start":
      self.handle_start()
      return self.resolve_loop()
    if data.get("type") == "ancient":
      self.handle_ancient(data.get("ancient"))
      return [None]  # Return a dummy iterable; do not start executing the game loop.
    if data.get("type") == "option":
      self.handle_option(data.get("expansion"), data.get("option"), data.get("enabled"))
      return [None]

    if char_idx not in range(len(self.characters)):
      raise InvalidPlayer(f"no such player {char_idx}")
    if data.get("type") == "set_slider":
      self.handle_slider(char_idx, data.get("name"), data.get("value"))
    elif data.get("type") == "give":
      self.handle_give(char_idx, data.get("recipient"), data.get("handle"), data.get("amount"))
    elif data.get("type") == "choice":
      self.handle_choice(char_idx, data.get("choice"))
    elif data.get("type") == "spend":
      self.handle_spend(char_idx, data.get("spend_type"))
    elif data.get("type") == "unspend":
      self.handle_unspend(char_idx, data.get("spend_type"))
    elif data.get("type") == "roll":
      self.handle_roll(char_idx)
    elif data.get("type") == "use":
      self.handle_use(char_idx, data.get("handle"))
    elif data.get("type") == "done_using":
      self.handle_done_using(char_idx)
    # Begin debugging commands here.
    elif data.get("type") == "add_doom":
      self.handle_add_doom()
    elif data.get("type") == "remove_doom":
      self.handle_remove_doom()
    elif data.get("type") == "clue":
      self.handle_spawn_clue(data.get("place"))
    elif data.get("type") == "remove_clue":
      self.handle_remove_clue(data.get("place"))
    elif data.get("type") == "remove_gate":
      self.handle_remove_gate(data.get("place"))
    elif data.get("type") == "seal":
      self.handle_toggle_seal(data.get("place"))
    elif data.get("type") == "monster":
      self.handle_spawn_monster(data.get("monster"), data.get("place"))
    elif data.get("type") == "remove_monster":
      self.handle_remove_monster(data.get("monster"), data.get("place"))
    elif data.get("type") == "gate":
      self.handle_spawn_gate(data.get("gate"), data.get("place"))
    elif data.get("type") == "set_stats":
      self.handle_set_stats(data)
    elif data.get("type") == "insane":
      self.handle_insane(data.get("char"))
    elif data.get("type") == "unconscious":
      self.handle_unconscious(data.get("char"))
    elif data.get("type") == "devoured":
      self.handle_devoured(data.get("char"))
    elif data.get("type") == "move_char":
      self.handle_move_char(data.get("char"), data.get("place"))
    elif data.get("type") == "give_item":
      self.handle_give_item(data.get("char"), data.get("item"))
    elif data.get("type") == "remove_item":
      self.handle_remove_item(data.get("char"), data.get("handle"))
    elif data.get("type") == "exhaust_item":
      self.handle_exhaust_item(data.get("char"), data.get("handle"))
    elif data.get("type") == "refresh_item":
      self.handle_refresh_item(data.get("char"), data.get("handle"))
    elif data.get("type") == "give_trophy":
      self.handle_give_trophy(data.get("char"), data.get("trophy"))
    elif data.get("type") == "remove_trophy":
      self.handle_remove_trophy(data.get("char"), data.get("handle"))
    elif data.get("type") == "redo_sliders":
      self.handle_redo_sliders(data.get("char"))
    elif data.get("type") == "set_encounter":  # noqa: SIM114
      self.handle_set_card(data.get("card"))
    elif data.get("type") == "set_mythos":  # noqa: SIM114
      self.handle_set_card(data.get("card"))
    elif data.get("type") == "set_gate":
      self.handle_set_card(data.get("card"))
    else:
      raise UnknownMove(data.get("type"))

    return self.resolve_loop()  # Returns a generator object.

  def resolve_loop(self):
    if not (self.event_stack or self.test_mode or self.game_stage in ("victory", "defeat")):
      self.next_turn()
      yield None
    while self.event_stack:
      event = self.event_stack[-1]
      self.start_event(event)
      if self.interrupt_stack[-1]:
        self.event_stack.append(self.interrupt_stack[-1].pop())
        continue
      # If the event requires the character to make a choice, stop here.
      # TODO: should we actually be doing the usable calculation after compute_choices?
      self.usables = self.get_usable_interrupts(event)
      # TODO: maybe we can have an Input class. Or a needs_input() method.
      if isinstance(event, events.ChoiceEvent) and not event.is_done():
        event.compute_choices(self)
        if not event.is_done():
          if event != self.event_stack[-1]:  # Some choices may put a new event on the stack.
            continue
          if isinstance(event, events.SpendMixin):
            self.spendables = self.get_spendables(event)
          yield None
          return
      if not self.test_mode and isinstance(event, events.DiceRoll) and not event.is_done():
        yield None
        return
      if isinstance(event, (events.SliderInput, events.InitialSliders)) and not event.is_done():
        yield None
        return
      if not all(self.done_using.get(char_idx) for char_idx in self.usables):
        yield None
        return
      if not event.is_done():
        event.resolve(self)
        self.validate_resolve(event)
      if not event.is_done():
        continue
      if self.finish_event(event):
        if event.animated():
          yield None
      if self.game_stage in ["victory", "defeat"]:
        break
      if self.trigger_stack[-1]:
        self.event_stack.append(self.trigger_stack[-1].pop())
        continue
      if not event.is_cancelled():
        self.usables = self.get_usable_triggers(event)
      if not all(self.done_using.get(char_idx) for char_idx in self.usables):
        yield None
        return
      self.pop_event(event)
      if not (self.event_stack or self.test_mode or self.game_stage in ("victory", "defeat")):
        self.next_turn()
        yield None

  def validate_resolve(self, event):
    if event.is_done():
      return
    if self.event_stack[-1] != event:
      return
    if isinstance(event, (events.ChoiceEvent, events.SliderInput, events.InitialSliders)):
      return
    raise RuntimeError(
      f"Event {event} returned from resolve() without (a) becoming resolved or "
      "(b) becoming cancelled or (c) adding a new event to the stack"
    )

  def start_event(self, event):
    if len(self.interrupt_stack) >= len(self.event_stack):
      return

    # Create a log event and attach it to its parent log event, if any.
    log = events.EventLog(event.log(self), event.flatten())
    if not log.flatten:
      if any(not prev_log.flatten for prev_log in self.log_stack):
        prev_log = next(prev_log for prev_log in reversed(self.log_stack) if not prev_log.flatten)
        prev_log.sub_events.append(log)
      else:
        self.event_log.append(log)

    # Extend all other stacks to match the event stack. Also initialize any interrupts.
    self.log_stack.append(log)
    self.interrupt_stack.append(self.get_interrupts(event))
    self.trigger_stack.append(None)
    err_str = f"{len(self.interrupt_stack)} interrupts but {len(self.event_stack)} events"
    err_str += " (multiple events added simultaneously?)"
    assert len(self.interrupt_stack) == len(self.event_stack), err_str

    # Clear out any usables.
    self.clear_usables()

  def finish_event(self, event):
    err_str = f"{len(self.trigger_stack)} triggers, but {len(self.event_stack)} events"
    log_err_str = f"{len(self.log_stack)} logs, but {len(self.event_stack)} events"
    assert len(self.trigger_stack) == len(self.event_stack), err_str
    assert len(self.log_stack) == len(self.event_stack), log_err_str
    if self.trigger_stack[-1] is not None:
      return False

    if not event.is_cancelled():
      self.trigger_stack[-1] = self.get_triggers(event)
    self.log_stack[-1].text = event.log(self)
    self.clear_usables()
    return True

  def pop_event(self, event):
    assert event == self.event_stack[-1], f"popped event not on top {event}"
    err_str = f"{len(self.event_stack)} events, {len(self.trigger_stack)} triggers, "
    err_str += f"{len(self.interrupt_stack)} interrupts, {len(self.log_stack)} logs"
    assert len(self.event_stack) == len(self.trigger_stack), err_str
    assert len(self.event_stack) == len(self.interrupt_stack), err_str
    assert len(self.event_stack) == len(self.log_stack), err_str
    self.log_stack[-1].text = event.log(self)
    self.event_stack.pop()
    self.trigger_stack.pop()
    self.interrupt_stack.pop()
    self.log_stack.pop()
    self.clear_usables()

  def clear_usables(self):
    self.spendables.clear()
    self.usables.clear()
    self.done_using.clear()

  # TODO: global interrupts/triggers from ancient one, environment, other mythos/encounter cards
  def get_interrupts(self, event):
    interrupts = []
    if isinstance(event, (events.MoveOne, events.WagonMove)):
      nearby_monsters = [mon for mon in self.monsters if mon.place == event.character.place]
      if nearby_monsters:
        interrupts.append(events.EvadeOrFightAll(event.character, nearby_monsters))
    interrupts.extend(
      sum([char.get_interrupts(event, self) for char in self.characters if not char.gone], [])
    )
    global_interrupts = [glob.get_interrupt(event, self) for glob in self.globals() if glob]
    interrupts.extend([interrupt for interrupt in global_interrupts if interrupt])
    if isinstance(event, self.MONSTER_EVENTS) and isinstance(event.monster, monsters.core.Monster):
      monster_interrupt = event.monster.get_interrupt(event, self)
      interrupts.extend([monster_interrupt] if monster_interrupt else [])
    return interrupts

  def get_usable_interrupts(self, event):
    i = {
      idx: char.get_usable_interrupts(event, self)
      for idx, char in enumerate(self.characters)
      if not char.gone
    }
    if self.turn_phase == "movement":
      # If the character is in another world with another character, let them trade before moving.
      if isinstance(event, (events.ForceMovement, events.ReturnGateChoice)) and not event.is_done():
        if len([char for char in self.characters if char.place == event.character.place]) > 1:
          i[self.characters.index(event.character)]["trade"] = events.Nothing()
    return {char_idx: interrupts for char_idx, interrupts in i.items() if interrupts}

  def get_spendables(self, event):
    return {
      idx: char.get_spendables(event, self)
      for idx, char in enumerate(self.characters)
      if char.get_spendables(event, self)
    }

  def get_triggers(self, event):
    triggers = []

    # If the ancient one's doom track is full, it wakes up.
    if isinstance(event, events.AddDoom) and self.ancient_one.doom == self.ancient_one.max_doom:
      if self.game_stage == "slumber":
        triggers.append(events.Awaken())

    # If there are twice as many monsters as the normal monster limit, the ancient one awakens.
    if isinstance(event, events.MonsterSpawnChoice):
      limit = self.monster_limit(original=True)
      count = len([mon for mon in self.monsters if isinstance(mon.place, places.CityPlace)])
      if count >= 2 * limit:
        triggers.append(events.Awaken())

    # Insane/Unconscious after sanity/stamina loss.
    if isinstance(event, (events.GainOrLoss, events.SpendMixin, events.CastSpell)):
      skip = False
      if isinstance(event, events.SpendMixin) and len(self.event_stack) > 1:
        if isinstance(self.event_stack[-2], events.CastSpell):
          skip = True  # In case of a spell, delay insanity calculations until it's done being cast.
      if not skip:
        if self.game_stage == "awakened":
          if event.character.sanity <= 0 or event.character.stamina <= 0:
            triggers.append(events.Devoured(event.character))
        else:
          if event.character.sanity <= 0 and event.character.stamina <= 0:
            triggers.append(events.Devoured(event.character))
          elif event.character.sanity <= 0:
            triggers.append(events.Insane(event.character))
          elif event.character.stamina <= 0:
            triggers.append(events.Unconscious(event.character))

    # Devoured if max sanity/stamina go to 0.
    if isinstance(event, events.CapStatsAtMax):
      if event.character.sanity <= 0 or event.character.stamina <= 0:
        triggers.append(events.Devoured(event.character))

    # Lost investigators are devoured when the ancient one awakens.
    if isinstance(event, events.Awaken):
      devour = [events.Devoured(cha) for cha in self.characters if cha.place == self.places["Lost"]]
      triggers.extend(devour)

    # Must fight monsters when you end your movement.
    if isinstance(event, (events.CityMovement, events.WagonMove, events.Return)):
      if self.turn_phase == "movement":
        nearby_monsters = [mon for mon in self.monsters if mon.place == event.character.place]
        if nearby_monsters:
          auto_evade = isinstance(event, events.Return)
          triggers.append(events.EvadeOrFightAll(event.character, nearby_monsters, auto_evade))

    # Collect clues when done with movement.
    if isinstance(event, events.Movement):
      if isinstance(event.character.place, places.Location) and event.character.place.clues:
        triggers.append(events.CollectClues(event.character, event.character.place))

    # Pulled through a gate if it opens on top of you.
    # Ancient one awakens if gate limit has been hit.
    if isinstance(event, events.SpawnGate) and event.opened:
      open_gates = len([place for place in self.places.values() if getattr(place, "gate", None)])
      if open_gates >= self.gate_limit():
        triggers.append(events.Awaken())
      loc = self.places[event.location_name]
      chars = [char for char in self.characters if char.place == loc]
      if chars:
        triggers.append(events.PullThroughGate(chars))

    # Non-spell items deactivate at the end of a combat round.
    deactivates = (events.CombatRound, events.InvestigatorAttack, events.InsaneOrUnconscious)
    if isinstance(event, deactivates):
      triggers.append(events.DeactivateItems(event.character))

    # Spells deactivate at the end of an entire combat.
    if isinstance(event, (events.Combat, events.InvestigatorAttack, events.InsaneOrUnconscious)):
      triggers.append(events.DeactivateCombatSpells(event.character))

    # If 6 gates are sealed or all gates are closed with enough trophies, win the game.
    if isinstance(event, events.CloseGate):
      gate_count = len([p for p in self.places.values() if getattr(p, "gate", None)])
      seal_count = len([p for p in self.places.values() if getattr(p, "sealed", False)])
      trophy_count = len(
        [g for char in self.characters for g in char.trophies if isinstance(g, gates.Gate)]
      )
      if seal_count >= 6:
        self.game_stage = "victory"
        self.event_stack.clear()
        self.event_log.append(events.EventLog("The players have won by sealing 6 gates.", False))
      elif gate_count == 0 and trophy_count >= len(self.characters):
        self.game_stage = "victory"
        self.event_stack.clear()
        self.event_log.append(events.EventLog("The players have won by closing all gates.", False))

    triggers.extend(
      sum([char.get_triggers(event, self) for char in self.characters if not char.gone], [])
    )
    global_triggers = [glob.get_trigger(event, self) for glob in self.globals() if glob]
    triggers.extend([trigger for trigger in global_triggers if trigger])
    if isinstance(event, self.MONSTER_EVENTS) and isinstance(event.monster, monsters.core.Monster):
      monster_trigger = event.monster.get_trigger(event, self)
      triggers.extend([monster_trigger] if monster_trigger else [])

    return triggers

  def get_usable_triggers(self, event):
    trgs = {
      idx: char.get_usable_triggers(event, self)
      for idx, char in enumerate(self.characters)
      if not char.gone
    }
    # If the character moved from another world to another character, let them trade after moving.
    if isinstance(event, (events.ForceMovement, events.Return)) and self.turn_phase == "movement":
      if len([char for char in self.characters if char.place == event.character.place]) > 1:
        trgs[self.characters.index(event.character)]["trade"] = events.Nothing()
    # If the ancient one has awakened and this is the end of the last upkeep phase before the
    # players attack, give all characters a chance to trade.
    if self.game_stage == "awakened" and isinstance(event, events.Upkeep):
      if not all(char.gone for char in self.characters):
        next_player = self.turn_idx + 1
        next_player %= len(self.characters)
        while self.characters[next_player].gone:
          next_player += 1
          next_player %= len(self.characters)
        if next_player == self.first_player:
          for idx, char in enumerate(self.characters):
            if not char.gone:
              trgs[idx]["trade"] = events.Nothing()
    return {char_idx: triggers for char_idx, triggers in trgs.items() if triggers}

  def handle_ancient(self, ancient):
    if self.game_stage != "setup":
      raise InvalidMove("The game has already started.")
    if ancient not in self.all_ancients:
      raise InvalidMove(f"Unknown ancient one {ancient}")
    self.ancient_one = self.all_ancients[ancient]

  def handle_option(self, expansion, option, enabled):
    if self.game_stage != "setup":
      raise InvalidMove("The game has already started.")
    if expansion not in self.options:
      raise InvalidMove(f"Unknown expansion {expansion}")
    if option is not None:
      exp_options = getattr(self, f"{expansion.upper()}_OPTIONS")
      if option not in exp_options:
        raise InvalidMove(f"Unknown option {option}")
    if enabled not in [True, False]:
      raise InvalidMove("Enabled must be true or false")

    if (option is None or option == "characters") and not enabled:
      new_characters = characters.CreateCharacters(self.expansions("characters") - {expansion})
      invalid_characters = self.pending_chars.keys() - new_characters.keys()
      if invalid_characters:
        names = "], [".join(invalid_characters)
        raise InvalidMove(f"Must abandon characters: [{names}] before disabling {expansion}")

    if option is None:
      if enabled:
        self.options[expansion] = set(getattr(self, f"{expansion.upper()}_OPTIONS"))
      else:
        self.options[expansion] = set()
    else:
      if enabled:
        self.options[expansion].add(option)
      else:
        self.options[expansion].discard(option)

    # If expansion boards are used, the corresponding mythos and encounter cards must be used.
    if expansion in {"hilltown", "seaside"}:
      if enabled:
        if "mythos" in self.options[expansion]:
          self.options[expansion] |= {"rules"}
        if "rules" in self.options[expansion]:
          self.options[expansion] |= {"mythos", "encounters"}
      else:
        if not {"mythos", "encounters"} <= self.options[expansion]:
          self.options[expansion] -= {"rules"}
        if "rules" not in self.options[expansion]:
          self.options[expansion] -= {"mythos"}
    elif expansion == "clifftown":
      if enabled and "rules" in self.options[expansion]:
        self.options[expansion] |= {"encounters"}
      if not enabled and "encounters" not in self.options[expansion]:
        self.options[expansion] -= {"rules"}
    elif expansion == "king":
      if enabled and "rules" in self.options[expansion]:
        self.options[expansion] |= {"mythos"}
      if not enabled and "mythos" not in self.options[expansion]:
        self.options[expansion] -= {"rules"}

    if option == "characters" or option is None:
      self.all_characters = characters.CreateCharacters(self.expansions("characters"))
    if option == "ancient_ones" or option is None:
      self.all_ancients = ancient_ones.AncientOnes(self.expansions("ancient_ones"))
      if self.ancient_one is not None and self.ancient_one.name not in self.all_ancients:
        self.ancient_one = None

  def handle_start(self):
    if self.game_stage != "setup":
      raise InvalidMove("The game has already started.")
    if self.ancient_one is None:
      raise InvalidMove("You must choose an ancient one first.")
    if not self.pending_chars:
      raise InvalidMove("At least one player is required to start the game.")
    invalid_characters = self.pending_chars.keys() - self.all_characters.keys()
    if invalid_characters:
      names = "], [".join(invalid_characters)
      raise InvalidMove(f"Characters [{names}] not allowed with chosen expansions")
    self.game_stage = "slumber"
    self.turn_idx = 0
    self.turn_number = -1
    self.turn_phase = "mythos"
    self.initialize()
    self.ancient_one.setup(self)
    sliders = self.add_pending_players()
    if any(char.name == "Scientist" for char in self.characters):
      self.places["Science"].clues = 0
    assert sliders.characters, "no players?"
    self.event_stack.append(events.Sequence([sliders, events.Mythos(None, first_turn=True)], None))

  def validate_new_character(self, name):
    if name not in self.all_characters:
      raise InvalidMove(f"Unknown character {name}")
    if self.all_characters[name].gone:
      raise InvalidMove("That character has already been devoured or retired.")
    if name in {char.name for char in self.characters} or name in self.pending_chars:
      raise InvalidMove("That character is already taken.")
    if self.game_stage not in ["setup", "slumber"]:
      raise InvalidMove("You cannot join the game right now.")

  def handle_join(self, old_name, char_name):
    self.validate_new_character(char_name)

    if old_name == char_name:
      return
    if old_name is not None and old_name in self.pending_chars:
      self.pending_chars.pop(old_name)
    self.pending_chars[char_name] = None

  def handle_choose_char(self, player_idx, name):
    if not self.characters[player_idx].gone:
      raise InvalidMove("You cannot choose a new character right now.")
    self.validate_new_character(name)

    to_remove = [name for name, idx in self.pending_chars.items() if idx == player_idx]
    for old_name in to_remove:
      self.pending_chars.pop(old_name)
    self.pending_chars[name] = player_idx

  def handle_use(self, char_idx, handle):
    if char_idx not in self.usables and char_idx not in self.spendables:
      raise InvalidMove("You cannot use any items or abilities at this time")
    if handle == "trade":  # "trade" is just a placeholder
      raise InvalidMove("Trade what?")
    if char_idx in self.usables and handle in self.usables[char_idx]:
      use_event = self.usables[char_idx].pop(handle)
      self.event_stack.append(use_event)
      return
    # For now, spending possessions/trophies goes through the same interface as using them.
    # TODO: split this out into a separate method.
    if char_idx in self.spendables and handle in self.spendables[char_idx]:
      spend_event = self.event_stack[-1]
      if self.spendables[char_idx][handle]:
        spend_event.spend_handle(handle, self.spendables[char_idx][handle])
      else:
        spend_event.unspend_handle(handle)
      return
    raise InvalidMove("{handle} is unknown or unusable at this time")

  def handle_done_using(self, char_idx):
    if char_idx not in self.usables:
      raise InvalidMove("You cannot use any items or abilities at this time")
    self.done_using[char_idx] = True

  def handle_choice(self, char_idx, choice):
    if not self.event_stack:
      raise InvalidMove("You cannot make any choices at this time")
    event = self.event_stack[-1]
    if not isinstance(event, events.ChoiceEvent):
      raise InvalidMove("You cannot make any choices at this time")
    if event.character != self.characters[char_idx]:
      raise InvalidMove("You cannot make any choices at this time")
    event.resolve(self, choice)

  def handle_spend(self, char_idx, spend_type):
    if not self.event_stack:
      raise InvalidMove("You cannot spend anything at this time")
    event = self.event_stack[-1]
    if not isinstance(event, events.SpendMixin):
      raise InvalidMove("You cannot spend anything at this time")
    if event.character != self.characters[char_idx]:
      raise InvalidMove("You cannot spend anything at this time")
    event.spend(spend_type)

  def handle_unspend(self, char_idx, spend_type):
    if not self.event_stack:
      raise InvalidMove("You cannot spend anything at this time")
    event = self.event_stack[-1]
    if not isinstance(event, events.SpendMixin):
      raise InvalidMove("You cannot spend anything at this time")
    if event.character != self.characters[char_idx]:
      raise InvalidMove("You cannot spend anything at this time")
    event.unspend(spend_type)

  def handle_roll(self, char_idx):
    if not self.event_stack:
      raise InvalidMove("You cannot roll the dice at this time")
    event = self.event_stack[-1]
    if not isinstance(event, events.DiceRoll):
      raise InvalidMove("You cannot roll the dice at this time")
    if event.character != self.characters[char_idx]:
      raise InvalidMove("It is not your turn to roll the dice")
    event.resolve(self)

  def handle_add_doom(self):
    self.ancient_one.doom += 1
    self.ancient_one.doom = min(self.ancient_one.doom, self.ancient_one.max_doom)

  def handle_remove_doom(self):
    self.ancient_one.doom -= 1
    self.ancient_one.doom = max(self.ancient_one.doom, 0)

  def handle_awaken(self):
    self.event_stack.append(events.Awaken())

  def handle_spawn_clue(self, place):
    assert place in self.places
    assert hasattr(self.places[place], "clues")
    self.places[place].clues += 1

  def handle_remove_clue(self, place):
    assert place in self.places
    assert hasattr(self.places[place], "clues")
    self.places[place].clues -= 1
    self.places[place].clues = max(self.places[place].clues, 0)

  def handle_remove_gate(self, place):
    assert place in self.places
    assert getattr(self.places[place], "gate", None) is not None
    self.gates.append(self.places[place].gate)
    self.places[place].gate = None

  def handle_toggle_seal(self, place):
    assert place in self.places
    assert hasattr(self.places[place], "sealed")
    self.places[place].sealed = not self.places[place].sealed

  def handle_spawn_gate(self, gate_name, place):
    assert place in self.places
    assert getattr(self.places[place], "gate", True) is None
    for gate in self.gates:
      if gate.name == gate_name:
        self.places[place].gate = gate
        self.gates.remove(gate)
        return
    raise InvalidMove("No gates of that type left in the stack.")

  def handle_spawn_monster(self, monster_name, place):
    assert place in self.places
    for monster in self.monsters:
      if monster.name == monster_name and monster.place == self.monster_cup:
        monster.place = self.places[place]
        return
    raise InvalidMove("No monsters of that type left in the cup.")

  def handle_remove_monster(self, monster_name, place):
    assert place in self.places
    for monster in self.monsters:
      if monster.name == monster_name and monster.place == self.places[place]:
        monster.place = self.monster_cup
        return
    raise InvalidMove("No monsters of that type in that place.")

  def handle_set_stats(self, data):
    name = data.get("name")
    stats = ["stamina", "sanity", "clues", "dollars"]
    chars = [char for char in self.characters if char.name == name]
    assert len(chars) == 1
    assert all(isinstance(data.get(stat), int) for stat in stats)
    char = chars[0]
    for stat in stats:
      setattr(char, stat, max(data[stat], 0))
    char.stamina = min(char.stamina, char.max_stamina(self))
    char.sanity = min(char.sanity, char.max_sanity(self))

  def handle_insane(self, name):
    chars = [char for char in self.characters if char.name == name]
    assert len(chars) == 1
    self.event_stack.append(events.Insane(chars[0]))

  def handle_unconscious(self, name):
    chars = [char for char in self.characters if char.name == name]
    assert len(chars) == 1
    self.event_stack.append(events.Unconscious(chars[0]))

  def handle_devoured(self, name):
    chars = [char for char in self.characters if char.name == name]
    assert len(chars) == 1
    self.event_stack.append(events.Devoured(chars[0]))

  def handle_move_char(self, name, place):
    chars = [char for char in self.characters if char.name == name]
    assert len(chars) == 1
    char = chars[0]
    if place in self.places:
      char.place = self.places[place]
    elif place + "1" in self.places:
      char.place = self.places[place + "1"]
    else:
      raise InvalidMove(f"Unknown place {place}")

  def handle_give_item(self, char_name, item_name):
    chars = [char for char in self.characters if char.name == char_name]
    assert len(chars) == 1
    char = chars[0]
    for deck in ["common", "unique", "spells", "skills", "allies", "specials", "tradables"]:
      found = [item for item in getattr(self, deck) if item.name == item_name]
      if found:
        getattr(self, deck).remove(found[0])
        char.possessions.append(found[0])
        return
    raise InvalidMove(f"Could not find {item_name} in any deck")

  def handle_remove_item(self, char_name, handle):
    chars = [char for char in self.characters if char.name == char_name]
    assert len(chars) == 1
    char = chars[0]
    found = [pos for pos in char.possessions if pos.handle == handle]
    assert len(found) == 1
    pos = found[0]
    assert hasattr(pos, "deck")
    char.possessions.remove(pos)
    getattr(self, pos.deck).append(pos)

  def handle_exhaust_item(self, char_name, handle):
    chars = [char for char in self.characters if char.name == char_name]
    assert len(chars) == 1
    char = chars[0]
    found = [pos for pos in char.possessions if pos.handle == handle]
    assert len(found) == 1
    pos = found[0]
    assert hasattr(pos, "_exhausted")
    pos._exhausted = True  # pylint: disable=protected-access

  def handle_refresh_item(self, char_name, handle):
    chars = [char for char in self.characters if char.name == char_name]
    assert len(chars) == 1
    char = chars[0]
    found = [pos for pos in char.possessions if pos.handle == handle]
    assert len(found) == 1
    pos = found[0]
    assert hasattr(pos, "_exhausted")
    pos._exhausted = False  # pylint: disable=protected-access

  def handle_give_trophy(self, char_name, monster_or_gate):
    chars = [char for char in self.characters if char.name == char_name]
    assert len(chars) == 1
    char = chars[0]
    for monster in self.monsters:
      if monster.place == self.monster_cup and monster.name == monster_or_gate:
        monster.place = None
        char.trophies.append(monster)
        return
    for gate in self.gates:
      if gate.name == monster_or_gate:
        self.gates.remove(gate)
        char.trophies.append(gate)
        return
    raise InvalidMove(f"Monster or gate {monster_or_gate} not found.")

  def handle_remove_trophy(self, char_name, handle):
    chars = [char for char in self.characters if char.name == char_name]
    assert len(chars) == 1
    char = chars[0]
    found = [trophy for trophy in char.trophies if trophy.handle == handle]
    assert len(found) == 1
    trophy = found[0]
    if isinstance(trophy, monsters.core.Monster):
      char.trophies.remove(trophy)
      trophy.place = self.monster_cup
    elif isinstance(trophy, gates.Gate):
      char.trophies.remove(trophy)
      self.gates.append(trophy)
    else:
      raise InvalidMove("Unknown trophy type")

  def handle_redo_sliders(self, name):
    chars = [char for char in self.characters if char.name == name]
    assert len(chars) == 1
    self.event_stack.append(events.SliderInput(chars[0], free=True))

  def handle_set_card(self, name):
    if name.startswith("Mythos"):
      cards = [card for card in self.mythos if card.name == name]
      assert len(cards) == 1
      self.mythos.remove(cards[0])
      self.mythos.appendleft(cards[0])
      return
    if name.startswith("Gate"):
      cards = [card for card in self.gate_cards if card.name == name]
      assert len(cards) == 1
      self.gate_cards.remove(cards[0])
      self.gate_cards.appendleft(cards[0])
      return
    for place in self.places.values():
      if not isinstance(getattr(place, "encounters", None), list):
        continue
      cards = [card for card in place.encounters if card.name == name]
      if len(cards) != 1:
        continue
      place.encounters.remove(cards[0])
      place.encounters.insert(0, cards[0])
      break
    else:
      raise InvalidMove(f"Card {name} not found")

  def handle_slider(self, char_idx, name, value):
    assert self.event_stack
    event = self.event_stack[-1]
    if isinstance(event, events.SliderInput):
      if event.character != self.characters[char_idx]:
        raise NotYourTurn("It is not your turn to set sliders.")
      event.resolve(self, name, value)
      return
    if isinstance(event, events.InitialSliders):
      event.resolve(self, name, value, char_idx)
      return
    raise InvalidMove("It is not time to move your sliders.")

  def handle_give(self, char_idx, recipient_idx, handle, amount):
    if not isinstance(recipient_idx, int):
      raise InvalidPlayer("Invalid recipient")
    if recipient_idx < 0 or recipient_idx >= len(self.characters):
      raise InvalidPlayer("Invalid recipient")
    if self.characters[recipient_idx].gone:
      raise InvalidMove("That player is either devoured or retired.")
    if recipient_idx == char_idx:
      raise InvalidMove("You cannot trade with yourself")
    recipient = self.characters[recipient_idx]
    donor = self.characters[char_idx]

    if not self.can_trade():
      raise InvalidMove("You cannot trade at this time.")
    if donor.place != recipient.place:
      raise InvalidMove("You must be in the same place to trade.")

    if handle == "dollars":
      if not isinstance(amount, int):
        raise InvalidMove("Invalid quantity")
      if amount < 0 or amount > donor.dollars:
        raise InvalidMove("Invalid quantity")
      # TODO: turn this into an event
      recipient.dollars += amount
      donor.dollars -= amount
      return

    if not isinstance(handle, str):
      raise InvalidMove("Invalid card")
    donations = [pos for pos in donor.possessions if pos.handle == handle]
    if len(donations) != 1:
      raise InvalidMove("Invalid card")
    donation = donations[0]
    if getattr(donation, "deck", None) not in {"common", "unique", "spells", "tradables"}:
      raise InvalidMove("You can only trade items")

    # TODO: turn this into an event.
    donor.possessions.remove(donation)
    recipient.possessions.append(donation)

  def can_trade(self):
    if not self.event_stack:
      return False
    if self.game_stage == "awakened":
      if self.turn_phase != "upkeep":
        return False
      return any("trade" in usables for usables in self.usables.values())
    if self.turn_phase != "movement":
      return False
    event = self.event_stack[-1]
    if isinstance(event, (events.CityMovement, events.ForceMovement, events.Return)):
      return True
    if len(self.event_stack) < 2:
      return False
    parent = self.event_stack[-2]
    if isinstance(parent, events.Return) and isinstance(event, events.ReturnGateChoice):  # noqa: SIM103
      return True
    return False

  def next_turn(self):
    if self.game_stage == "awakened":
      self.next_awaken_turn()
      return

    # Handle the end of the mythos phase separately.
    if self.turn_phase == "mythos":
      # If we have pending players that need to be added, don't start the next turn yet. next_turn
      # will be called again when they are done setting their sliders.
      seq = self.add_pending_players()
      if seq is not None:
        self.event_stack.append(seq)
        return

      # If there are any characters that were devoured and have not chosen a new character, stop.
      if any(char.gone for char in self.characters):
        raise InvalidMove("All players with devoured characters must choose new characters.")

      self.turn_number += 1
      if self.turn_number != 0:
        self.first_player += 1
        self.first_player %= len(self.characters)
      self.turn_idx = self.first_player
      self.turn_phase = "upkeep"
      for char in self.characters:  # TODO: is this the right place to check for this?
        if char.lose_turn_until and char.lose_turn_until <= self.turn_number:
          char.lose_turn_until = None
        if char.arrested_until and char.arrested_until <= self.turn_number:
          char.arrested_until = None
      self.event_stack.append(events.Upkeep(self.characters[self.turn_idx]))
      for place in self.places.values():
        if getattr(place, "closed_until", None) == self.turn_number:
          place.closed_until = None
      return

    # Handling end of all other turn types begins here.
    self.turn_idx += 1
    self.turn_idx %= len(self.characters)

    # Handle a switch to the next turn phase.
    if self.turn_idx == self.first_player:
      # Guaranteed to not go off the end of the list because this is not the mythos phase.
      phase_idx = self.TURN_PHASES.index(self.turn_phase)
      self.turn_phase = self.TURN_PHASES[phase_idx + 1]

    # We are done updating turn phase, turn number, turn index, and first player.
    self.event_stack.append(self.TURN_TYPES[self.turn_phase](self.characters[self.turn_idx]))

  def next_awaken_turn(self):
    if all(char.gone for char in self.characters):
      self.game_stage = "defeat"
      self.event_log.append(events.EventLog("The players were all devoured.", False))
      return
    if self.turn_phase == "ancient":
      self.turn_number += 1
      self.first_player += 1
      self.first_player %= len(self.characters)
      while self.characters[self.first_player].gone:
        self.first_player += 1
        self.first_player %= len(self.characters)
      self.turn_idx = self.first_player
      self.turn_phase = "upkeep"
      self.event_stack.append(events.Upkeep(self.characters[self.turn_idx]))
      return

    self.turn_idx += 1
    self.turn_idx %= len(self.characters)
    while self.characters[self.turn_idx].gone:
      self.turn_idx += 1
      self.turn_idx %= len(self.characters)

    if self.turn_idx == self.first_player:
      phase_idx = self.AWAKENED_PHASES.index(self.turn_phase)
      self.turn_phase = self.AWAKENED_PHASES[phase_idx + 1]

    self.event_stack.append(self.AWAKENED_TURNS[self.turn_phase](self.characters[self.turn_idx]))

  def add_pending_players(self):
    if not self.pending_chars:
      return None

    assert not {char.name for char in self.characters} & self.pending_chars.keys()
    new_characters = []
    for name, idx in self.pending_chars.items():
      new_characters.append(self.all_characters[name])
      if idx is None:
        self.characters.append(self.all_characters[name])
      else:
        assert self.characters[idx].gone
        old_trophies = self.characters[idx].trophies
        self.characters[idx] = self.all_characters[name]
        self.characters[idx].trophies.extend(old_trophies)
        old_trophies.clear()

    new_characters.sort(key=self.characters.index)  # Sort by order in self.characters.
    self.pending_chars.clear()

    # Abilities and fixed possessions.
    char_specials = abilities.CreateAbilities(self.expansions("characters"))
    for char in new_characters:
      char.place = self.places[char.home]
      char.possessions.extend([char_specials[name] for name in char.abilities()])
      self.give_fixed_possessions(char, char.fixed_possessions())
    # Random possessions.
    for char in new_characters:
      self.give_random_possessions(char, char.random_possessions())
    # Initial attributes.
    for char in new_characters:
      char.stamina = char.max_stamina(self)
      char.sanity = char.max_sanity(self)
      for attr, val in char.initial_attributes().items():
        setattr(char, attr, val)

    return events.InitialSliders(new_characters)


class EldritchGame(BaseGame):
  def __init__(self):
    self.game = GameState()
    self.connected = set()
    self.host = None
    self.player_sessions = {}
    self.pending_sessions = {}

  def game_url(self, game_id):
    return f"/eldritch/game.html?game_id={game_id}"

  def game_status(self):
    return self.game.game_status()

  @classmethod
  def parse_json(cls, json_str):  # pylint: disable=arguments-renamed,unused-argument
    return None  # TODO

  def json_str(self):
    output = self.game.json_repr()
    output["player_sessions"] = self.player_sessions
    output["pending_sessions"] = self.pending_sessions
    return json.dumps(output, cls=CustomEncoder)

  def for_player(self, session):
    output = self.game.for_player(self.player_sessions.get(session))
    # is_connected = {idx: sess in self.connected for sess, idx in self.player_sessions.items()}
    # TODO: send connection information somehow
    # for idx in range(len(output["characters"])):
    #   output["characters"][idx]["disconnected"] = not is_connected.get(idx, False)
    output["player_idx"] = self.player_sessions.get(session)
    output["pending_name"] = self.pending_sessions.get(session)
    output["host"] = self.host == session
    return json.dumps(output, cls=CustomEncoder)

  def connect_user(self, session):
    self.connected.add(session)
    if self.host is None:
      self.host = session

  def disconnect_user(self, session):
    self.connected.remove(session)
    if session in self.pending_sessions:
      name = self.pending_sessions[session]
      if name in self.game.pending_chars:
        self.game.pending_chars.pop(name)
      del self.pending_sessions[session]
    if self.host == session:
      if not self.connected:
        self.host = None
      else:
        self.host = next(iter(self.connected))

  def handle(self, session, data):
    if not isinstance(data, dict):
      raise InvalidMove("Data must be a dictionary.")
    if data.get("type") == "join":
      yield from self.handle_join(session, data)
      return
    if data.get("type") in ["start", "ancient", "option"]:  # Host actions
      if session != self.host:
        raise InvalidMove("Only the host can do that.")
    else:  # All other actions must be tied to a player that has joined the game.
      if session not in self.player_sessions:
        raise InvalidPlayer("Unknown player")
    for val in self.game.handle(self.player_sessions.get(session), data):
      self.update_pending_players()
      yield val

  def handle_join(self, session, data):
    if session in self.player_sessions:
      self.game.handle_choose_char(self.player_sessions[session], data.get("char"))
      yield from self.game.resolve_loop()
      return
    self.game.handle_join(self.pending_sessions.get(session), data.get("char"))
    self.pending_sessions[session] = data.get("char")
    yield None

  def update_pending_players(self):
    if not self.pending_sessions:
      return
    indexes = {char.name: idx for idx, char in enumerate(self.game.characters)}
    pending = {name: session for session, name in self.pending_sessions.items()}
    updated = indexes.keys() & pending.keys()
    for name in updated:
      self.player_sessions[pending[name]] = indexes[name]
      self.pending_sessions.pop(pending[name])
