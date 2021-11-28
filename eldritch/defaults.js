radiusRatio = 1 / 29;
widthRatio = 1 / 9;
heightRatio = 2 / 45;
markerWidthRatio = radiusRatio;
markerHeightRatio = radiusRatio * 3 / 2;

connections = {
  Easttown: ["Downtown", "Rivertown"],
  Merchant: ["Northside", "Rivertown", "University", "Downtown"],
  FrenchHill: ["Rivertown", "University", "Southside"],
  Uptown: ["Southside", "University"],
  Downtown: ["Northside"],
};

locations = {
  Shop: {name: "Curiositie Shoppe", color: "orange", x: 0.2240, y: 0.5379},
  Newspaper: {name: "Newspaper", color: "orange", x: 0.1332, y: 0.5379},
  Train: {name: "Train Station", color: "orange", x: 0.0513, y: 0.4769},
  Bank: {name: "Bank", color: "white", x: 0.0513, y: 0.3668},
  Asylum: {name: "Asylum", color: "white", x: 0.0506, y: 0.2634},
  Square: {name: "Independence Square", color: "white", x: 0.0506, y: 0.1615},
  Roadhouse: {name: "Hibb's Roadhouse", color: "dimgray", x: 0.1467, y: 0.1392},
  Diner: {name: "Velma's Diner", color: "dimgray", x: 0.2044, y: 0.0543},
  Police: {name: "Police Station", color: "dimgray", x: 0.3004, y: 0.0543},
  Graveyard: {name: "Graveyard", color: "purple", x: 0.4310, y: 0.0543},
  Cave: {name: "Black Cave", color: "purple", x: 0.5233, y: 0.0543},
  Store: {name: "General Store", color: "purple", x: 0.5366, y: 0.1726},
  Witch: {name: "The Witch House", color: "steelblue", x: 0.6672, y: 0.0521},
  Lodge: {name: "Silver Twilight Lodge", color: "steelblue", x: 0.7193, y: 0.1466},
  House: {name: "Ma's Boarding House", color: "saddlebrown", x: 0.8457, y: 0.0513},
  Church: {name: "South Church", color: "saddlebrown", x: 0.9479, y: 0.0900},
  Society: {name: "Historical Society", color: "saddlebrown", x: 0.9479, y: 0.2068},
  Woods: {name: "Woods", color: "firebrick", x: 0.9472, y: 0.3259},
  Shoppe: {name: "Þe Old Magick Shoppe", color: "firebrick", x: 0.9323, y: 0.4606},
  Hospital: {name: "St. Mary's Hospital", color: "firebrick", x: 0.8162, y: 0.5387},
  Library: {name: "Library", color: "yellow", x: 0.7149, y: 0.4523},
  Administration: {name: "Administration", color: "yellow", x: 0.6714, y: 0.5387},
  Science: {name: "Science Building", color: "yellow", x: 0.5729, y: 0.5387},
  Unnamable: {name: "The Unnamable", color: "green", x: 0.4918, y: 0.4523},
  Docks: {name: "River Docks", color: "green", x: 0.4501, y: 0.5387},
  Isle: {name: "Unvisited Isle", color: "green", x: 0.3616, y: 0.5387},
};

streets = {
  Northside: {name: "Northside", color: "orange", x: 0.2180, y: 0.3952},
  Downtown: {name: "Downtown", color: "white", x: 0.2180, y: 0.2920},
  Easttown: {name: "Easttown", color: "dimgray", x: 0.3050, y: 0.1713},
  Rivertown: {name: "Rivertown", color: "purple", x: 0.3966, y: 0.2473},
  FrenchHill: {name: "French Hill", color: "steelblue", x: 0.6069, y: 0.2473},
  Southside: {name: "Southside", color: "saddlebrown", x: 0.8122, y: 0.2473},
  Uptown: {name: "Uptown", color: "firebrick", x: 0.8122, y: 0.3575},
  University: {name: "Miskatonic University", color: "yellow", x: 0.6069, y: 0.3575},
  Merchant: {name: "Merchant District", color: "green", x: 0.3966, y: 0.3575},
};

