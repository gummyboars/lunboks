globalNames = {
  rsrc1: "sulfur",
  rsrc2: "olivine",
  rsrc3: "water",
  rsrc4: "clay",
  rsrc5: "metal",
  norsrc: "desert",
  space: "space",
};
imageInfo = {
  rsrc1: {"src": "/sulfur.png"},
  rsrc2: {"src": "/olivine.png"},
  rsrc3: {"src": "/permafrost.png"},
  rsrc4: {"src": "/clay.png"},
  rsrc5: {"src": "/metal.png"},
  rsrc1card: {"src": "/sulfurcard.png"},
  rsrc2card: {"src": "/olivinecard.png"},
  rsrc3card: {"src": "/watercard.png"},
  rsrc4card: {"src": "/claycard.png"},
  rsrc5card: {"src": "/metalcard.png"},
  norsrc: {"src": "/desert.png"},
  space: {"src": "/space.png"},
  spaceedgeleft: {},
  spaceedgeright: {},
  spacecorner: {},
  coast: {},
  port: {},
  rsrc1port: {"src": "/sulfurport.png"},
  rsrc2port: {"src": "/olivineport.png"},
  rsrc3port: {"src": "/waterport.png"},
  rsrc4port: {"src": "/clayport.png"},
  rsrc5port: {"src": "/metalport.png"},
  "3port": {"src": "/3port.png"},
  knight: {"src": "/knight.png"},
  roadbuilding: {"src": "/roadbuilding.png"},
  yearofplenty: {"src": "/yearofplenty.png"},
  monopoly: {"src": "/monopoly.png"},
  palace: {"src": "/palace.png"},
  chapel: {"src": "/chapel.png"},
  university: {"src": "/university.png"},
  library: {"src": "/library.png"},
  market: {"src": "/market.png"},
  cardback: {"src": "/cardback.png"},
  devcard: {"src": "/devcard.png"},
  longestroute: {"src": "/longestroad.png"},
  largestarmy: {"src": "/largestarmy.png"},
};

function initializeImageData() {
  let newImages = {};
  for (imgName in imageInfo) {
    let rawData = localStorage.getItem(imgName);
    let imgData = JSON.parse(rawData || "{}");
    if (imgData && imgData.src != null) {
      newImages[imgName] = imgData;
    } else {
      newImages[imgName] = {};
    }
  }
  for (imgName in newImages) {
    imageInfo[imgName] = newImages[imgName];
  }
}
function initializeNames() {
  let overrides = JSON.parse(localStorage.getItem("names") || "{}");
  if (!overrides) {
    return;
  }
  let newNames = {};
  for (let name in globalNames) {
    if (overrides[name]) {
      newNames[name] = overrides[name];
    }
  }
  for (let name in newNames) {
    globalNames[name] = newNames[name];
  }
}
function initializeSpace() {
  localStorage.setItem("rsrc1", '{"src": "/sulfur.png"}');
  localStorage.setItem("rsrc2", '{"src": "/olivine.png"}');
  localStorage.setItem("rsrc3", '{"src": "/permafrost.png"}');
  localStorage.setItem("rsrc4", '{"src": "/clay.png"}');
  localStorage.setItem("rsrc5", '{"src": "/metal.png"}');
  localStorage.setItem("rsrc1card", '{"src": "/sulfurcard.png"}');
  localStorage.setItem("rsrc2card", '{"src": "/olivinecard.png"}');
  localStorage.setItem("rsrc3card", '{"src": "/watercard.png"}');
  localStorage.setItem("rsrc4card", '{"src": "/claycard.png"}');
  localStorage.setItem("rsrc5card", '{"src": "/metalcard.png"}');
  localStorage.setItem("norsrc", '{"src": "/desert.png"}');
  localStorage.setItem("space", '{"src": "/space.png"}');
  localStorage.setItem("spaceedgeleft", '{}');
  localStorage.setItem("spaceedgeright", '{}');
  localStorage.setItem("spacecorner", '{}');
  localStorage.setItem("coast", '{}');
  localStorage.setItem("port", '{}');
  localStorage.setItem("rsrc1port", '{"src": "/sulfurport.png"}');
  localStorage.setItem("rsrc2port", '{"src": "/olivineport.png"}');
  localStorage.setItem("rsrc3port", '{"src": "/waterport.png"}');
  localStorage.setItem("rsrc4port", '{"src": "/clayport.png"}');
  localStorage.setItem("rsrc5port", '{"src": "/metalport.png"}');
  localStorage.setItem("3port", '{"src": "/3port.png"}');
  localStorage.setItem("knight", '{"src": "/knight.png"}');
  localStorage.setItem("roadbuilding", '{"src": "/roadbuilding.png"}');
  localStorage.setItem("yearofplenty", '{"src": "/yearofplenty.png"}');
  localStorage.setItem("monopoly", '{"src": "/monopoly.png"}');
  localStorage.setItem("palace", '{"src": "/palace.png"}');
  localStorage.setItem("chapel", '{"src": "/chapel.png"}');
  localStorage.setItem("university", '{"src": "/university.png"}');
  localStorage.setItem("library", '{"src": "/library.png"}');
  localStorage.setItem("market", '{"src": "/market.png"}');
  localStorage.setItem("cardback", '{"src": "/cardback.png"}');
  localStorage.setItem("devcard", '{"src": "/devcard.png"}');
  localStorage.setItem("longestroute", '{"src": "/longestroad.png"}');
  localStorage.setItem("largestarmy", '{"src": "/largestarmy.png"}');
}
