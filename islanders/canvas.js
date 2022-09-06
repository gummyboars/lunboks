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
turned = false;

hoverTile = null;
hoverNumber = null;
hoverCorner = null;
hoverEdge = null;
hoverTileEdge = null;
moveShipFromLocation = null;

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
function isLand(loc) {
  for (let tile of tiles) {
    if (locationsEqual(tile.location, loc)) {
      return tile.is_land;
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
    drawBarbarians(tiles[i], context);
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
    drawRoad(roads[i].location, playerData[roads[i].player].color, roads[i].road_type,
      roads[i].closed, roads[i].movable, roads[i].conquered, context);
  }
  // Draw pieces over roads.
  for (let i = 0; i < pieces.length; i++) {
    // Each piece does its own context.save() and context.restore();
    drawPiece(pieces[i].location, playerData[pieces[i].player].color, pieces[i].piece_type, pieces[i].conquered, context);
  }
  context.save();
  if (landings != null) {
    for (let i = 0; i < landings.length; i++) {
      drawLanding(landings[i], context);
    }
  }
  context.restore();
  context.save();
  for (let i = 0; i < treasures.length; i++) {
    drawTreasure(treasures[i].location, context);
  }
  context.restore();
  context.save();
  drawHover(context);
  context.restore();
  context.save();
  if (robberLoc != null) {
    drawRobber(context, [robberLoc[0]+1, robberLoc[1]], 1, true);
  }
  drawRobber(context, pirateLoc, 1, false);
  context.restore();
  drawDebug(context);
  context.restore();
  window.requestAnimationFrame(draw);
}

function coordsToEdgeCenter(loc) {
  let leftCorn = coordToCanvasLoc([loc[0], loc[1]]);
  let rightCorn = coordToCanvasLoc([loc[2], loc[3]]);
  return {
    x: (leftCorn.x + rightCorn.x) / 2,
    y: (leftCorn.y + rightCorn.y) / 2,
  };
}
function coordToCanvasLoc(loc) {
  let x = loc[0] * tileWidth / 4;
  let y = loc[1] * tileHeight / 2;
  if (turned) {
    return {x: y, y: -x};
  }
  return {x: x, y: y};
}
function drawRoad(roadLoc, style, road_type, closed, movable, conquered, ctx) {
  if (road_type == null) {
    return;
  }
  let leftCorner = coordToCanvasLoc([roadLoc[0], roadLoc[1]]);
  let rightCorner = coordToCanvasLoc([roadLoc[2], roadLoc[3]]);
  ctx.save();
  let centerX = (leftCorner.x + rightCorner.x) / 2;
  let centerY = (leftCorner.y + rightCorner.y) / 2;
  let rectLength = 0.8 * Math.hypot(rightCorner.x - leftCorner.x, rightCorner.y - leftCorner.y);
  let angle = Math.atan2((rightCorner.y - leftCorner.y), (rightCorner.x - leftCorner.x));
  ctx.translate(centerX, centerY);
  ctx.rotate(angle);
  if (road_type.startsWith("coast") && moveShipFromLocation != null) {
    road_type = "ship";
  }
  if (road_type.endsWith("down")) {
    ctx.rotate(Math.PI);
  }
  ctx.fillStyle = style;
  if (locationsEqual(roadLoc, moveShipFromLocation)) {
    ctx.globalAlpha = 0.5;
  }
  if (road_type.startsWith("coast")) {
    ctx.translate(0, -pieceRadius * 3/2);
  }
  if (!road_type.includes("road")) {
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
    if (closed == null || closed == true) {
      ctx.strokeStyle = "black";
    } else {
      ctx.strokeStyle = style;
    }
    ctx.stroke();
    if (conquered) {
      ctx.fillStyle = "#00000080";
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(-pieceRadius/2, -pieceRadius/2);
      ctx.lineTo(pieceRadius/2, pieceRadius/2);
      ctx.stroke();
      ctx.moveTo(pieceRadius/2, -pieceRadius/2);
      ctx.lineTo(-pieceRadius/2, pieceRadius/2);
      ctx.stroke();
    }
  }
  if (road_type.startsWith("coast")) {
    ctx.translate(0, pieceRadius * 3);
  }
  if (!road_type.includes("ship")) {
    ctx.strokeStyle = "black";
    ctx.fillRect(-rectLength / 2, -pieceRadius / 2, rectLength, pieceRadius);
    ctx.strokeRect(-rectLength / 2, -pieceRadius / 2, rectLength, pieceRadius);
    if (conquered) {
      ctx.fillStyle = "#00000080";
      ctx.fillRect(-rectLength / 2, -pieceRadius / 2, rectLength, pieceRadius);
      ctx.beginPath();
      ctx.moveTo(-pieceRadius/2, -pieceRadius/2);
      ctx.lineTo(pieceRadius/2, pieceRadius/2);
      ctx.stroke();
      ctx.moveTo(pieceRadius/2, -pieceRadius/2);
      ctx.lineTo(-pieceRadius/2, pieceRadius/2);
      ctx.stroke();
    }
  }
  ctx.restore();
}
function drawDebug(ctx) {
  let min, max;
  [min, max] = getMinMax();
  let minX = min.x - 2;
  let minY = min.y - 1;
  let maxX = max.x + 2;
  let maxY = max.y + 1;
  if (debug) {
    ctx.strokeStyle = "white";
    ctx.fillStyle = "white";
    ctx.lineWidth = 1;
    let i, start, end;
    for (i = minX; i <= maxX; i++) {
      start = coordToCanvasLoc([i, minY]);
      end = coordToCanvasLoc([i, maxY]);
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();
      ctx.fillText("" + i, start.x, start.y);
    }
    for (i = minY; i <= maxY; i++) {
      start = coordToCanvasLoc([minX, i]);
      end = coordToCanvasLoc([maxX, i]);
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
    if (hoverTileEdge != null) {
      ctx.fillText("" + hoverTileEdge.edge, 0, 0);
    }
  }
}
function drawLanding(landing, ctx) {
  let canvasLoc = coordToCanvasLoc(landing.location);
  ctx.strokeStyle = "black";
  ctx.beginPath();
  ctx.moveTo(canvasLoc.x, canvasLoc.y - 3 * pieceRadius / 4);
  ctx.lineTo(canvasLoc.x, canvasLoc.y - 2 * pieceRadius);
  ctx.stroke();
  ctx.fillStyle = playerData[landing.player].color;
  ctx.fillRect(canvasLoc.x - pieceRadius, canvasLoc.y - 2*pieceRadius, pieceRadius, pieceRadius/2);
  ctx.strokeRect(canvasLoc.x - pieceRadius, canvasLoc.y - 2*pieceRadius, pieceRadius, pieceRadius/2);
}
function drawPiece(pieceLoc, style, pieceType, conquered, ctx) {
  ctx.save();
  let canvasLoc = coordToCanvasLoc(pieceLoc);
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
    if (conquered) {
      ctx.fillStyle = "#00000080";
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(canvasLoc.x - pieceRadius/2, canvasLoc.y - pieceRadius/4);
      ctx.lineTo(canvasLoc.x + pieceRadius/2, canvasLoc.y + 3*pieceRadius/4);
      ctx.stroke();
      ctx.moveTo(canvasLoc.x + pieceRadius/2, canvasLoc.y - pieceRadius/4);
      ctx.lineTo(canvasLoc.x - pieceRadius/2, canvasLoc.y + 3*pieceRadius/4);
      ctx.stroke();
    }
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
    if (conquered) {
      ctx.fillStyle = "#00000080";
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(canvasLoc.x - pieceRadius/2, canvasLoc.y + pieceRadius/4);
      ctx.lineTo(canvasLoc.x + pieceRadius/2, canvasLoc.y + 5*pieceRadius/4);
      ctx.stroke();
      ctx.moveTo(canvasLoc.x + pieceRadius/2, canvasLoc.y + pieceRadius/4);
      ctx.lineTo(canvasLoc.x - pieceRadius/2, canvasLoc.y + 5*pieceRadius/4);
      ctx.stroke();
    }
  }
  ctx.restore();
}
function drawTreasure(loc, ctx) {
  let canvasLoc = coordToCanvasLoc(loc);
  ctx.fillStyle = "maroon";
  ctx.strokeStyle = "black";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(canvasLoc.x - pieceRadius * 3/2, canvasLoc.y + pieceRadius * 4/3);
  ctx.lineTo(canvasLoc.x - pieceRadius * 3/2, canvasLoc.y - pieceRadius * 1/3);
  ctx.arcTo(canvasLoc.x - pieceRadius * 3/2, canvasLoc.y - pieceRadius, canvasLoc.x - pieceRadius * 5/6, canvasLoc.y - pieceRadius, pieceRadius * 2/3);
  ctx.lineTo(canvasLoc.x + pieceRadius * 5/6, canvasLoc.y - pieceRadius);
  ctx.arcTo(canvasLoc.x + pieceRadius * 3/2, canvasLoc.y - pieceRadius, canvasLoc.x + pieceRadius * 3/2, canvasLoc.y - pieceRadius * 1/3, pieceRadius * 2/3);
  ctx.lineTo(canvasLoc.x + pieceRadius * 3/2, canvasLoc.y + pieceRadius * 4/3);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.moveTo(canvasLoc.x + pieceRadius * 5/6, canvasLoc.y - pieceRadius);
  ctx.arcTo(canvasLoc.x + pieceRadius * 1/6, canvasLoc.y - pieceRadius, canvasLoc.x + pieceRadius * 1/6, canvasLoc.y - pieceRadius * 1/3, pieceRadius * 2/3);
  ctx.lineTo(canvasLoc.x + pieceRadius * 1/6, canvasLoc.y + pieceRadius * 4/3);
  ctx.stroke();
  ctx.moveTo(canvasLoc.x + pieceRadius * 3/2, canvasLoc.y - pieceRadius * 1/3);
  ctx.lineTo(canvasLoc.x - pieceRadius * 3/2, canvasLoc.y - pieceRadius * 1/3);
  ctx.stroke();
}
function drawTile(tileData, ctx) {
  let img = getAsset(tileData.tile_type + "tile", tileData.variant);
  let canvasLoc = coordToCanvasLoc(tileData.location);
  ctx.save();
  ctx.translate(canvasLoc.x, canvasLoc.y);
  let rotation = 0;
  if (tileData.rotation) {
    rotation = (Math.PI * tileData.rotation / 3);
  }
  if (turned) {
    rotation = rotation - Math.PI / 2;
  }
  ctx.rotate(rotation);
  if (img != null) {
    ctx.drawImage(img, -tileWidth/2, -tileHeight/2, tileWidth, tileHeight);
    if (tileData.conquered) {
      let grad = ctx.createRadialGradient(0, 0, tileWidth/8, 0, 0, 2*tileWidth/3);
      grad.addColorStop(0, "#00000080");
      grad.addColorStop(1, "#00000000");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.moveTo(-tileWidth/2, 0);
      ctx.lineTo(-tileWidth/4, -tileHeight/2);
      ctx.lineTo(tileWidth/4, -tileHeight/2);
      ctx.lineTo(tileWidth/2, 0);
      ctx.lineTo(tileWidth/4, tileHeight/2);
      ctx.lineTo(-tileWidth/4, tileHeight/2);
      ctx.lineTo(-tileWidth/2, 0);
      ctx.closePath();
      ctx.fill();
    }
  }
  ctx.restore();
}
function drawBarbarians(tileData, ctx) {
  ctx.save();
  let offsets = [[1, 0], [-1, 0], [0, -0.5], [0, 0.5], [0.5, -0.25], [-0.5, 0.25]];
  let barbarians = tileData.barbarians || 0;
  for (let i = 0; i < barbarians && i < 6; i++) {
    let newLoc = [tileData.location[0] + offsets[i][0], tileData.location[1] + offsets[i][1]];
    let alpha = 1;
    if (i == barbarians - 1 && turnPhase == "expel" && locationsEqual(hoverTile, tileData.location)) {
      alpha = 0.5;
    }
    drawRobber(ctx, newLoc, alpha, tileData.is_land);
  }
  ctx.restore();
}
function drawPort(portData, ctx) {
  let portImg = getAsset("port", portData.variant);
  let img = getAsset(portData.port_type + "port", portData.variant);
  let canvasLoc = coordToCanvasLoc(portData.location);
  ctx.save();
  ctx.translate(canvasLoc.x, canvasLoc.y);
  let rotation = 0;
  if (portData.rotation) {
    rotation = (Math.PI * portData.rotation / 3);
  }
  if (turned) {
    rotation = rotation - Math.PI / 2;
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
  let canvasLoc = coordToCanvasLoc(tileData.location);
  ctx.save();
  ctx.translate(canvasLoc.x, canvasLoc.y);
  for (let rotation of tileData.land_rotations) {
    if ((rotation+6)%6 == portRotation) {
      continue;
    }
    ctx.save();
    let finalRotation = 0;
    finalRotation = (Math.PI * rotation / 3);
    if (turned) {
      finalRotation = finalRotation - Math.PI / 2;
    }
    ctx.rotate(finalRotation);
    ctx.drawImage(coastImg, -tileWidth/2, -tileHeight/2, tileWidth, tileHeight);
    ctx.restore();
  }
  ctx.restore();
}
function drawNumber(tileData, ctx) {
  let textHeightOffset = 12; // Adjust as necessary. TODO: textBaseline = middle?
  let canvasLoc = coordToCanvasLoc(tileData.location);
  ctx.save();
  let num = tileData.number;
  if (!num && locationsEqual(targetTile, tileData.location) && hoverNumber != null) {
    num = hoverNumber;
  }
  if (num) {
    // Draw the white circle.
    ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
    if (tileData.conquered) {
      ctx.fillStyle = '#FFFFFF33';
    }
    ctx.beginPath();
    ctx.arc(canvasLoc.x, canvasLoc.y, 28, 0, Math.PI * 2, true);
    ctx.fill();
    // Draw the number.
    if (num == '6' || num == '8') {
      ctx.fillStyle = 'red';
      ctx.font = 'bold 36px sans-serif';
    } else {
      ctx.fillStyle = 'black';
      ctx.font = 'bold 32px sans-serif';
    }
    if (tileData.conquered) {
      ctx.globalAlpha = 0.25;
    }
    if (turnPhase == "deplete" && turn == myIdx) {
      if (locationsEqual(hoverTile, tileData.location)) {
        ctx.globalAlpha = 0.25;
      }
      if (locationsEqual(targetTile, tileData.location)) {
        ctx.globalAlpha = 0.75;
      }
    }
    ctx.fillText(num + "", canvasLoc.x, canvasLoc.y + textHeightOffset);
  }
  ctx.restore();
}
function drawHover(ctx) {
  if (extraBuildTurn != null && extraBuildTurn != myIdx) {
    return;
  }
  if (extraBuildTurn == null && turn != myIdx) {
    return;
  }
  let canvas = document.getElementById("myCanvas");
  if (hoverTile != null) {
    if (["expel", "deplete"].includes(turnPhase)) {
      return;
    }
    if (!locationsEqual(robberLoc, hoverTile) && !locationsEqual(pirateLoc, hoverTile)) {
      if (isLand(hoverTile)) {
        drawRobber(ctx, [hoverTile[0]+1, hoverTile[1]], 0.5, true);
      } else {
        drawRobber(ctx, hoverTile, 0.5, false);
      }
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
    drawPiece(hoverCorner, 'rgba(127, 127, 127, 0.5)', drawType, false, ctx);
    canvas.style.cursor = "pointer";
    return;
  }
  if (hoverEdge != null) {
    drawRoad(hoverEdge.location, 'rgba(127, 127, 127, 0.5)', hoverEdge.edge_type, null, null, false, ctx);
    canvas.style.cursor = "pointer";
    return;
  }
  if (hoverTileEdge != null) {
    if (turnPhase == "placeport" && placementPort != null) {
      if (tiles[hoverTileEdge.tileNum].is_land) {
        return;
      }
      let tmpPort = {
        port_type: placementPort,
        location: tiles[hoverTileEdge.tileNum].location,
        rotation: hoverTileEdge.rotation,
      };
      drawPort(tmpPort, ctx);
      canvas.style.cursor = "pointer";
      return;
    }
    let edgeType = null;
    for (let i = 0; i < edges.length; i++) {
      if (locationsEqual(edges[i].location, hoverTileEdge.edge)) {
        edgeType = edges[i].edge_type;
        break;
      }
    }
    if (edgeType != null && edgeType.startsWith("coast")) {
      let shipAbove = tiles[hoverTileEdge.tileNum].location[1] < (hoverTileEdge.edge[1] + hoverTileEdge.edge[3]) / 2;
      if (edgeType == "coastdown") {
        shipAbove = !shipAbove;
      }
      let drawType = "coast";
      drawType += shipAbove ? "ship" : "road";
      drawType += edgeType == "coastup" ? "up" : "down";
      drawRoad(hoverTileEdge.edge, "rgba(127, 127, 127, 0.5)", drawType, null, null, null, ctx);
      canvas.style.cursor = "pointer";
      return;
    }
  }
  canvas.style.cursor = "auto";
}
function drawRobber(ctx, loc, alpha, land) {
  if (loc == null) {
    return;
  }
  let canvasLoc = coordToCanvasLoc(loc);
  let robimg, robWidth, robHeight;
  if (land) {
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
    let canvasLoc = coordToCanvasLoc(cList[i].location);
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
    let canvasLoc = coordToCanvasLoc(tiles[i].location);
    let centerX = canvasLoc.x * scale + offsetX + dX;
    let centerY = canvasLoc.y * scale + offsetY + dY;
    let distanceX = eventX - centerX;
    let distanceY = eventY - centerY;
    let distance = distanceX * distanceX + distanceY * distanceY;
    let radius = 42 * scale;
    if (distance < radius * radius) {
      return i;
    }
  }
  return null;
}
function getTileEdge(eventX, eventY) {
  for (let i = 0; i < tiles.length; i++) {
    let cornerOffsets = [[1, 1], [-1, 1], [-2, 0], [-1, -1], [1, -1], [2, 0], [1, 1]];
    for (let j = 0; j < 6; j++) {
      let loc1 = coordToCanvasLoc(tiles[i].location);
      let loc2 = coordToCanvasLoc([
        tiles[i].location[0] + cornerOffsets[j][0], tiles[i].location[1] + cornerOffsets[j][1]
      ]);
      let loc3 = coordToCanvasLoc([
        tiles[i].location[0] + cornerOffsets[j+1][0], tiles[i].location[1] + cornerOffsets[j+1][1]
      ]);
      let newX = (2*loc1.x + 3*loc2.x + 3*loc3.x) / 8;
      let newY = (2*loc1.y + 3*loc2.y + 3*loc3.y) / 8;
      let centerX = newX * scale + offsetX + dX;
      let centerY = newY * scale + offsetY + dY;
      let distanceX = eventX - centerX;
      let distanceY = eventY - centerY;
      let distance = distanceX * distanceX + distanceY * distanceY;
      let radius = pieceRadius * scale;
      if (distance < radius * radius) {
        let edge = [
          tiles[i].location[0] + cornerOffsets[j][0], tiles[i].location[1] + cornerOffsets[j][1],
          tiles[i].location[0] + cornerOffsets[j+1][0], tiles[i].location[1] + cornerOffsets[j+1][1],
        ];
        if (cornerOffsets[j][0] > cornerOffsets[j+1][0]) {
          edge = [edge[2], edge[3], edge[0], edge[1]];
        }
        return {tileNum: i, rotation: j, edge: edge};
      }
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
    let clickType = (tiles[clickTile].is_land ? "robber" : "pirate");
    if (["expel", "deplete"].includes(turnPhase)) {
      clickType = turnPhase;
    }
    let msg = {
      type: clickType,
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
    if (moveShipFromLocation != null) {
      let msg = {
        type: "move_ship",
        from: moveShipFromLocation,
        to: edges[clickEdge].location,
      };
      ws.send(JSON.stringify(msg));
      moveShipFromLocation = null;
      return;
    }
    if (edges[clickEdge].edge_type && !edges[clickEdge].edge_type.startsWith("coast")) {
      for (let road of roads) {
        if (locationsEqual(road.location, edges[clickEdge].location)) {
          if (road.player == myIdx && road.road_type == "ship") {
            moveShipFromLocation = road.location;
          }
          break;
        }
      }
      if (moveShipFromLocation == null) {
        let msg = {
          type: edges[clickEdge].edge_type,
          location: edges[clickEdge].location,
        };
        ws.send(JSON.stringify(msg));
      }
    }
  } else if (moveShipFromLocation != null) {
    moveShipFromLocation = null;
  }
  let clickTileEdge = getTileEdge(event.clientX, event.clientY);
  if (clickTileEdge != null) {
    if (turnPhase == "placeport" && placementPort != null) {
      let msg = {
        type: "placeport",
        location: tiles[clickTileEdge.tileNum].location,
        rotation: clickTileEdge.rotation,
      };
      ws.send(JSON.stringify(msg));
      return;
    }
    let edgeType = null;
    for (let i = 0; i < edges.length; i++) {
      if (locationsEqual(edges[i].location, clickTileEdge.edge)) {
        edgeType = edges[i].edge_type;
        break;
      }
    }
    if (edgeType != null && edgeType.startsWith("coast")) {
      let shipAbove = tiles[clickTileEdge.tileNum].location[1] < (clickTileEdge.edge[1] + clickTileEdge.edge[3]) / 2;
      if (edgeType == "coastdown") {
        shipAbove = !shipAbove;
      }
      let msg = {
        type: shipAbove ? "ship" : "road",
        location: clickTileEdge.edge,
      };
      ws.send(JSON.stringify(msg));
    }
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
  if (hoverLoc != null && turn == myIdx) {
    hoverNumber = tiles[hoverLoc].number;
  } else {
    hoverNumber = null;
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
  hoverTileEdge = getTileEdge(event.clientX, event.clientY);
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
  let minLoc = coordToCanvasLoc([min.x, min.y]);
  let maxLoc = coordToCanvasLoc([max.x, max.y]);
  return {x: (minLoc.x + maxLoc.x) / 2, y: (minLoc.y + maxLoc.y) / 2};
}
function centerCanvas() {
  let center = getCenterCoord();
  offsetX = canWidth / 2 - center.x;
  offsetY = canHeight / 2 - center.y;
}
