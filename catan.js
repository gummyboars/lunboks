// Constants.
// Haha, canvas height/width is no longer constant. Set on page load.
// TODO: update on resize.
canWidth = 1011;
canHeight = 876;
tileWidth = 337 / 2;
tileHeight = 292 / 2;
cardResources = ["sheep", "wood", "grain", "brick", "ore"];
devCards = ["knight", "roadbuilding", "yearofplenty", "monopoly", "palace", "chapel", "university", "library", "market"];
cardWidth = 145;
cardHeight = 210;
pieceRadius = 10;
margin = 50;  // For dice and trade toggle button.

// Trade window.
tradeCardWidth = 29 * 3;
tradeCardHeight = 41 * 3;
tradeVertBuffer = 40;
tradeWidth = tradeCardWidth * cardResources.length * 1.5 + (tradeCardWidth/2);
tradeOneHeight = tradeCardHeight + 2 * tradeVertBuffer;
tradeExtraHeight = 70;
tradeHeight = 2 * tradeOneHeight + tradeExtraHeight;
tradeSides = ["Want", "Give"];
// Trade buttons.
tradeButtonWidth = 1.5 * tradeCardWidth;
tradeButtonHeight = 28;
function tradeButtonX() {
  return canWidth / 2 - tradeWidth / 2;
}
function tradeButtonY() {
  return canHeight / 2 - tradeHeight / 2 + tradeSides.length * tradeOneHeight + tradeExtraHeight / 2 - tradeButtonHeight / 2;
}
function tradeButtons(partner) {
  let buttons = [];
  if (partner == "player") {
    // Offer (left) button.
    buttons.push({x: tradeButtonX() + tradeCardWidth / 2, y: tradeButtonY(), text: "Offer"});
    // Clear (right) button.
    buttons.push({
      x: tradeButtonX() + tradeWidth - tradeCardWidth / 2 - tradeButtonWidth,
      y: tradeButtonY(),
      text: "Clear",
    });
  } else if (partner == "bank") {
    // Accept (left) button.
    buttons.push({x: tradeButtonX() + tradeCardWidth / 2, y: tradeButtonY(), text: "Accept"});
    // Clear (right) button.
    buttons.push({
      x: tradeButtonX() + tradeWidth - tradeCardWidth / 2 - tradeButtonWidth,
      y: tradeButtonY(),
      text: "Clear",
    });
  }
  // Accept (center) button.
  // tradePButtons.push({x: tradeButtonX() + tradeWidth / 2 - tradeButtonWidth / 2, y: tradeButtonY(), text: "Yolo"});
  return buttons;
}

// Game state.
myColor = null;
playerColors = null;
tiles = [];
corners = [];
pieces = [];
edges = [];
roads = [];
cards = {};
turn = null;
diceRoll = null;
robberLoc = null;
tradeOffer = null;
gamePhase = null;
turnPhase = null;

// Local state.
debug = false;
scale = 1;
hoverTile = null;
hoverCorner = null;
hoverEdge = null;
tradeWindowActive = false;
tradeActiveOffer = [{}, {}];
tradePartner = "player";  // player or bank

// For dragging the canvas.
isDragging = false;
startX = null;
startY = null;
offsetX = 0;
offsetY = 0;
dX = 0;
dY = 0;

