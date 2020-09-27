// For manipulating the canvas.
isDragging = false;
startX = null;
startY = null;
offsetX = 0;
offsetY = 0;
dX = 0;
dY = 0;
scale = 1;

hoverTile = null;
hoverCorner = null;
hoverEdge = null;

function locationsEqual(locA, locB) {
  if (locA == null && locB == null) {
    return true;
  }
  if (locA == null || locB == null) {
    return false;
  }
  if (locA.length != locB.length) {
    return false;
  }
  for (let i = 0; i < locA.length; i++) {
    if (locA[i] != locB[i]) {
      return false;
    }
  }
  return true;
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
  context.save();
  for (let i = 0; i < tiles.length; i++) {
    drawTile(tiles[i], context);
    drawNumber(tiles[i], context);
  }
  context.restore();
  context.save();
  for (let i = 0; i < roads.length; i++) {
    drawRoad(roads[i].location, playerData[roads[i].player].color, context);
  }
  context.restore();
  context.save();
  // Draw pieces over roads.
  for (let i = 0; i < pieces.length; i++) {
    drawPiece(pieces[i].location, playerData[pieces[i].player].color, pieces[i].piece_type, context);
  }
  context.restore();
  context.save();
  drawHover(context);
  context.restore();
  context.save();
  if (robberLoc != null && !locationsEqual(robberLoc, hoverTile)) {
    drawRobber(context, robberLoc, 1);
  }
  context.restore();
  drawDebug(context);
  context.restore();
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
function drawPiece(pieceLoc, style, pieceType, ctx) {
  let canvasLoc = coordToCornerCenter(pieceLoc);
  ctx.fillStyle = style;
  if (pieceType == "settlement") {
    ctx.beginPath();
    ctx.moveTo(canvasLoc.x - pieceRadius, canvasLoc.y + pieceRadius * 3/2);
    ctx.lineTo(canvasLoc.x + pieceRadius, canvasLoc.y + pieceRadius * 3/2);
    ctx.lineTo(canvasLoc.x + pieceRadius, canvasLoc.y - pieceRadius * 1/2);
    ctx.lineTo(canvasLoc.x, canvasLoc.y - pieceRadius * 3/2);
    ctx.lineTo(canvasLoc.x - pieceRadius, canvasLoc.y - pieceRadius * 1/2);
    ctx.closePath();
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "black";
    ctx.stroke();
  }
  if (pieceType == "city") {
    let radius = pieceRadius * 1.5;
    ctx.beginPath();
    ctx.moveTo(canvasLoc.x - radius, canvasLoc.y + radius);
    ctx.lineTo(canvasLoc.x + radius, canvasLoc.y + radius);
    ctx.lineTo(canvasLoc.x + radius, canvasLoc.y - radius/2);
    ctx.lineTo(canvasLoc.x + radius/2, canvasLoc.y - radius);
    ctx.lineTo(canvasLoc.x, canvasLoc.y - radius/2);
    ctx.lineTo(canvasLoc.x, canvasLoc.y);
    ctx.lineTo(canvasLoc.x - radius, canvasLoc.y);
    ctx.closePath();
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "black";
    ctx.stroke();
  }
}
function drawTile(tileData, ctx) {
  let img = document.getElementById(tileData.tile_type);
  if (!img) {
    img = document.createElement("IMG");
    img.id = tileData.tile_type;
    img.src = imageNames[tileData.tile_type];
    img.style.display = "none";
    document.getElementsByTagName("BODY")[0].appendChild(img);
  }
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
  if (turn != myIdx) {
    return;
  }
  let canvas = document.getElementById("myCanvas");
  if (hoverTile != null) {
    drawRobber(ctx, hoverTile, 0.5);
    canvas.style.cursor = "pointer";
    return;
  }
  if (hoverCorner != null) {
    let drawType = "settlement";
    for (let i = 0; i < pieces.length; i++) {
      if (locationsEqual(pieces[i].location, hoverCorner)) {
        if (pieces[i].player == myIdx) {
          drawType = "city";
        }
        break;
      }
    }
    drawPiece(hoverCorner, 'rgba(127, 127, 127, 0.5)', drawType, ctx);
    canvas.style.cursor = "pointer";
    return;
  }
  if (hoverEdge != null) {
    drawRoad(hoverEdge, 'rgba(127, 127, 127, 0.5)', ctx);
    canvas.style.cursor = "pointer";
    return;
  }
  canvas.style.cursor = "auto";
}
function drawRobber(ctx, loc, alpha) {
  if (loc == null) {
    return;
  }
  let isLand = true;
  for (let tile of tiles) {
    if (locationsEqual(tile.location, loc)) {
      isLand = tile.is_land;
      break;
    }
  }
  let canvasLoc = coordToTileCenter(loc);
  let robimg, robWidth, robHeight;
  if (isLand) {
    robimg = document.getElementById("robber");
    robwidth = 26;
    robheight = 60;
  } else {
    robimg = document.getElementById("pirate");
    robwidth = 45;
    robheight = 40;
  }
  ctx.globalAlpha = alpha;
  ctx.drawImage(robimg, canvasLoc.x - robwidth/2, canvasLoc.y - robheight/2, robwidth, robheight);
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
function onclick(event) {
  // Ignore right/middle-click.
  if (event.button != 0) {
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
  if (clickPiece != null && pieces[clickPiece].player == myIdx) {
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