function renderDefaultToCanvas(cnv, width, height, assetName, variant) {
  if (assetName == "board") {
    return renderBoardToCanvas(cnv, width, height);
  }
  if (assetName == "Clue") {
    return renderTextCircle(cnv, "🔍", "#47BA1F", "black", 0.65);
  }
  if (characterNames.includes(assetName)) {
    return renderTextRectangle(cnv, assetName, "silver", "black");
  }
  if (monsterNames.includes(assetName)) {
    return renderTextRectangle(cnv, assetName, "black", "white");
  }
  if (monsterBacks.includes(assetName)) {
    return renderTextRectangle(cnv, assetName, "black", "white");
  }
  if (otherWorlds.includes(assetName)) {
    return renderOtherWorld(cnv, assetName, width, height);
  }
  if (assetName.startsWith("Gate ")) {
    return renderTextCircle(cnv, assetName.substring(5), "palegoldenrod", "black", 0.3);
  }
  if (extraNames.includes(assetName)) {
    let bgColor = {"Outskirts": "purple", "Sky": "green", "Lost": "yellow"}[assetName];
    return renderTextRectangle(cnv, assetName, bgColor, "black");
  }
  throw "unknown asset " + assetName;
}

function renderBoardToCanvas(cnv, width, height) {
  ctx = cnv.getContext("2d");
  ctx.fillStyle = "#D2A253";
  ctx.fillRect(0, 0, width, height);
  for (let conn in connections) {
    for (let dest of connections[conn]) {
      drawConnection(ctx, streets[conn], streets[dest], cnv.width);
    }
  }
  for (let loc in locations) {
    for (let street in streets) {
      if (streets[street].color == locations[loc].color) {
        drawConnection(ctx, streets[street], locations[loc], cnv.width);
      }
    }
    drawLocation(ctx, locations[loc], cnv.width);
  }
  for (let street in streets) {
    drawStreet(ctx, streets[street], cnv.width);
  }
}

function initializeDefaults() {
  let assets = document.getElementById("defaultassets");
  let ctx;
  let aspectRatio = 1.7;
  // let w = window.innerWidth;
  // let h = aspectRatio * window.innerHeight;
  let desiredWidth = document.documentElement.clientWidth * 0.8;
  let desiredHeight = document.documentElement.clientHeight * 0.9;
  let width, height;
  if (desiredHeight * aspectRatio > desiredWidth) {
    width = desiredWidth;
    height = desiredWidth / aspectRatio;
  } else {
    height = desiredHeight;
    width = desiredHeight * aspectRatio;
  }
  let board = document.createElement("CANVAS");
  board.width = width;
  board.height = height;
  ctx = board.getContext("2d");
  ctx.fillStyle = "#D2A253";
  ctx.fillRect(0, 0, width, height);
  for (let conn in connections) {
    for (let dest of connections[conn]) {
      drawConnection(ctx, streets[conn], streets[dest], board.width);
    }
  }
  for (let loc in locations) {
    for (let street in streets) {
      if (streets[street].color == locations[loc].color) {
        drawConnection(ctx, streets[street], locations[loc], board.width);
      }
    }
    drawLocation(ctx, locations[loc], board.width);
  }
  for (let street in streets) {
    drawStreet(ctx, streets[street], board.width);
  }
  board.id = "defaultboard";
  assets.appendChild(board);
  let cfgs = [
    {names: characterNames, color: "silver"},
    {names: commonNames, color: "darkkhaki"},
    {names: uniqueNames, color: "indianred"},
    {names: spellNames, color: "mediumpurple"},
    {names: skillNames, color: "gold"},
    {names: allyNames, color: "darkorange"},
    {names: abilityNames, color: "sienna"},
  ];
  for (let cfg of cfgs) {
    for (let name of cfg.names) {
      let asset = createTextRectangle(name, cfg.color, board.width, cfg.fgColor);
      asset.id = "default" + name;
      assets.appendChild(asset);
    }
  }
  for (let name of monsterNames) {
    let asset = createTextSquare(name, "black", board.width, "white");
    asset.id = "default" + name;
    assets.appendChild(asset);
    asset = createTextSquare(name + " back", "black", board.width, "white");
    asset.id = "default" + name + "back";
    assets.appendChild(asset);
  }
  for (let world of otherWorlds) {
    let asset = createTextCircle(world, "palegoldenrod", board.width, "black", 0.3);
    asset.id = "default" + "Gate " + world;
    assets.appendChild(asset);
    asset = createOtherWorld(world, board.width);
    asset.id = "default" + world;
    assets.appendChild(asset);
  }
  let clue = createTextCircle("🔍", "#47BA1F", board.width, "black", 0.65);
  clue.id = "defaultClue";
  assets.appendChild(clue);
  let outskirts = createTextSquare("Outskirts", "purple", board.width, "black");
  outskirts.id = "defaultOutskirts";
  assets.appendChild(outskirts);
  let sky = createTextSquare("Sky", "green", board.width, "black");
  sky.id = "defaultSky";
  assets.appendChild(sky);
  let lost = createTextSquare("Lost", "yellow", board.width, "black");
  lost.id = "defaultLost";
  assets.appendChild(lost);
}

