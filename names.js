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
};

function initializeImageData() {
  let newImages = {};
  for (imgName in imageInfo) {
    let rawData = localStorage.getItem(imgName);
    let imgData = JSON.parse(rawData || "{}");
    if (imgData && imgData.src != null) {
      newImages[imgName] = imgData;
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
