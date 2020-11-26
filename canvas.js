// For manipulating the canvas.
isDragging = false;
ignoreNextClick = false;
startX = null;
startY = null;
offsetX = 0;
offsetY = 0;
dX = 0;
dY = 0;
scale = 1;
eventX = null;
eventY = null;
flipped = false;

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
  let portMap = {};
  for (let i = 0; i < ports.length; i++) {
    let loc = ports[i].location.toString();
    portMap[loc] = ports[i];
  }
  context.save();
  for (let i = 0; i < tiles.length; i++) {
    drawTile(tiles[i], context);
    drawNumber(tiles[i], context);
  }
  context.restore();
  context.save();
  for (let i = 0; i < ports.length; i++) {
    drawPort(ports[i], context);
  }
  context.restore();
  context.save();
  for (let i = 0; i < tiles.length; i++) {
    if (!tiles[i].is_land) {
      drawCoast(tiles[i], portMap, context);
    }
  }
  context.restore();
  for (let i = 0; i < roads.length; i++) {
    // Each road does its own context.save() and context.restore();
    drawRoad(roads[i].location, playerData[roads[i].player].color, roads[i].road_type, context);
  }
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
  let robberOpacity = 1;
  if (robberLoc != null && locationsEqual(robberLoc, hoverTile)) {
    robberOpacity = 0.5;
  }
  drawRobber(context, robberLoc, robberOpacity);
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
  if (flipped) {
    return {x: y, y: x};
  }
  return {x: x, y: y};
}
function coordToTileUpperLeft(loc) {
  let x = loc[0] * tileWidth * 3 / 8 - tileWidth / 4;
  let y = loc[1] * tileHeight / 2;
  if (flipped) {
    return {x: y, y: x};
  }
  return {x: x, y: y};
}
function coordToTileCenter(loc) {
  let ul = coordToTileUpperLeft(loc);
  if (flipped) {
    return {x: ul.x + tileHeight/2, y: ul.y + tileWidth/2};
  }
  return {x: ul.x + tileWidth/2, y: ul.y + tileHeight/2};
}
function drawRoad(roadLoc, style, road_type, ctx) {
  if (road_type == null) {
    return;
  }
  let leftCorner = coordToCornerCenter([roadLoc[0], roadLoc[1]]);
  let rightCorner = coordToCornerCenter([roadLoc[2], roadLoc[3]]);
  ctx.save();
  let centerX = (leftCorner.x + rightCorner.x) / 2;
  let centerY = (leftCorner.y + rightCorner.y) / 2;
  let rectLength = 0.8 * Math.hypot(rightCorner.x - leftCorner.x, rightCorner.y - leftCorner.y);
  let angle = Math.atan2((rightCorner.y - leftCorner.y), (rightCorner.x - leftCorner.x));
  ctx.translate(centerX, centerY);
  ctx.rotate(angle);
  if (road_type == "coastdown") {
    ctx.rotate(Math.PI);
  }
  if (flipped) {
    ctx.rotate(Math.PI);
  }
  ctx.fillStyle = style;
  ctx.strokeStyle = "black";
  if (road_type.startsWith("coast")) {
    ctx.translate(0, -pieceRadius / 2);
  }
  if (road_type != "road") {
    ctx.beginPath();
    ctx.moveTo(-rectLength / 2, -pieceRadius / 2);
    ctx.lineTo(-3 * pieceRadius / 4, -pieceRadius / 2);
    ctx.arc(-3 * pieceRadius / 4, -pieceRadius / 2, 1.5 * pieceRadius, -Math.PI / 2, 0, false);
    ctx.lineTo(rectLength / 2, -pieceRadius / 2);
    ctx.arc(rectLength / 2 - pieceRadius, -pieceRadius / 2, pieceRadius, 0, Math.PI / 2, false);
    ctx.lineTo(-rectLength / 2 + pieceRadius, pieceRadius / 2);
    ctx.arc(-rectLength / 2 + pieceRadius, -pieceRadius / 2, pieceRadius, Math.PI / 2 , Math.PI, false);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }
  if (road_type.startsWith("coast")) {
    ctx.translate(0, pieceRadius);
  }
  if (road_type != "ship") {
    ctx.fillRect(-rectLength / 2, -pieceRadius / 2, rectLength, pieceRadius);
    ctx.strokeRect(-rectLength / 2, -pieceRadius / 2, rectLength, pieceRadius);
  }
  ctx.restore();
}
function drawDebug(ctx) {
  let min, max;
  [min, max] = getMinMax();
  let minX = min.x - 2;
  let minY = min.y;
  let maxX = max.x + 3;
  let maxY = max.y + 2;
  if (debug) {
    ctx.strokeStyle = "white";
    ctx.fillStyle = "white";
    ctx.lineWidth = 1;
    let i, start, end;
    for (i = minX; i <= maxX; i++) {
      start = coordToCornerCenter([i, minY]);
      end = coordToCornerCenter([i, maxY]);
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();
      ctx.fillText("" + i, start.x, start.y);
    }
    for (i = minY; i <= maxY; i++) {
      start = coordToCornerCenter([minX, i]);
      end = coordToCornerCenter([maxX, i]);
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();
      ctx.fillText("" + i, start.x-10, start.y);
    }
    if (hoverTile != null) {
      ctx.fillText("" + hoverTile[0] + ", " + hoverTile[1], 0, 0);
    }
    if (hoverCorner != null) {
      ctx.fillText("" + hoverCorner[0] + ", " + hoverCorner[1], 0, 0);
    }
    if (hoverEdge != null) {
      ctx.fillText("" + hoverEdge.location, 0, 0);
    }
  }
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
  let img = getAsset(tileData.tile_type + "tile", tileData.variant);
  let canvasLoc = coordToTileCenter(tileData.location);
  ctx.save();
  ctx.translate(canvasLoc.x, canvasLoc.y);
  let rotation = 0;
  if (tileData.rotation) {
    rotation = (Math.PI * tileData.rotation / 3);
  }
  if (flipped) {
    rotation = -rotation - (Math.PI / 2);
  }
  ctx.rotate(rotation);
  if (flipped) {
    ctx.transform(-1, 0, 0, 1, 0, 0);
  }
  if (img != null) {
    ctx.drawImage(img, -tileWidth/2, -tileHeight/2, tileWidth, tileHeight);
  }
  ctx.restore();
}
function drawPort(portData, ctx) {
  let portImg = getAsset("port", portData.variant);
  let img = getAsset(portData.port_type + "port", portData.variant);
  let canvasLoc = coordToTileCenter(portData.location);
  ctx.save();
  ctx.translate(canvasLoc.x, canvasLoc.y);
  let rotation = 0;
  if (portData.rotation) {
    rotation = (Math.PI * portData.rotation / 3);
  }
  if (flipped) {
    rotation = -rotation - (Math.PI / 2);
  }
  ctx.rotate(rotation);
  if (portImg != null) {
    ctx.drawImage(portImg, -tileWidth/2, -tileHeight/2, tileWidth, tileHeight);
  }
  if (img != null) {
    ctx.drawImage(img, -tileWidth/2, -tileHeight/2, tileWidth, tileHeight);
  }
  ctx.restore();
}
function drawCoast(tileData, portMap, ctx) {
  let coastImg = getAsset("coast", tileData.variant);
  if (coastImg == null || !Array.isArray(tileData.land_rotations)) {
    return;
  }
  let portData = portMap[tileData.location.toString()];
  let portRotation = null;
  if (portData != null) {
    portRotation = (portData.rotation + 6) % 6;
  }
  let canvasLoc = coordToTileCenter(tileData.location);
  ctx.save();
  ctx.translate(canvasLoc.x, canvasLoc.y);
  for (let rotation of tileData.land_rotations) {
    if ((rotation+6)%6 == portRotation) {
      continue;
    }
    ctx.save();
    let finalRotation = 0;
    finalRotation = (Math.PI * rotation / 3);
    if (flipped) {
      finalRotation = -finalRotation - (Math.PI / 2);
    }
    ctx.rotate(finalRotation);
    if (flipped) {
      ctx.transform(-1, 0, 0, 1, 0, 0);
    }
    ctx.drawImage(coastImg, -tileWidth/2, -tileHeight/2, tileWidth, tileHeight);
    ctx.restore();
  }
  ctx.restore();
}
function drawNumber(tileData, ctx) {
  let textHeightOffset = 12; // Adjust as necessary. TODO: textBaseline = middle?
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
    if (!locationsEqual(robberLoc, hoverTile)) {
      drawRobber(ctx, hoverTile, 0.5);
      canvas.style.cursor = "pointer";
    }
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
    drawRoad(hoverEdge.location, 'rgba(127, 127, 127, 0.5)', hoverEdge.edge_type, ctx);
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
    robimg = getAsset("robber");
    robwidth = 26;
    robheight = 60;
  } else {
    robimg = getAsset("pirate");
    robwidth = 54;
    robheight = 48;
  }
  ctx.globalAlpha = alpha;
  if (robimg != null) {
    ctx.drawImage(robimg, canvasLoc.x - robwidth/2, canvasLoc.y - robheight/2, robwidth, robheight);
  }
}
function getEdge(eventX, eventY) {
  for (let i = 0; i < edges.length; i++) {
    let edgeCenter = coordsToEdgeCenter(edges[i].location);
    let centerX = edgeCenter.x * scale + offsetX + dX;
    let centerY = edgeCenter.y * scale + offsetY + dY;
    let distanceX = eventX - centerX;
    let distanceY = eventY - centerY;
    let distance = distanceX * distanceX + distanceY * distanceY;
    let radius = pieceRadius * scale;
    if (distance < radius * radius) {
      return i;
    }
  }
}
function getCorner(eventX, eventY, cList) {
  for (let i = 0; i < cList.length; i++) {
    let canvasLoc = coordToCornerCenter(cList[i].location);
    let centerX = canvasLoc.x * scale + offsetX + dX;
    let centerY = canvasLoc.y * scale + offsetY + dY;
    let distanceX = eventX - centerX;
    let distanceY = eventY - centerY;
    let distance = distanceX * distanceX + distanceY * distanceY;
    let radius = pieceRadius * scale;
    if (distance < radius * radius) {
      return i;
    }
  }
}
function getTile(eventX, eventY) {
  for (let i = 0; i < tiles.length; i++) {
    let canvasLoc = coordToTileCenter(tiles[i].location);
    let centerX = canvasLoc.x * scale + offsetX + dX;
    let centerY = canvasLoc.y * scale + offsetY + dY;
    let distanceX = eventX - centerX;
    let distanceY = eventY - centerY;
    let distance = distanceX * distanceX + distanceY * distanceY;
    let radius = 50 * scale;
    if (distance < radius * radius) {
      return i;
    }
  }
  return null;
}
function onclick(event) {
  if (ignoreNextClick) {
    ignoreNextClick = false;
    return;
  }
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
  eventX = event.clientX;
  eventY = event.clientY;
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
    hoverEdge = edges[hoverLoc];
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
  let oldScale = scale;
  if (event.deltaY < 0) {
    scale += 0.05;
  } else if (event.deltaY > 0) {
    scale -= 0.05;
  }
  scale = Math.min(Math.max(0.125, scale), 4);
  offsetX = event.clientX - ((event.clientX - offsetX) * scale / oldScale);
  offsetY = event.clientY - ((event.clientY - offsetY) * scale / oldScale);
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
  if (isDragging && (dX != 0 || dY != 0)) {
    ignoreNextClick = true;
  }
  isDragging = false;
  offsetX += dX;
  offsetY += dY;
  dX = 0;
  dY = 0;
}
function getMinMax() {
  if (tiles.length < 1) {
    return [{x: 0, y: 0}, {x: 0, y: 0}];
  }
  let minX, maxX, minY, maxY;
  let loc = tiles[0].location;
  [minX, maxX, minY, maxY] = [loc[0], loc[0], loc[1], loc[1]];
  for (let i = 0; i < tiles.length; i++) {
    if (!tiles[i].is_land) {
      continue;
    }
    minX = Math.min(tiles[i].location[0], minX);
    minY = Math.min(tiles[i].location[1], minY);
    maxX = Math.max(tiles[i].location[0], maxX);
    maxY = Math.max(tiles[i].location[1], maxY);
  }
  return [{x: minX, y: minY}, {x: maxX, y: maxY}];
}
function getCenterCoord() {
  let min, max;
  [min, max] = getMinMax();
  let minLoc = coordToTileCenter([min.x, min.y]);
  let maxLoc = coordToTileCenter([max.x, max.y]);
  return {x: (minLoc.x + maxLoc.x) / 2, y: (minLoc.y + maxLoc.y) / 2};
}
function centerCanvas() {
  let center = getCenterCoord();
  offsetX = canWidth / 2 - center.x;
  offsetY = canHeight / 2 - center.y;
}