function getTextSize(ctx, text, maxWidth, maxHeight) {
  ctx.font = "72px sans-serif";
  let alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
  let widthMeasure = ctx.measureText(text);
  let heightMeasure = ctx.measureText(alphabet);
  let textHeight;
  if (heightMeasure.emHeightAscent) {
    textHeight = heightMeasure.emHeightAscent + heightMeasure.emHeightDescent;
  } else if (heightMeasure.fontBoundingBoxAscent) {
    textHeight = heightMeasure.fontBoundingBoxAscent + heightMeasure.fontBoundingBoxDescent;
  } else {
    textHeight = heightMeasure.actualBoundingBoxAscent + heightMeasure.actualBoundingBoxDescent;
  }
  let shrinkRatio = Math.min(maxWidth / widthMeasure.width, maxHeight / textHeight);
  return Math.floor(72 * shrinkRatio);
}

function drawConnection(ctx, src, dest, boardWidth) {
  ctx.save();
  ctx.strokeStyle = "black";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(src.x * boardWidth, src.y * boardWidth);
  ctx.lineTo(dest.x * boardWidth, dest.y * boardWidth);
  ctx.stroke();
  ctx.restore();
}

function drawLocation(ctx, data, boardWidth) {
  let width = boardWidth * 2 * radiusRatio;
  let height = width;
  ctx.save();
  ctx.translate(boardWidth * data.x, boardWidth * data.y);
  ctx.beginPath();
  ctx.arc(0, 0, width / 2, 0, 2 * Math.PI, true);
  ctx.closePath();
  ctx.fillStyle = data.color;
  ctx.fill();
  ctx.fillStyle = "white";
  ctx.fillRect(-width / 2, height / 3, width, height / 6);
  let newFontSize = getTextSize(ctx, data.name, width, height / 6);
  ctx.font = newFontSize + "px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "black";
  ctx.fillText(data.name, 0, 5 * height / 12);
  ctx.restore();
}

function drawStreet(ctx, data, boardWidth) {
  let width = boardWidth * widthRatio;
  let height = boardWidth * heightRatio;
  ctx.save();
  ctx.translate(boardWidth * data.x, boardWidth * data.y);
  ctx.fillStyle = data.color;
  ctx.fillRect(-width/2, -height/2, width, height);
  ctx.restore();
}

