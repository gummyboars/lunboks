function initializeDefaults() {
  let assets = document.getElementById("defaultassets");
  let ctx;
  let resourceDatas = [
    {name: "rsrc1", color: "#95B900"},
    {name: "rsrc2", color: "#2E9A35"},
    {name: "rsrc3", color: "#F2C024"},
    {name: "rsrc4", color: "#DE6B2B"},
    {name: "rsrc5", color: "#A7ADA9"},
    {name: "norsrc", color: "#D8D393"},
    {name: "anyrsrc", color: ["#B8860B", "#0000CD"]},
    {name: "space", color: "#56A4D8"},
  ];
  let devDatas = [
    {name: "knight", text: "robber"},
    {name: "roadbuilding", text: "2 roads"},
    {name: "yearofplenty", text: "2 cards"},
    {name: "monopoly", text: "monopoly"},
    {name: "palace", text: "1 point"},
    {name: "chapel", text: "1 point"},
    {name: "university", text: "1 point"},
    {name: "library", text: "1 point"},
    {name: "market", text: "1 point"},
  ];
  for (let resourceData of resourceDatas) {
    let tile = createHex(resourceData.color, "default" + resourceData.name + "tile");
    assets.appendChild(tile);
    let card = createCard(resourceData.color, "default" + resourceData.name + "card", cardWidth, cardHeight);
    assets.appendChild(card);
    let port = createPort(resourceData.color, "default" + resourceData.name + "port", "2:1");
    assets.appendChild(port);
  }
  for (let devData of devDatas) {
    let dev = createCard("#9D6BBB", "default" + devData.name, cardWidth, cardHeight, devData.text);
    assets.appendChild(dev);
  }
  let threeport = createPort("white", "default3port", "3:1");
  assets.appendChild(threeport);
  let longestRoute = createCard("green", "defaultlongestroute", cardHeight * 4 / 5, cardHeight, "Route");
  assets.appendChild(longestRoute);
  let largestArmy = createCard("indianred", "defaultlargestarmy", cardHeight * 4 / 5, cardHeight, "Army");
  assets.appendChild(largestArmy);
  let costCard = createCard("white", "defaultcostcard", cardHeight * 4 / 5, cardHeight, "Costs");
  assets.appendChild(costCard);

  let portbase = document.createElement("CANVAS");
  portbase.width = tileWidth;
  portbase.height = tileHeight;
  portbase.id = "defaultport";
  ctx = portbase.getContext("2d");
  ctx.clearRect(0, 0, cardWidth, cardHeight);
  ctx.save();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "black";
  ctx.beginPath();
  ctx.moveTo(tileWidth / 4, tileHeight);
  ctx.lineTo(tileWidth / 2, tileHeight / 2);
  ctx.lineTo(3 * tileWidth / 4, tileHeight);
  ctx.stroke();
  ctx.restore();
  assets.appendChild(portbase);
  let cardback = createCard("#3F6388", "defaultcardback", cardWidth, cardHeight);
  assets.appendChild(cardback);

  let devcard = createCard("white", "defaultdevcard", cardWidth, cardHeight);
  ctx = devcard.getContext("2d");
  ctx.save();
  ctx.beginPath();
  ctx.arc(cardWidth / 2, cardHeight / 2, cardWidth / 3, 0, Math.PI, true);
  ctx.fillStyle = "#BB303A";
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cardWidth / 2, cardHeight / 2, cardWidth / 4, 0, Math.PI, true);
  ctx.fillStyle = "#DEC200";
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cardWidth / 2, cardHeight / 2, cardWidth / 3, Math.PI, 2 * Math.PI, true);
  ctx.fillStyle = "#3C496B";
  ctx.fill();
  ctx.strokeStyle = "gray";
  ctx.strokeRect(0, 0, cardWidth, cardHeight);
  ctx.restore();
  assets.appendChild(devcard);

  let robber = document.createElement("CANVAS");
  robber.width = tileWidth / 4;
  robber.height = 3 * tileHeight / 4;
  robber.id = "defaultrobber";
  ctx = robber.getContext("2d");
  ctx.save();
  ctx.fillStyle = "black";
  ctx.beginPath();
  ctx.moveTo(0, tileHeight / 3);
  ctx.lineTo(0, 3 * tileHeight / 4);
  ctx.lineTo(tileWidth / 4, 3 * tileHeight / 4);
  ctx.lineTo(tileWidth / 4, tileHeight / 3);
  ctx.arc(tileWidth / 8, tileHeight / 3, tileWidth / 8, 0, Math.PI, true);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(tileWidth / 8, tileWidth / 8, tileWidth / 8, 0, 2 * Math.PI, true);
  ctx.fill();
  ctx.restore();
  assets.appendChild(robber);

  let pirate = document.createElement("CANVAS");
  pirate.width = 2 * tileWidth / 3;
  pirate.height = 11 * tileWidth / 30;
  pirate.id = "defaultpirate";
  ctx = pirate.getContext("2d");
  ctx.save();
  ctx.beginPath();
  ctx.arc(tileWidth / 6, tileWidth / 5, tileWidth / 6, Math.PI, Math.PI / 2, true);
  ctx.lineTo(tileWidth / 2, 11 * tileWidth / 30);
  ctx.arc(tileWidth / 2, tileWidth / 5, tileWidth / 6, Math.PI / 2, 0 , true);
  ctx.lineTo(13 * tileWidth / 30, tileWidth / 5);
  ctx.arc(7 * tileWidth / 30, tileWidth / 5, tileWidth / 5, 0, - Math.PI / 2, true);
  ctx.lineTo(7 * tileWidth / 30, tileWidth / 5);
  ctx.closePath();
  ctx.fillStyle = "black";
  ctx.fill();
  ctx.restore();
  assets.appendChild(pirate);
}

