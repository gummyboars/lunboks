hexWidth = tileWidth;
hexHeight = tileHeight;
function initializeDefaults() {
  let assets = document.getElementById("defaultassets");
  let ctx;
  let resourceDatas = [
    {name: "rsrc1", color: "#95B900", text: "🐑"},
    {name: "rsrc2", color: "#2E9A35", text: "🌲"},
    {name: "rsrc3", color: "#F2C024", text: "🌾"},
    {name: "rsrc4", color: "#DE6B2B", text: "🧱"},
    {name: "rsrc5", color: "#A7ADA9", text: "⛰️"},
    {name: "norsrc", color: "#D8D393", text: "🌵"},
    {name: "anyrsrc", color: ["#B8860B", "#0000CD"]},
    {name: "space", color: "#56A4D8"},
  ];
  let devDatas = [
    {name: "knight", text: "💂", bottomText: "knight"},
    {name: "roadbuilding", text: "🛤️", bottomText: "2 roads"},
    {name: "yearofplenty", text: "🎴", bottomText: "2 cards"},
    {name: "monopoly", text: "🧲", bottomText: "monopoly"},
    {name: "palace", text: "⛲", bottomText: "1 point"},
    {name: "chapel", text: "⛲", bottomText: "1 point"},
    {name: "university", text: "⛲", bottomText: "1 point"},
    {name: "library", text: "⛲", bottomText: "1 point"},
    {name: "market", text: "⛲", bottomText: "1 point"},
  ];
  for (let resourceData of resourceDatas) {
    let tile = createHex(resourceData.color, "default" + resourceData.name + "tile", resourceData.text);
    assets.appendChild(tile);
    let card = createCard(resourceData.color, "default" + resourceData.name + "card", cardWidth, cardHeight, resourceData.text);
    assets.appendChild(card);
    let port = createPort(resourceData.color, "default" + resourceData.name + "port", "2:1");
    assets.appendChild(port);
  }
  for (let devData of devDatas) {
    let dev = createCard("#9D6BBB", "default" + devData.name, cardWidth, cardHeight, devData.text, devData.bottomText);
    assets.appendChild(dev);
  }
  let threeport = createPort("white", "default3port", "3:1");
  assets.appendChild(threeport);
  let longestRoute = createCard("green", "defaultlongestroute", cardHeight * 4 / 5, cardHeight, "Route");
  assets.appendChild(longestRoute);
  let largestArmy = createCard("indianred", "defaultlargestarmy", cardHeight * 4 / 5, cardHeight, "Army");
  assets.appendChild(largestArmy);

  let costCard = document.createElement("CANVAS");
  costCard.width = cardHeight * 5 / 6;
  costCard.height = cardHeight;
  costCard.id = "defaultcostcard";
  ctx = costCard.getContext("2d");
  ctx.save();
  ctx.fillStyle = "#C8B8D0";
  ctx.fillRect(0, 0, costCard.width, costCard.height);
  ctx.translate(costCard.width / 2, costCard.height / 2);
  ctx.fillStyle = "black";
  ctx.textAlign = "start";
  ctx.textBaseline = "middle";
  let textSize = getTextSize(ctx, "🌾🌾⛰️⛰️⛰️", costCard.width * 7 / 10, costCard.height / 5);
  ctx.font = textSize + "px sans-serif";
  ctx.fillText("🌲🧱", costCard.width * -9 / 20, costCard.height * -3 / 8);
  ctx.fillText("🐑🌲🌾🧱", costCard.width * -9 / 20, costCard.height * -1 / 8);
  ctx.fillText("🌾🌾⛰️⛰️⛰️", costCard.width * -9 / 20, costCard.height * 1 / 8);
  ctx.fillText("🐑🌾⛰️", costCard.width * -9 / 20, costCard.height * 3 / 8);
  ctx.fillRect(costCard.width * 9 / 20 - 68, costCard.height * -3 / 8 - 5, 68, 10);
  ctx.beginPath();
  let radius = 8;
  let pieceX = costCard.width * 9 / 20 - radius;
  let pieceY = costCard.height * -1 / 8;
  ctx.moveTo(pieceX - radius, pieceY + radius * 3/2);
  ctx.lineTo(pieceX + radius, pieceY + radius * 3/2);
  ctx.lineTo(pieceX + radius, pieceY - radius * 1/2);
  ctx.lineTo(pieceX, pieceY - radius * 3/2);
  ctx.lineTo(pieceX - radius, pieceY - radius * 1/2);
  ctx.closePath();
  ctx.fill();
  radius = 13;
  pieceX = costCard.width * 9 / 20 - radius;
  pieceY = costCard.height * 1 / 8;
  ctx.beginPath();
  ctx.moveTo(pieceX - radius, pieceY + radius);
  ctx.lineTo(pieceX + radius, pieceY + radius);
  ctx.lineTo(pieceX + radius, pieceY - radius/2);
  ctx.lineTo(pieceX + radius/2, pieceY - radius);
  ctx.lineTo(pieceX, pieceY - radius/2);
  ctx.lineTo(pieceX, pieceY);
  ctx.lineTo(pieceX - radius, pieceY);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
  ctx.save();
  radius = 20;
  ctx.translate(costCard.width * 19 / 20 - radius, costCard.height * 7 / 8 - radius * 3 / 4);
  createDevCardBack(ctx, radius, radius * 3 / 2, false);
  ctx.restore();
  assets.appendChild(costCard);

  let portbase = document.createElement("CANVAS");
  portbase.width = hexWidth;
  portbase.height = hexHeight;
  portbase.id = "defaultport";
  ctx = portbase.getContext("2d");
  ctx.clearRect(0, 0, cardWidth, cardHeight);
  ctx.save();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "black";
  ctx.beginPath();
  ctx.moveTo(hexWidth / 4, hexHeight);
  ctx.lineTo(hexWidth / 2, hexHeight / 2);
  ctx.lineTo(3 * hexWidth / 4, hexHeight);
  ctx.stroke();
  ctx.restore();
  assets.appendChild(portbase);

  let cardback = createCard("#3F6388", "defaultcardback", cardWidth, cardHeight, "🏝️");
  assets.appendChild(cardback);

  let devcard = createCard("white", "defaultdevcard", cardWidth, cardHeight);
  ctx = devcard.getContext("2d");
  createDevCardBack(ctx, cardWidth, cardHeight, true);
  assets.appendChild(devcard);

  let robber = document.createElement("CANVAS");
  robber.width = hexWidth / 4;
  robber.height = 3 * hexHeight / 4;
  robber.id = "defaultrobber";
  ctx = robber.getContext("2d");
  ctx.save();
  ctx.fillStyle = "black";
  ctx.beginPath();
  ctx.moveTo(0, hexHeight / 3);
  ctx.lineTo(0, 3 * hexHeight / 4);
  ctx.lineTo(hexWidth / 4, 3 * hexHeight / 4);
  ctx.lineTo(hexWidth / 4, hexHeight / 3);
  ctx.arc(hexWidth / 8, hexHeight / 3, hexWidth / 8, 0, Math.PI, true);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(hexWidth / 8, hexWidth / 8, hexWidth / 8, 0, 2 * Math.PI, true);
  ctx.fill();
  ctx.restore();
  assets.appendChild(robber);

  let pirate = document.createElement("CANVAS");
  pirate.width = 2 * hexWidth / 3;
  pirate.height = 11 * hexWidth / 30;
  pirate.id = "defaultpirate";
  ctx = pirate.getContext("2d");
  ctx.save();
  ctx.beginPath();
  ctx.arc(hexWidth / 6, hexWidth / 5, hexWidth / 6, Math.PI, Math.PI / 2, true);
  ctx.lineTo(hexWidth / 2, 11 * hexWidth / 30);
  ctx.arc(hexWidth / 2, hexWidth / 5, hexWidth / 6, Math.PI / 2, 0 , true);
  ctx.lineTo(13 * hexWidth / 30, hexWidth / 5);
  ctx.arc(7 * hexWidth / 30, hexWidth / 5, hexWidth / 5, 0, - Math.PI / 2, true);
  ctx.lineTo(7 * hexWidth / 30, hexWidth / 5);
  ctx.closePath();
  ctx.fillStyle = "black";
  ctx.fill();
  ctx.restore();
  assets.appendChild(pirate);
}