function createTextRectangle(name, bgColor, boardWidth, fgColor) {
  let cnv = document.createElement("CANVAS");
  cnv.width = 3 * boardWidth * markerWidthRatio;
  cnv.height = 3 * boardWidth * markerHeightRatio;
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.fillStyle = bgColor;
  ctx.fillRect(0, 0, cnv.width, cnv.height);
  let fontSize = getTextSize(ctx, name, cnv.width, cnv.height);
  ctx.font = fontSize + "px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  if (fgColor != null) {
    ctx.fillStyle = fgColor;
  } else {
    ctx.fillStyle = "black";
  }
  ctx.fillText(name, cnv.width/2, cnv.height/2);
  ctx.restore();
  return cnv;
}

function createTextSquare(name, bgColor, boardWidth, fgColor) {
  let cnv = document.createElement("CANVAS");
  cnv.width = boardWidth / 12;
  cnv.height = boardWidth / 12;
  renderTextRectangle(cnv, name, bgColor, fgColor);
  return cnv;
}

function renderTextRectangle(cnv, name, bgColor, fgColor) {
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.fillStyle = bgColor;
  ctx.fillRect(0, 0, cnv.width, cnv.height);
  let fontSize = getTextSize(ctx, name, cnv.width, cnv.height);
  ctx.font = fontSize + "px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  if (fgColor != null) {
    ctx.fillStyle = fgColor;
  } else {
    ctx.fillStyle = "black";
  }
  ctx.fillText(name, cnv.width/2, cnv.height/2);
  ctx.restore();
}

function createTextCircle(name, bgColor, boardWidth, fgColor, heightFactor) {
  let cnv = document.createElement("CANVAS");
  let radius = boardWidth * radiusRatio;
  cnv.width = 2 * radius;
  cnv.height = 2 * radius;
  renderTextCircle(cnv, name, bgColor, fgColor, heightFactor);
  return cnv;
}

function renderTextCircle(cnv, name, bgColor, fgColor, heightFactor) {
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.fillStyle = bgColor;
  ctx.beginPath();
  ctx.arc(cnv.width/2, cnv.width/2, cnv.width/2, 0, 2 * Math.PI);
  ctx.fill();
  let fontSize = getTextSize(ctx, name, cnv.width, heightFactor * cnv.height);
  ctx.font = fontSize + "px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = fgColor;
  ctx.fillText(name, cnv.width/2, cnv.width/2);
  ctx.restore();
}

function createOtherWorld(name, boardWidth) {
  let cnv = document.createElement("CANVAS");
  let worldSize = boardWidth / 8;
  cnv.width = worldSize;
  cnv.height = worldSize;
  renderOtherWorld(cnv, name, cnv.width, cnv.height);
  return cnv;
}

function renderOtherWorld(cnv, name, width, height) {
  let colors = {
    "Abyss": ["red", "blue"],
    "Another Dimension": ["blue", "green", "red", "gold"],
    "City": ["green", "gold"],
    "Great Hall": ["blue", "green"],
    "Plateau": ["red", "green"],
    "Sunken City": ["red", "gold"],
    "Dreamlands": ["blue", "green", "red", "gold"],
    "Pluto": ["blue", "gold"],
  };
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.fillStyle = "palegoldenrod";
  ctx.fillRect(0, 0, width, height);
  let fontSize = getTextSize(ctx, name, width * 3 / 4, height / 4);
  ctx.font = fontSize + "px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "black";
  ctx.fillText(name, width / 2, height / 8);
  ctx.strokeStyle = "black";
  ctx.moveTo(0, height / 4);
  ctx.lineTo(width, height / 4);
  ctx.stroke();
  ctx.moveTo(width / 2, height / 4);
  ctx.lineTo(width / 2, height);
  ctx.stroke();
  for (let [idx, color] of colors[name].entries()) {
    let x, y;
    if (idx < 2) {
      x = width * 15 / 16;
    } else {
      x = width * 14 / 16;
    }
    y = (idx % 2) * height / 16;
    ctx.fillStyle = color;
    ctx.fillRect(x, y, width / 16, height / 16);
  }
  ctx.restore();
}
