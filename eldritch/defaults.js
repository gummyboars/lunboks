radiusRatio = 1 / 29;
widthRatio = 2 / 39;
heightRatio = 1 / 6;

connections = {
  Easttown: ["Downtown", "Rivertown"],
  Merchant: ["Northside", "Rivertown", "University", "Downtown"],
  FrenchHill: ["Rivertown", "University", "Southside"],
  Uptown: ["Southside", "University"],
  Downtown: ["Northside"],
};

locations = {
  Shop: {name: "Curiositie Shoppe", color: "orange", y: 0.2158, x: 0.0857},
  Newspaper: {name: "Newspaper", color: "orange", y: 0.1266, x: 0.0861},
  Train: {name: "Train Station", color: "orange", y: 0.0444, x: 0.1983},
  Bank: {name: "Bank", color: "white", y: 0.0439, x: 0.3768},
  Asylum: {name: "Asylum", color: "white", y: 0.0434, x: 0.5521},
  Square: {name: "Independence Square", color: "white", y: 0.0430, x: 0.7267},
  Roadhouse: {name: "Hibb's Roadhouse", color: "dimgray", y: 0.1585, x: 0.7306},
  Diner: {name: "Velma's Diner", color: "dimgray", y: 0.1577, x: 0.9088},
  Police: {name: "Police Station", color: "dimgray", y: 0.2518, x: 0.9100},
  Graveyard: {name: "Graveyard", color: "purple", y: 0.3928, x: 0.9100},
  Cave: {name: "Black Cave", color: "purple", y: 0.4834, x: 0.9115},
  Store: {name: "General Store", color: "purple", y: 0.4769, x: 0.7085},
  WitchHouse: {name: "The Witch House", color: "steelblue", y: 0.6174, x: 0.9131},
  Lodge: {name: "Silver Twilight Lodge", color: "steelblue", y: 0.6682, x: 0.7520},
  House: {name: "Ma's Boarding House", color: "saddlebrown", y: 0.7745, x: 0.9147},
  Church: {name: "South Church", color: "saddlebrown", y: 0.9094, x: 0.8483},
  Society: {name: "Historical Society", color: "saddlebrown", y: 0.9344, x: 0.6493},
  Woods: {name: "Woods", color: "firebrick", y: 0.9348, x: 0.4479},
  Shoppe: {name: "Þe Old Magick Shoppe", color: "firebrick", y: 0.9201, x: 0.2180},
  Hospital: {name: "St. Mary's Hospital", color: "firebrick", y: 0.8045, x: 0.0853},
  Library: {name: "Library", color: "yellow", y: 0.6525, x: 0.3515},
  Administration: {name: "Administration", color: "yellow", y: 0.6844, x: 0.1848},
  Science: {name: "Science Building", color: "yellow", y: 0.5628, x: 0.0857},
  Unnamable: {name: "The Unnamable", color: "green", y: 0.4824, x: 0.2662},
  Docks: {name: "River Docks", color: "green", y: 0.4404, x: 0.0861},
  Isle: {name: "Unvisited Isle", color: "green", y: 0.3530, x: 0.0869},
};

