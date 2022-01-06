assetPrefix = "eldritch";

assetSet = new Set([]);
function carefullyAdd(names) {
  for (let name of names) {
    if (assetSet.has(name)) {
      throw "Duplicate name " + name;
    }
    assetSet.add(name);
  }
}

characterSliders = {
  "Student": [1, 4, 1, 4, 1, 4],
  "Drifter": [0, 6, 2, 5, 0, 3],
  "Salesman": [2, 3, 1, 6, 0, 4],
  "Psychologist": [0, 3, 1, 4, 2, 5],
  "Photographer": [2, 3, 2, 4, 0, 4],
  "Magician": [2, 4, 1, 3, 2, 3],
  "Author": [1, 3, 0, 5, 1, 5],
  "Professor": [0, 5, 0, 3, 3, 4],
  "Dilettante": [0, 4, 1, 5, 1, 5],
  "Private Eye": [3, 4, 2, 3, 0, 3],
  "Scientist": [1, 5, 1, 3, 2, 4],
  "Researcher": [1, 5, 0, 5, 1, 3],
  "Nun": [1, 4, 0, 4, 1, 6],
  "Doctor": [0, 5, 0, 4, 2, 4],
  "Archaeologist": [1, 3, 2, 3, 1, 5],
  "Gangster": [2, 4, 3, 4, 0, 3],
};
characterNames = Object.keys(characterSliders);
carefullyAdd(characterNames);
characterTitles = characterNames.map(name => name + " title");
carefullyAdd(characterTitles);
characterPictures = characterNames.map(name => name + " picture");
carefullyAdd(characterPictures);
characterSliderNames = characterNames.map(name => name + " sliders");
carefullyAdd(characterSliderNames);
sliderLocations = [];
for (let i = 0; i < 4; i++) {
  for (let j = 0; j < 4; j++) {
    sliderLocations.push("Slider " + i + " " + j);
  }
}
carefullyAdd(sliderLocations);
commonNames = [
  ".18 Derringer",
  ".38 Revolver",
  ".45 Automatic",
  "Bullwhip",
  "Cross",
  "Dark Cloak",
  "Dynamite",
  "Food",
  "Tommy Gun",
  "Research Materials",
];
carefullyAdd(commonNames);
uniqueNames = [
  "Enchanted Knife",
  "Holy Water",
  "Magic Lamp",
];
carefullyAdd(uniqueNames);
spellNames = [
  "Dread Curse",
  "Enchant Weapon",
  "Find Gate",
  "Red Sign",
  "Shrivelling",
  "Voice",
  "Wither",
];
carefullyAdd(spellNames);
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
carefullyAdd(skillNames);
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
carefullyAdd(allyNames);
abilityNames = [
  "Medicine",
];
carefullyAdd(abilityNames);
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
carefullyAdd(monsterNames);
monsterBacks = monsterNames.map(name => name + " back");
carefullyAdd(monsterBacks);
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
carefullyAdd(otherWorlds);
gateNames = otherWorlds.map(name => "Gate " + name);
carefullyAdd(gateNames);
extraNames = ["Lost", "Sky", "Outskirts"];
carefullyAdd(extraNames);
assetNames = [...assetSet];
serverNames = {};
for (let name of assetNames) {
  serverNames[name] = name;
}
gateCards = [];
for (let i = 1; i <= 50; i++) {
  gateCards.push("Gate" + i);
}
carefullyAdd(gateCards);
mythosCards = [];
for (let i = 1; i <= 67; i++) {
  mythosCards.push("Mythos" + i);
}
carefullyAdd(mythosCards);
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
carefullyAdd(neighborhoodNames);
encounterCardNames = neighborhoodNames.map(name => name + " Card");
for (let n of neighborhoodNames) {
  for (let i = 1; i <= 7; i++) {
    encounterCardNames.push(n + i);
  }
}
carefullyAdd(encounterCardNames);
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
carefullyAdd(locationNames);
tokens = ["Dollar", "Clue", "Sanity", "Stamina", "Slider", "Seal", "Doom"];
carefullyAdd(tokens);
deckNames = ["common", "unique", "spells", "skills", "allies"];
carefullyAdd(deckNames);
assetNames = ["statsbg", "board"].concat([...assetSet]);