function toggleDebug() {
  debug = !debug;
}
function toggleTradeWindow(partner) {
  tradeWindowActive = !tradeWindowActive;
  tradePartner = partner;
  if (tradeWindowActive) {
    let activeButton = null;
    let disabledButton = null;
    if (tradePartner == "player") {
      activeButton = document.getElementById("tradeplayer");
      disabledButton = document.getElementById("tradebank");
    } else if (tradePartner == "bank") {
      activeButton = document.getElementById("tradebank");
      disabledButton = document.getElementById("tradeplayer");
    }
    activeButton.classList.add("active");
    disabledButton.classList.add("disabled");
    disabledButton.disabled = true;
  } else {
    playerButton = document.getElementById("tradeplayer");
    bankButton = document.getElementById("tradebank");
    playerButton.classList.remove("active");
    playerButton.classList.remove("disabled");
    playerButton.disabled = false;
    bankButton.classList.remove("active");
    bankButton.classList.remove("disabled");
    bankButton.disabled = false;
  }
}
function rollDice() {
  let msg = {
    type: "roll_dice",
  };
  ws.send(JSON.stringify(msg));
}
function endTurn() {
  let msg = {
    type: "end_turn",
  };
  ws.send(JSON.stringify(msg));
}
function draw() {
  var canvas = document.getElementById('myCanvas');
  var context = canvas.getContext('2d');

  if (tiles.length < 1) {
    window.requestAnimationFrame(draw);
    return;
  }

  context.save();
  context.clearRect(0, 0, canWidth, canHeight);
  context.translate(offsetX + dX, offsetY + dY);
  context.scale(scale, scale);
  context.textAlign = 'center';
  for (let i = 0; i < tiles.length; i++) {
    drawTile(tiles[i], context);
    drawNumber(tiles[i], context);
  }
  for (let i = 0; i < pieces.length; i++) {
    drawPiece(pieces[i], context);
  }
  for (let i = 0; i < roads.length; i++) {
    drawRoad(roads[i].location, roads[i].player, context);
  }
  drawHover(context);
  drawRobber(context);
  drawDebug(context);
  context.restore();
  if (gamePhase == "main") {
    // TODO: the tradeWindow should be its own div.
    drawTradeWindow(context);
  }
  window.requestAnimationFrame(draw);
}
function coordsToEdgeCenter(loc) {
  let leftCorn = coordToCornerCenter([loc[0], loc[1]]);
  let rightCorn = coordToCornerCenter([loc[2], loc[3]]);
  return {
    x: (leftCorn.x + rightCorn.x) / 2,
    y: (leftCorn.y + rightCorn.y) / 2,
  };
}
function coordToCornerCenter(loc) {
  let x = (2 * Math.floor(loc[0]/2)) * tileWidth * 3 / 8;
  let y = loc[1] * tileHeight / 2;
  if (Math.abs(loc[0]) % 2 == 1) {
    x += tileWidth / 2;
  }
  return {x: x, y: y};
}
function coordToTileUpperLeft(loc) {
  let x = loc[0] * tileWidth * 3 / 8 - tileWidth / 4;
  let y = loc[1] * tileHeight / 2;
  return {x: x, y: y};
}
function coordToTileCenter(loc) {
  let ul = coordToTileUpperLeft(loc);
  return {x: ul.x + tileWidth/2, y: ul.y + tileHeight/2};
}
function populateCards() {
  newContainer = document.createElement("DIV");
  newContainer.classList.add("uicards");
  newContainer.classList.add("noclick");
  oldContainer = document.getElementById("uibottom").firstChild;
  if (cards) {
    for (let i = 0; i < cardResources.length; i++) {
      for (let j = 0; j < cards[cardResources[i]]; j++) {
        addCard(newContainer, cardResources[i] + "card", false);
      }
    }
    for (let i = 0; i < devCards.length; i++) {
      for (let j = 0; j < cards[devCards[i]]; j++) {
        addCard(newContainer, devCards[i], true);
      }
    }
  }
  if (newContainer.childElementCount > 0) {
    newContainer.lastChild.classList.add("shown");
  }
  // TODO: how do we avoid the problem of having flicker?
  document.getElementById("uibottom").replaceChild(newContainer, oldContainer);
}
function addCard(cardContainer, elemId, usable) {
  let orig = document.getElementById(elemId);
  let img = document.createElement("IMG");
  img.src = orig.src;
  img.classList.add("clickable");
  img.width = cardWidth;
  img.height = cardHeight;
  img.style.display = "block";
  let div = document.createElement("DIV");
  div.classList.add("clickable");
  div.classList.add("uicard");
  div.appendChild(img);
  div.onmouseenter = bringforward;
  div.onmouseleave = pushbackward;
  if (usable) {
    div.onclick = function(e) {
      devCardModal(elemId);
    }
  }
  cardContainer.appendChild(div);
}
function bringforward(e) {
  e.currentTarget.style.overflowX = "visible";
}
function pushbackward(e) {
  e.currentTarget.style.overflowX = "hidden";
}
function devCardModal(cardType) {
  // TODO: show a dialog based on the card type. will probably need a resource picker.
  console.log(cardType);
}
function getClickedResource(eventX, eventY) {
  let centerX = canWidth / 2;
  let centerY = canHeight / 2;
  let leftX = centerX - tradeWidth / 2;
  let leftY = centerY - tradeHeight / 2;
  for (let side = 0; side < tradeSides.length; side++) {
    for (let i = 0; i < cardResources.length; i++) {
      let cardX = leftX + 1.5 * tradeCardWidth * i + tradeCardWidth / 2;
      let cardY = leftY + tradeVertBuffer + side * tradeOneHeight;
      if (eventX >= cardX && eventX <= cardX + tradeCardWidth &&
          eventY >= cardY && eventY <= cardY + tradeCardHeight) {
        return {
          resource: cardResources[i],
          side: side,
        };
      }
    }
  }
  return null;
}
function getClickedTradeButton(eventX, eventY, buttons) {
  for (let i = 0; i < buttons.length; i++) {
    if (eventX >= buttons[i].x && eventX <= buttons[i].x + tradeButtonWidth &&
        eventY >= buttons[i].y && eventY <= buttons[i].y + tradeButtonHeight) {
      return buttons[i].text;
    }
  }
  return null;
}
function drawTradeButton(ctx, button, isActive) {
  ctx.fillStyle = isActive ? 'darkkhaki' : 'lightgray';
  ctx.fillRect(button.x, button.y, tradeButtonWidth, tradeButtonHeight);
  ctx.fillStyle = isActive ? 'black' : 'darkgray';
  ctx.textAlign = 'center';
  ctx.font = tradeButtonHeight + 'px sans-serif';
  ctx.fillText(button.text, button.x + tradeButtonWidth/2, button.y + tradeButtonHeight - 4);
}
function drawTradeWindow(ctx) {
  if (!tradeWindowActive) {
    return;
  }
  let centerX = canWidth / 2;
  let centerY = canHeight / 2;
  let leftX = centerX - tradeWidth / 2;
  let leftY = centerY - tradeHeight / 2;
  ctx.fillStyle = '#6666FF';
  ctx.fillRect(leftX, leftY, tradeWidth, tradeHeight);
  // Draw buttons.
  let buttonList = tradeButtons(tradePartner);
  for (let i = 0; i < buttonList.length; i++) {
    drawTradeButton(ctx, buttonList[i], true);
  }
  // Draw trading windows.
  for (let side = 0; side < tradeSides.length; side++) {
    // Draw the You Want/Give text.
    ctx.font = '18px sans-serif';
    ctx.fillStyle = 'black';
    ctx.textAlign = 'left';
    ctx.fillText("You " + tradeSides[side], leftX, leftY + side * tradeOneHeight + 18);
    // Draw the separator.
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'black';
    ctx.beginPath();
    ctx.moveTo(leftX, leftY + (side + 1) * tradeOneHeight);
    ctx.lineTo(leftX + tradeWidth, leftY + (side + 1) * tradeOneHeight);
    ctx.stroke();
    // Draw the resources.
    for (let i = 0; i < cardResources.length; i++) {
      let img = document.getElementById(cardResources[i] + "card");
      let cardX = leftX + 1.5 * tradeCardWidth * i + tradeCardWidth / 2;
      let cardY = leftY + tradeVertBuffer + side * tradeOneHeight;
      ctx.drawImage(img, cardX, cardY, tradeCardWidth, tradeCardHeight);
      let num = tradeActiveOffer[side][cardResources[i]] || 0;
      ctx.textAlign = 'center';
      let textX = cardX + tradeCardWidth / 2;
      let textY = cardY + tradeCardHeight + tradeVertBuffer / 2;
      ctx.fillText("x" + num, textX, textY);
    }
  }
}
function drawRoad(roadLoc, style, ctx) {
  let leftCorner = coordToCornerCenter([roadLoc[0], roadLoc[1]]);
  let rightCorner = coordToCornerCenter([roadLoc[2], roadLoc[3]]);
  ctx.strokeStyle = style;
  ctx.lineWidth = pieceRadius;
  ctx.lineCap = 'butt';
  ctx.beginPath();
  let leftX = 0.15 * rightCorner.x + 0.85 * leftCorner.x;
  let rightX = 0.15 * leftCorner.x + 0.85 * rightCorner.x;
  let leftY = 0.15 * rightCorner.y + 0.85 * leftCorner.y;
  let rightY = 0.15 * leftCorner.y + 0.85 * rightCorner.y;
  ctx.moveTo(leftX, leftY);
  ctx.lineTo(rightX, rightY);
  ctx.stroke();
}
function drawDebug(ctx) {
  return;
}
function drawPiece(pieceData, ctx) {
  let canvasLoc = coordToCornerCenter(pieceData.location);
  ctx.fillStyle = pieceData.player;
  if (pieceData.piece_type == "settlement") {
    ctx.beginPath();
    ctx.arc(canvasLoc.x, canvasLoc.y, pieceRadius, 0, Math.PI * 2, true);
    ctx.fill();
  }
  if (pieceData.piece_type == "city") {
    let startX = canvasLoc.x - pieceRadius;
    let startY = canvasLoc.y - pieceRadius;
    ctx.fillRect(startX, startY, pieceRadius * 2, pieceRadius * 2);
  }
}
function drawTile(tileData, ctx) {
  let img = document.getElementById(tileData.tile_type);
  let canvasLoc = coordToTileCenter(tileData.location);
  ctx.save();
  ctx.translate(canvasLoc.x, canvasLoc.y);
  if (tileData.rotation) {
    ctx.rotate(Math.PI * tileData.rotation / 3);
  }
  if (img != null) {
    ctx.drawImage(img, -tileWidth/2, -tileHeight/2, tileWidth, tileHeight);
  }
  ctx.restore();
}
function drawNumber(tileData, ctx) {
  let textHeightOffset = 12; // Adjust as necessary.
  let canvasLoc = coordToTileCenter(tileData.location);
  if (tileData.number) {
    // Draw the white circle.
    ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.beginPath();
    ctx.arc(canvasLoc.x, canvasLoc.y, 28, 0, Math.PI * 2, true);
    ctx.fill();
    // Draw the number.
    if (tileData.number == '6' || tileData.number == '8') {
      ctx.fillStyle = 'red';
      ctx.font = 'bold 36px sans-serif';
    } else {
      ctx.fillStyle = 'black';
      ctx.font = 'bold 32px sans-serif';
    }
    ctx.fillText(tileData.number + "", canvasLoc.x, canvasLoc.y + textHeightOffset);
  }
}
function drawHover(ctx) {
  if (turn != myColor) {
    return;
  }
  if (hoverTile != null) {
    let canvasLoc = coordToTileCenter(hoverTile);
    ctx.fillStyle = 'rgba(127, 127, 127, 0.5)';
    ctx.beginPath();
    ctx.arc(canvasLoc.x, canvasLoc.y, 28, 0, Math.PI * 2, true);
    ctx.fill();
  }
  if (hoverCorner != null) {
    let canvasLoc = coordToCornerCenter(hoverCorner);
    ctx.fillStyle = 'rgba(127, 127, 127, 0.5)';
    ctx.beginPath();
    ctx.arc(canvasLoc.x, canvasLoc.y, pieceRadius, 0, Math.PI * 2, true);
    ctx.fill();
  }
  if (hoverEdge != null) {
    drawRoad(hoverEdge, 'rgba(127, 127, 127, 0.5)', ctx);
  }
}
function drawRobber(ctx) {
  if (robberLoc != null) {
    let canvasLoc = coordToTileCenter(robberLoc);
    let robimg = document.getElementById("robber");
    let robwidth = 26;
    let robheight = 60;
    ctx.drawImage(robimg, canvasLoc.x - robwidth/2, canvasLoc.y - robheight/2, robwidth, robheight);
  }
}
function getEdge(eventX, eventY) {
  for (let i = 0; i < edges.length; i++) {
    let edgeCenter = coordsToEdgeCenter(edges[i].location);
    let centerX = edgeCenter.x + offsetX + dX;
    let centerY = edgeCenter.y + offsetY + dY;
    let distanceX = eventX - centerX;
    let distanceY = eventY - centerY;
    let distance = distanceX * distanceX + distanceY * distanceY;
    let radius = pieceRadius;
    if (distance < radius * radius) {
      return i;
    }
  }
}
function getCorner(eventX, eventY, cList) {
  for (let i = 0; i < cList.length; i++) {
    let canvasLoc = coordToCornerCenter(cList[i].location);
    let centerX = canvasLoc.x + offsetX + dX;
    let centerY = canvasLoc.y + offsetY + dY;
    let distanceX = eventX - centerX;
    let distanceY = eventY - centerY;
    let distance = distanceX * distanceX + distanceY * distanceY;
    let radius = pieceRadius;
    if (distance < radius * radius) {
      return i;
    }
  }
}
function getTile(eventX, eventY) {
  for (let i = 0; i < tiles.length; i++) {
    let canvasLoc = coordToTileCenter(tiles[i].location);
    let centerX = canvasLoc.x + offsetX + dX;
    let centerY = canvasLoc.y + offsetY + dY;
    let distanceX = eventX - centerX;
    let distanceY = eventY - centerY;
    let distance = distanceX * distanceX + distanceY * distanceY;
    let radius = 50;
    if (distance < radius * radius) {
      return i;
    }
  }
  return null;
}
function clearTradeOffer() {
  for (side = 0; side < tradeSides.length; side++) {
    tradeActiveOffer[side] = {};
  }
}
function onclickTrade(event) {
  if (event.clientX < canWidth/2 - tradeWidth/2 || event.clientX > canWidth/2 + tradeWidth/2 ||
      event.clientY < canHeight/2 - tradeHeight/2 || event.clientY > canHeight/2 + tradeHeight/2) {
    toggleTradeWindow(tradePartner);
    return;
  }

  let chosenResource = getClickedResource(event.clientX, event.clientY);
  if (chosenResource) {
    let num = 1;
    if (event.shiftKey) {
      num = -1;
    }
    let rsrc = chosenResource.resource;
    let side = chosenResource.side;
    current = tradeActiveOffer[side][rsrc] || 0;
    tradeActiveOffer[side][rsrc] = current + num;
    if (tradeActiveOffer[side][rsrc] < 0) {
      tradeActiveOffer[side][rsrc] = 0;
    }
  }
  let clickedButton = getClickedTradeButton(event.clientX, event.clientY, tradeButtons(tradePartner));
  if (clickedButton == "Clear") {
    clearTradeOffer();
  }
  if (clickedButton == "Offer" && tradePartner == "player") {
    let msg = {
      type: "trade_offer",
      offer: tradeActiveOffer,
    };
    ws.send(JSON.stringify(msg));
  }
  if (clickedButton == "Accept" && tradePartner == "bank") {
    let msg = {
      type: "trade_bank",
      offer: tradeActiveOffer,
    };
    ws.send(JSON.stringify(msg));
  }
}
function onkey(event) {
  let thing = event.which || event.keyCode; // Cross-browser compatibility.
  console.log("keypress " + thing);
  if (thing == 32 && turnPhase == "dice") {
    rollDice();
    return;
  }
  if (thing == 13 && turnPhase == "main") {
    endTurn();
    return;
  }
}
function onclick(event) {
  // Ignore right/middle-click.
  if (event.button != 0) {
    return;
  }
  if (tradeWindowActive) {
    onclickTrade(event);
    return;
  }
  let clickTile = getTile(event.clientX, event.clientY);
  if (clickTile != null) {
    let msg = {
      type: "robber",
      location: tiles[clickTile].location,
    };
    ws.send(JSON.stringify(msg));
  }
  let clickPiece = getCorner(event.clientX, event.clientY, pieces);
  if (clickPiece != null && pieces[clickPiece].player == myColor) {
    let msg = {
      type: "city",
      location: pieces[clickPiece].location,
    };
    ws.send(JSON.stringify(msg));
  } else {
    let clickCorner = getCorner(event.clientX, event.clientY, corners);
    if (clickCorner != null) {
      let msg = {
        type: "settle",
        location: corners[clickCorner].location,
      };
      ws.send(JSON.stringify(msg));
    }
  }
  let clickEdge = getEdge(event.clientX, event.clientY);
  if (clickEdge != null) {
    let msg = {
      type: "road",
      location: edges[clickEdge].location,
    };
    ws.send(JSON.stringify(msg));
  }
}
function buyDevCard() {
  ws.send(JSON.stringify({type: "buy_dev"}));
}
function onmove(event) {
  let hoverLoc = getTile(event.clientX, event.clientY);
  if (hoverLoc != null) {
    hoverTile = tiles[hoverLoc].location;
  } else {
    hoverTile = null;
  }
  hoverLoc = getCorner(event.clientX, event.clientY, corners);
  if (hoverLoc != null) {
    hoverCorner = corners[hoverLoc].location;
  } else {
    hoverCorner = null;
  }
  hoverLoc = getEdge(event.clientX, event.clientY);
  if (hoverLoc != null) {
    hoverEdge = edges[hoverLoc].location;
  } else {
    hoverEdge = null;
  }
  if (isDragging) {
    newX = event.clientX;
    newY = event.clientY;
    
    dX = newX - startX;
    dY = newY - startY;
  }
}
function onwheel(event) {
  event.preventDefault();
  if (event.deltaY < 0) {
    scale += 0.125;
  } else if (event.deltaY > 0) {
    scale -= 0.125;
  }
  scale = Math.min(Math.max(0.125, scale), 4);
}
function ondown(event) {
  // Ignore right/middle-click.
  if (event.button != 0) {
    return;
  }
  if (tradeWindowActive) {
    return;
  }
  startX = event.clientX;
  startY = event.clientY;
  isDragging = true;
}
function onup(event) {
  // Ignore right/middle-click.
  if (event.button != 0) {
    return;
  }
  isDragging = false;
  offsetX += dX;
  offsetY += dY;
  dX = 0;
  dY = 0;
}
function onout(event) {
  hoverTile = null;
  hoverCorner = null;
  hoverEdge = null;
  onup(event);
}
function clearerror() {
  etxt = document.getElementById("errorText")
  if (etxt.holdSeconds > 0) {
    etxt.holdSeconds -= 0.1;
    setTimeout(clearerror, 100);
  } else {
    newOpac = etxt.style.opacity - 0.02;
    etxt.style.opacity = newOpac;
    if (newOpac <= 0.1) {
      etxt.innerText = null;
    } else {
      setTimeout(clearerror, 50);
    }
  }
}
function onmsg(event) {
  var data = JSON.parse(event.data);
  if (data.type == "error") {
    document.getElementById("errorText").holdSeconds = 3;
    document.getElementById("errorText").style.opacity = 1.0;
    document.getElementById("errorText").innerText = data.message;
    setTimeout(clearerror, 100);
    return;
  }
  // data.type should be game_state now - maybe handle more later
  if (data.you) {
    document.getElementById('name').value = data.you.name;
    myColor = data.you.color;
  }
  let firstMsg = false;
  if (tiles.length < 1) {
    firstMsg = true;
  }
  playerColors = data.player_colors;
  gamePhase = data.game_phase;
  turnPhase = data.turn_phase;
  tiles = data.tiles;
  corners = data.corners;
  edges = data.edges;
  robberLoc = data.robber;
  if (cards != data.cards) {
    console.log("cards changed; clearing active offer");
    clearTradeOffer();
  }
  cards = data.cards;
  diceRoll = data.dice_roll;
  pieces = data.pieces;
  roads = data.roads;
  turn = data.turn;
  if (firstMsg) {
    centerCanvas();
  }
  populateCards();
  updateDice();
  updateUI("buydev");
  updateUI("endturn");
  updateUI("tradeplayer");
  updateUI("tradebank");
  updateEndTurn();
}
function updateUI(elemName) {
  if (gamePhase != "main" || turn != myColor || turnPhase != "main") {
    document.getElementById(elemName).classList.add("disabled");
    document.getElementById(elemName).disabled = true;
  } else {
    document.getElementById(elemName).classList.remove("disabled");
    document.getElementById(elemName).disabled = false;
  }
}
function updateDice() {
  diceEl = document.getElementById("uidice");
  if (diceRoll == null && turnPhase != "dice") {
    diceEl.style.display = "none";
  } else {
    diceEl.style.display = "block";
  }
  if (diceRoll == null) {
    document.getElementById("reddie").firstChild.firstChild.innerText = "?";
    document.getElementById("whitedie").firstChild.firstChild.innerText = "?";
  } else {
    document.getElementById("reddie").firstChild.firstChild.innerText = diceRoll[0];
    document.getElementById("whitedie").firstChild.firstChild.innerText = diceRoll[1];
  }
  if (turn != myColor) {
    if (!diceEl.classList.contains("noclick")) {
      diceEl.classList.remove("clickable");
      diceEl.classList.add("noclick");
    }
  } else {
    if (!diceEl.classList.contains("clickable")) {
      diceEl.classList.remove("noclick");
      diceEl.classList.add("clickable");
    }
  }
}
function centerCanvas() {
  if (tiles.length < 1) {
    return;
  }
  let tileLoc = coordToTileCenter(tiles[0].location);
  let minX = tileLoc.x;
  let minY = tileLoc.y;
  let maxX = tileLoc.x;
  let maxY = tileLoc.y;
  for (let i = 0; i < tiles.length; i++) {
    tileLoc = coordToTileCenter(tiles[i].location);
    minX = Math.min(tileLoc.x, minX);
    minY = Math.min(tileLoc.y, minY);
    maxX = Math.max(tileLoc.x, maxX);
    maxY = Math.max(tileLoc.y, maxY);
  }
  offsetX = canWidth / 2 - (minX + maxX) / 2;
  offsetY = canHeight / 2 - (minY + maxY) / 2;
}
// TODO: persist this in a cookie or something
function login() {
  let msg = {
    type: "player",
    player: {
      name: document.getElementById('name').value,
    },
  };
  ws.send(JSON.stringify(msg));
}
function init() {
  totalWidth = document.documentElement.clientWidth;
  totalHeight = document.documentElement.clientHeight;
  document.getElementById('ui').style.width = totalWidth + "px";
  document.getElementById('ui').style.height = totalHeight + "px";
  document.getElementById('uibottom').style.width = totalWidth + "px";
  document.getElementById('uiright').style.height = (totalHeight - cardHeight) + "px";
  document.getElementById('uileft').style.height = (totalHeight - cardHeight) + "px";
  canWidth = totalWidth - document.getElementById('uiright').offsetWidth;
  canHeight = totalHeight;
  document.getElementById('myCanvas').width = canWidth;
  document.getElementById('myCanvas').height = canHeight;
  document.getElementById('buydev').width = cardWidth;
  document.getElementById('buydev').height = cardHeight;
  window.requestAnimationFrame(draw);
  let l = window.location;
  ws = new WebSocket("ws://" + l.hostname + ":8081/");
  ws.onmessage = onmsg;
  document.getElementById('myCanvas').onmousemove = onmove;
  document.getElementById('myCanvas').onclick = onclick;
  document.getElementById('myCanvas').onmousedown = ondown;
  document.getElementById('myCanvas').onmouseup = onup;
  document.getElementById('myCanvas').onmouseout = onout;
  document.getElementById('myCanvas').onkeydown = onkey;
  // TODO: zoom in/out should come later.
  // document.getElementById('myCanvas').onwheel = onwheel;
}
