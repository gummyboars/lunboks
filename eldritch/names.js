// TODO
assetPrefix = "eldritch";
characterNames = ["Nun", "Doctor", "Archaeologist", "Gangster"];
commonNames = [
  ".38 Revolver",
  "Bullwhip",
  "Cross",
  "Dynamite",
  "Food",
  "Tommy Gun",
  "Research Materials",
];
uniqueNames = [
  "Holy Water",
];
spellNames = [];
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
allyNames = [
  "Fortune Teller",
  "Traveling Salesman",
  "Police Detective",
  "Thief",
  "Brave Guy",
  "Mortician",
  "Arm Wrestler",
  "Visiting Painter",
  "Tough Guy",
  "Old Professor",
  "Dog",
];
abilityNames = [
  "Medicine",
];
monsterNames = [
  "Cultist",
  "Dimensional Shambler",
  "Elder Thing",
  "Formless Spawn",
  "Ghost",
  "Ghoul",
  "Furry Beast",
  "Maniac",
  "Dream Flier",
  "Warlock",
  "Zombie",
];
gateNames = [
  "Abyss",
  "Another Dimension",
  "City",
  "Great Hall",
  "Plateau",
  "Sunken City",
  "Dreamlands",
  "Pluto",
];
assetNames = ["board"].concat(characterNames).concat(commonNames).concat(uniqueNames).concat(spellNames).concat(skillNames).concat(allyNames).concat(abilityNames).concat(monsterNames).concat(gateNames);
serverNames = {};
for (let name of assetNames) {
  if (name == "board") {
    continue;
  }
  serverNames[name] = name;
}
gateCards = [];
for (let i = 1; i <= 50; i++) {
  gateCards.push("gate" + i);
}
mythosCards = [];
for (let i = 1; i <= 67; i++) {
  gateCards.push("mythos" + i);
}
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
encounterCardNames = [];
for (let n of neighborhoodNames) {
  for (let i = 1; i <= 7; i++) {
    encounterCardNames.push(n + i);
  }
}
assetNames = assetNames.concat(encounterCardNames).concat(gateCards).concat(mythosCards);
