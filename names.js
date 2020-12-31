serverNames = {
  rsrc1: "lime",
  rsrc2: "green",
  rsrc3: "yellow",
  rsrc4: "red",
  rsrc5: "gray",
  norsrc: "desert",
  anyrsrc: "bonus",
  space: "water",
};

assetPrefix = "";
assetNames = [
  // Tiles
  "rsrc1tile",
  "rsrc2tile",
  "rsrc3tile",
  "rsrc4tile",
  "rsrc5tile",
  "norsrctile",
  "anyrsrctile",
  "spacetile",
  "coast",
  "port",
  "rsrc1port",
  "rsrc2port",
  "rsrc3port",
  "rsrc4port",
  "rsrc5port",
  "3port",
  // Cards
  "rsrc1card",
  "rsrc2card",
  "rsrc3card",
  "rsrc4card",
  "rsrc5card",
  "knight",
  "roadbuilding",
  "yearofplenty",
  "monopoly",
  "palace",
  "chapel",
  "university",
  "library",
  "market",
  // Other
  "devcard",
  "cardback",
  "longestroute",
  "largestarmy",
  "robber",
  "pirate",
];

function initializeNames() {
  let overrides = JSON.parse(localStorage.getItem("names") || "{}");
  if (!overrides) {
    return;
  }
  let newNames = {};
  for (let name in serverNames) {
    if (overrides[name]) {
      newNames[name] = overrides[name];
    }
  }
  for (let name in newNames) {
    serverNames[name] = newNames[name];
  }
}

function initializeSpace() {
  localStorage.setItem("sources", JSON.stringify([
    "/sulfur.png", "/olivine.png", "/permafrost.png", "/clay.png", "/metal.png",
    "/sulfurcard.png", "/olivinecard.png", "/watercard.png", "/claycard.png", "/metalcard.png",
    "/sulfurport.png", "/olivineport.png", "/waterport.png", "/clayport.png", "/metalport.png",
    "/desert.png", "/space.png", "/3port.png",
    "/knight.png", "/roadbuilding.png", "/yearofplenty.png", "/monopoly.png",
    "/palace.png", "/chapel.png", "/university.png", "/library.png", "/market.png",
    "/cardback.png", "/devcard.png", "/longestroad.png", "/largestarmy.png",
    "/robber2.png", "/pirate.png",
  ]));
  localStorage.setItem("variants", "{}");
  localStorage.setItem("names", JSON.stringify({
    rsrc1: "sulfur",
    rsrc2: "olivine",
    rsrc3: "water",
    rsrc4: "clay",
    rsrc5: "metal",
    norsrc: "desert",
    anyrsrc: "gold",
    space: "space",
  }));
  localStorage.setItem("imageinfo", JSON.stringify({
    "rsrc1tile": {srcnum: 0},
    "rsrc2tile": {srcnum: 1},
    "rsrc3tile": {srcnum: 2},
    "rsrc4tile": {srcnum: 3},
    "rsrc5tile": {srcnum: 4},
    "rsrc1card": {srcnum: 5},
    "rsrc2card": {srcnum: 6},
    "rsrc3card": {srcnum: 7},
    "rsrc4card": {srcnum: 8},
    "rsrc5card": {srcnum: 9},
    "norsrctile": {srcnum: 15},
    "spacetile": {srcnum: 16},
    "coast": {},
    "port": {},
    "rsrc1port": {srcnum: 10},
    "rsrc2port": {srcnum: 11},
    "rsrc3port": {srcnum: 12},
    "rsrc4port": {srcnum: 13},
    "rsrc5port": {srcnum: 14},
    "3port": {srcnum: 17},
    "knight": {srcnum: 18},
    "roadbuilding": {srcnum: 19},
    "yearofplenty": {srcnum: 20},
    "monopoly": {srcnum: 21},
    "palace": {srcnum: 22},
    "chapel": {srcnum: 23},
    "university": {srcnum: 24},
    "library": {srcnum: 25},
    "market": {srcnum: 26},
    "cardback": {srcnum: 27},
    "devcard": {srcnum: 28},
    "longestroute": {srcnum: 29},
    "largestarmy": {srcnum: 30},
    "robber": {srcnum: 31},
    "pirate": {srcnum: 32},
  }));
}
function initializeNone() {
  localStorage.setItem("names", JSON.stringify({
    rsrc1: "lime",
    rsrc2: "green",
    rsrc3: "yellow",
    rsrc4: "red",
    rsrc5: "gray",
    norsrc: "desert",
    anyrsrc: "bonus",
    space: "water",
  }));
  localStorage.setItem("sources", "[]");
  localStorage.setItem("variants", "{}");
  localStorage.setItem("imageinfo", "{}");
}
function initializeCustom() {
  let names = localStorage.getItem("customnames") || "{}";
  let sources = localStorage.getItem("customsources") || "[]";
  let variants = localStorage.getItem("customvariants") || "{}";
  let imageinfo = localStorage.getItem("customimageinfo") || "{}";
  localStorage.setItem("names", names);
  localStorage.setItem("sources", sources);
  localStorage.setItem("variants", variants);
  localStorage.setItem("imageinfo", imageinfo);
}
