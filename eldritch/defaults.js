radiusRatio = 1 / 29;
widthRatio = 2 / 39;
heightRatio = 1 / 6;
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
  Shop: {name: "Curiositie Shoppe", color: "orange", x: 0.2158, y: 0.9143},
  Newspaper: {name: "Newspaper", color: "orange", x: 0.1266, y: 0.9139},
  Train: {name: "Train Station", color: "orange", x: 0.0444, y: 0.8017},
  Bank: {name: "Bank", color: "white", x: 0.0439, y: 0.6232},
  Asylum: {name: "Asylum", color: "white", x: 0.0434, y: 0.4479},
  Square: {name: "Independence Square", color: "white", x: 0.0430, y: 0.2733},
  Roadhouse: {name: "Hibb's Roadhouse", color: "dimgray", x: 0.1585, y: 0.2694},
  Diner: {name: "Velma's Diner", color: "dimgray", x: 0.1577, y: 0.0912},
  Police: {name: "Police Station", color: "dimgray", x: 0.2518, y: 0.0900},
  Graveyard: {name: "Graveyard", color: "purple", x: 0.3928, y: 0.0900},
  Cave: {name: "Black Cave", color: "purple", x: 0.4834, y: 0.0885},
  Store: {name: "General Store", color: "purple", x: 0.4769, y: 0.2915},
  WitchHouse: {name: "The Witch House", color: "steelblue", x: 0.6174, y: 0.0869},
  Lodge: {name: "Silver Twilight Lodge", color: "steelblue", x: 0.6682, y: 0.2480},
  House: {name: "Ma's Boarding House", color: "saddlebrown", x: 0.7745, y: 0.0853},
  Church: {name: "South Church", color: "saddlebrown", x: 0.9094, y: 0.1517},
  Society: {name: "Historical Society", color: "saddlebrown", x: 0.9344, y: 0.3507},
  Woods: {name: "Woods", color: "firebrick", x: 0.9348, y: 0.5521},
  Shoppe: {name: "Þe Old Magick Shoppe", color: "firebrick", x: 0.9201, y: 0.7820},
  Hospital: {name: "St. Mary's Hospital", color: "firebrick", x: 0.8045, y: 0.9147},
  Library: {name: "Library", color: "yellow", x: 0.6525, y: 0.6485},
  Administration: {name: "Administration", color: "yellow", x: 0.6844, y: 0.8152},
  Science: {name: "Science Building", color: "yellow", x: 0.5628, y: 0.9143},
  Unnamable: {name: "The Unnamable", color: "green", x: 0.4824, y: 0.7338},
  Docks: {name: "River Docks", color: "green", x: 0.4404, y: 0.9139},
  Isle: {name: "Unvisited Isle", color: "green", x: 0.3530, y: 0.9131},
};

streets = {
  Northside: {name: "Northside", color: "orange", x: 0.1978, y: 0.7030},
  Downtown: {name: "Downtown", color: "white", x: 0.1964, y: 0.4621},
  Easttown: {name: "Easttown", color: "dimgray", x: 0.3041, y: 0.3420},
  Rivertown: {name: "Rivertown", color: "purple", x: 0.3946, y: 0.3618},
  FrenchHill: {name: "French Hill", color: "steelblue", x: 0.5924, y: 0.3523},
  Southside: {name: "Southside", color: "saddlebrown", x: 0.8087, y: 0.3294},
  Uptown: {name: "Uptown", color: "firebrick", x: 0.8073, y: 0.5663},
  University: {name: "Miskatonic University", color: "yellow", x: 0.5735, y: 0.6082},
  Merchant: {name: "Merchant District", color: "green", x: 0.3956, y: 0.6106},
};

