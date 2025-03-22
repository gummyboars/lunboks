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
minCoord = {x: 0, y: 0};
maxCoord = {x: 0, y: 0};

hoverTile = null;  // The tile object
hoverCorner = null;  // The location x, y coordinates
hoverEdge = null;  // An edge object with a location and an edge_type
hoverTileEdge = null;  // An object with tile, edge, and rotation
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
function coordsFromElem(elem) {
  if (elem.location.length == 2) {
    return elem.location;
  }
  if (elem.location.length == 4) {
    return [(elem.location[0]+elem.location[2])/2, (elem.location[1]+elem.location[3])/2];
  }
  throw new Error(`Invalid location ${elem.location}`);
}

function draw() {
  var canvas = document.getElementById('myCanvas');
  var context = canvas.getContext('2d');

  if (tiles.length < 1) {
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
  [min, max] = getTileMinMax(false);
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
      ctx.fillText("" + hoverTile.location[0] + ", " + hoverTile.location[1], 0, 0);
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
    if (i == barbarians - 1 && turnPhase == "expel" && hoverTile != null && locationsEqual(hoverTile.location, tileData.location)) {
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
  if (!num && locationsEqual(targetTile, tileData.location) && hoverTile != null && hoverTile.number != null) {
    num = hoverTile.number;
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
      if (hoverTile != null && locationsEqual(hoverTile.location, tileData.location)) {
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
    if (!locationsEqual(robberLoc, hoverTile.location) && !locationsEqual(pirateLoc, hoverTile.location)) {
      if (hoverTile.is_land) {
        drawRobber(ctx, [hoverTile.location[0]+1, hoverTile.location[1]], 0.5, true);
      } else {
        drawRobber(ctx, hoverTile.location, 0.5, false);
      }
    }
    return;
  }
  if (hoverCorner != null) {
    let drawType = null;
    if (pieceMatrix[hoverCorner[0]] != null && pieceMatrix[hoverCorner[0]][hoverCorner[1]] != null) {
      if (pieceMatrix[hoverCorner[0]][hoverCorner[1]].player == myIdx) {
        drawType = "city";
      }
    }
    if (drawType == null) {
      if (cornerMatrix[hoverCorner[0]] != null && cornerMatrix[hoverCorner[0]][hoverCorner[1]] != null) {
        drawType = "settlement";
      }
    }
    if (drawType != null) {
      drawPiece(hoverCorner, 'rgba(127, 127, 127, 0.5)', drawType, false, ctx);
    }
    return;
  }
  let edgeType = null;
  if (hoverTileEdge != null) {
    if (turnPhase == "placeport" && placementPort != null) {
      if (hoverTileEdge.tile.is_land) {
        return;
      }
      let tmpPort = {
        port_type: placementPort,
        location: hoverTileEdge.tile.location,
        rotation: hoverTileEdge.rotation,
      };
      drawPort(tmpPort, ctx);
      return;
    }
    let [edgeX, edgeY] = [(hoverTileEdge.edge[0]+hoverTileEdge.edge[2])/2, (hoverTileEdge.edge[1]+hoverTileEdge.edge[3])/2];
    if (edgeMatrix[edgeX] != null && edgeMatrix[edgeX][edgeY] != null) {
      edgeType = edgeMatrix[edgeX][edgeY].edge_type;
    }
    if (edgeType != null && edgeType.startsWith("coast")) {
      let shipAbove = hoverTileEdge.tile.location[1] < edgeY;
      if (edgeType == "coastdown") {
        shipAbove = !shipAbove;
      }
      let drawType = "coast";
      drawType += shipAbove ? "ship" : "road";
      drawType += edgeType == "coastup" ? "up" : "down";
      drawRoad(hoverTileEdge.edge, "rgba(127, 127, 127, 0.5)", drawType, null, null, null, ctx);
      return;
    }
  }
  if ((edgeType == null || !edgeType.startsWith("coast")) && hoverEdge != null) {
    drawRoad(hoverEdge.location, 'rgba(127, 127, 127, 0.5)', hoverEdge.edge_type, null, null, false, ctx);
    return;
  }
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
function onClickTile(event, tileLoc) {
  if (event.button != 0) {
    return;
  }
  if (ignoreNextClick) {
    ignoreNextClick = false;
    return;
  }
  if (tileMatrix[tileLoc[0]] != null && tileMatrix[tileLoc[0]][tileLoc[1]] != null) {
    let clickType = (tileMatrix[tileLoc[0]][tileLoc[1]].is_land ? "robber" : "pirate");
    if (["expel", "deplete"].includes(turnPhase)) {
      clickType = turnPhase;
    }
    let msg = {
      type: clickType,
      location: tileLoc,
    };
    ws.send(JSON.stringify(msg));
  }
}
function onClickCorner(event, cornerLoc) {
  if (event.button != 0) {
    return;
  }
  if (ignoreNextClick) {
    ignoreNextClick = false;
    return;
  }
  if (pieceMatrix[cornerLoc[0]] != null && pieceMatrix[cornerLoc[0]][cornerLoc[1]] != null) {
    if (pieceMatrix[cornerLoc[0]][cornerLoc[1]].player == myIdx) {
      let msg = {
        type: "city",
        location: cornerLoc,
      };
      ws.send(JSON.stringify(msg));
      return;
    }
  }
  let msg = {
    type: "settle",
    location: cornerLoc,
  };
  ws.send(JSON.stringify(msg));
}
function onClickEdge(event, edgeLoc) {
  if (event.button != 0) {
    return;
  }
  if (ignoreNextClick) {
    ignoreNextClick = false;
    return;
  }
  if (moveShipFromLocation != null) {
    if (locationsEqual(moveShipFromLocation, edgeLoc)) {  // Cancel moving ship
      moveShipFromLocation = null;
      draw();
      return;
    }
    let msg = {
      type: "move_ship",
      from: moveShipFromLocation,
      to: edgeLoc,
    };
    ws.send(JSON.stringify(msg));
    moveShipFromLocation = null;
    return;
  }
  let edgeType = null;
  let [edgeX, edgeY] = [(edgeLoc[0]+edgeLoc[2])/2, (edgeLoc[1]+edgeLoc[3])/2];
  if (edgeMatrix[edgeX] != null && edgeMatrix[edgeX][edgeY] != null) {
    edgeType = edgeMatrix[edgeX][edgeY].edge_type;
  }
  if (edgeType && !edgeType.startsWith("coast")) {  // Coast must use tileedge instead
    if (roadMatrix[edgeX] != null && roadMatrix[edgeX][edgeY] != null) {
      if (roadMatrix[edgeX][edgeY].player == myIdx && roadMatrix[edgeX][edgeY].road_type == "ship") {
        moveShipFromLocation = edgeLoc;
        event.stopPropagation();
        draw();
        return;
      }
    }
    let msg = {
      type: edgeType,
      location: edgeLoc,
    };
    ws.send(JSON.stringify(msg));
  }
}
function onClickTileEdge(event, tileLoc, edgeLoc, rotation) {
  if (event.button != 0) {
    return;
  }
  if (ignoreNextClick) {
    ignoreNextClick = false;
    return;
  }
  if (turnPhase == "placeport" && placementPort != null) {
    let msg = {
      type: "placeport",
      port: placementPort,
      location: tileLoc,
      rotation: rotation,
    };
    ws.send(JSON.stringify(msg));
    return;
  }
  let edgeType = null;
  let [edgeX, edgeY] = [(edgeLoc[0]+edgeLoc[2])/2, (edgeLoc[1]+edgeLoc[3])/2];
  if (edgeMatrix[edgeX] != null && edgeMatrix[edgeX][edgeY] != null) {
    edgeType = edgeMatrix[edgeX][edgeY].edge_type;
  }
  if (edgeType != null && edgeType.startsWith("coast")) {
    let shipAbove = tileLoc[1] < (edgeLoc[1] + edgeLoc[3]) / 2;
    if (edgeType == "coastdown") {
      shipAbove = !shipAbove;
    }
    let msg = {
      type: shipAbove ? "ship" : "road",
      location: edgeLoc,
    };
    ws.send(JSON.stringify(msg));
  }
}
function onclick(event) {
  // Ignore right/middle-click.
  if (event.button != 0) {
    return;
  }
  if (ignoreNextClick) {
    ignoreNextClick = false;
    return;
  }
  if (moveShipFromLocation != null) {
    moveShipFromLocation = null;
    draw();
  }
}
function onmove(event) {
  eventX = event.clientX;
  eventY = event.clientY;
  if (isDragging) {
    newX = event.clientX;
    newY = event.clientY;
    
    dX = newX - startX;
    dY = newY - startY;
    moveGrid();
    draw();
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
  moveGrid();
  draw();
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
function canvasup(event) {
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
function getTileMinMax(includeAll) {
  if (tiles.length < 1) {
    return [{x: 0, y: 0}, {x: 0, y: 0}];
  }
  let minX, maxX, minY, maxY;
  let loc = tiles[0].location;
  [minX, maxX, minY, maxY] = [loc[0], loc[0], loc[1], loc[1]];
  for (let i = 0; i < tiles.length; i++) {
    if (!includeAll && !tiles[i].is_land) {
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
  let minLoc = coordToCanvasLoc([minCoord.x, minCoord.y]);
  let maxLoc = coordToCanvasLoc([maxCoord.x, maxCoord.y]);
  return {x: (minLoc.x + maxLoc.x) / 2, y: (minLoc.y + maxLoc.y) / 2};
}
function centerCanvas() {
  let center = getCenterCoord();
  offsetX = canWidth / 2 - center.x;
  offsetY = canHeight / 2 - center.y;
  moveGrid();
}
function moveGrid() {
  let grid = document.getElementById("grid");
  if (grid == null) {
    return;
  }
  let minXCoord = minCoord.x - 2;  // Minimum corner coordinate is two steps left of the minimum tile x coordinate.
  let minYCoord = minCoord.y - 1;  // Minimum corner coordinate is one step up from the minimum tile y coordinate.
  // We want the coordinate to be in the center of the box, so adjust the x coordinate by -0.5
  let targetXCoord = minXCoord - 0.5;
  // We will have two boxes for each one y coordinate, so adjust the y coordinate by -0.25
  let targetYCoord = minYCoord - 0.25;
  let targetLoc = coordToCanvasLoc([targetXCoord, targetYCoord]);
  let rotation = "rotate(0deg)";
  if (turned) {
    rotation = "rotate(-90deg)";
  }
  grid.style.transform = "translate(" + (offsetX + dX + targetLoc.x*scale) + "px, " + (offsetY + dY + targetLoc.y*scale) + "px) scale(" + scale + ") " + rotation;
}
function remakeGrid() {
  let grid = document.getElementById("grid");
  if (grid != null) {
    grid.parentNode.removeChild(grid);
  }
  let minXCoord = minCoord.x - 2;
  let minYCoord = minCoord.y - 1;
  let maxXCoord = maxCoord.x + 2;
  let maxYCoord = maxCoord.y + 1;
  let numCols = maxXCoord - minXCoord + 1;
  let numRows = (maxYCoord - minYCoord) * 2 + 1;
  grid = document.createElement("DIV");
  grid.id = "grid";
  grid.style.gridTemplateColumns = "repeat(" + numCols + ", " + tileWidth / 4 + "px)";
  grid.style.gridTemplateRows = "repeat(" + numRows + ", " + tileHeight / 4 + "px)";
  grid.style.width = tileWidth * (numCols) / 4 + "px";
  grid.style.height = tileHeight * (numRows) / 4 + "px";
  grid.onmousemove = onmove;
  grid.onclick = onclick;
  grid.onmousedown = ondown;
  grid.onwheel = onwheel;
  document.getElementById("uioverlay").appendChild(grid);
  for (let j = 0; j < numRows; j++) {
    for (let i = 0; i < numCols; i++) {
      let x = minXCoord + i;
      let y = minYCoord + j/2;
      let xMod6 = (x % 6 + 6) % 6;
      let yMod4 = (y % 4 + 4) % 4;
      if (xMod6 % 3 == 1 && yMod4 % 2 == (xMod6 % 2)) {  // Tile center
        createTileBox(grid, x, y, i, j);
      } 
      if (xMod6 % 3 == 1 && j % 2 == 0 && yMod4 % 2 != (xMod6 % 2)) {  // Top/bottom edge
        let xleft = x-1;
        let xright = x+1;
        createEdgeBox(grid, xleft, y, xright, y, i, j, 1);
      }
      if (j % 2 == 1 && (xMod6 % 3) == 2) {
        let isUp = false;
        let yleft;
        let yright;
        if (xMod6 == 2 && (y + 0.5) % 2 == 0) {
          isUp = false;
        } else if (xMod6 == 2) {
          isUp = true;
        } else if (xMod6 == 5 && (y + 0.5) % 2 == 0) {
          isUp = true;
        } else if (xMod6 == 5) {
          isUp = false;
        }
        if (isUp) {
          yleft = y - 0.5;
          yright = y + 0.5;
        } else {
          yleft = y + 0.5;
          yright = y - 0.5;
        }
        createEdgeBox(grid, x, yleft, x+1, yright, i, j, 2);
      }
      if (xMod6 != 1 && xMod6 != 4 && ((xMod6 < 3 && yMod4 % 2 == 0) || (xMod6 >= 3 && yMod4 % 2 == 1))) {  // Corner
        createCornerBox(grid, x, y, i, j);
      }
    }
  }
}
function createTileBox(grid, x, y, i, j) {
  let elem = document.createElement("DIV");
  elem.classList.add("gridelem", "tilebox");
  elem.style.width = 3 * tileHeight / 5 + "px";
  elem.style.height = 3 * tileHeight / 5 + "px";
  elem.style.gridColumn = (i) + "/" + (i + 3);
  elem.style.gridRow = (j) + "/" + (j + 3);
  elem.innerText = `${x}, ${y}`;
  grid.appendChild(elem);
  elem.onmouseenter = function() {
    if (tileMatrix[x] != null && tileMatrix[x][y] != null) {
      if (turn == myIdx) {
        hoverTile = tileMatrix[x][y];
        draw();
      }
    }
  };
  elem.onmouseleave = function() {
    if (hoverTile != null && locationsEqual(hoverTile.location, [x, y])) {
      hoverTile = null;
      draw();
    }
  };
  elem.onclick = function(event) { onClickTile(event, [x, y]); };
  let cornerOffsets = [[1, 1], [-1, 1], [-2, 0], [-1, -1], [1, -1], [2, 0], [1, 1]];
  for (let rotation = 0; rotation < 6; rotation++) {
    let tileEdgeContainer = document.createElement("DIV");
    tileEdgeContainer.classList.add("tileedgecontainer");
    tileEdgeContainer.style.height = tileHeight + "px";
    tileEdgeContainer.style.width = tileWidth / 4 + "px";
    tileEdgeContainer.style.gridColumn = (i+1) + "/" + (i + 2);
    tileEdgeContainer.style.gridRow = (j+1) + "/" + (j + 5);
    tileEdgeContainer.style.transform = "rotate(" + 60*rotation + "deg)";
    let tileEdge = document.createElement("DIV");
    tileEdge.classList.add("tileedge");
    tileEdge.style.width = tileHeight / 5 + "px";
    tileEdge.style.height = tileHeight / 5 + "px";
    tileEdgeContainer.appendChild(tileEdge);
    grid.appendChild(tileEdgeContainer);
    let tileLoc = [x, y];
    let edgeLoc = [
      x + cornerOffsets[rotation][0], y + cornerOffsets[rotation][1],
      x + cornerOffsets[rotation+1][0], y + cornerOffsets[rotation+1][1],
    ];
    if (cornerOffsets[rotation][0] > cornerOffsets[rotation+1][0]) {
      edgeLoc = [edgeLoc[2], edgeLoc[3], edgeLoc[0], edgeLoc[1]];
    }
    tileEdge.onmouseenter = function() {
      if (tileMatrix[x] != null && tileMatrix[x][y] != null) {
        hoverTileEdge = {tile: tileMatrix[x][y], edge: edgeLoc, rotation: rotation};
        draw();
      }
    };
    tileEdge.onmouseleave = function() {
      if (hoverTileEdge != null && locationsEqual(hoverTileEdge.edge, edgeLoc) && hoverTileEdge.rotation == rotation) {
        hoverTileEdge = null;
        draw();
      }
    };
    tileEdge.onclick = function(event) { onClickTileEdge(event, tileLoc, edgeLoc, rotation); };
  }
}
function createEdgeBox(grid, xleft, yleft, xright, yright, i, j, width) {
  let elem = document.createElement("DIV");
  elem.classList.add("gridelem", "edgebox");
  elem.style.width = tileHeight / 5 + "px";
  elem.style.height = tileHeight / 5 + "px";
  elem.style.gridColumn = (i + 1) + "/" + (i + 1 + width);
  elem.style.gridRow = (j + 1) + "/" + (j + 2);
  elem.innerText = `${xleft}, ${yleft}, ${xright}, ${yright}`;
  elem.onmouseenter = function() { 
    if (edgeMatrix[(xleft+xright)/2] != null && edgeMatrix[(xleft+xright)/2][(yleft+yright)/2] != null) {
      hoverEdge = {location: [xleft, yleft, xright, yright], edge_type: edgeMatrix[(xleft+xright)/2][(yleft+yright)/2].edge_type};
      draw();
    }
  };
  elem.onmouseleave = function() {
    if (hoverEdge != null && locationsEqual(hoverEdge.location, [xleft, yleft, xright, yright])) {
      hoverEdge = null;
      draw();
    }
  };
  elem.onclick = function(event) { onClickEdge(event, [xleft, yleft, xright, yright]); };
  grid.appendChild(elem);
}
function createCornerBox(grid, x, y, i, j) {
  let elem = document.createElement("DIV");
  elem.classList.add("gridelem");
  elem.style.width = tileHeight / 5 + "px";
  elem.style.height = tileHeight / 5 + "px";
  elem.style.gridColumn = (i + 1) + "/" + (i + 2);
  elem.style.gridRow = (j + 1) + "/" + (j + 2);
  elem.innerText = `${x}, ${y}`;
  elem.onmouseenter = function() { hoverCorner = [x, y]; draw(); };
  elem.onmouseleave = function() {
    if (locationsEqual(hoverCorner, [x, y])) {
      hoverCorner = null;
      draw();
    }
  };
  elem.onclick = function(event) { onClickCorner(event, [x, y]); };
  grid.appendChild(elem);
}
