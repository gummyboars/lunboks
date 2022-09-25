serverNames = {
  rsrc1: "lime",
  rsrc2: "green",
  rsrc3: "yellow",
  rsrc4: "red",
  rsrc5: "gray",
  norsrc: "desert",
  anyrsrc: "bonus",
  space: "water",
  gold: "gold",
};

assetPrefix = "islanders";
assetNames = [
  // Tiles
  "rsrc1tile",
  "rsrc2tile",
  "rsrc3tile",
  "rsrc4tile",
  "rsrc5tile",
  "norsrctile",
  "anyrsrctile",
  "discovertile",
  "randomizedtile",
  "spacetile",
  "castletile",
  "coast",
  "port",
  "rsrc1port",
  "rsrc2port",
  "rsrc3port",
  "rsrc4port",
  "rsrc5port",
  "randomizedport",
  "3port",
  // Cards
  "rsrc1card",
  "rsrc2card",
  "rsrc3card",
  "rsrc4card",
  "rsrc5card",
  "goldcard",
  "knight",
  "roadbuilding",
  "yearofplenty",
  "monopoly",
  "palace",
  "chapel",
  "university",
  "library",
  "market",
  "fastknight",
  "treason",
  "intrigue",
  // Other
  "devcard",
  "cardback",
  "longestroute",
  "largestarmy",
  "robber",
  "pirate",
  "costcard",
];

function initializeNames() {
  let overrides = JSON.parse(localStorage.getItem("islandersnames") || "{}");
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
  localStorage.setItem("islandersvariants", "{}");
  localStorage.setItem("islandersnames", JSON.stringify({
    rsrc1: "sulfur",
    rsrc2: "olivine",
    rsrc3: "water",
    rsrc4: "clay",
    rsrc5: "metal",
    norsrc: "desert",
    anyrsrc: "uranium",
    space: "space",
    gold: "gold",
  }));
  localStorage.setItem("islandersimageinfo", JSON.stringify({
    "rsrc1tile": {"src":"/islanders/images/sulfur.png"},
    "rsrc2tile": {"src":"/islanders/images/olivine.png"},
    "rsrc3tile": {"src":"/islanders/images/permafrost.png"},
    "rsrc4tile": {"src":"/islanders/images/clay.png"},
    "rsrc5tile": {"src":"/islanders/images/metal.png"},
    "rsrc1card": {"src":"/islanders/images/sulfurcard.png"},
    "rsrc2card": {"src":"/islanders/images/olivinecard.png"},
    "rsrc3card": {"src":"/islanders/images/watercard.png"},
    "rsrc4card": {"src":"/islanders/images/claycard.png"},
    "rsrc5card": {"src":"/islanders/images/metalcard.png"},
    "norsrctile": {"src":"/islanders/images/desert.png"},
    "spacetile": {"src":"/islanders/images/space.png"},
    "coast": {},
    "port": {},
    "rsrc1port": {"src":"/islanders/images/sulfurport.png"},
    "rsrc2port": {"src":"/islanders/images/olivineport.png"},
    "rsrc3port": {"src":"/islanders/images/waterport.png"},
    "rsrc4port": {"src":"/islanders/images/clayport.png"},
    "rsrc5port": {"src":"/islanders/images/metalport.png"},
    "3port": {"src":"/islanders/images/3port.png"},
    "knight": {"src":"/islanders/images/knight.png"},
    "roadbuilding": {"src":"/islanders/images/roadbuilding.png"},
    "yearofplenty": {"src":"/islanders/images/yearofplenty.png"},
    "monopoly": {"src":"/islanders/images/monopoly.png"},
    "palace": {"src":"/islanders/images/palace.png"},
    "chapel": {"src":"/islanders/images/chapel.png"},
    "university": {"src":"/islanders/images/university.png"},
    "library": {"src":"/islanders/images/library.png"},
    "market": {"src":"/islanders/images/market.png"},
    "cardback": {"src":"/islanders/images/cardback.png"},
    "devcard": {"src":"/islanders/images/devcard.png"},
    "longestroute": {"src":"/islanders/images/longestroad.png"},
    "largestarmy": {"src":"/islanders/images/largestarmy.png"},
    "robber": {"src":"/islanders/images/robber2.png"},
    "pirate": {"src":"/islanders/images/pirate.png"},
  }));
}
function initializeNone() {
  localStorage.setItem("islandersnames", JSON.stringify({
    rsrc1: "lime",
    rsrc2: "green",
    rsrc3: "yellow",
    rsrc4: "red",
    rsrc5: "gray",
    norsrc: "desert",
    anyrsrc: "bonus",
    space: "water",
    gold: "gold",
  }));
  localStorage.setItem("islandersvariants", "{}");
  localStorage.setItem("islandersimageinfo", "{}");
}
function initializeCustom() {
  let names = localStorage.getItem("islanderscustomnames") || "{}";
  let variants = localStorage.getItem("islanderscustomvariants") || "{}";
  let imageinfo = localStorage.getItem("islanderscustomimageinfo") || "{}";
  localStorage.setItem("islandersnames", names);
  localStorage.setItem("islandersvariants", variants);
  localStorage.setItem("islandersimageinfo", imageinfo);
}