streets = {
  Northside: {name: "Northside", color: "orange", y: 0.1978, x: 0.2970},
  Downtown: {name: "Downtown", color: "white", y: 0.1964, x: 0.5379},
  Easttown: {name: "Easttown", color: "dimgray", y: 0.3041, x: 0.6580},
  Rivertown: {name: "Rivertown", color: "purple", y: 0.3946, x: 0.6382},
  FrenchHill: {name: "French Hill", color: "steelblue", y: 0.5924, x: 0.6477},
  Southside: {name: "Southside", color: "saddlebrown", y: 0.8087, x: 0.6706},
  Uptown: {name: "Uptown", color: "firebrick", y: 0.8073, x: 0.4337},
  University: {name: "Miskatonic University", color: "yellow", y: 0.5735, x: 0.3918},
  Merchant: {name: "Merchant District", color: "green", y: 0.3956, x: 0.3894},
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
  if (assetName.startsWith("Terror")) {
    return renderTextCircle(cnv, assetName.substring(6), "white", "black", 0.7);
  }
  if (assetName == "Doom") {
    return renderTextCircle(cnv, "👁️", "royalblue", "black", 0.8);
  }
  if (assetName == "Seal") {
    renderTextCircle(cnv, "", "royalblue", "black");
    let ctx = cnv.getContext("2d");
    ctx.save();
    ctx.globalCompositeOperation = "destination-out";
    renderTextCircle(cnv, "⭐", "rgba(0, 0, 0, 0)", "black", 0.65);
    ctx.globalCompositeOperation = "destination-over";
    renderTextCircle(cnv, "", "silver", "black");
    ctx.globalCompositeOperation = "source-over";
    renderTextCircle(cnv, "👁️", "rgba(0, 0, 0, 0)", "black", 0.35);
    ctx.restore();
    return;
  }
  if (assetName == "Activity") {
    return renderTextHexagon(cnv, variant, "#002000", "red");
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
  if (assetName.endsWith(" focus")) {
    let focus = characterData[assetName.substring(0, assetName.length - 6)]["focus"];
    return renderTextRectangle(cnv, "Focus: " + focus, "silver", "black");
  }
  if (assetName.endsWith(" home")) {
    let home = characterData[assetName.substring(0, assetName.length - 5)]["home"];
    return renderTextRectangle(cnv, home, "silver", "black");
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
  if (assetName == "Gate Back") {
    return renderTextCircle(cnv, "Gate", "palegoldenrod", "black", 0.3);
  }
  if (assetName == "Gate Card") {
    return renderTextRectangle(cnv, assetName, "palegoldenrod", "black");
  }
  if (assetName == "Mythos Card") {
    return renderTextRectangle(cnv, "Mythos", "white", "black");
  }
  if (assetName.startsWith("Gate ")) {
    return renderTextCircle(cnv, assetName.substring(5), "palegoldenrod", "black", 0.3);
  }
  if (commonNames.includes(assetName) || assetName == "common") {
    return renderTextRectangle(cnv, assetName, "darkkhaki", "black");
  }
  if (uniqueNames.includes(assetName) || assetName == "unique") {
    return renderTextRectangle(cnv, assetName, "indianred", "black");
  }
  if (spellNames.includes(assetName) || assetName == "spells") {
    return renderTextRectangle(cnv, assetName, "mediumpurple", "black");
  }
  if (skillNames.includes(assetName) || assetName == "skills") {
    return renderTextRectangle(cnv, assetName, "gold", "black");
  }
  if (allyNames.includes(assetName) || assetName == "allies") {
    return renderTextRectangle(cnv, assetName, "darkorange", "black");
  }
  if (abilityNames.includes(assetName)) {
    return renderTextRectangle(cnv, assetName, "wheat", "black");
  }
  if (["Deputy", "Deputy's Revolver", "Patrol Wagon"].includes(assetName)) {
    return renderTextRectangle(cnv, assetName, "dimgray", "black");
  }
  if (assetName == "Lodge Membership") {
    return renderTextRectangle(cnv, assetName, "steelblue", "black");
  }
  if (assetName == "Retainer") {
    return renderTextRectangle(cnv, assetName, "yellowgreen", "black");
  }
  if (assetName == "Blessing") {
    return renderTextRectangle(cnv, assetName, "lightblue", "black");
  }
  if (assetName == "Curse") {
    return renderTextRectangle(cnv, assetName, "darkred", "black");
  }
  if (assetName == "Bank Loan") {
    return renderTextRectangle(cnv, assetName, "white", "black");
  }
  if (gateCards.includes(assetName)) {
    if (assetName.length < 6 || assetName < "Gate13") {
      return renderTextRectangle(cnv, assetName, "skyblue", "black");
    }
    if (assetName < "Gate25") {
      return renderTextRectangle(cnv, assetName, "yellowgreen", "black");
    }
    if (assetName < "Gate37") {
      return renderTextRectangle(cnv, assetName, "firebrick", "black");
    }
    return renderTextRectangle(cnv, assetName, "khaki", "black");
  }
  if (mythosCards.includes(assetName)) {
    return renderTextRectangle(cnv, assetName, "white", "black");
  }
  if (ancientOnes.includes(assetName)) {
    return renderTextRectangle(cnv, assetName, "midnightblue", "white");
  }
  if (assetName.endsWith(" worshippers") || assetName.endsWith(" slumber")) {
    return renderTextRectangle(cnv, assetName, "midnightblue", "white");
  }
  if (assetName.endsWith(" max")) {
    return renderTextCircle(cnv, ancientOneDoomMax[assetName.substring(0, assetName.length - 4)], "midnightblue", "white", 0.7);
  }
  if (encounterCardNames.includes(assetName)) {
    for (let neighborhood of neighborhoodNames) {
      if (assetName.startsWith(neighborhood)) {
        return renderTextRectangle(cnv, assetName, streets[neighborhood].color, "black");
      }
    }
    throw new Error("unknown neighborhood for " + assetName);
  }
  if (extraNames.includes(assetName)) {
    let bgColor = {"Outskirts": "purple", "Sky": "green", "Lost": "yellow"}[assetName];
    return renderTextRectangle(cnv, assetName, bgColor, "black");
  }
  throw new Error("unknown asset " + assetName);
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
  if (width/2 <= border) {
    return;  // Safeguard: ctx.arc errors out if radius is negative.
  }
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

    let sliderValue = characterData[charName]["sliders"][idx];
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
  let width = boardHeight * 2 * radiusRatio;
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
  let height = boardHeight * widthRatio;
  let width = boardWidth * heightRatio;
  ctx.save();
  ctx.translate(boardWidth * data.x, boardHeight * data.y);
  ctx.fillStyle = data.color;
  ctx.fillRect(-width/2, -height/2, width, height);
  ctx.restore();
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

function renderTextHexagon(cnv, name, bgColor, shadowColor) {
  let ctx = cnv.getContext("2d");
  ctx.save();
  ctx.fillStyle = bgColor;
  ctx.beginPath();
  ctx.moveTo(cnv.width / 4, 0);
  ctx.lineTo(cnv.width * 3 / 4, 0);
  ctx.lineTo(cnv.width, cnv.height / 2);
  ctx.lineTo(cnv.width * 3 / 4, cnv.height);
  ctx.lineTo(cnv.width / 4, cnv.height);
  ctx.lineTo(0, cnv.height / 2);
  ctx.fill();
  let fontSize = getTextSize(ctx, name, cnv.width, cnv.height);
  ctx.font = fontSize + "px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.shadowColor = shadowColor;
  ctx.shadowBlur = cnv.width/12;
  ctx.fillStyle = "white";
  ctx.fillText(name, cnv.width/2, cnv.height/2);
  ctx.restore();
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