function createHex(color, id) {
  let tile = document.createElement("CANVAS");
  tile.height = tileHeight;
  tile.width = tileWidth;
  tile.id = id;
  let ctx = tile.getContext("2d");
  ctx.clearRect(0, 0, tileWidth, tileHeight);
  ctx.save();
  if (Array.isArray(color)) {
    let grad = ctx.createLinearGradient(tileWidth/3, tileHeight/3, 3*tileWidth/4, tileHeight);
    for (let [idx, col] of color.entries()) {
      grad.addColorStop(idx / (color.length - 1), col);
    }
    ctx.fillStyle = grad;
  } else {
    ctx.fillStyle = color;
  }
  ctx.beginPath();
  ctx.moveTo(tileWidth / 4, 0);
  ctx.lineTo(3 * tileWidth / 4, 0);
  ctx.lineTo(tileWidth, tileHeight / 2);
  ctx.lineTo(3 * tileWidth / 4, tileHeight);
  ctx.lineTo(tileWidth / 4, tileHeight);
  ctx.lineTo(0, tileHeight / 2);
  ctx.lineTo(tileWidth / 4, 0);
  ctx.fill();
  ctx.strokeStyle = "black";
  ctx.stroke();
  ctx.restore();
  return tile;
}

function createPort(color, id, text) {
  let port = document.createElement("CANVAS");
  port.width = tileWidth;
  port.height = tileHeight;
  port.id = id;
  ctx = port.getContext("2d");
  ctx.clearRect(0, 0, cardWidth, cardHeight);
  ctx.save();
  ctx.beginPath();
  ctx.arc(tileWidth / 2, tileHeight / 2, tileHeight / 5, 0, Math.PI * 2, false);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = "black";
  ctx.stroke();
  ctx.restore();
  renderText(ctx, text, tileWidth / 2, tileHeight / 2, 2 * tileHeight / 5);
  return port;
}

function createCard(color, id, width, height, text) {
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
  return card;
}

function renderText(ctx, text, centerX, centerY, width) {
  if (text == null) {
    return;
  }
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.translate(centerX, centerY);
  let metrics = ctx.measureText(text);
  ctx.scale(width / metrics.width * 4 / 5, width / metrics.width * 4 / 5);
  ctx.fillText(text, 0, 0);
}