function renderDefaultToCanvas(cnv, width, height, assetName, variant) {
  if (assetName == "board") {
    return renderBoardToCanvas(cnv, width, height);
  }
  if (assetName == "Clue") {
    return renderTextCircle(cnv, "🔍", "#47BA1F", "black", 0.65);
  }
  if (assetName == "Dollar") {
    return renderTextRectangle(cnv, "💵", "rgba(0, 0, 0, 0)", "black");
  }
  if (assetName == "Stamina") {
    return renderTextRectangle(cnv, "❤️", "rgba(0, 0, 0, 0)", "black");
  }
  if (assetName == "Sanity") {
    let ctx = cnv.getContext("2d");
    ctx.save();
    ctx.filter = "hue-rotate(225deg)";
    renderTextRectangle(cnv, "🧠", "rgba(0, 0, 0, 0)", "black");
    ctx.restore();
    return;
  }
  if (assetName == "Slider") {
    return renderSlider(cnv, width, height);
  }
  if (assetName == "statsbg") {
    return renderTextRectangle(cnv, "", "silver", "black");
  }
  if (characterNames.includes(assetName)) {
    return renderTextRectangle(cnv, assetName, "silver", "black");
  }
  if (assetName.endsWith(" sliders")) {
    return renderSliders(cnv, assetName.substring(0, assetName.length - 8));
  }
  if (assetName.endsWith(" title")) {
    return renderTextRectangle(cnv, assetName.substring(0, assetName.length - 5), "silver", "black");
  }
  if (assetName.endsWith(" picture")) {
    return renderTextRectangle(cnv, assetName.substring(0, assetName.length - 8), "silver", "black");
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
      drawConnection(ctx, streets[conn], streets[dest], cnv.width, cnv.height);
    }
  }
  for (let loc in locations) {
    for (let street in streets) {
      if (streets[street].color == locations[loc].color) {
        drawConnection(ctx, streets[street], locations[loc], cnv.width, cnv.height);
      }
    }
    drawLocation(ctx, locations[loc], cnv.width, cnv.height);
  }
  for (let street in streets) {
    drawStreet(ctx, streets[street], cnv.width, cnv.height);
  }
}

function renderSlider(cnv, width, height) {
  let border = 2;
  let ctx = cnv.getContext("2d");
  ctx.lineWidth = border;
  ctx.beginPath();
  ctx.moveTo(width - border, height/2);
  ctx.lineTo(width - border, width/2);
  ctx.arc(width/2, width/2, width/2 - border, 0, Math.PI, true);
  ctx.lineTo(border, height/2);
  ctx.strokeStyle = "blue";
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(border, height/2);
  ctx.lineTo(border, height - width/2);
  ctx.arc(width/2, height - width/2, width/2 - border, Math.PI, 2*Math.PI, true);
  ctx.lineTo(width - border, height/2);
  ctx.strokeStyle = "red";
  ctx.stroke();
}

function renderSliders(cnv, charName) {
  let ctx = cnv.getContext("2d");
  ctx.fillStyle = "cornsilk";
  ctx.fillRect(0, 0, cnv.width, cnv.height);
  for (let [idx, name] of ["SPEED", "SNEAK", "FIGHT", "WILL", "LORE", "LUCK"].entries()) {
    let fontSize = getTextSize(ctx, "SPEED", 2 * cnv.width / 11, cnv.height / 8);
    ctx.font = fontSize + "px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "black";

    let numSpacesAbove = 1 + ((idx - idx % 2) / 2) * 0.5;
    let textY = (numSpacesAbove + idx) * cnv.height / 8;
    let textX = 1.25 * cnv.width / 11;
    ctx.fillText(name, textX, textY);

    let sliderValue = characterSliders[charName][idx];
    let sliderIncrement = (idx % 2 == 0) ? 1 : -1;
    let xoff = (idx % 4 == 2 || idx % 4 == 3) ? 2 : 1;
    for (let j = 1; j < 5; j++) {
      if (idx % 2 == 0) {
        ctx.fillStyle = "blue";
      } else {
        ctx.fillStyle = "red";
      }
      ctx.font = "bold " + fontSize + "px sans-serif";
      textX = (2 * j + xoff) * cnv.width / 11;
      ctx.fillText(sliderValue, textX, textY);
      sliderValue += sliderIncrement;
    }
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
      drawConnection(ctx, streets[conn], streets[dest], board.width, board.width / aspectRatio);
    }
  }
  for (let loc in locations) {
    for (let street in streets) {
      if (streets[street].color == locations[loc].color) {
        drawConnection(ctx, streets[street], locations[loc], board.width, board.width / aspectRatio);
      }
    }
    drawLocation(ctx, locations[loc], board.width, board.width / aspectRatio);
  }
  for (let street in streets) {
    drawStreet(ctx, streets[street], board.width, board.width / aspectRatio);
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

function drawConnection(ctx, src, dest, boardWidth, boardHeight) {
  ctx.save();
  ctx.strokeStyle = "black";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(src.x * boardWidth, src.y * boardHeight);
  ctx.lineTo(dest.x * boardWidth, dest.y * boardHeight);
  ctx.stroke();
  ctx.restore();
}

function drawLocation(ctx, data, boardWidth, boardHeight) {
  let width = boardWidth * 2 * radiusRatio;
  let height = width;
  ctx.save();
  ctx.translate(boardWidth * data.x, boardHeight * data.y);
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

function drawStreet(ctx, data, boardWidth, boardHeight) {
  let width = boardWidth * widthRatio;
  let height = boardHeight * heightRatio;
  ctx.save();
  ctx.translate(boardWidth * data.x, boardHeight * data.y);
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