function createHex(color, id, text) {
  let tile = document.createElement("CANVAS");
  tile.height = hexHeight;
  tile.width = hexWidth;
  tile.id = id;
  let ctx = tile.getContext("2d");
  ctx.clearRect(0, 0, hexWidth, hexHeight);
  ctx.save();
  if (Array.isArray(color)) {
    let grad = ctx.createLinearGradient(hexWidth/3, hexHeight/3, 3*hexWidth/4, hexHeight);
    for (let [idx, col] of color.entries()) {
      grad.addColorStop(idx / (color.length - 1), col);
    }
    ctx.fillStyle = grad;
  } else {
    ctx.fillStyle = color;
  }
  ctx.beginPath();
  ctx.moveTo(hexWidth / 4, 0);
  ctx.lineTo(3 * hexWidth / 4, 0);
  ctx.lineTo(hexWidth, hexHeight / 2);
  ctx.lineTo(3 * hexWidth / 4, hexHeight);
  ctx.lineTo(hexWidth / 4, hexHeight);
  ctx.lineTo(0, hexHeight / 2);
  ctx.lineTo(hexWidth / 4, 0);
  ctx.fill();
  ctx.strokeStyle = "black";
  ctx.stroke();
  ctx.restore();
  return tile;
}

function createPort(color, id, text) {
  let port = document.createElement("CANVAS");
  port.width = hexWidth;
  port.height = hexHeight;
  port.id = id;
  ctx = port.getContext("2d");
  ctx.clearRect(0, 0, cardWidth, cardHeight);
  ctx.save();
  ctx.beginPath();
  ctx.arc(hexWidth / 2, hexHeight / 2, hexHeight / 5, 0, Math.PI * 2, false);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = "black";
  ctx.stroke();
  ctx.restore();
  renderText(ctx, text, hexWidth / 2, hexHeight / 2, 2 * hexHeight / 5);
  return port;
}

