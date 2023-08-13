assetPrefix = "eldritch";

assetSet = new Set([]);
nameSet = new Set([]);
function carefullyAdd(names, isName) {
  for (let name of names) {
    if (assetSet.has(name)) {
      throw "Duplicate name " + name;
    }
    assetSet.add(name);
    if (isName) {
      nameSet.add(name);
    }
  }
}

characterData = {
  "Student": {"sliders": [1, 4, 1, 4, 1, 4], "focus": 3, "home": "Bank"},
  "Drifter": {"sliders": [0, 6, 2, 5, 0, 3], "focus": 1, "home": "Docks"},
  "Salesman": {"sliders": [2, 3, 1, 6, 0, 4], "focus": 1, "home": "Store"},
  "Psychologist": {"sliders": [0, 3, 1, 4, 2, 5], "focus": 2, "home": "Asylum"},
  "Photographer": {"sliders": [2, 3, 2, 4, 0, 4], "focus": 2, "home": "Newspaper"},
  "Magician": {"sliders": [2, 4, 1, 3, 2, 3], "focus": 2, "home": "Shoppe"},
  "Author": {"sliders": [1, 3, 0, 5, 1, 5], "focus": 2, "home": "Diner"},
  "Professor": {"sliders": [0, 5, 0, 3, 3, 4], "focus": 2, "home": "Administration"},
  "Dilettante": {"sliders": [0, 4, 1, 5, 1, 5], "focus": 1, "home": "Train"},
  "Private Eye": {"sliders": [3, 4, 2, 3, 0, 3], "focus": 3, "home": "Police"},
  "Scientist": {"sliders": [1, 5, 1, 3, 2, 4], "focus": 1, "home": "Science"},
  "Researcher": {"sliders": [1, 5, 0, 5, 1, 3], "focus": 2, "home": "Library"},
  "Nun": {"sliders": [1, 4, 0, 4, 1, 6], "focus": 1, "home": "Church"},
  "Doctor": {"sliders": [0, 5, 0, 4, 2, 4], "focus": 2, "home": "Hospital"},
  "Archaeologist": {"sliders": [1, 3, 2, 3, 1, 5], "focus": 2, "home": "Shop"},
  "Gangster": {"sliders": [2, 4, 3, 4, 0, 3], "focus": 1, "home": "House"},
};
characterNames = Object.keys(characterData);
carefullyAdd(characterNames, true);
characterTitles = characterNames.map(name => name + " title");
carefullyAdd(characterTitles, false);
characterPictures = characterNames.map(name => name + " picture");
carefullyAdd(characterPictures, false);
characterFocus = characterNames.map(name => name + " focus");
carefullyAdd(characterFocus, false);
characterHome = characterNames.map(name => name + " home");
carefullyAdd(characterHome, false);
characterSliderNames = characterNames.map(name => name + " sliders");
carefullyAdd(characterSliderNames, false);
sliderLocations = [];
for (let i = 0; i < 4; i++) {
  for (let j = 0; j < 4; j++) {
    sliderLocations.push("Slider " + i + " " + j);
  }
}
carefullyAdd(sliderLocations, false);
commonNames = [
  ".18 Derringer",
  ".38 Revolver",
  ".45 Automatic",
  "Ancient Tome",
  "Axe",
  "Bullwhip",
  "Cavalry Saber",
  "Cigarette Case",
  "Cross",
  "Dark Cloak",
  "Dynamite",
  "Food",
  "Knife",
  "Lantern",
  "Map",
  "Motorcycle",
  "OldJournal",
  "Research Materials",
  "Rifle",
  "Shotgun",
  "Tommy Gun",
  "Whiskey",
];
carefullyAdd(commonNames, true);
uniqueNames = [
  "Alien Statue",
  "Ancient Tablet",
  "Blue Watcher",
  "Tibetan Tome",
  "Mysticism Tome",
  "Black Magic Tome",
  "Dragon's Eye",
  "Sign",
  "Enchanted Blade",
  "Enchanted Jewelry",
  "Enchanted Knife",
  "Flute",
  "Gate Box",
  "Healing Stone",
  "Holy Water",
  "Magic Lamp",
  "Black Book",
  "Book of the Dead",
  "Obsidian Statue",
  "Pallid Mask",
  "Magic Powder",
  "Ruby",
  "Silver Key",
  "Sword of Glory",
  "Yellow Play",
  "Warding Statue",
];
carefullyAdd(uniqueNames, true);
spellNames = [
  "Bind Monster",
  "Dread Curse",
  "Enchant Weapon",
  "Find Gate",
  "Flesh Ward",
  "Heal",
  "Mists",
  "Red Sign",
  "Shrivelling",
  "Voice",
  "Wither",
];
carefullyAdd(spellNames, true);
skillNames = [
  "Speed",
  "Sneak",
  "Fight",
  "Will",
  "Lore",
  "Luck",
  "Stealth",
  "Marksman",
  "Bravery",
  "Expert Occultist",
];
carefullyAdd(skillNames, true);
allyNames = [
  "Fortune Teller",
  "Traveling Salesman",
  "Police Detective",
  "Thief",
  "Brave Guy",
  "Police Inspector",
  "Arm Wrestler",
  "Visiting Painter",
  "Tough Guy",
  "Old Professor",
  "Dog",
];
carefullyAdd(allyNames, true);
abilityNames = [
  "Studious",
  "Scrounge",
  "Shrewd Dealer",
  "Psychology",
  "Hometown Advantage",
  "Magical Gift",
  "Psychic Sensitivity",
  "Strong Mind",
  "Trust Fund",
  "Hunches",
  "Flux Stabilizer",
  "Research",
  "Guardian Angel",
  "Physician",
  "Archaeology",
  "Strong Body",
];
carefullyAdd(abilityNames, true);
otherNames = [
  "Deputy",
  "Deputy's Revolver",
  "Patrol Wagon",
  "Blessing",
  "Curse",
  "Retainer",
  "Bank Loan",
  "Lodge Membership",
];
carefullyAdd(otherNames, true);
monsterNames = [
  "Giant Insect",
  "Land Squid",
  "Cultist",
  "Tentacle Tree",
  "Dimensional Shambler",
  "Giant Worm",
  "Elder Thing",
  "Flame Matrix",
  "Subterranean Flier",
  "Formless Spawn",
  "Ghost",
  "Ghoul",
  "Furry Beast",
  "Haunter",
  "High Priest",
  "Hound",
  "Maniac",
  "Pinata",
  "Dream Flier",
  "Giant Amoeba",
  "Octopoid",
  "Vampire",
  "Warlock",
  "Witch",
  "Zombie",
];
carefullyAdd(monsterNames, true);
monsterBacks = monsterNames.map(name => name + " back");
carefullyAdd(monsterBacks, false);
monsterTexts = monsterNames.map(name => name + " text");
carefullyAdd(monsterTexts, false);
otherWorlds = [
  "Abyss",
  "Another Dimension",
  "City",
  "Great Hall",
  "Plateau",
  "Sunken City",
  "Dreamlands",
  "Pluto",
];
carefullyAdd(otherWorlds, true);
gateNames = otherWorlds.map(name => "Gate " + name);
carefullyAdd(gateNames, false);
extraNames = ["Lost", "Sky", "Outskirts"];
carefullyAdd(extraNames, false);
ancientOneDoomMax = {
  "Squid Face": 13,
  "The Yellow King": 13,
  "God of Chaos": 14,
  "Wendigo": 11,
  "The Thousand Masks": 11,
  "Black Goat of the Woods": 12,
  "Serpent God": 10,
  "Space Bubbles": 12,
}
ancientOnes = Object.keys(ancientOneDoomMax);
carefullyAdd(ancientOnes, true);
ancientOneWorshippers = ancientOnes.map(name => name + " worshippers");
carefullyAdd(ancientOneWorshippers, false);
ancientOneSlumbers = ancientOnes.map(name => name + " slumber");
carefullyAdd(ancientOneSlumbers, false);
ancientOneDooms = ancientOnes.map(name => name + " max");
carefullyAdd(ancientOneDooms, false);
gateCards = [];
for (let i = 1; i <= 50; i++) {
  gateCards.push("Gate" + i);
}
carefullyAdd(gateCards, true);
mythosCards = [];
for (let i = 1; i <= 67; i++) {
  mythosCards.push("Mythos" + i);
}
carefullyAdd(mythosCards, true);
carefullyAdd(["Gate Back", "Gate Card", "Mythos Card"], false);
neighborhoodNames = [
  "Northside",
  "Downtown",
  "Easttown",
  "Rivertown",
  "FrenchHill",
  "Southside",
  "Uptown",
  "University",
  "Merchant",
];
carefullyAdd(neighborhoodNames, true);
encounterCardNames = neighborhoodNames.map(name => name + " Card");
for (let n of neighborhoodNames) {
  for (let i = 1; i <= 7; i++) {
    encounterCardNames.push(n + i);
  }
}
carefullyAdd(encounterCardNames, false);
locationNames = [
  "Shop",
  "Newspaper",
  "Train",
  "Bank",
  "Asylum",
  "Square",
  "Roadhouse",
  "Diner",
  "Police",
  "Graveyard",
  "Cave",
  "Store",
  "WitchHouse",
  "Lodge",
  "House",
  "Church",
  "Society",
  "Woods",
  "Shoppe",
  "Hospital",
  "Library",
  "Administration",
  "Science",
  "Unnamable",
  "Docks",
  "Isle",
];
carefullyAdd(locationNames, true);
tokens = ["Dollar", "Clue", "Sanity", "Stamina", "Slider", "Seal", "Doom", "Closed", "Activity"];
carefullyAdd(tokens, false);
terrors = [];
for (let i = 0; i < 11; i++) {
  terrors.push("Terror" + i);
}
carefullyAdd(terrors, false);
deckNames = ["common", "unique", "spells", "skills", "allies"];
carefullyAdd(deckNames, false);
assetNames = ["statsbg", "board"].concat([...assetSet]);
serverNames = {};
for (let name of [...nameSet]) {
  serverNames[name] = name;
}
