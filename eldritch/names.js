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

characterNames = [
  "Student",
  "Drifter",
  "Salesman",
  "Psychologist",
  "Photographer",
  "Magician",
  "Author",
  "Professor",
  "Dilettante",
  "Private Eye",
  "Scientist",
  "Researcher",
  "Nun",
  "Doctor",
  "Archaeologist",
  "Gangster",
];
carefullyAdd(characterNames);
commonNames = [
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
  gateCards.push("gate" + i);
}
carefullyAdd(gateCards);
mythosCards = [];
for (let i = 1; i <= 67; i++) {
  mythosCards.push("mythos" + i);
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
encounterCardNames = [];
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
assetNames = ["Clue", "board"].concat([...assetSet]);