function createCard(color, id, width, height, text, bottomText) {
  let card = document.createElement("CANVAS");
  card.width = width;
  card.height = height;
  card.id = id;
  ctx = card.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = color;
  ctx.fillRect(width / 20, width / 20, 18 * width / 20, height - width / 10);
  ctx.restore();
  renderText(ctx, text, width / 2, height / 2, width);
  renderText(ctx, bottomText, width / 2, 6 * height / 7, width);
  return card;
}

function createDevCardBack(ctx, width, height, outline) {
  ctx.save();
  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, width, height);
  ctx.beginPath();
  ctx.arc(width / 2, height / 2, 4 * width / 10, 0, 2 * Math.PI, true);
  ctx.fillStyle = "#BB303A";
  ctx.fill();
  ctx.beginPath();
  ctx.arc(width / 2, height / 2, 3 * width / 10, 0, 2 * Math.PI, true);
  ctx.fillStyle = "#DEC200";
  ctx.fill();
  ctx.beginPath();
  ctx.arc(width / 2, height / 2, 4 * width / 10, 11 * Math.PI / 12, Math.PI / 12, true);
  ctx.fillStyle = "#3C496B";
  ctx.fill();
  if (outline) {
    ctx.strokeStyle = "gray";
    ctx.strokeRect(0, 0, width, height);
  }
  ctx.restore();
}

function renderText(ctx, text, centerX, centerY, width) {
  if (text == null) {
    return;
  }
  ctx.save();
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.translate(centerX, centerY);
  let metrics = ctx.measureText(text);
  ctx.scale(width / metrics.width * 4 / 5, width / metrics.width * 4 / 5);
  ctx.fillText(text, 0, 0);
  ctx.restore();
}

function getTextSize(ctx, text, maxWidth, maxHeight) {
  ctx.font = "72px sans-serif";
  let measurements = ctx.measureText(text);
  let textHeight;
  if (measurements.actualBoundingBoxAscent) {
    textHeight = measurements.actualBoundingBoxAscent + measurements.actualBoundingBoxDescent;
  } else {
    textHeight = measurements.fontBoundingBoxAscent + measurements.fontBoundingBoxDescent;
  }
  let shrinkRatio = Math.min(maxWidth / measurements.width, maxHeight / textHeight);
  return Math.floor(72 * shrinkRatio);
}
